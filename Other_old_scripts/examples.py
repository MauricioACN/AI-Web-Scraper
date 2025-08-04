#!/usr/bin/env python3
"""
Canadian Tire Scraper - Example Usage

This script demonstrates how to use the Canadian Tire Scraper module
for various scraping tasks.
"""

import json
from canadiantire_scraper import CanadianTireScraper


def example_single_product():
    """Example: Scrape a single product with all data."""
    print("=" * 60)
    print("EXAMPLE 1: Single Product Scraping")
    print("=" * 60)

    # Initialize scraper
    scraper = CanadianTireScraper()

    # Scrape a single product (example: ice scraper we tested before)
    result = scraper.scrape_single_product(
        product_id="0304426P",
        product_name="Subaru Ice Scraper",
        include_price=True,
        use_selenium_fallback=True
    )

    print(f"Result: {result['status']}")
    print(
        f"Reviews found: {result['reviews_count']} via {result.get('reviews_source', 'none')}")
    print(
        f"Price data: {'Available' if result['price_available'] else 'Not available'}")
    print(f"Files saved: {len(result['files_saved'])}")


def example_batch_scraping():
    """Example: Scrape multiple products."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Batch Product Scraping")
    print("=" * 60)

    # Initialize scraper
    scraper = CanadianTireScraper()

    # Define products to scrape
    products = [
        {"product_id": "0304426P", "name": "Subaru Ice Scraper"},
        {"product_id": "0396567P", "name": "Simoniz Air Dryer"},
        {"product_id": "0508732P", "name": "B-Toys Fishing Playset"}
    ]

    # Batch scrape
    results = scraper.scrape_multiple_products(
        product_list=products,
        include_price=True,
        use_selenium_fallback=True,
        max_workers=2  # Use 2 threads
    )

    # Print summary
    successful = len([r for r in results if r['status'] == 'success'])
    print(f"Batch complete: {successful}/{len(results)} successful")


def example_product_discovery():
    """Example: Discover and scrape products automatically."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Product Discovery and Scraping")
    print("=" * 60)

    # Initialize scraper
    scraper = CanadianTireScraper()

    # Discover and scrape 10 products
    results = scraper.discover_and_scrape(
        total_products=10,
        include_price=True,
        filter_existing=True  # Skip already scraped products
    )

    successful = len([r for r in results if r['status'] == 'success'])
    print(f"Discovery complete: {successful}/{len(results)} successful")


def example_search_products():
    """Example: Search for specific products."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Product Search")
    print("=" * 60)

    # Initialize scraper
    scraper = CanadianTireScraper()

    # Search for tools
    products = scraper.product_searcher.search_products(
        search_term="power tools",
        max_products=20
    )

    print(f"Found {len(products)} power tools")

    # Show first 5 results
    for i, product in enumerate(products[:5]):
        print(f"  {i+1}. {product['product_id']} - {product['name'][:50]}...")
        if product.get('rating'):
            print(
                f"     ⭐ {product['rating']} ({product.get('ratings_count', 0)} reviews)")


def example_resume_failed():
    """Example: Resume failed scraping operations."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Resume Failed Scraping")
    print("=" * 60)

    # Initialize scraper
    scraper = CanadianTireScraper()

    # Try to resume failed scraping
    results = scraper.resume_failed_scraping()

    if results:
        successful = len([r for r in results if r['status'] == 'success'])
        print(f"Resume complete: {successful}/{len(results)} successful")
    else:
        print("No failed products to resume")


def example_statistics():
    """Example: Get scraping statistics."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Scraping Statistics")
    print("=" * 60)

    # Initialize scraper
    scraper = CanadianTireScraper()

    # Get statistics
    stats = scraper.get_scraping_statistics()

    print(f"Total scraped products: {stats['total_scraped_products']}")
    print(f"API review files: {stats['api_review_files']}")
    print(f"Selenium review files: {stats['selenium_review_files']}")
    print(f"Price files: {stats['price_files']}")


def example_price_only():
    """Example: Scrape only price data for multiple products."""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Price-Only Scraping")
    print("=" * 60)

    # Initialize scraper
    scraper = CanadianTireScraper()

    # Product IDs to check prices for
    product_ids = ["0304426P", "0396567P", "0508732P", "0589879P"]

    # Scrape prices only
    results = scraper.price_scraper.scrape_multiple_prices(product_ids)

    print("Price results:")
    for result in results:
        if result['status'] == 'success':
            price_info = result['price_info']
            print(
                f"  {result['product_id']}: ${price_info.current_price} CAD (In stock: {price_info.in_stock})")
        else:
            print(f"  {result['product_id']}: {result['status']}")


def example_save_and_load():
    """Example: Demonstrate data saving and loading."""
    print("\n" + "=" * 60)
    print("EXAMPLE 8: Data Management")
    print("=" * 60)

    # Initialize scraper
    scraper = CanadianTireScraper()

    # Load existing product data
    product_data = scraper.data_manager.load_product_data("0304426P")

    if product_data:
        print("Found existing data for product 0304426P:")
        print(f"  Reviews: {len(product_data.get('reviews', []))}")
        print(f"  Source: {product_data.get('scraped_with', 'unknown')}")
    else:
        print("No existing data found for product 0304426P")

    # Show existing product IDs
    existing_ids = scraper.data_manager.load_existing_product_ids()
    print(f"Total products with data: {len(existing_ids)}")
    if existing_ids:
        print(f"  Examples: {list(existing_ids)[:5]}")


def main():
    """Run all examples."""
    print("🚀 Canadian Tire Scraper - Example Usage")
    print("This script demonstrates various features of the scraper module")

    try:
        # Run examples (comment out the ones you don't want to run)
        example_single_product()
        # example_batch_scraping()
        # example_product_discovery()
        example_search_products()
        example_statistics()
        example_price_only()
        example_save_and_load()
        # example_resume_failed()  # Only run if you have failed products

        print("\n🎉 All examples completed successfully!")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure you have:")
        print("1. Set up your .env file with the required tokens")
        print("2. Installed all dependencies (selenium, requests, etc.)")


if __name__ == "__main__":
    main()
