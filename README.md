# Ace Exchange Rate Fetcher

This system fetches exchange rates from Ace Money Transfer and stores them in a database.

## Components

- `fetcher.py`: Core module for fetching exchange rates with rate limiting
- `main.py`: Processes exchange rates and inserts them into the database
- `scheduler.py`: Runs the system at randomized intervals
- `providers.json`: Configuration file with currency and country information

## Setup

### Local Installation

1. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install requests psycopg2-binary python-dotenv
```

2. Create a `.env` file with your database credentials:
```
DB_PASSWORD=your_database_password
```

### Docker Deployment

#### Using Docker Compose

1. Create a `.env` file with your database credentials:
```
DB_PASSWORD=your_database_password
```

2. Build and run with Docker Compose:
```bash
docker-compose up -d
```

3. Check the logs:
```bash
docker-compose logs -f
```

4. Stop the container:
```bash
docker-compose down
```

#### Using Plain Docker Commands

If you don't have docker-compose available, you can use these Docker commands:

1. Create a logs directory:
```bash
mkdir -p logs
```

2. Build the Docker image:
```bash
docker build -t ace-rate-fetcher .
```

3. Run the container:
```bash
docker run -d \
  --name ace-rate-fetcher \
  --restart always \
  -e DB_PASSWORD=your_database_password \
  -v $(pwd)/logs:/app/logs \
  ace-rate-fetcher
```

4. Check the logs:
```bash
docker logs -f ace-rate-fetcher
```

5. Stop the container:
```bash
docker stop ace-rate-fetcher
```

6. Remove the container:
```bash
docker rm ace-rate-fetcher
```

## Usage

### Running manually

```bash
python main.py
```

### Running the scheduler

The scheduler runs the rate fetcher at random intervals between 30-60 minutes:

```bash
./scheduler.py
```

or

```bash
python scheduler.py
```

The scheduler implements graceful shutdown handling via SIGTERM/SIGINT (Ctrl+C) signals.

## Logs

Logs are stored in the `logs` directory:

- `logs/rate_fetcher.log`: Contains detailed logs of the scheduler and rate fetching operations

When running with Docker, logs are mounted to your local logs directory.

## How it works

1. Reads provider information from `providers.json`
2. Fetches exchange rates for each currency pair
3. Uses rate limiting (5 seconds between requests) to avoid API restrictions
4. Inserts rates into the database with proper country operating flags
5. Scheduler runs at randomized intervals to avoid detection

## Database Schema

The system uses the `rate_providers` table with the following structure:

- `provider_name`: Name of the rate provider
- `provider_logo`: URL to the provider's logo
- `source_currency`: Source currency code (e.g., EUR)
- `destination_currency`: Destination currency code (e.g., GHS)
- `rate`: The exchange rate value
- `created_at`: Timestamp when the rate was fetched
- Country flags: Boolean fields for each operating country

## Docker Configuration

The Docker setup includes:

- Automatic container restart on server reboots (`restart: always`)
- Volume mounting for logs to persist data
- Health check to ensure the application is running properly
- Environment variable support for database credentials 