import cv2, json, sys, os
import numpy as np

if len(sys.argv) < 2:
    print("Usage: python draw_roi.py <video_path>")
    sys.exit(1)

video_path = sys.argv[1]
cap = cv2.VideoCapture(video_path)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Failed to read video")
    sys.exit(1)

points = []
clone = frame.copy()

WIN_NAME = "Draw ROI | Left click points | S=save | R=reset"
MAX_W, MAX_H = 1200, 700   # fit screen nicely

scale = min(MAX_W / clone.shape[1], MAX_H / clone.shape[0])
if scale > 1.0:
    scale = 1.0  # never upscale

def redraw():
    img = clone.copy()

    if len(points) > 1:
        cv2.polylines(img, [np.array(points)], True, (0,255,0), 2)
    for p in points:
        cv2.circle(img, p, 5, (0,255,0), -1)

    display = cv2.resize(
        img,
        (int(img.shape[1] * scale), int(img.shape[0] * scale))
    )

    cv2.imshow(WIN_NAME, display)

def mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        # convert display → original coordinates
        ox = int(x / scale)
        oy = int(y / scale)
        points.append((ox, oy))
        redraw()

cv2.namedWindow(WIN_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(
    WIN_NAME,
    int(clone.shape[1] * scale),
    int(clone.shape[0] * scale)
)
cv2.setMouseCallback(WIN_NAME, mouse)
redraw()


while True:
    key = cv2.waitKey(0) & 0xFF
    if key == ord('s'):
        os.makedirs("python/roi_output", exist_ok=True)
        with open("python/roi_output/parking_roi.json", "w") as f:
            json.dump({"points": points}, f)
        print("Saved ROI → python/roi_output/parking_roi.json")
        break
    elif key == ord('r'):
        points.clear()
        redraw()
    elif key == 27:
        break

cv2.destroyAllWindows()
