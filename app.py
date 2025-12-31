import os, uuid, json, shutil, cv2, fitz
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont
import pytesseract

app = FastAPI()

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Static Files Connection
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/data", StaticFiles(directory=UPLOAD_DIR), name="data")

# --- OCR ENGINE ---
def get_ocr_data(img_path):
    try:
        img = Image.open(img_path)
        # psm 11 detects sparse text blocks; essential for scanned forms
        data = pytesseract.image_to_data(img, config='--psm 11', output_type=pytesseract.Output.DICT)
        words = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 30 and data['text'][i].strip():
                words.append({
                    "text": data['text'][i],
                    "x": data['left'][i], "y": data['top'][i],
                    "w": data['width'][i], "h": data['height'][i]
                })
        return words
    except Exception as e:
        print(f"OCR Error: {e}")
        return []

# --- ROUTES ---
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "static/index.html"))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    session_path = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_path, exist_ok=True)
    
    # Save original
    file_ext = file.filename.split('.')[-1].lower()
    input_path = os.path.join(session_path, f"input.{file_ext}")
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # PDF to Image Conversion
    if file_ext == 'pdf':
        doc = fitz.open(input_path)
        page = doc.load_page(0) # Logic for Page 1
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_filename = "page_0.png"
        img_path = os.path.join(session_path, img_filename)
        pix.save(img_path)
    else:
        img_filename = f"page_0.{file_ext}"
        img_path = os.path.join(session_path, img_filename)
        shutil.copy(input_path, img_path)

    words = get_ocr_data(img_path)
    return {
        "session_id": session_id, 
        "image_url": f"/data/{session_id}/{img_filename}", 
        "words": words
    }

@app.post("/edit")
async def process_edits(session_id: str = Form(...), edits: str = Form(...)):
    edit_data = json.loads(edits)
    session_path = os.path.join(UPLOAD_DIR, session_id)
    img_path = os.path.join(session_path, "page_0.png")
    
    # 1. Image Inpainting (Erase Text)
    img = cv2.imread(img_path)
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for e in edit_data:
        # Create a slightly larger mask to ensure clean erasure
        cv2.rectangle(mask, (e['x']-2, e['y']-2), (e['x']+e['w']+2, e['y']+e['h']+2), 255, -1)
    
    # Telea algorithm fills the gap based on surrounding pixels
    inpainted = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    
    # 2. PIL Drawing (New Text)
    inpainted_rgb = cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(inpainted_rgb)
    draw = ImageDraw.Draw(pil_img)
    
    # System font fallback for Render/Linux
    try: font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    except: font_path = None

    for e in edit_data:
        f_size = max(12, int(e['h'] * 0.85))
        try: font = ImageFont.truetype(font_path, f_size) if font_path else ImageFont.load_default()
        except: font = ImageFont.load_default()
        draw.text((e['x'], e['y']), e['new_text'], fill=(0,0,0), font=font)
    
    # 3. Export to PDF
    out_img_path = os.path.join(session_path, "edited.png")
    pil_img.save(out_img_path)
    
    pdf_path = os.path.join(session_path, "final_export.pdf")
    img_doc = fitz.open(out_img_path)
    pdf_bytes = img_doc.convert_to_pdf()
    final_pdf = fitz.open("pdf", pdf_bytes)
    final_pdf.save(pdf_path)
    
    return {"download_url": f"/data/{session_id}/final_export.pdf"}