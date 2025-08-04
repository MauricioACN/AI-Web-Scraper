
import requests
import os
import json
from scraper_reviews import BASE_HEADERS


def fetch_reviews_debug(product_id, limit=30):
    """Versión de debug para analizar la estructura de respuesta"""
    url = "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/cv2/resources/data/reviews.json"

    params = {
        "resource": "reviews",
        "action": "REVIEWS_N_STATS",
        "filter": f"productid:eq:{product_id}",
        "filter_reviews": "contentlocale:eq:en*,fr*,en_CA,en_CA",
        "filter_isratingsonly": "eq:false",
        "include": "authors,products,comments",
        "filteredstats": "reviews",
        "Stats": "Reviews",
        "limit": limit,
        "offset": 0,
        "limit_comments": 3,
        "sort": "submissiontime:desc",
        "apiversion": "5.5",
        "displaycode": "15041_3_0-en_ca"
    }

    resp = requests.get(url, headers=BASE_HEADERS, params=params)

    print(f"Status Code: {resp.status_code}")
    print(f"Headers: {resp.headers}")

    if resp.status_code == 200:
        data = resp.json()
        print(f"Top level keys: {list(data.keys())}")

        # Verificar diferentes posibles estructuras
        if "response" in data:
            print(f"Response keys: {list(data['response'].keys())}")
            if "Results" in data["response"]:
                print(f"Results count: {len(data['response']['Results'])}")
            else:
                print("No 'Results' key in response")

        # Verificar si hay reviews en otro lugar
        if "Results" in data:
            print(f"Direct Results count: {len(data['Results'])}")

        # Imprimir estructura completa para un producto problemático
        print(
            f"Full response structure: {json.dumps(data, indent=2)[:1000]}...")

    return resp.json() if resp.status_code == 200 else None


def test_different_tokens(product_id):
    """Prueba diferentes configuraciones de headers"""

    base_headers_variations = [
        # Sin BV token
        {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "origin": "https://www.canadiantire.ca",
            "referer": "https://www.canadiantire.ca/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "ocp-apim-subscription-key": os.getenv("OCP_APIM_SUBSCRIPTION_KEY")
        },
        # Con BV token
        BASE_HEADERS,
        # Solo con user agent básico
        {
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    ]

    for i, headers in enumerate(base_headers_variations):
        print(f"\n--- Testing header variation {i+1} ---")
        try:
            resp = requests.get(
                "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/cv2/resources/data/reviews.json",
                headers=headers,
                params={
                    "resource": "reviews",
                    "action": "REVIEWS_N_STATS",
                    "filter": f"productid:eq:{product_id}",
                    "limit": 5
                }
            )
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                print(f"Keys: {list(data.keys())}")
        except Exception as e:
            print(f"Error: {e}")


def test_simpler_filters(product_id):
    """Prueba con filtros más simples"""

    filter_variations = [
        # Filtro actual (complejo)
        {
            "filter": f"productid:eq:{product_id}",
            "filter_reviews": "contentlocale:eq:en*,fr*,en_CA,en_CA",
            "filter_isratingsonly": "eq:false",
        },
        # Filtro simple
        {
            "filter": f"productid:eq:{product_id}",
        },
        # Sin filtros de idioma
        {
            "filter": f"productid:eq:{product_id}",
            "filter_isratingsonly": "eq:false",
        }
    ]

    base_params = {
        "resource": "reviews",
        "action": "REVIEWS_N_STATS",
        "include": "authors,products,comments",
        "limit": 5,
        "apiversion": "5.5"
    }

    for i, filters in enumerate(filter_variations):
        print(f"\n--- Testing filter variation {i+1} ---")
        params = {**base_params, **filters}

        resp = requests.get(
            "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/cv2/resources/data/reviews.json",
            headers=BASE_HEADERS,
            params=params
        )

        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # Buscar reviews en toda la respuesta
            reviews_found = find_reviews_in_response(data)
            print(f"Reviews found: {len(reviews_found)}")


def find_reviews_in_response(data, path=""):
    """Busca reviews en cualquier parte de la respuesta JSON"""
    reviews = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            if key.lower() in ['results', 'reviews', 'review'] and isinstance(value, list):
                print(f"Found potential reviews at: {current_path}")
                reviews.extend(value)
            else:
                reviews.extend(find_reviews_in_response(value, current_path))

    elif isinstance(data, list):
        for i, item in enumerate(data):
            reviews.extend(find_reviews_in_response(item, f"{path}[{i}]"))

    return reviews


def debug_specific_product(product_id):
    """Debug completo para un producto específico"""
    print(f"🔍 Debugging product: {product_id}")

    # 1. Verificar estructura de respuesta
    print("\n1. Testing response structure...")
    fetch_reviews_debug(product_id)

    # 2. Probar diferentes headers
    print("\n2. Testing different headers...")
    test_different_tokens(product_id)

    # 3. Probar filtros más simples
    print("\n3. Testing simpler filters...")
    test_simpler_filters(product_id)

    # 4. Verificar si el producto existe en la web
    print(
        f"\n4. Check product on web: https://www.canadiantire.ca/en/pdp/product/{product_id}.html")


if __name__ == "__main__":
    # Usar con un producto problemático
    debug_specific_product(input("Enter product ID to debug: "))
