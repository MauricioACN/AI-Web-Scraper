import glob
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import json
import gzip
import brotli
from io import BytesIO
import time
from dotenv import load_dotenv

load_dotenv()


BASE_HEADERS = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9",
    "bv-bfd-token": os.getenv("BV_BFD_TOKEN"),
    "origin": "https://www.canadiantire.ca",
    "referer": "https://www.canadiantire.ca/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "ocp-apim-subscription-key": os.getenv("OCP_APIM_SUBSCRIPTION_KEY")
}


def fetch_reviews(product_id, limit=30):
    url = "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/cv2/resources/data/reviews.json"

    # Usar headers originales sin modificar Accept-Encoding
    headers = BASE_HEADERS

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

    all_reviews = []
    offset = 0

    while True:
        params["offset"] = offset
        print(
            f"DEBUG URL: {url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}")

        resp = requests.get(url, headers=headers, params=params)
        print(
            f"DEBUG [{resp.status_code}] Content-Encoding: {resp.headers.get('content-encoding', 'none')}")

        if resp.status_code != 200:
            print(f"❌ Error {resp.status_code}: {resp.text}")
            break

        # Simplificar: usar resp.json() directamente
        try:
            data = resp.json()
            print("✅ JSON parsed successfully")
        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
            print("Raw response preview:", resp.content[:200])
            break

        # Acceder correctamente a los resultados
        response_data = data.get("response", {})
        reviews = response_data.get("Results", [])

        if not reviews:
            print("No more reviews found")
            break

        all_reviews.extend(reviews)
        offset += limit
        print(f"✅ Fetched {len(all_reviews)} reviews so far...")

        # Evitar rate limiting
        time.sleep(0.5)

        # Limitar para testing (opcional)
        if len(all_reviews) >= 100:  # Limitar a 100 para pruebas
            print("Reached limit for testing")
            break

    return all_reviews


def fetch_highlights(product_id):
    url = f"https://rh.nexus.bazaarvoice.com/highlights/v3/1/canadiantire-ca/{product_id}"
    resp = requests.get(url, headers=BASE_HEADERS)
    return resp.json().get("subjects", {})


def fetch_features(product_id):
    url = "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/sentiments/resources/sentiment/v1/features"
    params = {"productId": product_id, "language": "en"}
    resp = requests.get(url, headers=BASE_HEADERS, params=params)
    return resp.json().get("response", {}).get("features", [])


def export_reviews_to_json(reviews, highlights, features, filename):
    """Export reviews, highlights, and features to JSON file"""
    data = {
        "reviews": [],
        "highlights": highlights,
        "features": features
    }

    for r in reviews:
        review_data = {
            "review_id": r.get("Id", ""),
            "author": r.get("UserNickname", ""),
            "rating": r.get("Rating", ""),
            "title": r.get("Title", ""),
            "text": r.get("ReviewText", ""),
            "submission_time": r.get("SubmissionTime", ""),
            "comments": []
        }

        comments_list = r.get("Comments", [])
        if comments_list:
            review_data["comments"] = [
                {
                    "comment_text": c.get("CommentText", ""),
                    "author": c.get("AuthorId", ""),
                    "submission_time": c.get("SubmissionTime", "")
                }
                for c in comments_list
            ]

        data["reviews"].append(review_data)

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print(f"✅ JSON saved as {filename}")


def get_category_products(category_url, max_products=100):
    """
    Obtiene productos de una categoría específica de Canadian Tire
    """
    # API de búsqueda de Canadian Tire
    search_url = "https://apim.canadiantire.ca/v1/search/api/v1/search"

    # Extraer categoría del URL si es necesario
    category_match = re.search(r'/([^/]+)/?$', category_url.rstrip('/'))
    category = category_match.group(1) if category_match else "products"

    params = {
        "q": "*",  # Buscar todo
        "category": category,
        "lang": "en_CA",
        "storeId": "33",
        "baseStoreId": "CTR",
        "rows": 50,  # Máximo por request
        "start": 0
    }

    all_products = []

    while len(all_products) < max_products:
        try:
            resp = requests.get(
                search_url, headers=BASE_HEADERS, params=params)
            if resp.status_code != 200:
                print(f"❌ Error {resp.status_code} for category {category}")
                break

            data = resp.json()
            products = data.get('products', [])

            if not products:
                print(f"No more products in category {category}")
                break

            for product in products:
                if len(all_products) >= max_products:
                    break

                product_info = {
                    'product_id': product.get('code'),
                    'name': product.get('name'),
                    'category': category,
                    'price': product.get('price', {}).get('value'),
                    'url': f"https://www.canadiantire.ca{product.get('url', '')}"
                }
                all_products.append(product_info)

            params['start'] += params['rows']
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"❌ Error fetching category {category}: {e}")
            break

    return all_products


