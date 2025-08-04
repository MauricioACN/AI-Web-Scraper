#!/usr/bin/env python3
"""
Test alternative Canadian Tire price endpoints
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


def test_alternative_endpoints():
    """Test different ways to get price data"""

    base_headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "ocp-apim-subscription-key": os.getenv("OCP_APIM_SUBSCRIPTION_KEY"),
        "origin": "https://www.canadiantire.ca",
        "referer": "https://www.canadiantire.ca/"
    }

    # Test different endpoint variations
    endpoints = [
        # Original endpoint with GET
        {
            "name": "Original GET",
            "url": "https://apim.canadiantire.ca/v1/product/api/v2/product/sku/PriceAvailability",
            "method": "GET",
            "params": {"lang": "en_CA", "storeId": "33", "cache": "true", "pCode": "0710113p", "bannerId": "CTR"},
            "headers": base_headers
        },

        # Try without cache
        {
            "name": "Without cache",
            "url": "https://apim.canadiantire.ca/v1/product/api/v2/product/sku/PriceAvailability",
            "method": "GET",
            "params": {"lang": "en_CA", "storeId": "33", "pCode": "0710113p", "bannerId": "CTR"},
            "headers": base_headers
        },

        # Try the search API for product info
        {
            "name": "Search API for product",
            "url": "https://apim.canadiantire.ca/v1/search/v2/search",
            "method": "GET",
            "params": {"q": "0710113", "store": "33", "rows": 1, "lang": "en_CA"},
            "headers": base_headers
        },

        # Try product details API
        {
            "name": "Product details",
            "url": "https://apim.canadiantire.ca/v1/product/api/v1/product/productFamily",
            "method": "GET",
            "params": {"lang": "en_CA", "storeId": "33", "productCode": "0710113p"},
            "headers": base_headers
        }
    ]

    for test in endpoints:
        print(f"\n🔍 Testing: {test['name']}")
        print(f"URL: {test['url']}")

        try:
            if test['method'] == 'GET':
                response = requests.get(
                    test['url'], headers=test['headers'], params=test['params'])
            else:
                response = requests.post(
                    test['url'], headers=test['headers'], params=test['params'])

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS!")
                print("Response preview:")
                print(json.dumps(data, indent=2)[:500] + "...")

                # Save successful response
                with open(f"test_response_{test['name'].replace(' ', '_')}.json", "w") as f:
                    json.dump(data, f, indent=2)
                print(
                    f"💾 Saved to test_response_{test['name'].replace(' ', '_')}.json")

            else:
                print(f"❌ Error: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Exception: {e}")


if __name__ == "__main__":
    test_alternative_endpoints()
