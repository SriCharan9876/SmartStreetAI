#!/usr/bin/env python3
import argparse
import json
import sys
import time
import os
import math

import cv2
import numpy as np
from ultralytics import YOLO

# ------------------------------
# stderr logging (Node-safe)
# ------------------------------
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# ------------------------------
# Simple Centroid Tracker (UNCHANGED)
# ------------------------------
class CentroidTracker:
    def __init__(self, max_disappeared=15, max_distance=80):
        self.next_id = 1
        self.objects = {}
        self.seen_count = {}
        self.disappeared = {}
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def update(self, detections):
        if not detections:
            for oid in list(self.objects.keys()):
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    self._deregister(oid)
            return self.objects

        if not self.objects:
            for d in detections:
                self._register(d)
            return self.objects

        used = set()
        for oid, (ox, oy) in list(self.objects.items()):
            best, best_dist = None, None
            for d in detections:
                if d in used:
                    continue
                dist = math.hypot(ox - d[0], oy - d[1])
                if dist < self.max_distance and (best_dist is None or dist < best_dist):
                    best, best_dist = d, dist

            if best:
                self.objects[oid] = best
                self.seen_count[oid] += 1
                self.disappeared[oid] = 0
                used.add(best)
            else:
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    self._deregister(oid)

        for d in detections:
            if d not in used:
                self._register(d)

        return self.objects

    def _register(self, centroid):
        oid = self.next_id
        self.next_id += 1
        self.objects[oid] = centroid
        self.seen_count[oid] = 1
        self.disappeared[oid] = 0

    def _deregister(self, oid):
        self.objects.pop(oid, None)
        self.seen_count.pop(oid, None)
        self.disappeared.pop(oid, None)

