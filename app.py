import os, uuid, json, shutil, cv2, fitz
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont
import pytesseract

app = FastAPI()

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory=UPLOAD_DIR), name="data")

# --- CORE API: OCR READING ---
def get_ocr_data(img_path):
    img = Image.open(img_path)
    # Using psm 11 to find sparse text in scanned documents
    data = pytesseract.image_to_data(img, config='--psm 11', output_type=pytesseract.Output.DICT)
    words = []
    for i in range(len(data['text'])):
        if int(data['conf'][i]) > 40 and data['text'][i].strip():
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
    
    # If PDF, convert first page to high-res image
    if file_ext == 'pdf':
        doc = fitz.open(save_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_path = os.path.join(path, "work.png")
        pix.save(img_path)
    else:
        img_path = save_path

    return {"session_id": sid, "image_url": f"/data/{sid}/{os.path.basename(img_path)}", "words": get_ocr_data(img_path)}

# --- CORE API: SEAMLESS EDITING ---
@app.post("/edit")
async def edit(session_id: str = Form(...), edits: str = Form(...)):
    edit_list = json.loads(edits)
    path = os.path.join(UPLOAD_DIR, session_id)
    img_path = os.path.join(path, "work.png")
    
    # 1. Image Healing (Inpainting)
    img = cv2.imread(img_path)
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for e in edit_list:
        # Create a mask for the old text
        cv2.rectangle(mask, (e['x'], e['y']), (e['x']+e['w'], e['y']+e['h']), 255, -1)
    
    # Fill the mask using surrounding paper texture
    healed = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    
    # 2. Text Overlay
    healed_rgb = cv2.cvtColor(healed, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(healed_rgb)
    draw = ImageDraw.Draw(pil_img)
    
    for e in edit_list:
        font_size = max(12, int(e['h'] * 0.9))
        try: font = ImageFont.truetype("DejaVuSans.ttf", font_size)
        except: font = ImageFont.load_default()
        draw.text((e['x'], e['y']), e['new_text'], fill=(0,0,0), font=font)
    
    out_path = os.path.join(path, "final.pdf")
    pil_img.save(os.path.join(path, "edited.png"))
    
    # Convert back to PDF
    img_doc = fitz.open(os.path.join(path, "edited.png"))
    pdf_bytes = img_doc.convert_to_pdf()
    with open(out_path, "wb") as f: f.write(pdf_bytes)
    
    return {"download_url": f"/data/{session_id}/final.pdf"}