def get_popular_categories():
    """
    Lista de categorías populares para scraping masivo
    """
    return [
        "automotive",
        "tools-hardware",
        "sports-recreation",
        "home-garden",
        "electronics",
        "appliances",
        "household-essentials",
        "baby-kids",
        "clothing-footwear",
        "seasonal-outdoor-living"
    ]


def scrape_product_reviews_batch(product_list, max_workers=5):
    """
    Scraping masivo de reviews usando threading
    """
    def scrape_single_product(product):
        product_id = product['product_id']
        print(f"🔄 Processing {product['name']} ({product_id})")

        try:
            # Fetch data for this product
            # Limitar para eficiencia
            reviews = fetch_reviews(product_id, limit=50)
            highlights = fetch_highlights(product_id)
            features = fetch_features(product_id)

            if reviews:
                filename = f"reviews_{product_id}.json"
                export_reviews_to_json(reviews, highlights, features, filename)
                return {
                    'product_id': product_id,
                    'name': product['name'],
                    'status': 'success',
                    'reviews_count': len(reviews),
                    'filename': filename
                }
            else:
                return {
                    'product_id': product_id,
                    'name': product['name'],
                    'status': 'no_reviews',
                    'reviews_count': 0
                }
        except Exception as e:
            return {
                'product_id': product_id,
                'name': product['name'],
                'status': 'error',
                'error': str(e)
            }

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_product = {
            executor.submit(scrape_single_product, product): product
            for product in product_list
        }

        for future in as_completed(future_to_product):
            result = future.result()
            results.append(result)
            print(f"✅ Completed: {result['name']} - {result['status']}")

    return results


def massive_product_analysis(products_per_category=20, total_limit=200):
    """
    Análisis masivo de productos por categorías
    """
    print("🚀 Starting massive product analysis...")

    categories = get_popular_categories()
    all_products = []

    # Step 1: Collect products from all categories
    for category in categories:
        if len(all_products) >= total_limit:
            break

        print(f"📦 Fetching products from category: {category}")
        category_products = get_category_products(
            f"https://www.canadiantire.ca/en/c/{category}",
            max_products=products_per_category
        )

        all_products.extend(category_products)
        print(f"✅ Found {len(category_products)} products in {category}")
        time.sleep(1)  # Rate limiting between categories

    # Limitar al total especificado
    all_products = all_products[:total_limit]

    print(f"\n📊 Total products collected: {len(all_products)}")

    # Step 2: Save product list
    with open("product_list.json", "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    print("✅ Product list saved to product_list.json")

    # Step 3: Batch scrape reviews
    print("\n🔄 Starting batch review scraping...")
    results = scrape_product_reviews_batch(all_products, max_workers=3)

    # Step 4: Save results summary
    summary = {
        'total_products': len(all_products),
        'successful_scrapes': len([r for r in results if r['status'] == 'success']),
        'failed_scrapes': len([r for r in results if r['status'] == 'error']),
        'no_reviews': len([r for r in results if r['status'] == 'no_reviews']),
        'results': results
    }

    with open("scraping_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n📈 Analysis Complete!")
    print(f"✅ Successful: {summary['successful_scrapes']}")
    print(f"❌ Failed: {summary['failed_scrapes']}")
    print(f"🔍 No reviews: {summary['no_reviews']}")

    return results

# ...existing code...


def get_products_from_search_v2(search_term="*", max_products=500, store_id="33"):
    """
    Método actualizado usando la API v2 de búsqueda que funciona correctamente
    """
    search_url = "https://apim.canadiantire.ca/v1/search/v2/search"

    all_products = []
    page = 1

    while len(all_products) < max_products:
        params = {
            "q": search_term,
            "store": store_id,
            "page": page,
            "lang": "en_CA",
            "baseStoreId": "CTR",
            "rows": 50,
            "start": (page - 1) * 50,
            "apiversion": "5.5",
            "displaycode": "15041_3_0-en_ca"
        }

        try:
            print(f"🔍 Fetching page {page} for search term: '{search_term}'")
            resp = requests.get(
                search_url, headers=BASE_HEADERS, params=params)

            if resp.status_code != 200:
                print(f"❌ Search API error: {resp.status_code}")
                print(f"Response: {resp.text[:500]}")
                break

            data = resp.json()
            products = data.get('products', [])

            if not products:
                print("No more products found in search")
                break

            for product in products:
                if len(all_products) >= max_products:
                    break

                # Extraer información del producto con la nueva estructura
                product_info = {
                    'product_id': product.get('code'),
                    'name': product.get('title'),
                    'category': extract_category_from_breadcrumb(product.get('breadcrumbList', [])),
                    'price': extract_price_info(product),
                    'url': f"https://www.canadiantire.ca{product.get('url', '')}",
                    'brand': product.get('brand', {}).get('label'),
                    'rating': product.get('rating'),
                    'ratings_count': product.get('ratingsCount'),
                    'badges': product.get('badges', []),
                    'image': get_main_image(product.get('images', []))
                }

                # Solo agregar productos con ID válido
                if product_info['product_id']:
                    all_products.append(product_info)

            print(
                f"✅ Found {len(products)} products on page {page} (Total: {len(all_products)})")

            # Verificar si hay más páginas
            pagination = data.get('pagination', {})
            if not pagination.get('nextUrl'):
                print("No more pages available")
                break

            page += 1
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"❌ Error fetching page {page}: {e}")
            break

    return all_products


