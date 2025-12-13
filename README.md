# SmartStreetAI — City Surveillance using AI Vision

SmartStreetAI is a web-based AI vision system that analyzes short street videos (≤30 seconds) to automatically detect civic governance issues such as **illegal parking** and **street crowding** using a YOLO-based object detection pipeline.  
The project emphasizes **practical engineering**, combining object detection, tracking, and rule-based reasoning with a lightweight web interface.

---

## Demo Video
 **YouTube Demo:** https://youtu.be/GhfO4Tu9Erg 

---

## Features Implemented

### 1. Illegal Parking Detection
- Detects vehicles (`car`, `bus`, `truck`, `motorbike`) using YOLO
- User-defined **Parking ROI**
- A vehicle is flagged as *illegally parked* if:
  - It remains inside the parking ROI
  - Pixel movement is below a threshold
  - Duration exceeds **2 seconds**
- Uses **centroid tracking** for temporal consistency
- Visual indicators:
  - 🟡 *Parking check*
  - 🔴 *Illegal parking*

### 2. Street Crowding Detection
- Detects people using YOLO (`person` class)
- Separate **Crowd ROI**
- Flags street crowding if:
  - Number of people exceeds a threshold
  - Crowd persists for a minimum duration
- Crowd warnings rendered directly on the annotated video

### 3. Annotated Video Output
- Bounding boxes with labels and confidence scores
- ROI overlays for parking and crowd zones
- Issue-specific warnings rendered on video frames
- Processed video available for **download** from frontend

### 4. Web-Based Interface
- Upload short street video
- Trigger AI analysis
- Download annotated output
- View structured detection summary

---

## Tech Stack & AI Models

### Backend
- Node.js
- Express.js

### Frontend
- HTML
- CSS
- Vanilla JavaScript (no frameworks)

### AI / Computer Vision
- Python
- OpenCV
- **Ultralytics YOLOv8**
  - Default: `yolov8n.pt`
  - Optional swap: `yolov8s.pt` (better accuracy, no code change)

### Supported Platforms
- Linux-friendly deployment
- Works on Windows / macOS / Linux (CPU)

---

##  How to Use the Project

### 1️. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/SmartStreetAI.git
cd SmartStreetAI
```

### 2️. Install Backend Dependencies
```bash
cd backend
npm install
```

### 3️. Install Python Dependencies
```bash
pip install ultralytics opencv-python numpy
```

### 4️. Generate ROIs (One-Time per Scene) (For parking Roi and Crowd Roi)
```bash
python python/roi_draw_parking.py --video sample.mp4
python python/roi_draw_crowd.py --video sample.mp4
```
ROIs are saved as:
```bash
python/roi_output/parking_roi.json
python/roi_output/crowd_roi.json
```

### 5️. Start the Server
```bash
node server.js
```

### 6️. Open in Browser
```bash
http://localhost:3000
```
Upload a video and run analysis.

##  Limitations
- Slow-moving traffic may be misclassified as parked  
- Top-down camera angles reduce vehicle shape clarity  
- Heavy occlusion affects people counting  
- CPU-only inference limits processing speed  
- COCO-pretrained model not optimized for parking-specific scenes  

---

##  Failure Scenarios
- Vehicles in traffic jams may appear stationary  
- People partially hidden by vehicles may be undercounted  
- ROI misplacement can affect detection accuracy  
- Sudden camera shake reduces tracking stability  

---

##  Improvements Possible
- Speed estimation instead of pixel movement  
- Lane and curb segmentation  
- Custom-trained dataset for illegal parking  
- Crowd density estimation instead of count-based rules  
- GPU / TensorRT acceleration  
- Re-identification (ReID) for long-term tracking  
