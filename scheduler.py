#!/usr/bin/env python3
import time
import random
import logging
import signal
import sys
import os
from datetime import datetime
import main  # Your existing main.py module

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"{log_dir}/rate_fetcher.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Graceful shutdown handling
should_run = True

def signal_handler(sig, frame):
    global should_run
    logging.info("Shutdown signal received, exiting after current cycle...")
    should_run = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def run_with_random_interval():
    """Run the FX rate fetcher at random intervals between 30 and 60 minutes."""
    global should_run
    
    logging.info("Ace rate provider fetcher scheduler started")
    if os.getenv("DRY_RUN", "0").lower() in ("1", "true", "yes", "on"):
        logging.info("Running in DRY-RUN mode (no DB writes)")
    
    while should_run:
        try:
            start_time = datetime.now()
            logging.info(f"Starting FX rate fetcher at {start_time}")
            
            # Run the main function
            main.main()
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            logging.info(f"Completed in {execution_time:.2f} seconds")
            
            if not should_run:
                break
                
            # Randomized wait time between 30-60 minutes (in seconds)
            wait_minutes = random.uniform(30, 60)
            wait_seconds = int(wait_minutes * 60)
            next_run = datetime.now().timestamp() + wait_seconds
            next_run_time = datetime.fromtimestamp(next_run)
            
            logging.info(f"Next run scheduled in {wait_minutes:.2f} minutes at {next_run_time}")
            
            # Sleep in shorter intervals to allow for clean shutdown
            sleep_interval = 10  # Check for shutdown signal every 10 seconds
            for _ in range(wait_seconds // sleep_interval):
                if not should_run:
                    break
                time.sleep(sleep_interval)
                
            # Sleep any remaining seconds
            if should_run and wait_seconds % sleep_interval:
                time.sleep(wait_seconds % sleep_interval)
                
        except Exception as e:
            logging.error(f"Error in scheduler: {e}")
            # Wait 5 minutes before retrying after an error
            time.sleep(300)

if __name__ == "__main__":
    run_with_random_interval() 