def extract_category_from_breadcrumb(breadcrumb_list):
    """
    Extrae la categoría principal del breadcrumb
    """
    if breadcrumb_list and len(breadcrumb_list) > 0:
        return breadcrumb_list[-1] if isinstance(breadcrumb_list, list) else "Unknown"
    return "Unknown"


def extract_price_info(product):
    """
    Extrae información de precio del producto
    """
    # En la nueva API, el precio podría estar en diferentes lugares
    if product.get('currentPrice'):
        return product.get('currentPrice')
    return None


def get_main_image(images):
    """
    Obtiene la imagen principal del producto
    """
    if images and len(images) > 0:
        return images[0].get('url')
    return None


def get_products_by_category_v2(category_filter=None, max_products=100):
    """
    Obtiene productos filtrados por categoría usando los facets de la API
    """
    search_url = "https://apim.canadiantire.ca/v1/search/v2/search"

    params = {
        "q": "*",  # Buscar todo
        "store": "33"
    }

    # Si hay categoría específica, agregarla como filtro
    if category_filter:
        params['x1'] = 'ast-id-level-1'
        params['q1'] = category_filter

    all_products = []
    page = 1

    while len(all_products) < max_products:
        params['page'] = page

        try:
            resp = requests.get(
                search_url, headers=BASE_HEADERS, params=params)

            if resp.status_code != 200:
                print(f"❌ Category search error: {resp.status_code}")
                break

            data = resp.json()
            products = data.get('products', [])

            if not products:
                break

            for product in products:
                if len(all_products) >= max_products:
                    break

                product_info = {
                    'product_id': product.get('code'),
                    'name': product.get('title'),
                    'category': category_filter or "All",
                    'price': extract_price_info(product),
                    'url': f"https://www.canadiantire.ca{product.get('url', '')}",
                    'brand': product.get('brand', {}).get('label'),
                    'rating': product.get('rating'),
                    'ratings_count': product.get('ratingsCount')
                }

                if product_info['product_id']:
                    all_products.append(product_info)

            # Verificar paginación
            pagination = data.get('pagination', {})
            if not pagination.get('nextUrl'):
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error in category search: {e}")
            break

    return all_products


def get_available_categories():
    """
    Obtiene las categorías disponibles desde la API
    """
    search_url = "https://apim.canadiantire.ca/v1/search/v2/search"

    params = {
        "q": "*",
        "store": "33",
        "page": 1,
        "lang": "en_CA",
        "baseStoreId": "CTR",
        "apiversion": "5.5",
        "displaycode": "15041_3_0-en_ca"
    }

    try:
        resp = requests.get(search_url, headers=BASE_HEADERS, params=params)

        if resp.status_code == 200:
            data = resp.json()
            facets = data.get('facets', [])

            for facet in facets:
                if facet.get('id') == 'category_ast':
                    categories = []
                    for value in facet.get('values', []):
                        categories.append({
                            'name': value.get('label'),
                            'id': value.get('url', '').split('q1=')[-1] if 'q1=' in value.get('url', '') else '',
                            'count': value.get('count')
                        })
                    return categories

    except Exception as e:
        print(f"❌ Error getting categories: {e}")

    return []


