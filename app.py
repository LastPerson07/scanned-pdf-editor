import os
import uuid
import json
import shutil
import cv2
import numpy as np
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/data", StaticFiles(directory=UPLOAD_DIR), name="data")

# --- Routes ---

@app.get("/")
async def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        sid = str(uuid.uuid4())
        session_path = os.path.join(UPLOAD_DIR, sid)
        os.makedirs(session_path, exist_ok=True)

        # Save Original
        ext = file.filename.split('.')[-1].lower()
        orig_path = os.path.join(session_path, f"original.{ext}")
        with open(orig_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Convert to Image for Processing
        work_img_path = os.path.join(session_path, "page.png")

        if ext == "pdf":
            doc = fitz.open(orig_path)
            page = doc[0] # Handle first page only for MVP
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Higher res for OCR
            pix.save(work_img_path)
        else:
            img = Image.open(orig_path).convert("RGB")
            img.save(work_img_path)

        # Run OCR
        words = get_ocr_words(work_img_path)

        return {
            "session_id": sid,
            "image_url": f"/data/{sid}/page.png",
            "words": words
        }
    except Exception as e:
        print(f"Upload Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/edit")
async def edit(session_id: str = Form(...), edits: str = Form(...)):
    try:
        edit_list = json.loads(edits)
        session_path = os.path.join(UPLOAD_DIR, session_id)
        img_path = os.path.join(session_path, "page.png")

        if not os.path.exists(img_path):
             return JSONResponse(status_code=404, content={"error": "Session expired"})

        # Load for Inpainting (OpenCV)
        img_cv = cv2.imread(img_path)
        mask = np.zeros(img_cv.shape[:2], dtype=np.uint8)

        # Create mask from edit regions
        for e in edit_list:
            x, y, w, h = int(e['x']), int(e['y']), int(e['w']), int(e['h'])
            # Dilate mask slightly to cover artifacts
            cv2.rectangle(mask, (x-2, y-2), (x+w+2, y+h+2), 255, -1)

        # Inpaint
        inpainted = cv2.inpaint(img_cv, mask, 3, cv2.INPAINT_TELEA)

        # Convert to PIL for Text Drawing
        img_pil = Image.fromarray(cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        # Attempt to load a good font
        try:
            # Common Linux path
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            default_font = ImageFont.truetype(font_path, 20)
        except:
            default_font = ImageFont.load_default()

        for e in edit_list:
            text = e['new_text']
            size = int(e.get('font_size', 20))
            color_hex = e.get('color', '#000000')
            
            # Parse color
            color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            
            try:
                font = ImageFont.truetype(font_path, size) if 'font_path' in locals() else ImageFont.load_default()
            except:
                font = ImageFont.load_default()

            # Centering logic
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            
            x, y, w, h = int(e['x']), int(e['y']), int(e['w']), int(e['h'])
            pos_x = x + (w - text_w) // 2
            pos_y = y + (h - text_h) // 2

            draw.text((pos_x, pos_y), text, fill=color, font=font)

        # Save as PDF
        output_pdf = os.path.join(session_path, "edited.pdf")
        img_pil.save(output_pdf, "PDF", resolution=150.0)

        return {"download_url": f"/data/{session_id}/edited.pdf"}
    
    except Exception as e:
        print(f"Edit Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- Helper ---
def get_ocr_words(img_path):
    import pytesseract
    
    img = cv2.imread(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Preprocessing for better OCR
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    data = pytesseract.image_to_data(thresh, output_type=pytesseract.Output.DICT)
    
    words = []
    for i in range(len(data['text'])):
        if int(data['conf'][i]) > 40 and data['text'][i].strip():
            words.append({
                "text": data['text'][i],
                "x": data['left'][i],
                "y": data['top'][i],
                "w": data['width'][i],
                "h": data['height'][i]
            })
    return words
