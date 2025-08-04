import json
import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()

# MongoDB connection
uri = "mongodb+srv://alejandrocanomn:" + \
    os.getenv("DB_PASSWORD") + \
    "@cluster0.vlqder.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"


def save_reviews_fixed(reviews_collection, product_id, reviews, source):
    """Save reviews using ONLY review_id for duplicate detection (the correct way)."""
    saved_count = 0
    anonymous_counter = 1

    for review in reviews:
        # Get the original review_id (which should be unique)
        review_id = review.get('review_id')

        if not review_id:
            print(
                f"      ⚠️ Skipping review without review_id in {product_id}")
            continue

        # Handle author (for display only, not for duplicate detection)
        author = review.get('author')
        if author is None or author == "":
            author = f"Anonymous_{anonymous_counter}"
            anonymous_counter += 1
        else:
            author = str(author)

        # Handle rating
        rating = review.get('rating', 0)
        if rating is None:
            rating = 0

        # Handle date conversion (keeping your existing logic)
        review_date = None
        submission_time = review.get('submission_time') or review.get('date')

        if submission_time:
            try:
                if 'T' in str(submission_time):
                    clean_date = re.sub(r'\.\d+.*$', '', str(submission_time))
                    clean_date = clean_date.replace('Z', '')
                    try:
                        review_date = datetime.fromisoformat(clean_date)
                    except:
                        clean_date = clean_date.replace('T', ' ')
                        review_date = datetime.strptime(
                            clean_date, '%Y-%m-%d %H:%M:%S')
                else:
                    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
                    for fmt in formats:
                        try:
                            review_date = datetime.strptime(
                                str(submission_time), fmt)
                            break
                        except:
                            continue
            except Exception as e:
                print(
                    f"      ⚠️ Date parsing error for {submission_time}: {e}")
                review_date = None

        # Create review document
        review_doc = {
            'product_id': product_id,
            'review_id': review_id,  # Use original review_id directly
            'author': author,
            'rating': int(rating),
            'title': review.get('title') or "",
            'text': review.get('text') or "",
            'submission_time': review_date,
            'submission_time_string': str(submission_time) if submission_time else "",
            'verified_purchase': review.get('verified_purchase', False),
            'helpful_count': review.get('helpful_count', 0),
            'comments': review.get('comments', []),
            'source': source,
            'created_at': datetime.utcnow()
        }

        # SIMPLE: Check only by review_id (since it's unique)
        existing = reviews_collection.find_one({'review_id': review_id})

        if not existing:
            try:
                reviews_collection.insert_one(review_doc)
                saved_count += 1

                if saved_count <= 3:
                    date_display = review_date.strftime(
                        '%Y-%m-%d') if review_date else 'No date'
                    print(
                        f"      📝 {author} ({rating}⭐) - {date_display} - ID:{review_id}")

            except Exception as e:
                # Handle any remaining index conflicts
                if 'E11000' in str(e):
                    print(
                        f"      ⚠️ Index conflict for review_id: {review_id}")
                    print(
                        f"         Run 'python fix_indexes.py' to resolve index issues")
                else:
                    print(f"   ⚠️ Error saving review {review_id}: {e}")
                continue
        else:
            print(f"      ⏭️ Review {review_id} already exists")

    return saved_count


