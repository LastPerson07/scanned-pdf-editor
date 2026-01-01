import os
import uuid
import json
import shutil
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

# Import our new robust processor
from image_processor import get_ocr_data, render_edits

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/data", StaticFiles(directory=UPLOAD_DIR), name="data")

@app.get("/")
async def home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        sid = str(uuid.uuid4())
        session_path = os.path.join(UPLOAD_DIR, sid)
        os.makedirs(session_path, exist_ok=True)

        ext = file.filename.split('.')[-1].lower()
        orig_path = os.path.join(session_path, f"original.{ext}")
        with open(orig_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        work_img_path = os.path.join(session_path, "page.png")

        # High Quality Conversion
        if ext == "pdf":
            doc = fitz.open(orig_path)
            page = doc[0]
            # Zoom = 2 (144 DPI) is usually a sweet spot for OCR vs Speed
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            pix.save(work_img_path)
        else:
            img = Image.open(orig_path).convert("RGB")
            img.save(work_img_path)

        # Process: Deskew -> OCR
        words = get_ocr_data(work_img_path)

        return {
            "session_id": sid,
            "image_url": f"/data/{sid}/page.png", # Returns the deskewed image!
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
        output_pdf = os.path.join(session_path, "edited.pdf")

        if not os.path.exists(img_path):
             return JSONResponse(status_code=404, content={"error": "Session expired"})

        render_edits(img_path, edit_list, output_pdf)

        return {"download_url": f"/data/{session_id}/edited.pdf"}
    
    except Exception as e:
        print(f"Edit Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
