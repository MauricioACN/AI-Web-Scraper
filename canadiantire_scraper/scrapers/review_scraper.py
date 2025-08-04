"""
Review Scraper for Canadian Tire

Handles API-based review scraping using Bazaarvoice endpoints.
"""

import requests
import time
from typing import List, Dict, Any, Optional

from ..models.product import Product, Review
from ..utils.config import Config


class ReviewScraper:
    """Scraper for product reviews using Canadian Tire's Bazaarvoice API."""

    def __init__(self):
        """Initialize the review scraper."""
        self.config = Config()
        self.config.validate_config()

    def fetch_reviews(self, product_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch reviews for a product using the Bazaarvoice API.

        Args:
            product_id: Product ID to fetch reviews for
            limit: Maximum number of reviews per request (default from config)

        Returns:
            List of raw review data from API
        """
        if limit is None:
            limit = self.config.DEFAULT_REVIEW_LIMIT

        url = self.config.REVIEWS_API_URL
        headers = self.config.BASE_HEADERS

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

        print(f"🔍 Fetching reviews for product: {product_id}")

        while True:
            params["offset"] = offset

            try:
                resp = requests.get(url, headers=headers, params=params)

                if resp.status_code != 200:
                    print(f"❌ API Error {resp.status_code}: {resp.text[:200]}")
                    break

                data = resp.json()
                response_data = data.get("response", {})
                reviews = response_data.get("Results", [])

                if not reviews:
                    print("📄 No more reviews found")
                    break

                all_reviews.extend(reviews)
                offset += limit
                print(f"✅ Fetched {len(all_reviews)} reviews so far...")

                # Rate limiting
                time.sleep(self.config.API_DELAY)

                # Limit for large result sets
                if len(all_reviews) >= 200:
                    print("📄 Reached maximum review limit (200)")
                    break

            except Exception as e:
                print(f"❌ Error fetching reviews: {e}")
                break

        print(f"✅ Total reviews fetched: {len(all_reviews)}")
        return all_reviews

    def fetch_highlights(self, product_id: str) -> Dict[str, Any]:
        """
        Fetch review highlights for a product.

        Args:
            product_id: Product ID to fetch highlights for

        Returns:
            Dictionary of highlight data
        """
        url = self.config.HIGHLIGHTS_API_URL.format(product_id=product_id)

        try:
            resp = requests.get(url, headers=self.config.BASE_HEADERS)
            if resp.status_code == 200:
                return resp.json().get("subjects", {})
        except Exception as e:
            print(
                f"⚠️ Warning: Could not fetch highlights for {product_id}: {e}")

        return {}

    def fetch_features(self, product_id: str) -> List[Dict[str, Any]]:
        """
        Fetch product features and sentiments.

        Args:
            product_id: Product ID to fetch features for

        Returns:
            List of feature data
        """
        url = self.config.FEATURES_API_URL
        params = {"productId": product_id, "language": "en"}

        try:
            resp = requests.get(
                url, headers=self.config.BASE_HEADERS, params=params)
            if resp.status_code == 200:
                return resp.json().get("response", {}).get("features", [])
        except Exception as e:
            print(
                f"⚠️ Warning: Could not fetch features for {product_id}: {e}")

        return []

    def parse_review_data(self, raw_review: Dict[str, Any]) -> Review:
        """
        Parse raw API review data into Review object.

        Args:
            raw_review: Raw review data from API

        Returns:
            Parsed Review object
        """
        comments = []
        comments_list = raw_review.get("Comments", [])
        if comments_list:
            comments = [
                {
                    "comment_text": c.get("CommentText", ""),
                    "author": c.get("AuthorId", ""),
                    "submission_time": c.get("SubmissionTime", "")
                }
                for c in comments_list
            ]

        return Review(
            review_id=raw_review.get("Id", ""),
            author=raw_review.get("UserNickname", ""),
            rating=raw_review.get("Rating", 0),
            title=raw_review.get("Title", ""),
            text=raw_review.get("ReviewText", ""),
            date=raw_review.get("SubmissionTime", ""),
            source="api",
            verified_purchase=raw_review.get("IsVerifiedPurchaser", False),
            recommendation=raw_review.get("IsRecommended"),
            submission_time=raw_review.get("SubmissionTime", ""),
            comments=comments
        )

    def scrape_product(self, product_id: str, product_name: str = None) -> Product:
        """
        Scrape complete review data for a product.

        Args:
            product_id: Product ID to scrape
            product_name: Optional product name

        Returns:
            Product object with reviews and metadata
        """
        if product_name is None:
            product_name = f"Product {product_id}"

        print(f"🔄 Scraping reviews for: {product_name} ({product_id})")

        # Create product object
        product = Product(
            product_id=product_id,
            name=product_name
        )

        try:
            # Fetch all data
            raw_reviews = self.fetch_reviews(product_id)
            highlights = self.fetch_highlights(product_id)
            features = self.fetch_features(product_id)

            # Parse reviews
            for raw_review in raw_reviews:
                review = self.parse_review_data(raw_review)
                product.add_review(review)

            # Add metadata
            product.highlights = highlights
            product.features = features

            print(f"✅ Successfully scraped {len(product.reviews)} reviews")
            return product

        except Exception as e:
            print(f"❌ Error scraping product {product_id}: {e}")
            raise

    def scrape_multiple_products(self, product_list: List[Dict[str, str]],
                                 max_workers: int = None) -> List[Dict[str, Any]]:
        """
        Scrape reviews for multiple products.

        Args:
            product_list: List of product dictionaries with 'product_id' and 'name'
            max_workers: Maximum number of threads (not used in this implementation)

        Returns:
            List of scraping results
        """
        if max_workers is None:
            max_workers = self.config.DEFAULT_MAX_WORKERS

        results = []

        print(
            f"🚀 Starting batch review scraping for {len(product_list)} products")

        for i, product_info in enumerate(product_list):
            product_id = product_info.get('product_id')
            product_name = product_info.get('name', f'Product {product_id}')

            print(f"\n[{i+1}/{len(product_list)}] Processing: {product_name}")

            try:
                product = self.scrape_product(product_id, product_name)

                result = {
                    'product_id': product_id,
                    'name': product_name,
                    'status': 'success' if product.reviews else 'no_reviews',
                    'reviews_count': len(product.reviews),
                    'product': product
                }

            except Exception as e:
                result = {
                    'product_id': product_id,
                    'name': product_name,
                    'status': 'error',
                    'error': str(e),
                    'reviews_count': 0
                }

            results.append(result)

            # Rate limiting between products
            if i < len(product_list) - 1:
                time.sleep(self.config.API_DELAY)

        successful = len([r for r in results if r['status'] == 'success'])
        print(
            f"\n📊 Batch complete: {successful}/{len(product_list)} successful")

        return results
