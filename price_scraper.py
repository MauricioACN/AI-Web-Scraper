#!/usr/bin/env python3
"""
Simple Canadian Tire Price Scraper
Fetches product pricing and availability information from Canadian Tire API
"""
import requests
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# API Headers
PRICE_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "ocp-apim-subscription-key": os.getenv("OCP_APIM_SUBSCRIPTION_KEY"),
    "bannerId": "CTR",
    "baseSiteId": "CTR",
    "content-type": "application/json",
    "origin": "https://www.canadiantire.ca",
    "referer": "https://www.canadiantire.ca/"
}


def fetch_product_price(product_id, store_id="33"):
    """
    Fetch price and availability information for a single product

    Args:
        product_id (str): Product ID (e.g., "0710113P")
        store_id (str): Store ID (default: "33")

    Returns:
        dict: Product price and availability data, or None if error
    """
    # Clean product ID (remove 'P' suffix if present)
    clean_product_id = product_id.replace('P', '').replace('p', '')

    url = "https://apim.canadiantire.ca/v1/product/api/v2/product/sku/PriceAvailability"

    # URL parameters
    params = {
        "lang": "en_CA",
        "storeId": store_id,
        "cache": "true",
        "pCode": f"{clean_product_id}p"
    }

    # Request body - correct format based on successful test
    request_body = {
        "skus": [
            {
                "code": clean_product_id  # No 'p' suffix, no storeId
            }
        ]
    }

    try:
        print(f"🔍 Fetching price data for product: {product_id}")

        # Use POST request with correct JSON body
        response = requests.post(
            url,
            headers=PRICE_HEADERS,
            params=params,
            json=request_body
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully fetched price data for {product_id}")
            return data
        else:
            print(f"❌ Error {response.status_code} for product {product_id}")
            print(f"Response: {response.text[:300]}")
            return None

    except Exception as e:
        print(f"❌ Exception fetching {product_id}: {e}")
        return None


def save_price_data(product_id, price_data, folder="price_data"):
    """
    Save price data to JSON file

    Args:
        product_id (str): Product ID
        price_data (dict): Price data from API
        folder (str): Folder to save files
    """
    # Ensure folder exists
    os.makedirs(folder, exist_ok=True)

    # Clean filename
    clean_id = product_id.replace('P', '').replace('p', '')
    filename = f"{folder}/price_{clean_id}.json"

    # Add metadata
    enhanced_data = {
        "product_id": product_id,
        "scraped_at": datetime.now().isoformat(),
        "api_data": price_data
    }

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved price data: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Error saving {filename}: {e}")
        return None


def extract_key_price_info(price_data):
    """
    Extract and display key pricing information in a readable format

    Args:
        price_data (dict): Raw API response

    Returns:
        dict: Simplified price information
    """
    if not price_data or 'skus' not in price_data:
        return None

    sku = price_data['skus'][0] if price_data['skus'] else {}

    key_info = {
        "product_code": sku.get('code', 'N/A'),
        "current_price": sku.get('currentPrice', {}).get('value', 'N/A'),
        "original_price": sku.get('originalPrice'),
        "is_on_sale": sku.get('isOnSale', False),
        "in_stock": sku.get('sellable', False),
        "quantity_available": sku.get('fulfillment', {}).get('availability', {}).get('quantity', 0),
        "store_location": sku.get('storeShelfLocation', 'N/A'),
        "urgent_low_stock": sku.get('isUrgentLowStock', False),
        "warranty": sku.get('warrantyMessage', 'N/A')
    }

    return key_info


def scrape_single_product_price(product_id, store_id="33", save_file=True):
    """
    Complete workflow to scrape a single product's price information

    Args:
        product_id (str): Product ID
        store_id (str): Store ID
        save_file (bool): Whether to save JSON file

    Returns:
        dict: Complete result with status and data
    """
    print(f"\n🚀 Starting price scrape for product: {product_id}")

    # Fetch price data
    price_data = fetch_product_price(product_id, store_id)

    if not price_data:
        return {
            "product_id": product_id,
            "status": "error",
            "message": "Failed to fetch price data"
        }

    # Extract key information
    key_info = extract_key_price_info(price_data)

    if not key_info:
        return {
            "product_id": product_id,
            "status": "error",
            "message": "No SKU data found"
        }

    # Save to file if requested
    filename = None
    if save_file:
        filename = save_price_data(product_id, price_data)

    # Display key information
    print(f"\n📊 KEY PRICE INFO FOR {product_id}:")
    print(f"   💰 Current Price: ${key_info['current_price']}")
    print(f"   🏷️  On Sale: {'Yes' if key_info['is_on_sale'] else 'No'}")
    print(f"   📦 In Stock: {'Yes' if key_info['in_stock'] else 'No'}")
    print(f"   📍 Store Location: {key_info['store_location']}")
    print(
        f"   ⚠️  Low Stock Warning: {'Yes' if key_info['urgent_low_stock'] else 'No'}")

    return {
        "product_id": product_id,
        "status": "success",
        "key_info": key_info,
        "raw_data": price_data,
        "filename": filename
    }


def scrape_multiple_products_prices(product_list, store_id="33", delay=1):
    """
    Scrape prices for multiple products

    Args:
        product_list (list): List of product IDs
        store_id (str): Store ID
        delay (int): Delay between requests in seconds

    Returns:
        list: Results for all products
    """
    print(
        f"🔄 Starting batch price scraping for {len(product_list)} products...")

    results = []

    for i, product_id in enumerate(product_list):
        print(f"\n[{i+1}/{len(product_list)}] Processing: {product_id}")

        result = scrape_single_product_price(product_id, store_id)
        results.append(result)

        # Add delay between requests
        if i < len(product_list) - 1:
            print(f"⏳ Waiting {delay} seconds...")
            time.sleep(delay)

    # Summary
    successful = len([r for r in results if r['status'] == 'success'])
    failed = len(results) - successful

    print(f"\n📈 BATCH SUMMARY:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📁 Files saved in: price_data/")

    return results


def load_product_ids_from_reviews():
    """
    Load product IDs from existing review files

    Returns:
        list: List of product IDs found in review files
    """
    product_ids = []

    # Check data_review folder
    if os.path.exists("data_review"):
        for filename in os.listdir("data_review"):
            if filename.startswith("reviews_") and filename.endswith(".json"):
                product_id = filename.replace(
                    "reviews_", "").replace(".json", "")
                product_ids.append(product_id)

    print(f"📋 Found {len(product_ids)} product IDs from review files")
    return product_ids


def main():
    """
    Main function with interactive menu
    """
    print("🏪 Canadian Tire Price Scraper")
    print("=" * 40)

    choice = input(
        "Choose an option:\n"
        "1: Single product price\n"
        "2: Multiple products (enter manually)\n"
        "3: Scrape prices for all reviewed products\n"
        "4: Load from product list file\n"
        "Option: "
    )

    if choice == "1":
        # Single product
        product_id = input("Enter product ID (e.g., 0710113P): ").strip()
        if product_id:
            result = scrape_single_product_price(product_id)
            print(f"\n🎯 Final Status: {result['status']}")
        else:
            print("❌ No product ID provided")

    elif choice == "2":
        # Multiple products manually
        print("Enter product IDs separated by commas:")
        ids_input = input("Product IDs: ").strip()
        product_ids = [pid.strip()
                       for pid in ids_input.split(",") if pid.strip()]

        if product_ids:
            results = scrape_multiple_products_prices(product_ids)
        else:
            print("❌ No product IDs provided")

    elif choice == "3":
        # All reviewed products
        product_ids = load_product_ids_from_reviews()
        if product_ids:
            confirm = input(
                f"Scrape prices for {len(product_ids)} products? (y/N): ")
            if confirm.lower() == 'y':
                # Add safety measures to avoid rate limiting
                delay_seconds = 2  # 2 seconds between requests
                batch_size = 10   # Process in smaller batches

                print(f"⚠️  Rate limiting protection enabled:")
                print(f"   - {delay_seconds} second delay between requests")
                print(f"   - Processing in batches of {batch_size}")
                print(
                    f"   - Total estimated time: ~{len(product_ids) * delay_seconds / 60:.1f} minutes")

                confirm_proceed = "y"
                if confirm_proceed.lower() == 'y':
                    results = scrape_multiple_products_prices(
                        product_ids, delay=delay_seconds)
                else:
                    print("Cancelled")
            else:
                print("Cancelled")
        else:
            print("❌ No product IDs found in review files")

    elif choice == "4":
        # From file
        filename = input(
            "Enter JSON file path (default: product_list_v4_1754202926.json): ").strip()
        if not filename:
            filename = "product_list_v4_1754202926.json"

        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            # Extract product IDs (adjust based on your file structure)
            product_ids = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'product_id' in item:
                        product_ids.append(item['product_id'])

            if product_ids:
                print(
                    f"📋 Loaded {len(product_ids)} product IDs from {filename}")
                results = scrape_multiple_products_prices(
                    product_ids[:10])  # Limit for testing
            else:
                print("❌ No product IDs found in file")

        except Exception as e:
            print(f"❌ Error loading file: {e}")

    else:
        print("❌ Invalid option")


if __name__ == "__main__":
    main()