def massive_product_analysis_v3(total_limit=200):
    """
    Versión 3: Usando la API v2 funcional
    """
    print("🚀 Starting massive product analysis v3 with working API...")

    # Step 1: Obtener categorías disponibles
    print("\n📂 Getting available categories...")
    categories = get_available_categories()

    if categories:
        print(f"✅ Found {len(categories)} categories:")
        for cat in categories[:10]:  # Mostrar solo las primeras 10
            print(f"   - {cat['name']} ({cat['count']} products)")

    # Step 2: Obtener productos usando diferentes estrategias
    print(
        f"\n🔍 Collecting {total_limit} products using multiple search terms...")

    # Términos de búsqueda diversificados
    search_terms = [
        "tools", "electronics", "home", "automotive", "sports",
        "appliances", "toys", "hardware", "outdoor", "bedroom"
    ]

    # Términos de búsqueda más diversos y populares (30 términos)
    search_terms = [
        "tools", "electronics", "home", "automotive", "sports",
        "appliances", "toys", "hardware", "outdoor", "bedroom",
        "kitchen", "bathroom", "garden", "camping", "fitness",
        "cleaning", "storage", "lighting", "paint", "plumbing",
        "electrical", "safety", "bike", "winter", "summer",
        "Christmas", "BBQ", "pool", "lawn", "furniture"
    ]

    all_products = []
    products_per_term = total_limit // len(search_terms)

    for term in search_terms:
        if len(all_products) >= total_limit:
            break

        print(f"   Searching for: '{term}' (max {products_per_term} products)")
        products = get_products_from_search_v2(
            search_term=term,
            max_products=products_per_term
        )

        all_products.extend(products)
        print(f"   ✅ Found {len(products)} products for '{term}'")
        time.sleep(1)

    # Step 3: Remover duplicados y limitar
    unique_products = []
    seen_ids = set()

    for product in all_products:
        if product['product_id'] not in seen_ids and product['product_id']:
            unique_products.append(product)
            seen_ids.add(product['product_id'])

        if len(unique_products) >= total_limit:
            break

    print(f"\n📊 Total unique products collected: {len(unique_products)}")

    # Step 4: Guardar lista de productos
    with open("product_list_v3.json", "w", encoding="utf-8") as f:
        json.dump(unique_products, f, indent=2, ensure_ascii=False)
    print("✅ Product list saved to product_list_v3.json")

    # Step 5: Hacer scraping de reviews de una muestra
    test_products = unique_products  # Testing con todos los productos únicos
    print(f"\n🔄 Testing review scraping with {len(test_products)} products...")

    results = scrape_product_reviews_batch(test_products, max_workers=3)

    # Step 6: Guardar resumen
    summary = {
        'total_products_found': len(unique_products),
        'categories_available': len(categories),
        'search_terms_used': search_terms,
        'tested_products': len(test_products),
        'successful_scrapes': len([r for r in results if r['status'] == 'success']),
        'failed_scrapes': len([r for r in results if r['status'] == 'error']),
        'no_reviews': len([r for r in results if r['status'] == 'no_reviews']),
        'api_version': 'v2_working',
        'results': results
    }

    with open("scraping_summary_v3.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n📈 Analysis Complete!")
    print(f"✅ Products found: {len(unique_products)}")
    print(f"✅ Categories available: {len(categories)}")
    print(f"✅ Successful scrapes: {summary['successful_scrapes']}")
    print(f"❌ Failed scrapes: {summary['failed_scrapes']}")
    print(f"🔍 No reviews: {summary['no_reviews']}")

    return results


def load_existing_scraped_products():
    """
    Carga la lista de productos que ya han sido scrapeados exitosamente
    """
    scraped_products = set()

    # Buscar archivos de reviews existentes
    review_files = glob.glob("reviews_*.json")
    for file in review_files:
        # Extraer product_id del nombre del archivo
        product_id = file.replace("reviews_", "").replace(".json", "")
        scraped_products.add(product_id)

    # También cargar desde summaries anteriores si existen
    summary_files = ["scraping_summary.json", "scraping_summary_v3.json"]
    for summary_file in summary_files:
        if os.path.exists(summary_file):
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    summary = json.load(f)

                # Agregar productos exitosamente scrapeados
                for result in summary.get('results', []):
                    if result.get('status') == 'success':
                        scraped_products.add(result.get('product_id'))
            except Exception as e:
                print(f"⚠️ Warning: Could not load {summary_file}: {e}")

    print(f"📚 Found {len(scraped_products)} previously scraped products")
    return scraped_products


def filter_new_products(all_products, scraped_products):
    """
    Filtra solo los productos que no han sido scrapeados antes
    """
    new_products = []
    for product in all_products:
        if product['product_id'] not in scraped_products:
            new_products.append(product)

    print(f"🆕 Found {len(new_products)} new products to scrape")
    return new_products


def save_incremental_progress(results, batch_number):
    """
    Guarda progreso incremental para evitar perder trabajo
    """
    filename = f"scraping_progress_batch_{batch_number}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"💾 Progress saved to {filename}")


