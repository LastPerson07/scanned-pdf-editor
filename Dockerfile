FROM python:3.9-slim

# Install system dependencies for OCR and Image Processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    # Using libgl1 instead of the deprecated libgl1-mesa-glx
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create the folder where PDFs will be processed
RUN mkdir -p uploads && chmod 777 uploads

# Use the port from render.yaml
EXPOSE 10000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
