import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF
import os


def pdf_to_images(pdf_path: str, output_folder: str) -> list[str]:
    """
    Converts each page of a PDF to high-resolution PNG images.
    
    Args:
        pdf_path: Path to input PDF
        output_folder: Folder to save PNGs
    
    Returns:
        List of paths to generated page images
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    os.makedirs(output_folder, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    image_paths = []
    
    zoom = 2.0  # 2x resolution (300 DPI equivalent on most PDFs)
    mat = fitz.Matrix(zoom, zoom)
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=mat, alpha=False)  # No alpha for cleaner output
        output_filename = os.path.join(output_folder, f"page_{page_num + 1}.png")
        pix.save(output_filename)
        image_paths.append(output_filename)
    
    doc.close()
    return image_paths


def apply_edits_to_image(image_path: str, edits: list[dict], output_path: str) -> str:
    """
    Applies text edits to a single page image:
    - Inpaints (erases) original text areas
    - Draws new text with proper alignment and font
    
    Args:
        image_path: Input page image
        edits: List of edit dicts with keys: x, y, w, h, new_text, (optional: font_size, color)
        output_path: Where to save edited image
    
    Returns:
        Path to saved output image
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Load with OpenCV for inpainting
    cv_img = cv2.imread(image_path)
    if cv_img is None:
        raise ValueError(f"Failed to load image with OpenCV: {image_path}")
    
    # Create combined mask for all edits
    mask = np.zeros(cv_img.shape[:2], dtype=np.uint8)
    
    for edit in edits:
        x, y, w, h = edit['x'], edit['y'], edit['w'], edit['h']
        # Slightly enlarge mask to fully cover old text
        margin = 4
        cv2.rectangle(
            mask,
            (max(0, x - margin), max(0, y - margin)),
            (x + w + margin, y + h + margin),
            255,
            -1
        )
    
    # Inpaint all erased areas at once (more seamless)
    if np.any(mask):
        cv_img = cv2.inpaint(cv_img, mask, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    
    # Convert to PIL for high-quality text rendering
    pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    
    # Use reliable font available in Docker (DejaVuSans)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    fallback_font = None
    
    for edit in edits:
        new_text = edit.get('new_text', '')
        if not new_text:
            continue
            
        x, y, w, h = edit['x'], edit['y'], edit['w'], edit['h']
        font_size = edit.get('font_size', int(h * 0.8))
        font_size = max(8, font_size)  # Minimum readable size
        
        color = edit.get('color', '#000000')
        color_rgb = tuple(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        
        try:
            if fallback_font is None:
                font = ImageFont.truetype(font_path, font_size)
            else:
                font = fallback_font
        except IOError:
            if fallback_font is None:
                fallback_font = ImageFont.load_default()
            font = fallback_font
        
        # Center text in bounding box
        bbox = draw.textbbox((0, 0), new_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        pos_x = x + (w - text_w) // 2
        pos_y = y + (h - text_h) // 2
        
        draw.text((pos_x, pos_y), new_text, fill=color_rgb, font=font)
    
    pil_img.save(output_path, "PNG")
    return output_path


def images_to_pdf(image_paths: list[str], output_pdf_path: str) -> str:
    """
    Combines multiple edited page images back into a single PDF.
    
    Args:
        image_paths: List of edited PNG page paths
        output_pdf_path: Output PDF path
    
    Returns:
        Path to saved PDF
    """
    if not image_paths:
        raise ValueError("No images provided to convert to PDF")
    
    doc = fitz.open()
    
    for img_path in image_paths:
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Image not found during PDF creation: {img_path}")
            
        img_doc = fitz.open(img_path)
        rect = img_doc[0].rect
        
        # Convert image to PDF bytes
        pdf_bytes = img_doc.convert_to_pdf()
        img_doc.close()
        
        img_pdf = fitz.open("pdf", pdf_bytes)
        
        # Create new page with exact image dimensions
        page = doc.new_page(width=rect.width, height=rect.height)
        page.show_pdf_page(rect, img_pdf, 0)
    
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    doc.save(output_pdf_path)
    doc.close()
    
    return output_pdf_path
