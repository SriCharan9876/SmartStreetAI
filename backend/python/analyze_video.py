#!/usr/bin/env python3
import argparse
import json
import sys
import time
from collections import defaultdict
import os

import cv2
from ultralytics import YOLO

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Input video path')
    parser.add_argument('--output', required=True, help='Output (annotated) video path')
    parser.add_argument('--model', default='yolov8n.pt', help='YOLO model weights (default: yolov8n.pt)')
    parser.add_argument('--roi_fraction', default=0.6, type=float, help='start of ROI as fraction of frame height')
    parser.add_argument('--stay_frames_threshold', default=30, type=int, help='frames threshold to count as "staying"')
    args = parser.parse_args()

    eprint(f"analyze_video.py start | input={args.input} output={args.output} model={args.model}")

    # Load model
    try:
        model = YOLO(args.model)
    except Exception as e:
        eprint("Failed to load YOLO model:", e)
        eprint(json.dumps({"error": "failed_to_load_model", "details": str(e)}))
        sys.exit(2)

    # Open video
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        eprint("Failed to open input:", args.input)
        eprint(json.dumps({"error": "failed_to_open_input", "path": args.input}))
        sys.exit(3)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)

    # Use AVI/XVID output for best cross-browser behavior with OpenCV
    # Ensure output path ends with .avi
    out_path = args.output
    if out_path.lower().endswith('.mp4'):
        out_path = out_path[:-4] + '.avi'

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    roi_y_start = int(height * args.roi_fraction)
    grid_size = max(40, int(min(width, height) * 0.05))
    seen_in_cell = defaultdict(int)
    cell_flagged_ts = {}
    issue_events = []
    vehicle_detections_total = 0
    frame_idx = 0
    start_time = time.time()

    # Common COCO vehicle labels (ultralytics names for COCO)
    vehicle_labels = {'car', 'bus', 'truck', 'motorbike', 'motorcycle'}

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            # draw ROI rectangle for visualization
            cv2.rectangle(frame, (0, roi_y_start), (width, height), (255, 0, 0), 2)

            # Run model inference on the frame
            results = model(frame)               # ultralytics returns a Results object (list-like)
            res0 = results[0] if isinstance(results, (list, tuple)) else results

            # If no detections, just write frame
            if not getattr(res0, 'boxes', None):
                out.write(frame)
                continue

            # Iterate over detected boxes
            for box in res0.boxes:
                # xyxy as [x1, y1, x2, y2]
                try:
                    xyxy = box.xyxy[0].tolist()
                except Exception:
                    # if structure differs, skip this box
                    continue

                x1, y1, x2, y2 = map(int, xyxy[:4])

                # class id and confidence
                try:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                except Exception:
                    # fallback defaults
                    cls_id = None
                    conf = 0.0

                label = res0.names[cls_id] if (hasattr(res0, 'names') and cls_id is not None and cls_id in res0.names) else str(cls_id)

                # draw bbox and label
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (x1, max(15, y1 - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

                # Vehicle-specific logic
                if label in vehicle_labels:
                    vehicle_detections_total += 1
                    cx = int((x1 + x2) / 2)
                    cy = int((y1 + y2) / 2)
                    cv2.circle(frame, (cx, cy), 3, (0, 0, 255), -1)

                    # Check ROI (no-parking zone)
                    if cy >= roi_y_start:
                        cell_x = cx // grid_size
                        cell_y = cy // grid_size
                        cell_key = (cell_x, cell_y)
                        seen_in_cell[cell_key] += 1

                        if seen_in_cell[cell_key] >= args.stay_frames_threshold:
                            last_flag_ts = cell_flagged_ts.get(cell_key, 0)
                            if time.time() - last_flag_ts > 5.0:
                                ev = {
                                    "frame": frame_idx,
                                    "type": "illegal_parking",
                                    "cell": {"x": cell_x, "y": cell_y},
                                    "message": f"Vehicle detected staying in ROI for >= {args.stay_frames_threshold} frames"
                                }
                                issue_events.append(ev)
                                cell_flagged_ts[cell_key] = time.time()

            # occasional decay of counts to avoid stale accumulation
            if frame_idx % 30 == 0:
                for k in list(seen_in_cell.keys()):
                    seen_in_cell[k] = max(0, seen_in_cell[k] - 2)
                    if seen_in_cell[k] == 0:
                        del seen_in_cell[k]

            # write annotated frame
            out.write(frame)

    except Exception as e:
        eprint("Runtime error:", str(e))
        eprint(json.dumps({"error": "runtime_failure", "details": str(e)}))
        cap.release()
        out.release()
        sys.exit(4)

    cap.release()
    out.release()
    elapsed = time.time() - start_time

    # Build summary - ensure output path returned is the actual file written
    summary = {
        "input": args.input,
        "output": os.path.abspath(out_path),
        "frame_count_processed": frame_idx,
        "fps_used": fps,
        "resolution": {"width": width, "height": height},
        "vehicle_detections_total": vehicle_detections_total,
        "issues": issue_events,
        "illegal_parking_count": sum(1 for e in issue_events if e.get("type") == "illegal_parking"),
        "processing_time_seconds": elapsed
    }

    # Print only this JSON to stdout
    print(json.dumps(summary))
    sys.stdout.flush()
    sys.exit(0)

if __name__ == '__main__':
    main()
