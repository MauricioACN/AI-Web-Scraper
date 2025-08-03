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

    # Use original headers without modifying Accept-Encoding
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

        # Simplify: use resp.json() directly
        try:
            data = resp.json()
            print("✅ JSON parsed successfully")
        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
            print("Raw response preview:", resp.content[:200])
            break

        # Access results correctly
        response_data = data.get("response", {})
        reviews = response_data.get("Results", [])

        if not reviews:
            print("No more reviews found")
            break

        all_reviews.extend(reviews)
        offset += limit
        print(f"✅ Fetched {len(all_reviews)} reviews so far...")

        # Avoid rate limiting
        time.sleep(0.5)

        # Limit for testing (optional)
        if len(all_reviews) >= 100:  # Limit to 100 for testing
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


def scrape_product_reviews_batch(product_list, max_workers=5):
    """
    Massive review scraping using threading
    """
    def scrape_single_product(product):
        product_id = product['product_id']
        print(f"🔄 Processing {product['name']} ({product_id})")

        try:
            # Fetch data for this product
            # Limit for efficiency
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


def extract_category_from_breadcrumb(breadcrumb_list):
    """
    Extracts the main category from breadcrumb
    """
    if breadcrumb_list and len(breadcrumb_list) > 0:
        return breadcrumb_list[-1] if isinstance(breadcrumb_list, list) else "Unknown"
    return "Unknown"


def extract_price_info(product):
    """
    Extracts price information from product
    """
    # In the new API, price could be in different places
    if product.get('currentPrice'):
        return product.get('currentPrice')
    return None


def get_main_image(images):
    """
    Gets the main product image
    """
    if images and len(images) > 0:
        return images[0].get('url')
    return None


def load_existing_scraped_products():
    """
    Loads the list of products that have been successfully scraped
    """
    scraped_products = set()

    # Search for existing review files
    review_files = glob.glob("reviews_*.json")
    for file in review_files:
        # Extract product_id from filename
        product_id = file.replace("reviews_", "").replace(".json", "")
        scraped_products.add(product_id)

    # Also load from previous summaries if they exist
    summary_files = ["scraping_summary.json", "scraping_summary_v3.json"]
    for summary_file in summary_files:
        if os.path.exists(summary_file):
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    summary = json.load(f)

                # Add successfully scraped products
                for result in summary.get('results', []):
                    if result.get('status') == 'success':
                        scraped_products.add(result.get('product_id'))
            except Exception as e:
                print(f"⚠️ Warning: Could not load {summary_file}: {e}")

    print(f"📚 Found {len(scraped_products)} previously scraped products")
    return scraped_products


def filter_new_products(all_products, scraped_products):
    """
    Filters only products that haven't been scraped before
    """
    new_products = []
    for product in all_products:
        if product['product_id'] not in scraped_products:
            new_products.append(product)

    print(f"🆕 Found {len(new_products)} new products to scrape")
    return new_products


