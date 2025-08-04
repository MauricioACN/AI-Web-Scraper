"""
Data Manager for Canadian Tire Scraper

Handles data storage, loading, and organization of scraped data.
"""

import json
import os
import glob
import time
from typing import List, Dict, Any, Set, Optional
from pathlib import Path

from ..models.product import Product, Review, PriceInfo
from .config import Config


class DataManager:
    """Manages data storage and retrieval for the scraper."""

    def __init__(self, base_path: str = "."):
        """Initialize data manager with base storage path."""
        self.base_path = Path(base_path)
        self.review_folder = self.base_path / Config.DEFAULT_REVIEW_FOLDER
        self.price_folder = self.base_path / Config.DEFAULT_PRICE_FOLDER
        self.selenium_folder = self.base_path / Config.DEFAULT_SELENIUM_FOLDER
        self.summary_folder = self.base_path / Config.DEFAULT_SUMMARY_FOLDER

        # Create directories if they don't exist
        self._create_directories()

    def _create_directories(self) -> None:
        """Create necessary directories for data storage."""
        for folder in [self.review_folder, self.price_folder,
                       self.selenium_folder, self.summary_folder]:
            folder.mkdir(exist_ok=True)

    def save_product_data(self, product: Product, source: str = "api") -> str:
        """
        Save complete product data to appropriate folder.

        Args:
            product: Product object to save
            source: Source of the data ("api" or "selenium")

        Returns:
            Path to the saved file
        """
        if source == "selenium":
            folder = self.selenium_folder
            filename = f"selenium_reviews_{product.product_id}.json"
        else:
            folder = self.review_folder
            filename = f"reviews_{product.product_id}.json"

        filepath = folder / filename

        # Create export data structure
        export_data = {
            "product_info": {
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "brand": product.brand,
                "url": product.url,
                "scraped_at": product.scraped_at
            },
            "reviews": [review.to_dict() for review in product.reviews],
            "highlights": product.highlights,
            "features": product.features,
            "scraped_with": source
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved product data: {filepath}")
        return str(filepath)

    def save_price_data(self, price_info: PriceInfo) -> str:
        """
        Save price information to price folder.

        Args:
            price_info: PriceInfo object to save

        Returns:
            Path to the saved file
        """
        filename = f"price_{price_info.product_id}.json"
        filepath = self.price_folder / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(price_info.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"✅ Saved price data: {filepath}")
        return str(filepath)

    def load_existing_product_ids(self) -> Set[str]:
        """
        Load all product IDs that have been previously scraped.

        Returns:
            Set of product IDs that already have data
        """
        scraped_products = set()

        # Search for review files in all folders
        patterns = [
            self.review_folder / "reviews_*.json",
            self.selenium_folder / "selenium_reviews_*.json",
            self.base_path / "reviews_*.json"  # Legacy files
        ]

        for pattern in patterns:
            for file_path in glob.glob(str(pattern)):
                # Extract product ID from filename
                filename = os.path.basename(file_path)
                if filename.startswith("reviews_"):
                    product_id = filename.replace(
                        "reviews_", "").replace(".json", "")
                elif filename.startswith("selenium_reviews_"):
                    product_id = filename.replace(
                        "selenium_reviews_", "").replace(".json", "")
                else:
                    continue

                scraped_products.add(product_id)

        # Also check summary files for successful scrapes
        summary_patterns = [
            self.summary_folder / "*.json",
            self.base_path / "scraping_summary*.json",
            self.base_path / "scraping_progress*.json"
        ]

        for pattern in summary_patterns:
            for summary_file in glob.glob(str(pattern)):
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)

                    # Handle different summary structures
                    results = []
                    if isinstance(summary_data, dict) and 'results' in summary_data:
                        results = summary_data['results']
                    elif isinstance(summary_data, list):
                        results = summary_data

                    # Add successful products
                    for result in results:
                        if (isinstance(result, dict) and
                            result.get('status') == 'success' and
                                result.get('product_id')):
                            scraped_products.add(result['product_id'])

                except Exception as e:
                    print(f"⚠️ Warning: Could not load {summary_file}: {e}")

        print(f"📚 Found {len(scraped_products)} previously scraped products")
        return scraped_products

    def save_scraping_summary(self, results: List[Dict[str, Any]],
                              operation_type: str = "scraping") -> str:
        """
        Save scraping operation summary.

        Args:
            results: List of scraping results
            operation_type: Type of operation (e.g., "scraping", "price_check")

        Returns:
            Path to the saved summary file
        """
        timestamp = int(time.time())
        filename = f"{operation_type}_summary_{timestamp}.json"
        filepath = self.summary_folder / filename

        summary_data = {
            'timestamp': timestamp,
            'operation_type': operation_type,
            'total_products': len(results),
            'successful': len([r for r in results if r.get('status') == 'success']),
            'failed': len([r for r in results if r.get('status') == 'error']),
            'no_data': len([r for r in results if r.get('status') == 'no_reviews']),
            'results': results
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        print(f"📊 Summary saved: {filepath}")
        return str(filepath)

    def load_product_data(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Load product data by ID.

        Args:
            product_id: Product ID to load

        Returns:
            Product data dictionary or None if not found
        """
        # Check different possible file locations
        possible_paths = [
            self.review_folder / f"reviews_{product_id}.json",
            self.selenium_folder / f"selenium_reviews_{product_id}.json",
            self.base_path / f"reviews_{product_id}.json"
        ]

        for filepath in possible_paths:
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"⚠️ Error loading {filepath}: {e}")

        return None

    def get_failed_products(self, summary_file: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get list of products that failed in previous scraping attempts.

        Args:
            summary_file: Specific summary file to check, or None for latest

        Returns:
            List of failed product information
        """
        if summary_file is None:
            # Find the most recent summary file
            summary_files = list(
                glob.glob(str(self.summary_folder / "*.json")))
            summary_files.extend(
                glob.glob(str(self.base_path / "scraping_summary*.json")))

            if not summary_files:
                print("❌ No summary files found")
                return []

            summary_file = max(summary_files, key=os.path.getctime)

        print(f"📄 Loading summary: {summary_file}")

        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
        except Exception as e:
            print(f"❌ Error loading summary: {e}")
            return []

        # Get already scraped products
        scraped_products = self.load_existing_product_ids()

        # Extract failed products
        failed_products = []
        results = summary_data.get('results', []) if isinstance(
            summary_data, dict) else summary_data

        for result in results:
            if isinstance(result, dict):
                product_id = result.get('product_id')
                status = result.get('status')

                # Include failed products that aren't already scraped
                if (status in ['error', 'no_reviews'] and
                    product_id and
                        product_id not in scraped_products):

                    failed_products.append({
                        'product_id': product_id,
                        'name': result.get('name', f'Product {product_id}'),
                        'status': status,
                        'error': result.get('error', '')
                    })

        print(f"🔄 Found {len(failed_products)} failed products to retry")
        return failed_products

    def cleanup_old_files(self, days_old: int = 30) -> None:
        """
        Clean up old temporary files.

        Args:
            days_old: Remove files older than this many days
        """
        import time

        cutoff_time = time.time() - (days_old * 24 * 60 * 60)

        # Clean up old summary files
        for summary_file in glob.glob(str(self.summary_folder / "*.json")):
            if os.path.getctime(summary_file) < cutoff_time:
                os.remove(summary_file)
                print(f"🗑️ Removed old summary: {summary_file}")

        print(f"✅ Cleanup complete: removed files older than {days_old} days")
