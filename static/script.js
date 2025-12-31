# Inside your app.py edit route
@app.post("/edit")
async def process_edits(session_id: str = Form(...), edits: str = Form(...)):
    edit_data = json.loads(edits)
    session_path = os.path.join(UPLOAD_DIR, session_id)
    img_path = os.path.join(session_path, "page_0.png")
    
    img = cv2.imread(img_path)
    # 1. SMART INPAINTING (The magic "Anti-White-Box" logic)
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for e in edit_data:
        # We target the exact bounding box for erasure
        cv2.rectangle(mask, (e['x'], e['y']), (e['x']+e['w'], e['y']+e['h']), 255, -1)
    
    # This "heals" the background by copying neighboring paper texture
    inpainted = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
    
    # 2. RENDER NEW TEXT
    inpainted_rgb = cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(inpainted_rgb)
    draw = ImageDraw.Draw(pil_img)
    
    for e in edit_data:
        # Font scaling logic to match the original scan size
        size = max(10, int(e['h'] * 0.9)) 
        try: font = ImageFont.truetype("DejaVuSans.ttf", size)
        except: font = ImageFont.load_default()
        
        # Overlaying the new text onto the healed background
        draw.text((e['x'], e['y']), e['new_text'], fill=(0,0,0), font=font)
    
    # ... save and export as PDF
