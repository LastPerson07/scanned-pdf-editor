import os, uuid, json, shutil
import cv2
import numpy as np
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont

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

def get_ocr_words(img_path):
    import pytesseract
    from PIL import Image
    img = Image.open(img_path)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    words = []
    for i in range(len(data["text"])):
        if int(data["conf"][i]) > 30 and data["text"][i].strip():
            words.append({
                "text": data["text"][i].strip(),
                "x": data["left"][i],
                "y": data["top"][i],
                "w": data["width"][i],
                "h": data["height"][i]
            })
    return words

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    sid = str(uuid.uuid4())
    session_path = os.path.join(UPLOAD_DIR, sid)
    os.makedirs(session_path, exist_ok=True)

    orig_path = os.path.join(session_path, f"original.{file.filename.split('.')[-1]}")
    with open(orig_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    work_img_path = os.path.join(session_path, "page.png")

    if file.filename.lower().endswith(".pdf"):
        doc = fitz.open(orig_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # High quality
        pix.save(work_img_path)
    else:
        img = Image.open(orig_path).convert("RGB")
        img.save(work_img_path)

    words = get_ocr_words(work_img_path)

    return {
        "session_id": sid,
        "image_url": f"/data/{sid}/page.png",
        "words": words
    }

@app.post("/edit")
async def edit(session_id: str = Form(...), edits: str = Form(...)):
    edit_list = json.loads(edits)
    session_path = os.path.join(UPLOAD_DIR, session_id)
    img_path = os.path.join(session_path, "page.png")

    img = cv2.imread(img_path)
    mask = np.zeros(img.shape[:2], dtype=np.uint8)

    for e in edit_list:
        x, y, w, h = e['x'], e['y'], e['w'], e['h']
        cv2.rectangle(mask, (x-2, y-2), (x+w+2, y+h+2), 255, -1)

    inpainted = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    pil_img = Image.fromarray(cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

    for e in edit_list:
        font_size = e.get('font_size', int(e['h'] * 0.8))
        color = tuple(int(e['color'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except:
            font = ImageFont.load_default()

        text = e['new_text']
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pos_x = e['x'] + (e['w'] - text_w) // 2
        pos_y = e['y'] + (e['h'] - text_h) // 2

        draw.text((pos_x, pos_y), text, fill=color, font=font)

    output_pdf = os.path.join(session_path, "edited.pdf")
    pil_img.save(output_pdf, "PDF", resolution=100.0)

    return {"download_url": f"/data/{session_id}/edited.pdf"}
