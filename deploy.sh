#!/bin/bash
# Deploy script for Ace Rate Fetcher using plain Docker

set -e  # Exit on error

# Create logs directory
mkdir -p logs

# Check if .env file exists
if [ ! -f .env ]; then
  echo "Error: .env file not found!"
  echo "Please create a .env file with your database credentials (DB_PASSWORD=your_password)"
  exit 1
fi

# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Check if DB_PASSWORD is set
if [ -z "$DB_PASSWORD" ]; then
  echo "Error: DB_PASSWORD is not set in .env file!"
  exit 1
fi

# Check if the container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^ace-rate-fetcher$"; then
  echo "Stopping and removing existing container..."
  docker stop ace-rate-fetcher || true
  docker rm ace-rate-fetcher || true
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t ace-rate-fetcher .

# Run the container
echo "Starting container..."
docker run -d \
  --name ace-rate-fetcher \
  --restart always \
  -e DB_PASSWORD="$DB_PASSWORD" \
  -v "$(pwd)/logs:/app/logs" \
  ace-rate-fetcher

echo "Container started! To check logs, run: docker logs -f ace-rate-fetcher" 