def massive_product_analysis_v4_incremental(total_limit=200, batch_size=50):
    """
    Versión 4: Scraping incremental - solo productos nuevos
    """
    print("🚀 Starting incremental massive product analysis v4...")

    # Step 1: Cargar productos ya scrapeados
    print("\n📚 Loading previously scraped products...")
    scraped_products = load_existing_scraped_products()

    # Step 2: Obtener categorías disponibles
    print("\n📂 Getting available categories...")
    categories = get_available_categories()

    if categories:
        print(f"✅ Found {len(categories)} categories:")
        for cat in categories[:5]:  # Mostrar solo las primeras 5
            print(f"   - {cat['name']} ({cat['count']} products)")

    # Step 3: Obtener productos usando diferentes estrategias
    print(
        f"\n🔍 Collecting up to {total_limit} products using multiple search terms...")

    # Términos de búsqueda más diversos
    search_terms = [
        "tools", "electronics", "home", "automotive", "sports",
        "appliances", "toys", "hardware", "outdoor", "bedroom",
        "kitchen", "bathroom", "garden", "camping", "fitness",
        "cleaning", "storage", "lighting", "paint", "plumbing",
        "electrical", "safety", "bike", "winter", "summer",
        "Christmas", "BBQ", "pool", "lawn", "furniture"
    ]

    all_products = []
    products_per_term = total_limit // len(search_terms)

    for term in search_terms:
        if len(all_products) >= total_limit:
            break

        print(f"   Searching for: '{term}' (max {products_per_term} products)")
        products = get_products_from_search_v2(
            search_term=term,
            max_products=products_per_term
        )

        all_products.extend(products)
        print(f"   ✅ Found {len(products)} products for '{term}'")
        time.sleep(1)

    # Step 4: Remover duplicados
    unique_products = []
    seen_ids = set()

    for product in all_products:
        if product['product_id'] not in seen_ids and product['product_id']:
            unique_products.append(product)
            seen_ids.add(product['product_id'])

        if len(unique_products) >= total_limit:
            break

    print(f"\n📊 Total unique products found: {len(unique_products)}")

    # Step 5: Filtrar solo productos nuevos
    print("\n🔍 Filtering new products...")
    new_products = filter_new_products(unique_products, scraped_products)

    if not new_products:
        print("🎉 No new products to scrape! All products are already processed.")
        return []

    # Step 6: Guardar lista actualizada de productos
    timestamp = int(time.time())
    product_list_file = f"product_list_v4_{timestamp}.json"
    with open(product_list_file, "w", encoding="utf-8") as f:
        json.dump({
            'all_products': unique_products,
            'new_products': new_products,
            'already_scraped': len(scraped_products),
            'timestamp': timestamp
        }, f, indent=2, ensure_ascii=False)
    print(f"✅ Product lists saved to {product_list_file}")

    # Step 7: Scraping por lotes para control mejor
    print(
        f"\n🔄 Starting incremental review scraping for {len(new_products)} new products...")
    print(f"📦 Processing in batches of {batch_size}")

    all_results = []
    batch_number = 1

    for i in range(0, len(new_products), batch_size):
        batch = new_products[i:i + batch_size]
        print(
            f"\n🔄 Processing batch {batch_number}/{(len(new_products) + batch_size - 1) // batch_size}")
        print(f"   Products in this batch: {len(batch)}")

        try:
            batch_results = scrape_product_reviews_batch(batch, max_workers=3)
            all_results.extend(batch_results)

            # Guardar progreso incremental
            save_incremental_progress(batch_results, batch_number)

            # Mostrar estadísticas del lote
            successful = len(
                [r for r in batch_results if r['status'] == 'success'])
            failed = len([r for r in batch_results if r['status'] == 'error'])
            no_reviews = len(
                [r for r in batch_results if r['status'] == 'no_reviews'])

            print(
                f"   ✅ Batch {batch_number} complete: {successful} success, {failed} failed, {no_reviews} no reviews")

            # Pausa entre lotes para evitar rate limiting
            if i + batch_size < len(new_products):
                print("   ⏸️ Pausing 30 seconds between batches...")
                time.sleep(30)

        except Exception as e:
            print(f"❌ Error processing batch {batch_number}: {e}")
            continue

        batch_number += 1

    # Step 8: Guardar resumen final
    summary = {
        'timestamp': timestamp,
        'total_products_found': len(unique_products),
        'previously_scraped': len(scraped_products),
        'new_products_found': len(new_products),
        'new_products_processed': len(all_results),
        'categories_available': len(categories),
        'search_terms_used': search_terms,
        'successful_scrapes': len([r for r in all_results if r['status'] == 'success']),
        'failed_scrapes': len([r for r in all_results if r['status'] == 'error']),
        'no_reviews': len([r for r in all_results if r['status'] == 'no_reviews']),
        'api_version': 'v4_incremental',
        'batch_size': batch_size,
        'results': all_results
    }

    summary_file = f"scraping_summary_v4_{timestamp}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n📈 Incremental Analysis Complete!")
    print(f"🔍 Total products found: {len(unique_products)}")
    print(f"📚 Previously scraped: {len(scraped_products)}")
    print(f"🆕 New products found: {len(new_products)}")
    print(f"✅ Successfully scraped: {summary['successful_scrapes']}")
    print(f"❌ Failed scrapes: {summary['failed_scrapes']}")
    print(f"🔍 No reviews: {summary['no_reviews']}")
    print(f"💾 Summary saved to: {summary_file}")

    return all_results


