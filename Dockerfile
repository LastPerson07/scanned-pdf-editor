FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
  tesseract-ocr \
  libtesseract-dev \
  libgl1-mesa-glx \
  libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directory for uploads
RUN mkdir -p uploads

EXPOSE 10000

# Run using Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]