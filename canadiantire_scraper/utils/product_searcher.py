"""
Product Search Utility for Canadian Tire

Handles product discovery and search functionality.
"""

import requests
import time
from typing import List, Dict, Any, Set

from ..utils.config import Config


class ProductSearcher:
    """Utility for searching and discovering Canadian Tire products."""

    def __init__(self):
        """Initialize the product searcher."""
        self.config = Config()
        self.config.validate_config()

    def search_products(self, search_term: str = "*", max_products: int = 100,
                        store_id: str = None) -> List[Dict[str, Any]]:
        """
        Search for products using Canadian Tire's search API.

        Args:
            search_term: Search query (use "*" for all products)
            max_products: Maximum number of products to return
            store_id: Store ID for location-specific results

        Returns:
            List of product information dictionaries
        """
        if store_id is None:
            store_id = self.config.DEFAULT_STORE_ID

        search_url = self.config.SEARCH_API_URL
        headers = self.config.BASE_HEADERS

        all_products = []
        seen_product_ids = set()
        page = 1
        rows_per_page = 50
        consecutive_empty_pages = 0
        max_empty_pages = 3

        print(f"🔍 Searching for products: '{search_term}'")

        while len(all_products) < max_products and consecutive_empty_pages < max_empty_pages:
            start_offset = len(all_products)

            params = {
                "q": search_term,
                "store": store_id,
                "start": start_offset,
                "rows": rows_per_page,
                "lang": "en_CA",
                "baseStoreId": "CTR",
                "apiversion": "5.5",
                "displaycode": "15041_3_0-en_ca",
                "sort": "relevance desc, code asc"
            }

            try:
                print(f"🔍 Fetching page {page} (offset: {start_offset})")
                resp = requests.get(search_url, headers=headers, params=params)

                if resp.status_code != 200:
                    print(f"❌ Search API error: {resp.status_code}")
                    break

                data = resp.json()
                products = data.get('products', [])

                if not products:
                    consecutive_empty_pages += 1
                    print(
                        f"⚠️ Empty page {page} (consecutive: {consecutive_empty_pages})")
                    page += 1
                    continue

                consecutive_empty_pages = 0
                new_products_in_page = 0

                for product in products:
                    product_id = product.get('code')

                    if not product_id or product_id in seen_product_ids:
                        continue

                    seen_product_ids.add(product_id)

                    product_info = {
                        'product_id': product_id,
                        'name': product.get('title', ''),
                        'category': self._extract_category(product.get('breadcrumbList', [])),
                        'brand': self._extract_brand(product),
                        'url': f"https://www.canadiantire.ca{product.get('url', '')}",
                        'rating': product.get('rating'),
                        'ratings_count': product.get('ratingsCount'),
                        'badges': product.get('badges', []),
                        'image_url': self._get_main_image(product.get('images', []))
                    }

                    all_products.append(product_info)
                    new_products_in_page += 1

                    if len(all_products) >= max_products:
                        break

                print(
                    f"✅ Page {page}: {new_products_in_page} new products (Total: {len(all_products)})")

                # Check if we've reached the end
                pagination = data.get('pagination', {})
                total_results = pagination.get('totalResults', 0)

                if start_offset + rows_per_page >= total_results:
                    print(
                        f"📄 Reached end of results (Total available: {total_results})")
                    break

                if new_products_in_page == 0:
                    consecutive_empty_pages += 1

                page += 1
                time.sleep(self.config.API_DELAY)

            except Exception as e:
                print(f"❌ Error fetching page {page}: {e}")
                break

        print(f"🎯 Search complete: {len(all_products)} unique products found")
        return all_products

    def discover_products_by_categories(self, total_limit: int = 350) -> List[Dict[str, Any]]:
        """
        Discover products across multiple categories.

        Args:
            total_limit: Maximum total products to discover

        Returns:
            List of diverse product information
        """
        search_terms = self.config.SEARCH_TERMS
        all_products = []
        products_per_term = max(total_limit // len(search_terms), 10)

        print(f"🚀 Discovering products across {len(search_terms)} categories")

        for i, term in enumerate(search_terms):
            if len(all_products) >= total_limit:
                break

            print(f"\n[{i+1}/{len(search_terms)}] Searching category: '{term}'")

            products = self.search_products(
                search_term=term,
                max_products=products_per_term
            )

            all_products.extend(products)
            print(
                f"   ✅ Added {len(products)} products (Total: {len(all_products)})")

            # Rate limiting between categories
            time.sleep(2)

        # Remove duplicates and limit results
        unique_products = []
        seen_ids = set()

        for product in all_products:
            if product['product_id'] not in seen_ids:
                unique_products.append(product)
                seen_ids.add(product['product_id'])

                if len(unique_products) >= total_limit:
                    break

        print(
            f"\n📊 Discovery complete: {len(unique_products)} unique products across categories")
        return unique_products

    def filter_products_by_criteria(self, products: List[Dict[str, Any]],
                                    min_rating: float = None,
                                    min_reviews: int = None,
                                    categories: List[str] = None) -> List[Dict[str, Any]]:
        """
        Filter products by specific criteria.

        Args:
            products: List of products to filter
            min_rating: Minimum rating threshold
            min_reviews: Minimum number of reviews
            categories: List of allowed categories

        Returns:
            Filtered list of products
        """
        filtered = []

        for product in products:
            # Rating filter
            if min_rating and product.get('rating', 0) < min_rating:
                continue

            # Reviews count filter
            if min_reviews and product.get('ratings_count', 0) < min_reviews:
                continue

            # Category filter
            if categories and product.get('category', '').lower() not in [c.lower() for c in categories]:
                continue

            filtered.append(product)

        print(f"🔍 Filtered {len(products)} -> {len(filtered)} products")
        return filtered

    def _extract_category(self, breadcrumb_list: List[str]) -> str:
        """Extract the main category from breadcrumb."""
        if breadcrumb_list and len(breadcrumb_list) > 0:
            return breadcrumb_list[-1] if isinstance(breadcrumb_list, list) else "Unknown"
        return "Unknown"

    def _extract_brand(self, product: Dict[str, Any]) -> str:
        """Extract brand information from product data."""
        brand_info = product.get('brand', {})
        if isinstance(brand_info, dict):
            return brand_info.get('label', '')
        return str(brand_info) if brand_info else ''

    def _get_main_image(self, images: List[Dict[str, Any]]) -> str:
        """Get the main product image URL."""
        if images and len(images) > 0:
            return images[0].get('url', '')
        return ''
