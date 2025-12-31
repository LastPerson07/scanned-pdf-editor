import pytesseract
from PIL import Image

# Ensure Tesseract is in your PATH or set it here
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' 

def extract_text_data(image_path):
    """
    Runs OCR on an image and returns a list of words with their bounding boxes.
    """
    img = Image.open(image_path)
    # data includes: left, top, width, height, conf, text
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    
    words = []
    n_boxes = len(data['text'])
    
    for i in range(n_boxes):
        # Filter out empty text or low confidence garbage
        if int(data['conf'][i]) > 0 and data['text'][i].strip():
            words.append({
                "text": data['text'][i],
                "x": data['left'][i],
                "y": data['top'][i],
                "w": data['width'][i],
                "h": data['height'][i],
                "conf": data['conf'][i]
            })
    return words