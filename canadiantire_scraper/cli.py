#!/usr/bin/env python3
"""
Canadian Tire Scraper - Command Line Interface

A comprehensive tool for scraping Canadian Tire product data including reviews and prices.
Supports both API-based scraping and Selenium fallback methods.

Usage:
    python -m canadiantire_scraper.cli [command] [options]

Commands:
    single      - Scrape a single product
    batch       - Scrape multiple products from a list
    discover    - Discover and scrape products automatically
    resume      - Resume failed scraping operations
    stats       - Show scraping statistics
    search      - Search for products by criteria

Examples:
    python -m canadiantire_scraper.cli single 0304426P
    python -m canadiantire_scraper.cli discover --total 100
    python -m canadiantire_scraper.cli resume
"""

import argparse
import json
import sys
from pathlib import Path

from .orchestrator import CanadianTireScraper
from .utils.config import Config


def setup_parser():
    """Set up the command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Canadian Tire Scraper - Extract product reviews and pricing data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--base-path',
                        default=".",
                        help='Base directory for data storage (default: current directory)')

    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')

    # Single product command
    single_parser = subparsers.add_parser(
        'single', help='Scrape a single product')
    single_parser.add_argument(
        'product_id', help='Product ID to scrape (e.g., 0304426P)')
    single_parser.add_argument('--name', help='Product name (optional)')
    single_parser.add_argument('--no-price', action='store_true',
                               help='Skip price data collection')
    single_parser.add_argument('--no-selenium', action='store_true',
                               help='Disable Selenium fallback')

    # Batch scraping command
    batch_parser = subparsers.add_parser(
        'batch', help='Scrape multiple products')
    batch_parser.add_argument('--file', required=True,
                              help='JSON file containing product list')
    batch_parser.add_argument('--no-price', action='store_true',
                              help='Skip price data collection')
    batch_parser.add_argument('--no-selenium', action='store_true',
                              help='Disable Selenium fallback')
    batch_parser.add_argument('--workers', type=int, default=3,
                              help='Number of worker threads (default: 3)')
    batch_parser.add_argument('--batch-size', type=int, default=50,
                              help='Batch size for processing (default: 50)')

    # Discovery command
    discover_parser = subparsers.add_parser(
        'discover', help='Discover and scrape products')
    discover_parser.add_argument('--total', type=int, default=100,
                                 help='Total products to discover (default: 100)')
    discover_parser.add_argument('--no-price', action='store_true',
                                 help='Skip price data collection')
    discover_parser.add_argument('--include-existing', action='store_true',
                                 help='Include already scraped products')

    # Resume command
    resume_parser = subparsers.add_parser(
        'resume', help='Resume failed scraping')
    resume_parser.add_argument('--summary-file',
                               help='Specific summary file to resume from')

    # Statistics command
    stats_parser = subparsers.add_parser(
        'stats', help='Show scraping statistics')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for products')
    search_parser.add_argument('--term', default='*',
                               help='Search term (default: * for all products)')
    search_parser.add_argument('--max-results', type=int, default=50,
                               help='Maximum results to return (default: 50)')
    search_parser.add_argument('--min-rating', type=float,
                               help='Minimum product rating filter')
    search_parser.add_argument('--min-reviews', type=int,
                               help='Minimum number of reviews filter')
    search_parser.add_argument('--category', action='append',
                               help='Category filter (can be used multiple times)')
    search_parser.add_argument('--output',
                               help='Save results to JSON file')

    return parser


def load_product_list(file_path: str):
    """Load product list from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Handle different file formats
        if isinstance(data, list):
            # List of product IDs or product objects
            products = []
            for item in data:
                if isinstance(item, str):
                    products.append(
                        {'product_id': item, 'name': f'Product {item}'})
                elif isinstance(item, dict) and 'product_id' in item:
                    products.append(item)
                else:
                    print(f"⚠️ Skipping invalid item: {item}")
            return products

        elif isinstance(data, dict):
            # Handle various dict structures
            if 'products' in data:
                return data['products']
            elif 'results' in data:
                return [r for r in data['results'] if 'product_id' in r]
            else:
                print(f"❌ Unrecognized file format: {list(data.keys())}")
                return []

        else:
            print(
                f"❌ Invalid file format. Expected list or dict, got {type(data)}")
            return []

    except Exception as e:
        print(f"❌ Error loading file {file_path}: {e}")
        return []


