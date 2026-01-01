import pytesseract
from PIL import Image
import os

# Optional: Explicitly set Tesseract path if needed (uncomment if issues occur)
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def extract_text_data(image_path: str, min_confidence: int = 30, lang: str = 'eng') -> list[dict]:
    """
    Runs OCR on an image and returns a list of detected words with bounding boxes and confidence.

    Args:
        image_path (str): Path to the image file (PNG, JPG, etc.)
        min_confidence (int): Minimum confidence level (0-100) to include a word. Default: 30
        lang (str): Language code for Tesseract (e.g., 'eng', 'fra', 'deu'). Default: 'eng'

    Returns:
        list[dict]: List of dictionaries containing text and bounding box info:
                    {'text': str, 'x': int, 'y': int, 'w': int, 'h': int, 'conf': int}
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        img = Image.open(image_path)
        
        # Recommended config for better word-level detection
        custom_config = r'--oem 3 --psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?:;()"\'-'

        data = pytesseract.image_to_data(
            img,
            lang=lang,
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )

        words = []
        n_boxes = len(data['text'])

        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])

            if conf > min_confidence and text:
                words.append({
                    "text": text,
                    "x": data['left'][i],
                    "y": data['top'][i],
                    "w": data['width'][i],
                    "h": data['height'][i],
                    "conf": conf
                })

        return words

    except Exception as e:
        raise RuntimeError(f"OCR failed on {image_path}: {str(e)}")
