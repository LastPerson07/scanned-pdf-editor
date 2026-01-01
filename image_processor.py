import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import os

def deskew_image(image):
    """
    Detects text orientation and rotates the image to be perfectly horizontal.
    Crucial for OCR accuracy on scanned docs.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    
    # Threshold to get text pixels
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    
    # Get all point coordinates that are > 0
    coords = np.column_stack(np.where(thresh > 0))
    
    # Find the min area rectangle
    angle = cv2.minAreaRect(coords)[-1]
    
    # Fix angle calculation (cv2 returns different ranges based on version)
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # Rotate only if the angle is significant (> 0.5 degrees)
    if abs(angle) > 0.5:
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated
    
    return image

def preprocess_for_ocr(image):
    """
    Creates a high-contrast version of the image strictly for Tesseract to read.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Denoise (remove salt-and-pepper noise from scans)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    
    # Adaptive Thresholding (handles shadows/lighting gradients)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    return thresh

def get_ocr_data(image_path):
    """
    Full pipeline: Load -> Deskew -> Preprocess -> OCR
    """
    # Load original
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not load image")

    # 1. Deskew (Straighten)
    # We overwrite the image in memory because we want the UI to show the straight version too
    img = deskew_image(img)
    
    # Save the deskewed version back so the UI shows the straight image
    cv2.imwrite(image_path, img) 

    # 2. Create optimized OCR image
    processed_img = preprocess_for_ocr(img)

    # 3. Run Tesseract
    # --psm 11: Sparse text (better for forms/scattered words)
    # --oem 3: Default engine
    config = r'--oem 3 --psm 11'
    
    data = pytesseract.image_to_data(processed_img, config=config, output_type=pytesseract.Output.DICT)
    
    words = []
    n_boxes = len(data['text'])
    
    for i in range(n_boxes):
        # Filter out low confidence garbage
        conf = int(data['conf'][i])
        text = data['text'][i].strip()
        
        # Confidence > 30 and non-empty text
        if conf > 30 and text:
            words.append({
                "text": text,
                "x": data['left'][i],
                "y": data['top'][i],
                "w": data['width'][i],
                "h": data['height'][i],
                "conf": conf
            })
            
    return words

def render_edits(image_path, edits, output_path):
    """
    High-quality text replacement.
    """
    img_cv = cv2.imread(image_path)
    
    # 1. Inpainting (Erasing old text)
    mask = np.zeros(img_cv.shape[:2], dtype=np.uint8)
    for e in edits:
        x, y, w, h = int(e['x']), int(e['y']), int(e['w']), int(e['h'])
        # Expand mask slightly (dilation) to ensure no edges of old letters remain
        pad = 2
        cv2.rectangle(mask, (x-pad, y-pad), (x+w+pad, y+h+pad), 255, -1)
        
    inpainted = cv2.inpaint(img_cv, mask, 3, cv2.INPAINT_TELEA)
    
    # 2. Drawing New Text (PIL)
    img_pil = Image.fromarray(cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    
    # Font Logic - Try to get a real font
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arial.ttf"
    ]
    
    selected_font_path = None
    for p in font_paths:
        if os.path.exists(p):
            selected_font_path = p
            break
            
    for e in edits:
        text = e['new_text']
        # Default font size logic if missing
        orig_h = int(e['h'])
        font_size = int(e.get('font_size', max(12, orig_h * 0.8))) 
        
        if selected_font_path:
            font = ImageFont.truetype(selected_font_path, font_size)
        else:
            font = ImageFont.load_default()
            
        color_hex = e.get('color', '#000000')
        color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        # Calculate centering
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x, w = int(e['x']), int(e['w'])
        y, h = int(e['y']), int(e['h'])
        
        pos_x = x + (w - text_w) // 2
        pos_y = y + (h - text_h) // 2
        
        draw.text((pos_x, pos_y), text, fill=color, font=font)
        
    img_pil.save(output_path, "PDF", resolution=150.0)
    return output_path
