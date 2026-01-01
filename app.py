import os
import uuid
import shutil
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List

# Third-party imports
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageFont, ImageDraw

# Initialize FastAPI
app = FastAPI(title="ScanEdit Pro Modern API")

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ThreadPool for CPU-bound tasks (OCR, Image Processing)
# This prevents the main async event loop from being blocked
ocr_executor = ThreadPoolExecutor(max_workers=4)

# --- Helper Functions (CPU Bound) ---

def process_image_sync(file_path: str, session_id: str):
    """
    Synchronous function to be run in a separate thread.
    Performs Deskew and OCR.
    """
    try:
        # 1. Load Image
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError("Could not read image")

        # 2. Pre-processing (Simple Deskew)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        coords = np.column_stack(np.where(gray > 0))
        angle = cv2.minAreaRect(coords)[-1]
        
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        # Save processed image for the frontend
        processed_path = os.path.join(UPLOAD_DIR, session_id, "processed.png")
        cv2.imwrite(processed_path, rotated)

        # 3. OCR with Data Extraction
        # Output dict includes: left, top, width, height, conf, text
        data = pytesseract.image_to_data(rotated, output_type=pytesseract.Output.DICT)
        
        words = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(data['conf'][i]) > 30 and data['text'][i].strip():
                words.append({
                    "id": str(uuid.uuid4()),
                    "text": data['text'][i],
                    "x": data['left'][i],
                    "y": data['top'][i],
                    "w": data['width'][i],
                    "h": data['height'][i],
                    "conf": data['conf'][i]
                })
                
        return {"image_url": f"/data/{session_id}/processed.png", "words": words}

    except Exception as e:
        print(f"Error in worker: {e}")
        raise e

# --- Async Endpoints ---

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Handles file upload asynchronously.
    Offloads OCR to a thread pool.
    """
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    file_path = os.path.join(session_dir, file.filename)
    
    # Async file write
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Get the running event loop
        loop = asyncio.get_event_loop()
        
        # Run the CPU-heavy OCR in the executor
        result = await loop.run_in_executor(
            ocr_executor, 
            process_image_sync, 
            file_path, 
            session_id
        )
        
        return JSONResponse(content={"status": "success", "session_id": session_id, **result})
        
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(session_dir, ignore_errors=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.mount("/data", StaticFiles(directory=UPLOAD_DIR), name="data")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
