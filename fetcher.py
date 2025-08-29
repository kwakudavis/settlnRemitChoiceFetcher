import requests
import re
import json
import time

# Global variable to track the last API request time
last_request_time = 0

def load_providers():
    """Load provider configuration from providers.json"""
    try:
        with open('providers.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading providers.json: {str(e)}")
        return None

def rate_limit(seconds=5):
    """
    Implements rate limiting by ensuring the specified number
    of seconds has passed since the last API request
    """
    global last_request_time
    current_time = time.time()
    time_passed = current_time - last_request_time
    
    if time_passed < seconds:
        sleep_time = seconds - time_passed
        print(f"Rate limiting: Waiting {sleep_time:.2f} seconds...")
        time.sleep(sleep_time)
    
    # Update the last request time
    last_request_time = time.time()

def get_exchange_rate(sending_currency="EUR", receiving_country_code="GHA"):
    """
    Get exchange rate for a specific currency pair based on provider config.
    Uses the representative country for the sending currency.
    All operating countries for a sending currency share the same rate.
    """
    providers = load_providers()
    if not providers:
        return "Error: Could not load provider configuration"
    
    # Find the receiving currency and country name for the given country code
    receiving_currency = None
    receiving_country_name = None
    for country in providers["receiving_countries"]:
        if country["receiving_country"] == receiving_country_code:
            receiving_currency = country["receiving_currency"]
            receiving_country_name = country["receiving_country_name"].lower()
            break
    
    if not receiving_currency:
        return f"Error: Receiving country {receiving_country_code} not found in provider configuration"
    
    # Find the representative country for the sending currency
    representative_country = None
    operating_countries = []
    for currency in providers["sending_currencies"]:
        if currency["sending_currency"] == sending_currency:
            representative_country = currency["representative_country"]
            operating_countries = currency["operating_countries"]
            break
    
    if not representative_country:
        return f"Error: Sending currency {sending_currency} not found in provider configuration"
    
    # For debugging
    print(f"Fetching rate for {sending_currency} to {receiving_country_code} ({receiving_currency})")
    print(f"Using representative country: {representative_country}")
    print(f"Referer URL: https://www.remitchoice.com/fee-free-send-money-to/{receiving_country_name}")
    
    # Apply rate limiting before making the API request
    rate_limit(5)
    
    # Fetch the exchange rate (using representative country)
    try:
        # URL for the request
        url = 'https://www.remitchoice.com/ajaxcalculator.php'
        
        # Headers copied from the HTTP request
        headers = {
            'Host': 'www.remitchoice.com',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.140 Safari/537.36',
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.remitchoice.com',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': f'https://www.remitchoice.com/fee-free-send-money-to/{receiving_country_name}',
            'Priority': 'u=4, i'
        }
        
        # Form data payload - matching the exact case from the working request
        payload = {
            'sending_country': representative_country,
            'receiving_country': receiving_country_code,
            'sendingcurrencycode': sending_currency,
            'receivingcurrencycode': receiving_currency,
            'payout_method': 'Bank',
            'payout_patner': 'BANK',  # Changed to uppercase to match the working request
            'sending_amount': '1',
            'receiving_amount': '',
            'total_payable_amount': '',
            'action': 'sending'
        }
        
        # Print the request details for debugging
        print("Payload:", payload)
        
        # Send POST request with automatic content decompression
        response = requests.post(url, headers=headers, data=payload)
        
        # Print response status for debugging
        print(f"Response status: {response.status_code}")
        
        # Extract exchange rate using regex - pattern now handles both decimal and whole numbers
        exchange_rate_pattern = rf'Exchange Rate 1 {sending_currency} = (\d+(?:\.\d+)?) {receiving_currency}'
        exchange_rate_match = re.search(exchange_rate_pattern, response.text)
        
        # Print a sample of the response to help debug
        print(f"Response sample (first 200 chars): {response.text[:200]}")
        
        if exchange_rate_match:
            # Extract just the numerical value
            rate = float(exchange_rate_match.group(1))
            return {
                'sending_currency': sending_currency,
                'receiving_currency': receiving_currency,
                'rate': rate,
                'representative_country': representative_country,
                'receiving_country': receiving_country_code,
                'receiving_country_name': receiving_country_name,
                'operating_countries': operating_countries,
                'note': 'Same rate applies to all operating countries'
            }
        else:
            # Try alternative patterns
            patterns = [
                rf'1 {sending_currency} = (\d+(?:\.\d+)?) {receiving_currency}',  # Without "Exchange Rate" prefix
                rf'{sending_currency} = (\d+(?:\.\d+)?) {receiving_currency}',    # Even more simplified
                rf'= (\d+(?:\.\d+)?) {receiving_currency}'                       # Most general pattern
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    rate = float(match.group(1))
                    return {
                        'sending_currency': sending_currency,
                        'receiving_currency': receiving_currency,
                        'rate': rate,
                        'representative_country': representative_country,
                        'receiving_country': receiving_country_code,
                        'receiving_country_name': receiving_country_name,
                        'operating_countries': operating_countries,
                        'note': f'Same rate applies to all operating countries (matched with pattern: {pattern})'
                    }
            
            # If we reach here, no patterns matched
            print(f"Full response: {response.text}")
            return f"Exchange rate not found in the response for {sending_currency} to {receiving_currency}"
    except Exception as e:
        return f"Error fetching data: {str(e)}"

def get_all_rates():
    """
    Fetch rates for all currency pairs in the provider configuration.
    For each sending currency, only fetches once using the representative country
    since all operating countries share the same rate.
    """
    providers = load_providers()
    if not providers:
        return "Error: Could not load provider configuration"
    
    rates = {}
    
    # For each sending currency
    for sending_currency_info in providers["sending_currencies"]:
        sending_currency = sending_currency_info["sending_currency"]
        
        # For each receiving country
        for receiving_country_info in providers["receiving_countries"]:
            receiving_country = receiving_country_info["receiving_country"]
            
            # Get rate using representative country
            rate_info = get_exchange_rate(sending_currency, receiving_country)
            key = f"{sending_currency}_{receiving_country}"
            rates[key] = rate_info
    
    return rates

# For backward compatibility
def get_statement():
    return get_exchange_rate()

if __name__ == "__main__":
    # Example of getting single rate
    rate_info = get_exchange_rate("EUR", "NGA")  # Test with Nigeria which has whole number rates
    if isinstance(rate_info, dict):
        print(f"Exchange Rate: 1 {rate_info['sending_currency']} = {rate_info['rate']} {rate_info['receiving_currency']}")
        print(f"This rate applies to all {rate_info['sending_currency']} operating countries: {', '.join(rate_info['operating_countries'])}")
    else:
        print(rate_info)
    
    # Uncomment to get all rates (this will make many API calls)
    # all_rates = get_all_rates()
    # print(json.dumps(all_rates, indent=2))