def create_product_document_fixed(product_id, data):
    """Create product document handling various data structures."""

    # Handle different possible structures
    product_name = ""
    total_reviews = 0
    average_rating = 0.0
    category = ""
    url = ""
    brand = ""
    scraping_date = ""

    # Extract from different possible keys
    if isinstance(data, dict):
        # Common keys from your review files
        product_name = (data.get('product_name') or
                        data.get('name') or
                        data.get('title') or "")

        total_reviews = (data.get('total_reviews') or
                         data.get('review_count') or
                         len(data.get('reviews', [])))

        average_rating = (data.get('average_rating') or
                          data.get('avg_rating') or
                          data.get('rating') or 0.0)

        category = (data.get('category') or
                    data.get('product_category') or "")

        url = (data.get('product_url') or
               data.get('url') or "")

        brand = (data.get('brand') or
                 data.get('manufacturer') or "")

        scraping_date = (data.get('scraping_date') or
                         data.get('scraped_at') or
                         data.get('timestamp') or "")

    # Ensure proper types
    try:
        total_reviews = int(total_reviews) if total_reviews is not None else 0
    except (ValueError, TypeError):
        total_reviews = 0

    try:
        average_rating = float(
            average_rating) if average_rating is not None else 0.0
    except (ValueError, TypeError):
        average_rating = 0.0

    return {
        'product_id': product_id,
        'name': str(product_name),
        'total_reviews': total_reviews,
        'average_rating': round(average_rating, 2),
        'category': str(category),
        'url': str(url),
        'brand': str(brand),
        'scraping_date': str(scraping_date),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }


def save_price_data_fixed(prices_collection, product_id, price_data):
    """Save price data handling both NEW direct structure and OLD api_data structure."""
    try:
        # Initialize variables
        current_price = None
        original_price = None
        sale_price = None
        currency = 'CAD'
        in_stock = False
        inventory_count = 0
        scraped_at = price_data.get('scraped_at')
        store_shelf_location = ''
        urgent_low_stock = False
        warranty = ''

        # Check if this is the NEW structure (direct fields)
        if 'current_price' in price_data:
            # NEW STRUCTURE: Direct fields
            current_price = price_data.get('current_price')
            original_price = price_data.get('original_price')
            sale_price = price_data.get('sale_price')
            currency = price_data.get('currency', 'CAD')
            in_stock = price_data.get('in_stock', False)
            inventory_count = price_data.get('inventory_count', 0)

            # Handle store availability nested object
            store_availability = price_data.get('store_availability', {})
            store_shelf_location = store_availability.get(
                'store_shelf_location', '')
            urgent_low_stock = store_availability.get(
                'urgent_low_stock', False)
            warranty = store_availability.get('warranty', '')

        elif 'api_data' in price_data:
            # OLD STRUCTURE: api_data.skus format
            api_data = price_data.get('api_data', {})
            skus = api_data.get('skus', [])

            if skus and len(skus) > 0:
                sku = skus[0]  # Use first SKU

                # Extract price from currentPrice.value
                current_price_obj = sku.get('currentPrice')
                if current_price_obj and isinstance(current_price_obj, dict):
                    current_price = current_price_obj.get('value')

                # Extract original price
                original_price = sku.get('originalPrice')

                # Determine if on sale
                is_on_sale = sku.get('isOnSale', False)
                if is_on_sale and current_price and original_price:
                    sale_price = current_price
                    # current_price becomes original_price in this case
                    current_price, original_price = original_price, current_price

                # Extract availability info
                fulfillment = sku.get('fulfillment', {})
                availability = fulfillment.get('availability', {})

                # Check if orderable/sellable
                in_stock = sku.get('sellable', False) and sku.get(
                    'orderable', False)

                # Try to get inventory count
                corporate_info = availability.get('Corporate', {})
                inventory_count = corporate_info.get(
                    'Quantity', 0) or availability.get('quantity', 0)

                # Store location
                store_shelf_location = sku.get('storeShelfLocation', '')

                # Check for low stock
                urgent_low_stock = sku.get('isUrgentLowStock', False)

                # Warranty
                warranty = sku.get('warrantyMessage', '')

        # Convert scraped_at to datetime if it exists
        scraped_datetime = None
        if scraped_at:
            try:
                # Remove microseconds and convert
                clean_date = re.sub(r'\.\d+.*$', '', str(scraped_at))
                scraped_datetime = datetime.fromisoformat(clean_date)
            except Exception as e:
                print(f"      ⚠️ Date parsing error for {scraped_at}: {e}")
                scraped_datetime = None

        # Validate and convert price data
        if current_price is not None:
            try:
                current_price = float(current_price)
            except (ValueError, TypeError):
                current_price = None

        if original_price is not None:
            try:
                original_price = float(original_price)
            except (ValueError, TypeError):
                original_price = None

        if sale_price is not None:
            try:
                sale_price = float(sale_price)
            except (ValueError, TypeError):
                sale_price = None

        # Create price document
        price_doc = {
            'product_id': product_id,
            'current_price': current_price,
            'original_price': original_price,
            'sale_price': sale_price,
            'currency': str(currency),
            'in_stock': bool(in_stock),
            'inventory_count': int(inventory_count) if inventory_count is not None else 0,
            'store_shelf_location': str(store_shelf_location),
            'urgent_low_stock': bool(urgent_low_stock),
            'warranty': str(warranty),
            'scraped_at': scraped_datetime,
            'scraped_at_string': str(scraped_at) if scraped_at else "",
            'timestamp': datetime.utcnow(),
            'raw_data': price_data  # Keep original for reference
        }

        # Only save if we have actual price data
        if current_price is not None and current_price > 0:
            prices_collection.insert_one(price_doc)
            stock_text = "In Stock" if in_stock else "Out of Stock"
            sale_text = f" (Sale: ${sale_price})" if sale_price else ""
            print(
                f"      💰 Price: ${current_price} {currency}{sale_text} - {stock_text} ({inventory_count} available)")
            return True
        else:
            print(f"      ⚠️ No valid price found for {product_id}")
            return False

    except Exception as e:
        print(f"   ❌ Price save error for {product_id}: {e}")
        return False