def command_single(args, scraper):
    """Handle single product scraping command."""
    print(f"🎯 Scraping single product: {args.product_id}")

    result = scraper.scrape_single_product(
        product_id=args.product_id,
        product_name=args.name,
        include_price=not args.no_price,
        use_selenium_fallback=not args.no_selenium
    )

    print(f"\n📊 Results:")
    print(f"   Status: {result['status']}")
    print(
        f"   Reviews: {result['reviews_count']} ({result.get('reviews_source', 'none')})")
    print(f"   Price: {'✅' if result['price_available'] else '❌'}")
    print(f"   Files saved: {len(result['files_saved'])}")

    if result['files_saved']:
        for file_path in result['files_saved']:
            print(f"      📁 {file_path}")

    return result['status'] == 'success'


def command_batch(args, scraper):
    """Handle batch scraping command."""
    print(f"📦 Batch scraping from file: {args.file}")

    # Load product list
    products = load_product_list(args.file)
    if not products:
        print("❌ No valid products found in file")
        return False

    print(f"📋 Loaded {len(products)} products from file")

    # Start batch scraping
    results = scraper.scrape_multiple_products(
        product_list=products,
        include_price=not args.no_price,
        use_selenium_fallback=not args.no_selenium,
        max_workers=args.workers,
        batch_size=args.batch_size
    )

    # Print summary
    successful = len([r for r in results if r['status'] == 'success'])
    print(f"\n📊 Batch complete: {successful}/{len(results)} successful")

    return successful > 0


def command_discover(args, scraper):
    """Handle product discovery command."""
    print(f"🔍 Discovering {args.total} products")

    results = scraper.discover_and_scrape(
        total_products=args.total,
        include_price=not args.no_price,
        filter_existing=not args.include_existing
    )

    successful = len([r for r in results if r['status'] == 'success'])
    print(f"\n📊 Discovery complete: {successful}/{len(results)} successful")

    return successful > 0


def command_resume(args, scraper):
    """Handle resume failed scraping command."""
    print("🔄 Resuming failed scraping operations")

    results = scraper.resume_failed_scraping(args.summary_file)

    if not results:
        print("ℹ️ No failed products to resume")
        return True

    successful = len([r for r in results if r['status'] == 'success'])
    print(f"\n📊 Resume complete: {successful}/{len(results)} successful")

    return successful > 0


def command_stats(args, scraper):
    """Handle statistics command."""
    print("📊 Scraping Statistics")
    print("=" * 50)

    stats = scraper.get_scraping_statistics()

    print(f"Total scraped products: {stats['total_scraped_products']}")
    print(f"API review files: {stats['api_review_files']}")
    print(f"Selenium review files: {stats['selenium_review_files']}")
    print(f"Price files: {stats['price_files']}")

    print(f"\nData folders:")
    for folder_type, path in stats['data_folders'].items():
        print(f"   {folder_type}: {path}")

    return True


def command_search(args, scraper):
    """Handle product search command."""
    print(f"🔍 Searching products: '{args.term}'")

    # Perform search
    products = scraper.product_searcher.search_products(
        search_term=args.term,
        max_products=args.max_results
    )

    # Apply filters
    if args.min_rating or args.min_reviews or args.category:
        products = scraper.product_searcher.filter_products_by_criteria(
            products=products,
            min_rating=args.min_rating,
            min_reviews=args.min_reviews,
            categories=args.category
        )

    print(f"📋 Found {len(products)} products")

    # Display results
    for i, product in enumerate(products[:10]):  # Show first 10
        print(f"   {i+1}. {product['product_id']} - {product['name'][:50]}...")
        if product.get('rating'):
            print(
                f"      ⭐ {product['rating']} ({product.get('ratings_count', 0)} reviews)")

    if len(products) > 10:
        print(f"   ... and {len(products) - 10} more")

    # Save to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
        print(f"📁 Results saved to: {args.output}")

    return True


def main():
    """Main CLI entry point."""
    parser = setup_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        # Validate configuration
        print("🔧 Validating configuration...")
        Config.validate_config()

        # Initialize scraper
        print("🚀 Initializing Canadian Tire Scraper...")
        scraper = CanadianTireScraper(base_path=args.base_path)

        # Execute command
        if args.command == 'single':
            success = command_single(args, scraper)
        elif args.command == 'batch':
            success = command_batch(args, scraper)
        elif args.command == 'discover':
            success = command_discover(args, scraper)
        elif args.command == 'resume':
            success = command_resume(args, scraper)
        elif args.command == 'stats':
            success = command_stats(args, scraper)
        elif args.command == 'search':
            success = command_search(args, scraper)
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1

        return 0 if success else 1

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("   Make sure you have set the required environment variables:")
        print("   - BV_BFD_TOKEN")
        print("   - OCP_APIM_SUBSCRIPTION_KEY")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
