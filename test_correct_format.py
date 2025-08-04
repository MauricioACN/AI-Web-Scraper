#!/usr/bin/env python3
"""
Test price API with correct body format
"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


def test_correct_body_format():
    """Test price API with the correct body format based on error messages"""

    url = "https://apim.canadiantire.ca/v1/product/api/v2/product/sku/PriceAvailability"

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "ocp-apim-subscription-key": os.getenv("OCP_APIM_SUBSCRIPTION_KEY"),
        "bannerId": "CTR",
        "baseSiteId": "CTR",
        "content-type": "application/json",
        "origin": "https://www.canadiantire.ca",
        "referer": "https://www.canadiantire.ca/"
    }

    params = {
        "lang": "en_CA",
        "storeId": "33",
        "cache": "true",
        "pCode": "0710113p"
    }

    # Test with 'skus' in body (as required by error message)
    test_bodies = [
        # Test 1: skus array
        {
            "skus": ["0710113p"]
        },

        # Test 2: skus with store info
        {
            "skus": ["0710113p"],
            "storeId": "33"
        },

        # Test 3: More detailed sku format
        {
            "skus": [
                {
                    "code": "0710113p",
                    "storeId": "33"
                }
            ]
        },

        # Test 4: Simple sku format
        {
            "skus": [
                {
                    "code": "0710113"
                }
            ]
        }
    ]

    for i, body in enumerate(test_bodies, 1):
        print(f"\n🧪 Test {i}: {json.dumps(body)}")

        try:
            response = requests.post(
                url, headers=headers, params=params, json=body)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS!")

                # Display price info
                if 'skus' in data and data['skus']:
                    sku = data['skus'][0]
                    price = sku.get('currentPrice', {}).get('value', 'N/A')
                    in_stock = sku.get('sellable', False)
                    location = sku.get('storeShelfLocation', 'N/A')

                    print(f"   💰 Price: ${price}")
                    print(f"   📦 In Stock: {in_stock}")
                    print(f"   📍 Location: {location}")

                # Save successful response
                with open("successful_price_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("💾 Saved to successful_price_response.json")
                return data

            else:
                print(f"❌ Error: {response.text[:400]}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    return None


if __name__ == "__main__":
    result = test_correct_body_format()
    if result:
        print("\n🎉 Found working API format!")
    else:
        print("\n❌ Still no success. May need additional authentication or different approach.")
