import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
import os

def pdf_to_images(pdf_path, output_folder):
    """Converts PDF to high-res images for editing."""
    doc = fitz.open(pdf_path)
    image_paths = []
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for quality
        output_filename = os.path.join(output_folder, f"page_{page_num}.png")
        pix.save(output_filename)
        image_paths.append(output_filename)
        
    return image_paths

def apply_edits_to_image(image_path, edits, output_path):
    """
    1. Reads image.
    2. For each edit: Inpaints (erases) old area -> Draws new text.
    3. Saves result.
    """
    # 1. Load Image for OpenCV (Inpainting)
    cv_img = cv2.imread(image_path)
    
    # 2. Inpaint (Erase) Loop
    for edit in edits:
        x, y, w, h = edit['x'], edit['y'], edit['w'], edit['h']
        
        # Create a mask for the text box area
        mask = np.zeros(cv_img.shape[:2], dtype=np.uint8)
        # Dilate mask slightly to ensure all pixels of the letter are covered
        cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
        
        # Inpaint: Replaces the text with surrounding background pixels
        cv_img = cv2.inpaint(cv_img, mask, 3, cv2.INPAINT_TELEA)

    # Convert back to PIL for high-quality text drawing
    cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(cv_img)
    draw = ImageDraw.Draw(pil_img)

    # 3. Text Drawing Loop
    for edit in edits:
        new_text = edit['new_text']
        x, y, w, h = edit['x'], edit['y'], edit['w'], edit['h']
        
        # Dynamic font scaling
        font_size = int(h * 0.8) # 80% of box height
        try:
            # Use a standard font. On Linux/Docker, paths might vary.
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        # Draw text (color black usually fits scanned docs)
        # Improve this by detecting average color of region if needed
        draw.text((x, y + (h*0.1)), new_text, fill=(0, 0, 0), font=font)

    pil_img.save(output_path)
    return output_path

def images_to_pdf(image_paths, output_pdf_path):
    """Combines processed images back into a PDF."""
    doc = fitz.open()
    for img_path in image_paths:
        img = fitz.open(img_path)
        rect = img[0].rect
        pdfbytes = img.convert_to_pdf()
        img.close()
        imgPDF = fitz.open("pdf", pdfbytes)
        page = doc.new_page(width = rect.width, height = rect.height)
        page.show_pdf_page(rect, imgPDF, 0)
    
    doc.save(output_pdf_path)