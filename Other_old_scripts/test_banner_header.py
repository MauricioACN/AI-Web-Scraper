#!/usr/bin/env python3
"""
Test price API with bannerId in headers
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


def test_price_with_banner_header():
    """Test price API with bannerId in headers"""

    url = "https://apim.canadiantire.ca/v1/product/api/v2/product/sku/PriceAvailability"

    # Headers with bannerId
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "ocp-apim-subscription-key": os.getenv("OCP_APIM_SUBSCRIPTION_KEY"),
        "bannerId": "CTR",  # Add as header
        "baseSiteId": "CTR",
        "origin": "https://www.canadiantire.ca",
        "referer": "https://www.canadiantire.ca/"
    }

    # Test cases
    test_cases = [
        {
            "name": "GET with bannerId header",
            "method": "GET",
            "params": {"lang": "en_CA", "storeId": "33", "cache": "true", "pCode": "0710113p"}
        },
        {
            "name": "GET with bannerId in both",
            "method": "GET",
            "params": {"lang": "en_CA", "storeId": "33", "cache": "true", "pCode": "0710113p", "bannerId": "CTR"}
        },
        {
            "name": "POST with empty body",
            "method": "POST",
            "params": {"lang": "en_CA", "storeId": "33", "cache": "true", "pCode": "0710113p"},
            "body": {}
        },
        {
            "name": "POST with product array",
            "method": "POST",
            "params": {"lang": "en_CA", "storeId": "33"},
            "body": {"productCodes": ["0710113p"]}
        }
    ]

    for test in test_cases:
        print(f"\n🧪 {test['name']}")

        try:
            if test['method'] == 'GET':
                response = requests.get(
                    url, headers=headers, params=test['params'])
            else:
                response = requests.post(
                    url, headers=headers, params=test['params'], json=test.get('body', {}))

            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS!")
                print("Price data found:")

                # Extract price info
                if 'skus' in data and data['skus']:
                    sku = data['skus'][0]
                    price = sku.get('currentPrice', {}).get('value', 'N/A')
                    in_stock = sku.get('sellable', False)
                    print(f"   💰 Price: ${price}")
                    print(f"   📦 In Stock: {in_stock}")

                # Save the working response
                with open("working_price_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("💾 Saved working response to working_price_response.json")
                return data

            else:
                print(f"❌ Error: {response.text[:300]}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    return None


if __name__ == "__main__":
    result = test_price_with_banner_header()
    if not result:
        print("\n❌ All tests failed. The API might require authentication or different parameters.")