def load_products_from_json(products_collection, json_file_path):
    """Load products from the product list JSON file."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        products = data.get('all_products', [])
        print(f"📦 Loading products from {json_file_path}...")
        print(f"   Found {len(products)} products")

        loaded_count = 0

        for product in products:
            try:
                # Extract product data
                product_id = product.get('product_id')
                if not product_id:
                    print(f"   ⚠️ Skipping product without product_id")
                    continue

                # Create product document matching the expected structure
                product_doc = {
                    'product_id': product_id,
                    # MongoDB validation requires 'name' field
                    'name': product.get('name', ''),
                    # Keep for compatibility
                    'product_name': product.get('name', ''),
                    'category': product.get('category', 'Unknown'),
                    'brand': product.get('brand', ''),
                    'url': product.get('url', ''),
                    'image': product.get('image', ''),
                    'price': product.get('price', {}).get('value', 0.0),
                    'max_price': product.get('price', {}).get('maxPrice'),
                    'min_price': product.get('price', {}).get('minPrice'),
                    'rating': product.get('rating', 0.0),
                    'ratings_count': product.get('ratings_count', 0),
                    'badges': product.get('badges', []),
                    'last_updated': datetime.now()
                }

                # Check if product already exists
                existing = products_collection.find_one(
                    {'product_id': product_id})
                if existing:
                    print(f"      ⏭️ Product {product_id} already exists")
                else:
                    # Save new product
                    save_product(products_collection, product_doc)
                    loaded_count += 1
                    print(
                        f"      ✅ Product {product_id}: {product_doc['product_name']}")

            except Exception as e:
                print(
                    f"   ❌ Error processing product {product.get('product_id', 'Unknown')}: {e}")
                continue

        print(f"   ✅ Loaded {loaded_count} new products")
        return loaded_count

    except Exception as e:
        print(f"❌ Error loading products from JSON: {e}")
        return 0


def load_products_only():
    """Load ONLY products from the JSON file to MongoDB."""
    print("📦 Loading ONLY products to MongoDB...")

    # Connect to MongoDB
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client.canadiantire_scraper
    products_collection = db.products

    # Load products from JSON
    product_json_file = "product_list_v4_1754202926.json"

    if os.path.exists(product_json_file):
        products_loaded = load_products_from_json(
            products_collection, product_json_file)
        print(f"\n🎉 Products migration completed! Loaded: {products_loaded}")
    else:
        print(f"❌ Product JSON file not found: {product_json_file}")
        products_loaded = 0

    client.close()
    return products_loaded


def load_all_data_to_mongodb_fixed():
    """Load all data with improved error handling and structure detection."""

    print("🚀 Starting improved data migration to MongoDB...")

    # Connect to MongoDB
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client.canadiantire_scraper

    # Get collections
    products_collection = db.products
    reviews_collection = db.reviews
    prices_collection = db.prices

    # Statistics
    stats = {
        'products_loaded': 0,
        'reviews_loaded': 0,
        'prices_loaded': 0,
        'errors': []
    }

    # 0. Load Products from JSON file
    print("\n📦 Loading products from JSON...")
    product_json_file = "product_list_v4_1754202926.json"

    if os.path.exists(product_json_file):
        products_loaded = load_products_from_json(
            products_collection, product_json_file)
        stats['products_loaded'] += products_loaded
    else:
        print(f"   ⚠️ Product JSON file not found: {product_json_file}")

    # 1. Load Reviews Data
    print("\n📚 Loading reviews data...")
    reviews_folder = "data_review"

    if os.path.exists(reviews_folder):
        files = [f for f in os.listdir(reviews_folder) if f.endswith('.json')]
        print(f"   Found {len(files)} review files")

        for filename in files:
            try:
                file_path = os.path.join(reviews_folder, filename)

                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract product ID
                product_id = extract_product_id_from_filename(filename)

                if not product_id:
                    print(
                        f"   ⚠️ Could not extract product ID from {filename}")
                    continue

                # Process data
                if isinstance(data, dict):
                    # Save product information
                    product_doc = create_product_document_fixed(
                        product_id, data)
                    save_product(products_collection, product_doc)
                    stats['products_loaded'] += 1

                    # Save reviews
                    reviews = data.get('reviews', [])
                    if reviews:
                        reviews_saved = save_reviews_fixed(
                            reviews_collection, product_id, reviews, "api")
                        stats['reviews_loaded'] += reviews_saved

                print(
                    f"   ✅ {filename}: {len(reviews) if 'reviews' in locals() else 0} reviews")

            except Exception as e:
                error_msg = f"Error processing {filename}: {e}"
                print(f"   ❌ {error_msg}")
                stats['errors'].append(error_msg)

    # 2. Load Price Data
    print("\n💰 Loading price data...")
    price_folder = "price_data"

    if os.path.exists(price_folder):
        files = [f for f in os.listdir(price_folder) if f.endswith('.json')]
        print(f"   Found {len(files)} price files")

        for filename in files:
            try:
                file_path = os.path.join(price_folder, filename)

                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract product ID
                product_id = extract_product_id_from_filename(filename)

                if not product_id:
                    continue

                # Save price data
                if isinstance(data, dict):
                    price_saved = save_price_data_fixed(
                        prices_collection, product_id, data)
                    if price_saved:
                        stats['prices_loaded'] += 1

                print(f"   ✅ {filename}")

            except Exception as e:
                error_msg = f"Error processing {filename}: {e}"
                print(f"   ❌ {error_msg}")
                stats['errors'].append(error_msg)

    # 3. Load Selenium Reviews
    print("\n🔍 Loading selenium reviews data...")
    selenium_folder = "selenium_reviews"

    if os.path.exists(selenium_folder):
        files = [f for f in os.listdir(selenium_folder)
                 if f.endswith('.json') and 'selenium_reviews_' in f]
        print(f"   Found {len(files)} selenium review files")

        for filename in files:
            try:
                file_path = os.path.join(selenium_folder, filename)

                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract product ID
                product_id = extract_product_id_from_filename(filename)

                if not product_id:
                    continue

                # Process selenium reviews
                if isinstance(data, dict):
                    reviews = data.get('reviews', [])
                    if reviews:
                        reviews_saved = save_reviews_fixed(
                            reviews_collection, product_id, reviews, "selenium")
                        stats['reviews_loaded'] += reviews_saved

                print(
                    f"   ✅ {filename}: {len(reviews) if 'reviews' in locals() else 0} reviews")

            except Exception as e:
                error_msg = f"Error processing {filename}: {e}"
                print(f"   ❌ {error_msg}")
                stats['errors'].append(error_msg)

    # Close connection
    client.close()

    # Print final statistics
    print_final_stats(stats)


def extract_product_id_from_filename(filename):
    """Extract product ID from filename using regex."""
    patterns = [
        r'reviews_(\d+P?)\.json',
        r'price_(\d+P?)\.json',
        r'selenium_reviews_(\d+P?)\.json'
    ]

    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            product_id = match.group(1)
            if not product_id.endswith('P'):
                product_id += 'P'
            return product_id

    return None


def save_product(products_collection, product_doc):
    """Save or update product in MongoDB."""
    products_collection.update_one(
        {'product_id': product_doc['product_id']},
        {'$set': product_doc},
        upsert=True
    )


def print_final_stats(stats):
    """Print final migration statistics."""
    print("\n" + "="*50)
    print("📊 MIGRATION COMPLETED!")
    print("="*50)
    print(f"✅ Products loaded: {stats['products_loaded']}")
    print(f"✅ Reviews loaded: {stats['reviews_loaded']}")
    print(f"✅ Prices loaded: {stats['prices_loaded']}")

    if stats['errors']:
        print(f"\n⚠️ Errors encountered: {len(stats['errors'])}")
        for error in stats['errors'][:3]:  # Show first 3 errors
            print(f"   - {error}")
        if len(stats['errors']) > 3:
            print(f"   ... and {len(stats['errors']) - 3} more errors")

    total_docs = stats['products_loaded'] + \
        stats['reviews_loaded'] + stats['prices_loaded']
    print(f"\n🎉 Total documents loaded: {total_docs}")


def verify_data_loaded():
    """Verify that data was loaded correctly."""
    print("\n🔍 Verifying loaded data...")

    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client.canadiantire_scraper

    # Count documents
    products_count = db.products.count_documents({})
    reviews_count = db.reviews.count_documents({})
    prices_count = db.prices.count_documents({})

    print(f"📦 Products: {products_count}")
    print(f"💬 Reviews: {reviews_count}")
    print(f"💰 Prices: {prices_count}")

    # Show samples with proper data
    if reviews_count > 0:
        sample_review = db.reviews.find_one({'submission_time': {'$ne': None}})
        if sample_review:
            print(f"\n📝 Sample review with date:")
            print(f"   Author: {sample_review.get('author')}")
            print(f"   Date: {sample_review.get('submission_time')}")
            print(f"   Type: {type(sample_review.get('submission_time'))}")

    if prices_count > 0:
        sample_price = db.prices.find_one({'current_price': {'$ne': None}})
        if sample_price:
            print(f"\n💰 Sample price:")
            print(f"   Product: {sample_price.get('product_id')}")
            print(
                f"   Price: ${sample_price.get('current_price')} {sample_price.get('currency')}")

    client.close()


if __name__ == "__main__":
    print("🚀 Fixed MongoDB Data Migration Tool")
    print("This script handles null values and date formats properly")

    # First analyze the structure
    print("\n🔍 Analyzing data structure...")
    os.system("python analyze_data_structure.py")

    # Confirm migration
    response = input("\n⚠️ Proceed with migration? (y/N): ").strip().lower()

    if response == 'y':
        load_all_data_to_mongodb_fixed()
        verify_data_loaded()
    else:
        print("❌ Migration cancelled.")