def resume_failed_scraping():
    """
    Función para reanudar scraping de productos que fallaron anteriormente
    """
    print("🔄 Resuming failed scraping...")

    # Buscar summaries existentes
    summary_files = glob.glob("scraping_summary_v*.json")
    if not summary_files:
        print("❌ No previous scraping summaries found")
        return

    # Usar el summary más reciente
    latest_summary = max(summary_files, key=os.path.getctime)
    print(f"📄 Loading latest summary: {latest_summary}")

    with open(latest_summary, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # Encontrar productos que fallaron
    failed_products = []
    for result in summary.get('results', []):
        if result.get('status') in ['error', 'no_reviews']:
            # Crear estructura de producto básica
            product = {
                'product_id': result.get('product_id'),
                'name': result.get('name'),
                'category': 'Retry',
                'price': None,
                'url': f"https://www.canadiantire.ca/en/pdp/product/{result.get('product_id')}.html"
            }
            failed_products.append(product)

    if not failed_products:
        print("🎉 No failed products to retry!")
        return

    print(f"🔄 Found {len(failed_products)} failed products to retry")

    # Scraping de retry
    retry_results = scrape_product_reviews_batch(
        failed_products, max_workers=2)

    # Guardar resultados de retry
    timestamp = int(time.time())
    retry_summary = {
        'timestamp': timestamp,
        'original_summary': latest_summary,
        'retry_products': len(failed_products),
        'successful_retries': len([r for r in retry_results if r['status'] == 'success']),
        'failed_retries': len([r for r in retry_results if r['status'] == 'error']),
        'no_reviews_retries': len([r for r in retry_results if r['status'] == 'no_reviews']),
        'results': retry_results
    }

    with open(f"retry_summary_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(retry_summary, f, indent=2, ensure_ascii=False)

    print(
        f"✅ Retry complete: {retry_summary['successful_retries']} successful")
    return retry_results


def get_products_from_search_v2_improved(search_term="*", max_products=100, store_id="33"):
    """
    Método mejorado con paginación consistente y detección de duplicados
    """
    search_url = "https://apim.canadiantire.ca/v1/search/v2/search"

    all_products = []
    seen_product_ids = set()  # Para evitar duplicados
    page = 1
    rows_per_page = 50
    consecutive_empty_pages = 0
    max_empty_pages = 3  # Límite de páginas vacías consecutivas

    while len(all_products) < max_products and consecutive_empty_pages < max_empty_pages:
        # Usar offset basado en productos únicos realmente obtenidos
        start_offset = len(all_products)

        params = {
            "q": search_term,
            "store": store_id,
            "start": start_offset,  # Offset basado en productos únicos
            "rows": rows_per_page,
            "lang": "en_CA",
            "baseStoreId": "CTR",
            "apiversion": "5.5",
            "displaycode": "15041_3_0-en_ca",
            # Agregar parámetro para ordenamiento consistente
            "sort": "relevance desc, code asc"  # Ordenamiento determinístico
        }

        try:
            print(
                f"🔍 Fetching page {page} (offset: {start_offset}) for '{search_term}'")
            resp = requests.get(
                search_url, headers=BASE_HEADERS, params=params)

            if resp.status_code != 200:
                print(f"❌ Search API error: {resp.status_code}")
                print(f"Response: {resp.text[:500]}")
                break

            data = resp.json()
            products = data.get('products', [])

            if not products:
                consecutive_empty_pages += 1
                print(
                    f"⚠️ Empty page {page} (consecutive: {consecutive_empty_pages})")
                page += 1
                continue

            # Reset contador de páginas vacías
            consecutive_empty_pages = 0

            # Procesar productos y detectar duplicados
            new_products_in_page = 0
            for product in products:
                product_id = product.get('code')

                if not product_id:
                    continue

                # Verificar si ya tenemos este producto
                if product_id in seen_product_ids:
                    print(f"⚠️ Duplicate product found: {product_id}")
                    continue

                # Agregar a conjunto de IDs vistos
                seen_product_ids.add(product_id)

                # Crear info del producto
                product_info = {
                    'product_id': product_id,
                    'name': product.get('title'),
                    'category': extract_category_from_breadcrumb(product.get('breadcrumbList', [])),
                    'price': extract_price_info(product),
                    'url': f"https://www.canadiantire.ca{product.get('url', '')}",
                    'brand': product.get('brand', {}).get('label'),
                    'rating': product.get('rating'),
                    'ratings_count': product.get('ratingsCount'),
                    'badges': product.get('badges', []),
                    'image': get_main_image(product.get('images', []))
                }

                all_products.append(product_info)
                new_products_in_page += 1

                # Verificar si alcanzamos el límite
                if len(all_products) >= max_products:
                    break

            print(
                f"✅ Page {page}: {new_products_in_page} new products (Total: {len(all_products)})")

            # Verificar paginación desde la respuesta de la API
            pagination = data.get('pagination', {})
            total_results = pagination.get('totalResults', 0)

            # Si no hay más resultados disponibles
            if start_offset + rows_per_page >= total_results:
                print(
                    f"📄 Reached end of results (Total available: {total_results})")
                break

            # Si esta página no agregó productos nuevos, podríamos estar en un loop
            if new_products_in_page == 0:
                consecutive_empty_pages += 1
                print(f"⚠️ No new products in page {page}")

            page += 1
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"❌ Error fetching page {page}: {e}")
            break

    print(
        f"🎯 Final results: {len(all_products)} unique products from {len(seen_product_ids)} total")
    return all_products


def analyze_search_pagination(search_term, max_pages=10):
    """
    Función para analizar cómo funciona la paginación de una búsqueda específica
    """
    search_url = "https://apim.canadiantire.ca/v1/search/v2/search"

    print(f"🔍 Analyzing pagination for search term: '{search_term}'")

    pagination_analysis = {
        'search_term': search_term,
        'pages_analyzed': [],
        'total_unique_products': 0,
        'duplicates_found': 0,
        'pagination_info': {}
    }

    seen_products = set()
    rows_per_page = 20  # Usar menos productos para análisis

    for page in range(1, max_pages + 1):
        start_offset = (page - 1) * rows_per_page

        params = {
            "q": search_term,
            "store": "33",
            "start": start_offset,
            "rows": rows_per_page,
            "lang": "en_CA",
            "sort": "relevance desc, code asc"
        }

        try:
            resp = requests.get(
                search_url, headers=BASE_HEADERS, params=params)

            if resp.status_code != 200:
                print(f"❌ Error on page {page}: {resp.status_code}")
                break

            data = resp.json()
            products = data.get('products', [])
            pagination = data.get('pagination', {})

            # Analizar productos en esta página
            page_products = []
            duplicates_in_page = 0

            for product in products:
                product_id = product.get('code')
                if product_id:
                    if product_id in seen_products:
                        duplicates_in_page += 1
                        pagination_analysis['duplicates_found'] += 1
                    else:
                        seen_products.add(product_id)
                        pagination_analysis['total_unique_products'] += 1

                    page_products.append({
                        'id': product_id,
                        'name': product.get('title', '')[:50],
                        'is_duplicate': product_id in seen_products
                    })

            page_info = {
                'page': page,
                'offset': start_offset,
                'products_returned': len(products),
                'unique_products': len(products) - duplicates_in_page,
                'duplicates': duplicates_in_page,
                'pagination_data': pagination,
                'sample_products': page_products[:5]  # Primeros 5 para muestra
            }

            pagination_analysis['pages_analyzed'].append(page_info)

            print(
                f"📄 Page {page}: {len(products)} products, {duplicates_in_page} duplicates")

            # Verificar si llegamos al final
            total_results = pagination.get('totalResults', 0)
            if start_offset + rows_per_page >= total_results:
                print(f"📄 Reached end: {total_results} total results")
                pagination_analysis['pagination_info'] = pagination
                break

            time.sleep(0.3)

        except Exception as e:
            print(f"❌ Error analyzing page {page}: {e}")
            break

    # Guardar análisis
    timestamp = int(time.time())
    filename = f"pagination_analysis_{search_term}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(pagination_analysis, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Pagination Analysis Results:")
    print(f"🔍 Search term: {search_term}")
    print(f"📄 Pages analyzed: {len(pagination_analysis['pages_analyzed'])}")
    print(f"🎯 Unique products: {pagination_analysis['total_unique_products']}")
    print(f"🔄 Duplicates found: {pagination_analysis['duplicates_found']}")
    print(f"💾 Analysis saved to: {filename}")

    return pagination_analysis


