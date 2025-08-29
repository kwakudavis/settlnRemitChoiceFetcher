from fetcher import get_exchange_rate, get_all_rates, load_providers
import json
from datetime import datetime
import os
from datetime import datetime
import psycopg2
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

# PostgreSQL connection
def get_db_connection():
    password = os.getenv("DB_PASSWORD")
    
    # Use the direct Supabase connection string format
    conn_string = f"postgresql://postgres.yuyfrpclwmtjlxdymqdy:{urllib.parse.quote_plus(password)}@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"
    
    return psycopg2.connect(conn_string)

def parse_timestamp(dt=None):
    """Format current timestamp or provided datetime"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def insert_rate(cursor, rate, provider_info):
    """Insert rate into the database, with UPSERT behavior"""
    # Base fields
    provider_name = rate.get("provider_name")
    provider_logo = provider_info.get("logo")
    source_currency = rate.get("source_currency")
    destination_currency = rate.get("destination_currency")
    rate_value = rate.get("rate")
    created_at = rate.get("created_at")

    # Get all operating countries from provider_info
    all_operating_countries = set()
    for currency_info in provider_info.get("sending_currencies", []):
        for country in currency_info.get("operating_countries", []):
            all_operating_countries.add(country.lower())
    
    # Create country flags dict - only True for countries operating with this source currency
    country_flags = {}
    operating_countries = []
    for currency_info in provider_info.get("sending_currencies", []):
        if currency_info.get("sending_currency") == source_currency:
            operating_countries = [country.lower() for country in currency_info.get("operating_countries", [])]
    
    # Set flags for all countries
    for country in all_operating_countries:
        country_flags[country] = country in operating_countries

    # Prepare columns and values
    base_columns = ["provider_name", "provider_logo", "source_currency", "destination_currency", "rate", "created_at"]
    base_values = [provider_name, provider_logo, source_currency, destination_currency, rate_value, created_at]

    # Add country columns and values
    country_columns = list(country_flags.keys())
    country_values = [country_flags[code] for code in country_columns]

    # Complete columns and placeholders for SQL
    columns = base_columns + country_columns
    placeholders = ["%s"] * len(columns)
    
    # UPSERT SQL statement
    sql = f"""
    INSERT INTO rate_providers ({', '.join(columns)}) 
    VALUES ({', '.join(placeholders)})
    ON CONFLICT (provider_name, source_currency, destination_currency) 
    DO UPDATE SET 
        provider_logo = EXCLUDED.provider_logo,
        rate = EXCLUDED.rate,
        created_at = EXCLUDED.created_at,
        {', '.join(f"{col} = EXCLUDED.{col}" for col in country_columns)}
    """
    
    # Execute and return success/failure
    try:
        cursor.execute(sql, base_values + country_values)
        return True
    except Exception as e:
        print(f"Database error: {str(e)}")
        return False

def main():
    # Load providers configuration
    providers = load_providers()
    if not providers:
        print("Error: Could not load provider configuration")
        return
    
    provider_name = providers.get("provider_name", "")
    provider_logo = providers.get("logo", "")
    
    # Get all possible operating countries from the configuration
    all_operating_countries = set()
    for currency_info in providers["sending_currencies"]:
        for country in currency_info["operating_countries"]:
            all_operating_countries.add(country.lower())
    
    # Connect to database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        print("Connected to database successfully")
    except Exception as e:
        print(f"Failed to connect to database: {str(e)}")
        return
    
    try:
        # Process each sending currency and receiving country
        for sending_currency_info in providers["sending_currencies"]:
            sending_currency = sending_currency_info["sending_currency"]
            representative_country = sending_currency_info["representative_country"]
            operating_countries = [country.lower() for country in sending_currency_info["operating_countries"]]
            
            # Process all receiving countries in the provider configuration
            for country_info in providers["receiving_countries"]:
                country_code = country_info["receiving_country"]
                
                # Fetch rate using the representative country
                rate_info = get_exchange_rate(sending_currency, country_code)
                
                if isinstance(rate_info, dict):
                    destination_currency = rate_info["receiving_currency"]
                    rate_value = rate_info["rate"]
                    created_at = parse_timestamp()
                    
                    # Create rate record for database
                    rate_record = {
                        "provider_name": provider_name,
                        "provider_logo": provider_logo,
                        "source_currency": sending_currency,
                        "destination_currency": destination_currency,
                        "rate": rate_value,
                        "created_at": created_at
                    }
                    
                    # Insert into database
                    success = insert_rate(cursor, rate_record, providers)
                    if success:
                        conn.commit()
                        print(f"✅ Inserted rate: {sending_currency} → {destination_currency}: {rate_value}")
                    else:
                        conn.rollback()
                        print(f"❌ Failed to insert rate: {sending_currency} → {destination_currency}")
                    
                    # Print formatted output
                    print("{")
                    print(f'    "provider_name": "{provider_name}",')
                    print(f'    "provider_logo": "{provider_logo}",')
                    print(f'    "source_currency": "{sending_currency}",')
                    print(f'    "destination_currency": "{destination_currency}",')
                    print(f'    "rate": {rate_value},')
                    print(f'    "created_at": "{created_at}",')
                    
                    # Add fields for all operating countries dynamically
                    country_fields = []
                    for country in all_operating_countries:
                        is_operating = country in operating_countries
                        country_fields.append(f'    "{country}": {str(is_operating).lower()}')
                    
                    # Join all country fields with commas and print
                    print(',\n'.join(country_fields))
                    print("}")
                    print()
                else:
                    print(f"Error fetching {sending_currency} → {country_code}: {rate_info}")
    except Exception as e:
        print(f"Error processing rates: {str(e)}")
    finally:
        # Close database connection
        cursor.close()
        conn.close()
        print("Database connection closed")

if __name__ == "__main__":
    main()