# ------------------------------
# Main
# ------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--model', default='yolov8n.pt')
    parser.add_argument('--parking_roi', default='python/roi_output/parking_roi.json')
    parser.add_argument('--crowd_roi', default='python/roi_output/crowd_roi.json')
    parser.add_argument('--conf', type=float, default=0.35)
    parser.add_argument('--min_seen_frames', type=int, default=3)
    args = parser.parse_args()

    # -------- thresholds --------
    PARKING_TIME_THRESHOLD = 2.0
    MOVEMENT_THRESHOLD = 20

    CROWD_COUNT_THRESHOLD = 5
    CROWD_TIME_THRESHOLD = 2.0

    model = YOLO(args.model)

    # -------- Load ROIs --------
    parking_roi = None
    crowd_roi = None

    if os.path.exists(args.parking_roi):
        with open(args.parking_roi) as f:
            parking_roi = np.array(json.load(f)["points"], dtype=np.int32)

    if os.path.exists(args.crowd_roi):
        with open(args.crowd_roi) as f:
            crowd_roi = np.array(json.load(f)["points"], dtype=np.int32)

    cap = cv2.VideoCapture(args.input)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path = args.output.replace(".mp4", ".avi")
    out = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'XVID'), fps, (w, h))

    tracker = CentroidTracker()

    # -------- parking state (UNCHANGED) --------
    first_seen_ts = {}
    last_position = {}
    stationary_time = {}
    flagged_ids = set()
    last_boxes = {}

    # -------- crowd state --------
    crowd_start_ts = None
    crowd_reported = False

    issue_events = []
    frame_idx = 0
    start_time = time.time()
    total_vehicle_detections = 0
    max_people_detected = 0

    vehicle_labels = {'car', 'bus', 'truck', 'motorbike', 'motorcycle'}

    # ==============================
    # Frame loop
    # ==============================
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        last_boxes.clear()

        results = model(frame)
        res0 = results[0]

        vehicle_detections = []
        people_count = 0

        if res0.boxes:
            for box in res0.boxes:
                conf = float(box.conf[0])
                if conf < args.conf:
                    continue

                cls_id = int(box.cls[0])
                label = res0.names[cls_id]
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1+x2)//2, (y1+y2)//2

                # -------- VEHICLES --------
                if label in vehicle_labels:
                    total_vehicle_detections += 1

                    if parking_roi is not None and cv2.pointPolygonTest(parking_roi, (cx,cy), False) >= 0:
                        vehicle_detections.append((cx,cy))
                        last_boxes[(cx,cy)] = (x1,y1,x2,y2,label,conf)
                    else:
                        cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
                        cv2.putText(frame,f"{label} {conf:.2f}",
                                    (x1,y1-5),cv2.FONT_HERSHEY_SIMPLEX,
                                    0.45,(0,255,0),1)

                # -------- PEOPLE (crowd) --------
                if label == "person":
                    if crowd_roi is not None and cv2.pointPolygonTest(crowd_roi,(cx,cy),False)>=0:
                        people_count += 1
                        cv2.rectangle(frame,(x1,y1),(x2,y2),(255,165,0),2)
                        cv2.putText(frame,f"person {conf:.2f}",
                                    (x1,y1-5),cv2.FONT_HERSHEY_SIMPLEX,
                                    0.45,(255,165,0),1)

        # -------- Illegal parking (UNCHANGED) --------
        tracked = tracker.update(vehicle_detections)
        now = time.time()

        for oid,(cx,cy) in tracked.items():
            if tracker.seen_count[oid] < args.min_seen_frames:
                continue

            nearest, best = None, None
            for (px,py),box in last_boxes.items():
                d = math.hypot(px-cx, py-cy)
                if best is None or d < best:
                    nearest, best = box, d
            if not nearest:
                continue

            x1,y1,x2,y2,label,conf = nearest

            if oid not in first_seen_ts:
                first_seen_ts[oid] = now
                last_position[oid] = (cx,cy)
                stationary_time[oid] = 0
                continue

            px,py = last_position[oid]
            movement = math.hypot(cx-px, cy-py)
            dt = now - first_seen_ts[oid]

            if movement < MOVEMENT_THRESHOLD:
                stationary_time[oid] += dt
            else:
                stationary_time[oid] = 0

            first_seen_ts[oid] = now
            last_position[oid] = (cx,cy)

            if stationary_time[oid] >= PARKING_TIME_THRESHOLD:
                if oid not in flagged_ids:
                    flagged_ids.add(oid)
                    issue_events.append({
                        "type":"illegal_parking",
                        "vehicle_id":oid,
                        "duration_seconds":round(stationary_time[oid],2)
                    })

                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,0,255),2)
                cv2.putText(frame,f"ILLEGAL PARKING | ID {oid}",
                            (x1,y1-8),cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,(0,0,255),2)
            else:
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,255),2)
                cv2.putText(frame,"PARKING CHECK…",
                            (x1,y1-8),cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,(0,255,255),2)

        # -------- Crowd logic --------
        max_people_detected = max(max_people_detected, people_count)

        if people_count >= CROWD_COUNT_THRESHOLD:
            if crowd_start_ts is None:
                crowd_start_ts = now
            elif now - crowd_start_ts >= CROWD_TIME_THRESHOLD and not crowd_reported:
                crowd_reported = True
                issue_events.append({
                    "type":"street_crowding",
                    "people_count":people_count,
                    "duration_seconds":round(now-crowd_start_ts,2)
                })
                cv2.putText(frame,"STREET CROWDING",
                            (40,50),cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,(0,0,255),3)
        else:
            crowd_start_ts = None
            crowd_reported = False

        # -------- Draw ROIs --------
        if parking_roi is not None:
            cv2.polylines(frame,[parking_roi],True,(255,0,0),2)
        if crowd_roi is not None:
            cv2.polylines(frame,[crowd_roi],True,(255,165,0),2)

        out.write(frame)

    cap.release()
    out.release()

    elapsed = time.time() - start_time

    summary = {
        "input": os.path.abspath(args.input),
        "output": os.path.abspath(out_path),
        "frame_count_processed": frame_idx,
        "vehicles": {
            "total_detections": total_vehicle_detections,
            "illegal_parked": len(flagged_ids)
        },
        "crowd": {
            "max_people_detected": max_people_detected
        },
        "issues": issue_events,
        "processing_time_seconds": round(elapsed,2)
    }

    print(json.dumps(summary))
    sys.exit(0)

if __name__ == "__main__":
    main()