def resume_failed_scraping():
    """
    Function to resume scraping of products that failed previously
    """
    print("🔄 Resuming failed scraping...")

    # Search for existing summaries
    summary_files = glob.glob("scraping_summary_v*.json")
    if not summary_files:
        print("❌ No previous scraping summaries found")
        return

    # Use the most recent summary
    latest_summary = max(summary_files, key=os.path.getctime)
    print(f"📄 Loading latest summary: {latest_summary}")

    with open(latest_summary, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # Find products that failed
    failed_products = []
    for result in summary.get('results', []):
        if result.get('status') in ['error', 'no_reviews']:
            # Create basic product structure
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

    # Retry scraping
    retry_results = scrape_product_reviews_batch(
        failed_products, max_workers=2)

    # Save retry results
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
    Improved method with consistent pagination and duplicate detection
    """
    search_url = "https://apim.canadiantire.ca/v1/search/v2/search"

    all_products = []
    seen_product_ids = set()  # To avoid duplicates
    page = 1
    rows_per_page = 50
    consecutive_empty_pages = 0
    max_empty_pages = 3  # Limit of consecutive empty pages

    while len(all_products) < max_products and consecutive_empty_pages < max_empty_pages:
        # Use offset based on unique products actually obtained
        start_offset = len(all_products)

        params = {
            "q": search_term,
            "store": store_id,
            "start": start_offset,  # Offset based on unique products
            "rows": rows_per_page,
            "lang": "en_CA",
            "baseStoreId": "CTR",
            "apiversion": "5.5",
            "displaycode": "15041_3_0-en_ca",
            # Add parameter for consistent sorting
            "sort": "relevance desc, code asc"  # Deterministic sorting
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

            # Reset empty pages counter
            consecutive_empty_pages = 0

            # Process products and detect duplicates
            new_products_in_page = 0
            for product in products:
                product_id = product.get('code')

                if not product_id:
                    continue

                # Check if we already have this product
                if product_id in seen_product_ids:
                    print(f"⚠️ Duplicate product found: {product_id}")
                    continue

                # Add to seen IDs set
                seen_product_ids.add(product_id)

                # Create product info
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

                # Check if we reached the limit
                if len(all_products) >= max_products:
                    break

            print(
                f"✅ Page {page}: {new_products_in_page} new products (Total: {len(all_products)})")

            # Check pagination from API response
            pagination = data.get('pagination', {})
            total_results = pagination.get('totalResults', 0)

            # If no more results available
            if start_offset + rows_per_page >= total_results:
                print(
                    f"📄 Reached end of results (Total available: {total_results})")
                break

            # If this page didn't add new products, we might be in a loop
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


def test_different_pagination_strategies(search_term="tools"):
    """
    Tests different pagination strategies to find the best one
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

    # Find best strategy
    best_strategy = max(results.keys(), key=lambda k: results[k]['efficiency'])

    print(f"\n🏆 Best strategy: {best_strategy}")
    print(f"📊 Results summary:")
    for strategy, data in results.items():
        print(
            f"   {strategy}: {data['unique_products']} unique ({data['efficiency']:.2%} efficiency)")

    return results


def massive_product_analysis_v5_optimized(total_limit=350, batch_size=50):
    """
    Version 5: With optimized pagination and duplicate analysis
    """
    print("🚀 Starting optimized massive product analysis v5...")

    # Step 0: Analyze pagination if necessary
    print("\n🔬 Testing pagination strategy...")
    test_different_pagination_strategies("tools")

    # Step 1: Load already scraped products
    print("\n📚 Loading previously scraped products...")
    scraped_products = load_existing_scraped_products()

    # Step 2: Get products with improved pagination
    search_terms = [
        "power tools", "hand tools", "kitchen appliances", "bathroom fixtures",
        "outdoor furniture", "camping gear", "fitness equipment", "automotive parts",
        "home security", "lighting fixtures", "storage solutions", "cleaning supplies",
        "pet supplies", "baby products", "seasonal decorations", "plumbing supplies",
        "electrical components", "paint supplies", "flooring materials", "window treatments",
        "garage organization", "lawn care", "snow removal", "pool supplies",
        "workshop equipment", "safety gear", "heating cooling", "smart home devices"
    ]

    all_products = []
    products_per_term = max(total_limit // len(search_terms), 10)

    for term in search_terms:
        if len(all_products) >= total_limit:
            break

        print(
            f"\n🔍 Searching for: '{term}' (target: {products_per_term} products)")

        # Use the improved function
        products = get_products_from_search_v2_improved(
            search_term=term,
            max_products=products_per_term
        )

        all_products.extend(products)
        print(
            f"   ✅ Added {len(products)} products for '{term}' (Total: {len(all_products)})")
        time.sleep(2)  # Longer pause between terms

    # Rest of code same...
    unique_products = []
    seen_ids = set()

    for product in all_products:
        if product['product_id'] not in seen_ids and product['product_id']:
            unique_products.append(product)
            seen_ids.add(product['product_id'])

        if len(unique_products) >= total_limit:
            break

    print(f"\n📊 Final unique products: {len(unique_products)}")

    # Continue with normal filtering and scraping process...
    new_products = filter_new_products(unique_products, scraped_products)

    if not new_products:
        print("🎉 No new products to scrape!")
        return []

    # Process in batches
    results = []
    for i in range(0, len(new_products), batch_size):
        batch = new_products[i:i + batch_size]
        batch_results = scrape_product_reviews_batch(batch, max_workers=3)
        results.extend(batch_results)

        if i + batch_size < len(new_products):
            time.sleep(30)  # Pause between batches

    return results


# Update main to include new options
if __name__ == "__main__":
    choice = input(
        "What type of analysis?\n"
        "1: Individual product\n"
        "5: Incremental analysis v5 [optimized - new products only]\n"
        "6: Resume failed scraping\n"
        "Option: "
    )

    if choice == "5":
        # New incremental version
        total_limit = int(
            input("Total product limit (default 200): ") or "200")
        batch_size = int(input("Batch size (default 50): ") or "50")
        massive_product_analysis_v5_optimized(total_limit, batch_size)

    elif choice == "6":
        # Resume failed products
        resume_failed_scraping()

    else:
        # Original code for individual product
        product_id = input("Enter product_id: ") or "0762121P"

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
