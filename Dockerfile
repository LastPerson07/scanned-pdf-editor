FROM python:3.9-slim

# Install system dependencies: Tesseract OCR + languages + fonts + OpenCV libs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \  # Add more languages if needed, e.g. tesseract-ocr-fra
    libtesseract-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    fonts-dejavu-core \  # Provides DejaVuSans.ttf
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create uploads folder
RUN mkdir -p uploads && chmod 777 uploads

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
