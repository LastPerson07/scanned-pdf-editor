FROM python:3.9-slim

# Install system dependencies
# We replaced libgl1-mesa-glx with libgl1
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libgl1 \
    libglib2.0-0 \
    # Added for better PDF handling and image support
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure the upload directory exists with correct permissions
RUN mkdir -p uploads && chmod 777 uploads

# Use the port Render expects
EXPOSE 10000

# Start the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