def test_different_pagination_strategies(search_term="tools"):
    """
    Prueba diferentes estrategias de paginación para encontrar la mejor
    """
    print(f"🧪 Testing pagination strategies for '{search_term}'")

    strategies = [
        {
            "name": "Page-based",
            "params_func": lambda page, rows: {"page": page, "rows": rows}
        },
        {
            "name": "Offset-based",
            "params_func": lambda page, rows: {"start": (page-1)*rows, "rows": rows}
        },
        {
            "name": "Hybrid",
            "params_func": lambda page, rows: {"page": page, "start": (page-1)*rows, "rows": rows}
        }
    ]

    results = {}

    for strategy in strategies:
        print(f"\n🔬 Testing strategy: {strategy['name']}")

        seen_products = set()
        unique_count = 0
        duplicate_count = 0

        for page in range(1, 6):  # Test 5 pages
            params = {
                "q": search_term,
                "store": "33",
                "lang": "en_CA",
                **strategy["params_func"](page, 20)
            }

            try:
                resp = requests.get("https://apim.canadiantire.ca/v1/search/v2/search",
                                    headers=BASE_HEADERS, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    products = data.get('products', [])

                    for product in products:
                        product_id = product.get('code')
                        if product_id:
                            if product_id in seen_products:
                                duplicate_count += 1
                            else:
                                seen_products.add(product_id)
                                unique_count += 1

                time.sleep(0.3)

            except Exception as e:
                print(f"❌ Error in {strategy['name']} page {page}: {e}")

        results[strategy['name']] = {
            'unique_products': unique_count,
            'duplicates': duplicate_count,
            'efficiency': unique_count / (unique_count + duplicate_count) if (unique_count + duplicate_count) > 0 else 0
        }

        print(f"   ✅ Unique: {unique_count}, Duplicates: {duplicate_count}")

    # Encontrar mejor estrategia
    best_strategy = max(results.keys(), key=lambda k: results[k]['efficiency'])

    print(f"\n🏆 Best strategy: {best_strategy}")
    print(f"📊 Results summary:")
    for strategy, data in results.items():
        print(
            f"   {strategy}: {data['unique_products']} unique ({data['efficiency']:.2%} efficiency)")

    return results

# Actualizar la función principal para usar la versión mejorada


def massive_product_analysis_v5_optimized(total_limit=350, batch_size=50):
    """
    Versión 5: Con paginación optimizada y análisis de duplicados
    """
    print("🚀 Starting optimized massive product analysis v5...")

    # Step 0: Analizar paginación si es necesario
    print("\n🔬 Testing pagination strategy...")
    test_different_pagination_strategies("tools")

    # Step 1: Cargar productos ya scrapeados
    print("\n📚 Loading previously scraped products...")
    scraped_products = load_existing_scraped_products()

    # Step 2: Obtener productos con paginación mejorada
    search_terms = [
        "tools", "electronics", "home", "automotive", "sports",
        "appliances", "toys", "hardware", "outdoor", "bedroom",
        "kitchen", "bathroom", "garden", "camping", "fitness"
    ]

    all_products = []
    products_per_term = max(total_limit // len(search_terms), 10)

    for term in search_terms:
        if len(all_products) >= total_limit:
            break

        print(
            f"\n🔍 Searching for: '{term}' (target: {products_per_term} products)")

        # Usar la función mejorada
        products = get_products_from_search_v2_improved(
            search_term=term,
            max_products=products_per_term
        )

        all_products.extend(products)
        print(
            f"   ✅ Added {len(products)} products for '{term}' (Total: {len(all_products)})")
        time.sleep(2)  # Pausa más larga entre términos

    # Resto del código igual...
    unique_products = []
    seen_ids = set()

    for product in all_products:
        if product['product_id'] not in seen_ids and product['product_id']:
            unique_products.append(product)
            seen_ids.add(product['product_id'])

        if len(unique_products) >= total_limit:
            break

    print(f"\n📊 Final unique products: {len(unique_products)}")

    # Continuar con el proceso normal de filtrado y scraping...
    new_products = filter_new_products(unique_products, scraped_products)

    if not new_products:
        print("🎉 No new products to scrape!")
        return []

    # Procesar en lotes
    results = []
    for i in range(0, len(new_products), batch_size):
        batch = new_products[i:i + batch_size]
        batch_results = scrape_product_reviews_batch(batch, max_workers=3)
        results.extend(batch_results)

        if i + batch_size < len(new_products):
            time.sleep(30)  # Pausa entre lotes

    return results


# Actualizar el main para incluir nuevas opciones
if __name__ == "__main__":
    choice = input(
        "¿Qué tipo de análisis?\n"
        "1: Producto individual\n"
        "2: Análisis masivo v1 (original)\n"
        "3: Análisis masivo v2 (comentado)\n"
        "4: Análisis masivo v3 (API v2)\n"
        "5: Análisis incremental v4 [NUEVO - solo productos nuevos]\n"
        "6: Reanudar scraping fallido\n"
        "Opción: "
    )

    if choice == "5":
        # Nueva versión incremental
        total_limit = int(
            input("Límite total de productos (default 200): ") or "200")
        batch_size = int(input("Tamaño de lote (default 50): ") or "50")
        massive_product_analysis_v5_optimized(total_limit, batch_size)

    elif choice == "6":
        # Reanudar productos fallidos
        resume_failed_scraping()

    elif choice == "4":
        # Versión v3 original
        total_limit = int(
            input("Límite total de productos (default 100): ") or "100")
        massive_product_analysis_v3(total_limit)

    elif choice == "2":
        # Versión original (con problemas)
        products_per_category = int(
            input("Productos por categoría (default 20): ") or "20")
        total_limit = int(
            input("Límite total de productos (default 200): ") or "200")
        massive_product_analysis(products_per_category, total_limit)

    else:
        # Código original para producto individual
        product_id = input("Ingresa el product_id: ") or "0762121P"

        print("Fetching reviews...")
        reviews = fetch_reviews(product_id)
        print(f"✅ Total reviews fetched: {len(reviews)}")

        print("\nFetching highlights...")
        highlights = fetch_highlights(product_id)
        print(f"✅ Highlights found: {len(highlights.keys())}")

        print("\nFetching features...")
        features = fetch_features(product_id)
        print(f"✅ Features found: {[f['feature'] for f in features]}")

        print("\nExporting to JSON...")
        if reviews:
            export_reviews_to_json(reviews, highlights,
                                   features, f"reviews_{product_id}.json")
