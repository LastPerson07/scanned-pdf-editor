import os, uuid, json, shutil, cv2, fitz
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont
import pytesseract

app = FastAPI()

# Absolute Pathing for Docker/Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# MOUNTING (Order matters)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/data", StaticFiles(directory=UPLOAD_DIR), name="data")

# --- THE FIX FOR YOUR URL ---
@app.get("/")
async def serve_home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# --- OCR ENGINE ---
def get_ocr_data(img_path):
    img = Image.open(img_path)
    data = pytesseract.image_to_data(img, config='--psm 11', output_type=pytesseract.Output.DICT)
    words = []
    for i in range(len(data['text'])):
        if int(data['conf'][i]) > 35 and data['text'][i].strip():
            words.append({
                "text": data['text'][i],
                "x": data['left'][i], "y": data['top'][i],
                "w": data['width'][i], "h": data['height'][i]
            })
    return words

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    sid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, sid)
    os.makedirs(path, exist_ok=True)
    
    file_ext = file.filename.split('.')[-1].lower()
    save_path = os.path.join(path, f"orig.{file_ext}")
    
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # PDF to Image Logic
    if file_ext == 'pdf':
        doc = fitz.open(save_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_path = os.path.join(path, "work.png")
        pix.save(img_path)
    else:
        img_path = os.path.join(path, "work.png")
        with Image.open(save_path) as im:
            im.convert("RGB").save(img_path)

    return {
        "session_id": sid, 
        "image_url": f"/data/{sid}/work.png", 
        "words": get_ocr_data(img_path)
    }

@app.post("/edit")
async def edit(session_id: str = Form(...), edits: str = Form(...)):
    edit_list = json.loads(edits)
    path = os.path.join(UPLOAD_DIR, session_id)
    img_path = os.path.join(path, "work.png")
    
    img = cv2.imread(img_path)
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for e in edit_list:
        cv2.rectangle(mask, (e['x']-1, e['y']-1), (e['x']+e['w']+1, e['y']+e['h']+1), 255, -1)
    
    # Heal background
    healed = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    pil_img = Image.fromarray(cv2.cvtColor(healed, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    
    for e in edit_list:
        size = max(10, int(e['h'] * 0.85))
        try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except: font = ImageFont.load_default()
        draw.text((e['x'], e['y']), e['new_text'], fill=(0,0,0), font=font)
    
    out_path = os.path.join(path, "final.pdf")
    img_doc = fitz.open("pdf", pil_img.tobytes("jpeg", "RGB")) # Temporary fix for PDF conversion
    # Better PDF export
    pil_img.save(os.path.join(path, "temp.pdf"), resolution=100.0)
    
    return {"download_url": f"/data/{session_id}/temp.pdf"}
