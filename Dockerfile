FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Make the scheduler script executable
RUN chmod +x scheduler.py

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the scheduler
CMD ["./scheduler.py"] 