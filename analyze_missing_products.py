#!/usr/bin/env python3
"""
Script to analyze products in scraping files and find missing ones
"""
import json
import glob
import os


def load_json_file(filepath):
    """Load JSON file safely"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return None


def extract_product_ids_from_summary(data):
    """Extract product IDs from summary files"""
    product_ids = set()
    if isinstance(data, dict):
        results = data.get('results', [])
        for result in results:
            if isinstance(result, dict) and 'product_id' in result:
                product_ids.add(result['product_id'])
    return product_ids


def extract_product_ids_from_batch(data):
    """Extract product IDs from batch progress files"""
    product_ids = set()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and 'product_id' in item:
                product_ids.add(item['product_id'])
    elif isinstance(data, dict):
        # Handle different formats
        if 'results' in data:
            for result in data['results']:
                if isinstance(result, dict) and 'product_id' in result:
                    product_ids.add(result['product_id'])
    return product_ids


def extract_product_ids_from_reviews():
    """Extract product IDs from review files"""
    product_ids = set()
    review_files = glob.glob("data_review/reviews_*.json")
    for file in review_files:
        # Extract product_id from filename
        filename = os.path.basename(file)
        product_id = filename.replace("reviews_", "").replace(".json", "")
        product_ids.add(product_id)
    return product_ids


def main():
    print("🔍 Analyzing scraping files for missing products...\n")

    # Get all product IDs from different sources
    all_product_ids = set()

    # 1. From summary files
    summary_files = glob.glob("scraping_summary*.json")
    summary_products = set()

    print("📄 Processing summary files:")
    for file in summary_files:
        print(f"  Processing: {file}")
        data = load_json_file(file)
        if data:
            products = extract_product_ids_from_summary(data)
            summary_products.update(products)
            all_product_ids.update(products)
            print(f"    Found {len(products)} products")

    print(f"  📊 Total from summaries: {len(summary_products)}")

    # 2. From batch progress files
    batch_files = glob.glob("scraping_progress_batch*.json")
    batch_products = set()

    print("\n📦 Processing batch progress files:")
    for file in batch_files:
        print(f"  Processing: {file}")
        data = load_json_file(file)
        if data:
            products = extract_product_ids_from_batch(data)
            batch_products.update(products)
            all_product_ids.update(products)
            print(f"    Found {len(products)} products")

    print(f"  📊 Total from batches: {len(batch_products)}")

    # 3. From review files
    print("\n📝 Processing review files:")
    review_products = extract_product_ids_from_reviews()
    all_product_ids.update(review_products)
    print(f"  📊 Total from reviews: {len(review_products)}")

    # 4. From retry summary files
    retry_files = glob.glob("retry_summary/retry_summary_*.json")
    retry_products = set()

    print("\n🔄 Processing retry summary files:")
    for file in retry_files:
        print(f"  Processing: {file}")
        data = load_json_file(file)
        if data:
            products = extract_product_ids_from_summary(data)
            retry_products.update(products)
            all_product_ids.update(products)
            print(f"    Found {len(products)} products")

    print(f"  📊 Total from retries: {len(retry_products)}")

    # Analysis
    print(f"\n📈 ANALYSIS RESULTS:")
    print(f"{'='*50}")
    print(f"📊 Total unique products found: {len(all_product_ids)}")
    print(f"📄 Products in summaries: {len(summary_products)}")
    print(f"📦 Products in batches: {len(batch_products)}")
    print(f"📝 Products in reviews: {len(review_products)}")
    print(f"🔄 Products in retries: {len(retry_products)}")

    # Find products only in certain files
    only_in_batches = batch_products - summary_products - retry_products
    only_in_summaries = summary_products - batch_products - retry_products
    not_in_reviews = all_product_ids - review_products

    print(f"\n🔍 MISSING ANALYSIS:")
    print(f"{'='*50}")

    if only_in_batches:
        print(f"⚠️  Products ONLY in batch files: {len(only_in_batches)}")
        print("   These might be missing from summaries:")
        for pid in sorted(list(only_in_batches)[:10]):  # Show first 10
            print(f"     - {pid}")
        if len(only_in_batches) > 10:
            print(f"     ... and {len(only_in_batches) - 10} more")
    else:
        print("✅ No products found only in batch files")

    if only_in_summaries:
        print(
            f"\n⚠️  Products ONLY in summary files: {len(only_in_summaries)}")
        print("   These might be missing from batches:")
        for pid in sorted(list(only_in_summaries)[:10]):  # Show first 10
            print(f"     - {pid}")
        if len(only_in_summaries) > 10:
            print(f"     ... and {len(only_in_summaries) - 10} more")
    else:
        print("✅ No products found only in summary files")

    if not_in_reviews:
        print(f"\n⚠️  Products NOT in review files: {len(not_in_reviews)}")
        print("   These products might need to be scraped:")
        for pid in sorted(list(not_in_reviews)[:10]):  # Show first 10
            print(f"     - {pid}")
        if len(not_in_reviews) > 10:
            print(f"     ... and {len(not_in_reviews) - 10} more")
    else:
        print("✅ All products have corresponding review files")

    # Save detailed analysis
    analysis_result = {
        "timestamp": "2025-08-03",
        "total_unique_products": len(all_product_ids),
        "summary_products": len(summary_products),
        "batch_products": len(batch_products),
        "review_products": len(review_products),
        "retry_products": len(retry_products),
        "only_in_batches": sorted(list(only_in_batches)),
        "only_in_summaries": sorted(list(only_in_summaries)),
        "not_in_reviews": sorted(list(not_in_reviews)),
        "all_product_ids": sorted(list(all_product_ids))
    }

    with open("product_analysis_report.json", "w", encoding="utf-8") as f:
        json.dump(analysis_result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Detailed analysis saved to: product_analysis_report.json")


if __name__ == "__main__":
    main()
