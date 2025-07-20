FROM --platform=linux/amd64 python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Run the main application
CMD ["python", "main.py"]
