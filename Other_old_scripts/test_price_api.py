#!/usr/bin/env python3
"""
Simple test for the Canadian Tire Price API
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


def test_price_api():
    """Test the exact API call based on the network request you provided"""

    url = "https://apim.canadiantire.ca/v1/product/api/v2/product/sku/PriceAvailability"

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "ocp-apim-subscription-key": os.getenv("OCP_APIM_SUBSCRIPTION_KEY"),
        "bannerid": "CTR",
        "basesiteid": "CTR",
        "content-type": "application/json",
        "origin": "https://www.canadiantire.ca",
        "referer": "https://www.canadiantire.ca/",
        "service-client": "ctr/web",
        "x-web-host": "www.canadiantire.ca"
    }

    params = {
        "lang": "en_CA",
        "storeId": "33",
        "cache": "true",
        "pCode": "0710113p"
    }

    # Try different request body formats
    test_cases = [
        # Test 1: Array format
        ["0710113p"],

        # Test 2: Object format
        {
            "productCodes": ["0710113p"],
            "storeId": "33"
        },

        # Test 3: Simple object
        {
            "pCode": "0710113p",
            "storeId": "33"
        },

        # Test 4: Just the product code
        {"productCode": "0710113p"}
    ]

    for i, body in enumerate(test_cases, 1):
        print(f"\n🧪 Test {i}: {body}")

        try:
            response = requests.post(
                url, headers=headers, params=params, json=body)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS!")
                print(json.dumps(data, indent=2)[:500] + "...")
                return data
            else:
                print(f"❌ Error: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    return None


if __name__ == "__main__":
    result = test_price_api()
