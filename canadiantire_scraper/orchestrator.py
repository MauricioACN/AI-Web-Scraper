"""
Canadian Tire Scraper Orchestrator

Main class that coordinates all scraping operations and provides a unified interface.
"""

import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .scrapers.review_scraper import ReviewScraper
from .scrapers.price_scraper import PriceScraper
from .scrapers.selenium_scraper import SeleniumScraper
from .utils.data_manager import DataManager
from .utils.product_searcher import ProductSearcher
from .utils.config import Config
from .models.product import Product


class CanadianTireScraper:
    """
    Main orchestrator class for Canadian Tire scraping operations.

    Provides a unified interface for scraping reviews, prices, and product data
    using multiple methods (API and Selenium fallback).
    """

    def __init__(self, base_path: str = "."):
        """
        Initialize the scraper orchestrator.

        Args:
            base_path: Base directory for data storage
        """
        self.config = Config()
        self.config.validate_config()

        # Initialize components
        self.review_scraper = ReviewScraper()
        self.price_scraper = PriceScraper()
        self.selenium_scraper = SeleniumScraper()
        self.data_manager = DataManager(base_path)
        self.product_searcher = ProductSearcher()

        print("🚀 Canadian Tire Scraper initialized successfully")

    def scrape_single_product(self, product_id: str,
                              include_price: bool = True,
                              use_selenium_fallback: bool = True,
                              product_name: str = None) -> Dict[str, Any]:
        """
        Scrape complete data for a single product.

        Args:
            product_id: Product ID to scrape
            include_price: Whether to fetch price data
            use_selenium_fallback: Whether to use Selenium if API fails
            product_name: Optional product name

        Returns:
            Dictionary containing scraping results
        """
        if product_name is None:
            product_name = f"Product {product_id}"

        print(f"🎯 Scraping complete data for: {product_name} ({product_id})")

        result = {
            'product_id': product_id,
            'name': product_name,
            'status': 'success',
            'reviews_source': None,
            'reviews_count': 0,
            'price_available': False,
            'files_saved': []
        }

        try:
            # Step 1: Try API review scraping
            print("📝 Attempting API review scraping...")
            product = self.review_scraper.scrape_product(
                product_id, product_name)

            if product.reviews:
                print(
                    f"✅ API scraping successful: {len(product.reviews)} reviews")
                result['reviews_source'] = 'api'
                result['reviews_count'] = len(product.reviews)

                # Save review data
                file_path = self.data_manager.save_product_data(
                    product, source='api')
                result['files_saved'].append(file_path)

            elif use_selenium_fallback:
                print("🔄 API returned no reviews, trying Selenium fallback...")

                # Step 2: Selenium fallback
                selenium_product = self.selenium_scraper.scrape_product_reviews(
                    product_id)
                selenium_product.name = product_name

                if selenium_product.reviews:
                    print(
                        f"✅ Selenium scraping successful: {len(selenium_product.reviews)} reviews")
                    result['reviews_source'] = 'selenium'
                    result['reviews_count'] = len(selenium_product.reviews)

                    # Save selenium data
                    file_path = self.data_manager.save_product_data(
                        selenium_product, source='selenium')
                    result['files_saved'].append(file_path)

                    # Use selenium product for further processing
                    product = selenium_product
                else:
                    print("⚠️ No reviews found via Selenium either")
                    result['status'] = 'no_reviews'
            else:
                print("⚠️ No reviews found via API and Selenium fallback disabled")
                result['status'] = 'no_reviews'

            # Step 3: Price scraping (if requested)
            if include_price:
                print("💰 Fetching price data...")
                price_info = self.price_scraper.fetch_product_price(product_id)

                if price_info:
                    print(
                        f"✅ Price data retrieved: ${price_info.current_price} CAD")
                    result['price_available'] = True

                    # Add price to product and save
                    product.price_info = price_info

                    # Save price data separately
                    price_file = self.data_manager.save_price_data(price_info)
                    result['files_saved'].append(price_file)
                else:
                    print("⚠️ Price data not available")

            result['product'] = product

        except Exception as e:
            print(f"❌ Error scraping product {product_id}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)

        return result

    def scrape_multiple_products(self, product_list: List[Dict[str, str]],
                                 include_price: bool = True,
                                 use_selenium_fallback: bool = True,
                                 max_workers: int = None,
                                 batch_size: int = None) -> List[Dict[str, Any]]:
        """
        Scrape multiple products with optional threading.

        Args:
            product_list: List of dictionaries with 'product_id' and 'name'
            include_price: Whether to fetch price data
            use_selenium_fallback: Whether to use Selenium fallback
            max_workers: Maximum number of threads (None for sequential)
            batch_size: Process products in batches (None for all at once)

        Returns:
            List of scraping results
        """
        if max_workers is None:
            max_workers = self.config.DEFAULT_MAX_WORKERS

        if batch_size is None:
            batch_size = self.config.DEFAULT_BATCH_SIZE

        print(f"🚀 Starting batch scraping: {len(product_list)} products")
        print(
            f"📊 Configuration: price={include_price}, selenium_fallback={use_selenium_fallback}")

        all_results = []

        # Process in batches to avoid overwhelming the system
        for i in range(0, len(product_list), batch_size):
            batch = product_list[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(product_list) + batch_size - 1) // batch_size

            print(
                f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} products)")

            if max_workers == 1:
                # Sequential processing
                batch_results = []
                for j, product_info in enumerate(batch):
                    print(
                        f"  [{j+1}/{len(batch)}] Processing: {product_info.get('name', product_info['product_id'])}")
                    result = self.scrape_single_product(
                        product_info['product_id'],
                        include_price=include_price,
                        use_selenium_fallback=use_selenium_fallback,
                        product_name=product_info.get('name')
                    )
                    batch_results.append(result)

                    # Rate limiting
                    if j < len(batch) - 1:
                        time.sleep(self.config.API_DELAY)
            else:
                # Threaded processing
                batch_results = []
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_product = {
                        executor.submit(
                            self.scrape_single_product,
                            product_info['product_id'],
                            include_price,
                            use_selenium_fallback,
                            product_info.get('name')
                        ): product_info
                        for product_info in batch
                    }

                    for future in as_completed(future_to_product):
                        result = future.result()
                        batch_results.append(result)
                        print(
                            f"✅ Completed: {result['name']} - {result['status']}")

            all_results.extend(batch_results)

            # Pause between batches
            if i + batch_size < len(product_list):
                print(
                    f"⏸️ Pausing {self.config.BATCH_DELAY}s between batches...")
                time.sleep(self.config.BATCH_DELAY)

        # Generate summary
        successful = len([r for r in all_results if r['status'] == 'success'])
        no_reviews = len(
            [r for r in all_results if r['status'] == 'no_reviews'])
        errors = len([r for r in all_results if r['status'] == 'error'])

        print(f"\n📊 Batch scraping complete:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ⚠️ No reviews: {no_reviews}")
        print(f"   ❌ Errors: {errors}")

        # Save summary
        summary_file = self.data_manager.save_scraping_summary(
            all_results, "batch_scraping")
        print(f"📄 Summary saved: {summary_file}")

        return all_results

    def discover_and_scrape(self, total_products: int = 100,
                            include_price: bool = True,
                            filter_existing: bool = True) -> List[Dict[str, Any]]:
        """
        Discover products and scrape them in one operation.

        Args:
            total_products: Number of products to discover and scrape
            include_price: Whether to include price data
            filter_existing: Whether to skip already scraped products

        Returns:
            List of scraping results
        """
        print(f"🔍 Discovering and scraping {total_products} products")

        # Step 1: Discover products
        products = self.product_searcher.discover_products_by_categories(
            total_products)

        # Step 2: Filter existing products if requested
        if filter_existing:
            existing_ids = self.data_manager.load_existing_product_ids()
            products = [p for p in products if p['product_id']
                        not in existing_ids]
            print(f"🔍 Filtered to {len(products)} new products")

        if not products:
            print("ℹ️ No new products to scrape")
            return []

        # Step 3: Scrape discovered products
        return self.scrape_multiple_products(
            products,
            include_price=include_price,
            use_selenium_fallback=True
        )

    def resume_failed_scraping(self, summary_file: str = None) -> List[Dict[str, Any]]:
        """
        Resume scraping of previously failed products.

        Args:
            summary_file: Specific summary file to resume from (None for latest)

        Returns:
            List of retry results
        """
        print("🔄 Resuming failed product scraping...")

        # Get failed products
        failed_products = self.data_manager.get_failed_products(summary_file)

        if not failed_products:
            print("🎉 No failed products to retry!")
            return []

        print(f"🔄 Found {len(failed_products)} failed products to retry")

        # Convert to expected format
        product_list = [
            {
                'product_id': p['product_id'],
                'name': p['name']
            }
            for p in failed_products
        ]

        # Retry scraping
        results = self.scrape_multiple_products(
            product_list,
            include_price=True,
            use_selenium_fallback=True,
            max_workers=2  # Lower concurrency for retries
        )

        # Save retry summary
        retry_summary_file = self.data_manager.save_scraping_summary(
            results, "retry_scraping")
        print(f"📄 Retry summary saved: {retry_summary_file}")

        return results

    def get_scraping_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about scraped data.

        Returns:
            Dictionary with scraping statistics
        """
        existing_ids = self.data_manager.load_existing_product_ids()

        # Count files by type
        review_files = len(
            list(self.data_manager.review_folder.glob("reviews_*.json")))
        selenium_files = len(
            list(self.data_manager.selenium_folder.glob("selenium_reviews_*.json")))
        price_files = len(
            list(self.data_manager.price_folder.glob("price_*.json")))

        return {
            'total_scraped_products': len(existing_ids),
            'api_review_files': review_files,
            'selenium_review_files': selenium_files,
            'price_files': price_files,
            'data_folders': {
                'reviews': str(self.data_manager.review_folder),
                'selenium_reviews': str(self.data_manager.selenium_folder),
                'prices': str(self.data_manager.price_folder),
                'summaries': str(self.data_manager.summary_folder)
            }
        }
