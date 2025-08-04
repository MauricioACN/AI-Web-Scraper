#!/usr/bin/env python3
"""
Test the URL finder function separately
"""

import requests
import json


def test_product_url(product_id):
    """
    Test the product URL finding function
    """
    search_id = product_id.replace('P', '').replace('p', '')

    search_url = "https://apim.canadiantire.ca/v1/search/v2/search"
    headers = {
        "ocp-apim-subscription-key": "c01ef3612328420c9f5cd9277e815a0e",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    params = {
        "q": search_id,
        "store": "33",
        "rows": 10,
        "lang": "en_CA",
        "baseStoreId": "CTR",
        "apiversion": "5.5"
    }

    try:
        print(f"🔍 Testing URL for product: {product_id}")
        print(f"🔍 Search ID: {search_id}")
        print(f"🔍 URL: {search_url}")
        print(f"🔍 Params: {params}")

        resp = requests.get(search_url, headers=headers, params=params)
        print(f"🔍 Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            print(f"🔍 API Response keys: {list(data.keys())}")
            print(f"🔍 Result count: {data.get('resultCount', 'N/A')}")

            # Print full response for debugging
            print(f"🔍 Full response sample:")
            print(json.dumps(data, indent=2)[:1000] + "...")

            products = data.get('products')
            print(f"🔍 Products value: {products}")
            print(f"🔍 Products type: {type(products)}")

            if products is None:
                print("⚠️ Products is None - trying alternative searches...")

                # Try with the full product ID
                alt_params = params.copy()
                alt_params['q'] = product_id
                print(f"🔍 Trying search with full ID: {product_id}")

                resp2 = requests.get(
                    search_url, headers=headers, params=alt_params)
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    products = data2.get('products')
                    print(
                        f"🔍 Alt search products: {type(products)}, count: {len(products) if products else 0}")

            if products and len(products) > 0:
                print(f"🔍 First few product codes:")
                for i, product in enumerate(products[:5]):
                    code = product.get('code', 'NO_CODE')
                    url = product.get('url', 'NO_URL')
                    name = product.get('name', 'NO_NAME')[:50]
                    print(f"  {i+1}. Code: {code}, URL: {url}, Name: {name}")

                # Look for exact match
                for product in products:
                    if product.get('code') == search_id:
                        product_url = product.get('url', '')
                        if product_url:
                            full_url = f"https://www.canadiantire.ca{product_url}"
                            print(f"✅ Found exact match URL: {full_url}")
                            return full_url

                print(f"⚠️ No exact match for code: {search_id}")
            else:
                print("⚠️ No products in response")

        else:
            print(f"❌ API Error: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    return None


if __name__ == "__main__":
    test_product_url("0710113P")
