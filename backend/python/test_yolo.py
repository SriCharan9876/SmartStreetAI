from ultralytics import YOLO
import cv2

# 1. Load model (weights are downloaded automatically first time)
model = YOLO("yolov8n.pt")  # 'n' = nano (small, fast)

# 2. Read an image
img = cv2.imread("test_street.jpg")

# 3. Run inference
results = model(img)

# 4. Visualize results on the image
for r in results:
    boxes = r.boxes
    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()  # bounding box
        cls_id = int(box.cls[0].item())        # class index
        conf = float(box.conf[0].item())       # confidence
        label = model.names[cls_id]            # class name, e.g. 'car'

        # Draw rectangle
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(img, f"{label} {conf:.2f}",
                    (int(x1), int(y1) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 1)

# 5. Save output image
cv2.imwrite("test_street_annotated.jpg", img)
print("Saved test_street_annotated.jpg")
