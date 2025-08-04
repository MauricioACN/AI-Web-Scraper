"""
Selenium Scraper for Canadian Tire

Fallback scraper for products that don't return reviews via API.
Uses Selenium WebDriver to extract reviews directly from web pages.
"""

import requests
import re
import time
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from ..models.product import Product, Review
from ..utils.config import Config


class SeleniumScraper:
    """Selenium-based scraper for Canadian Tire product reviews."""

    def __init__(self, headless: bool = True):
        """
        Initialize the Selenium scraper.

        Args:
            headless: Whether to run Chrome in headless mode
        """
        self.config = Config()
        self.headless = headless
        self.driver = None

    def setup_driver(self) -> webdriver.Chrome:
        """
        Setup Chrome WebDriver with optimized options.

        Returns:
            Configured Chrome WebDriver instance
        """
        options = Options()

        # Add standard options
        for option in self.config.SELENIUM_OPTIONS:
            if option == "--headless" and not self.headless:
                continue  # Skip headless if disabled
            options.add_argument(option)

        # Additional experimental options
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        return webdriver.Chrome(options=options)

    def get_product_url(self, product_id: str) -> Optional[str]:
        """
        Find the real product URL using Canadian Tire search API.

        Args:
            product_id: Product ID to find URL for

        Returns:
            Full product URL or None if not found
        """
        search_id = product_id.replace('P', '').replace('p', '')

        search_url = self.config.SEARCH_API_URL
        headers = {
            "ocp-apim-subscription-key": self.config.OCP_APIM_SUBSCRIPTION_KEY,
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        params = {
            "q": search_id,
            "store": self.config.DEFAULT_STORE_ID,
            "rows": 10,
            "lang": "en_CA",
            "baseStoreId": "CTR",
            "apiversion": "5.5"
        }

        try:
            print(f"🔍 Finding URL for product: {product_id}")
            resp = requests.get(search_url, headers=headers, params=params)

            if resp.status_code == 200:
                data = resp.json()

                # Check for direct redirect URL first
                redirect_url = data.get('redirectUrl', '')
                if redirect_url:
                    full_url = f"https://www.canadiantire.ca{redirect_url}"
                    print(f"✅ Found redirect URL: {full_url}")
                    return full_url

                # Fallback to products search
                products = data.get('products', [])
                if products:
                    for product in products:
                        if product.get('code') == search_id:
                            product_url = product.get('url', '')
                            if product_url:
                                full_url = f"https://www.canadiantire.ca{product_url}"
                                print(f"✅ Found product URL: {full_url}")
                                return full_url

                print(f"⚠️ Product {product_id} not found in search results")
            else:
                print(f"❌ Search API error: {resp.status_code}")

        except Exception as e:
            print(f"❌ Error finding URL: {e}")

        return None

    def extract_review_data(self, review_element, index: int) -> Optional[Review]:
        """
        Extract review data from a web element.

        Args:
            review_element: Selenium WebElement containing review
            index: Review index for ID generation

        Returns:
            Review object or None if extraction failed
        """
        try:
            full_text = review_element.text.strip()
            print(f"🔍 Processing review {index}: {full_text[:100]}...")

            # Extract rating from text patterns
            rating = 0
            rating_pattern = r'(\d+)\s*out of\s*(\d+)\s*stars?'
            rating_match = re.search(rating_pattern, full_text, re.IGNORECASE)
            if rating_match:
                rating = int(rating_match.group(1))
                print(f"✅ Found rating: {rating}")

            # Extract title (usually after rating)
            title = ""
            lines = full_text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if rating_match and rating_match.group(0) in line:
                    if i + 1 < len(lines):
                        potential_title = lines[i + 1].strip()
                        if potential_title and len(potential_title) < 200:
                            title = potential_title
                            print(f"✅ Found title: {title[:50]}...")
                            break

            # Extract author using improved patterns
            author = ""
            author_patterns = [
                r'(?:stars?\.?\s*\n.*?\n)([A-Za-z][A-Za-z\s]{1,25})\s*(?:\n.*?(?:EMPLOYEE|VERIFIED|INCENTIVIZED|months?|years?|days?))',
                r'\n([A-Za-z][A-Za-z\s]{1,25})\s*\n.*?(?:VERIFIED PURCHASER|EMPLOYEE REVIEW)',
                r'\n([A-Za-z][A-Za-z\s]{1,25})\s*(?:VERIFIED|EMPLOYEE|INCENTIVIZED)',
                r'\n([A-Za-z][A-Za-z\s]{1,25})\s*\d+\s*(?:months?|years?|days?)\s*ago'
            ]

            excluded_words = [
                'Employee Review', 'Verified Purchaser', 'Incentivized Review', 'Ice scraper']

            for pattern in author_patterns:
                author_match = re.search(pattern, full_text)
                if author_match:
                    potential_author = author_match.group(1).strip()
                    if (potential_author and
                        potential_author not in excluded_words and
                        len(potential_author) > 1 and
                            len(potential_author) < 50):
                        author = potential_author
                        print(f"✅ Found author: {author}")
                        break

            # Extract date
            date = ""
            date_pattern = r'(\d+\s*(?:months?|years?|days?)\s*ago|a\s*(?:month|year|day)\s*ago)'
            date_match = re.search(date_pattern, full_text, re.IGNORECASE)
            if date_match:
                date = date_match.group(1)
                print(f"✅ Found date: {date}")

            # Check for verified purchase
            verified_purchase = 'Verified Purchaser' in full_text
            if verified_purchase:
                print("✅ Verified purchase detected")

            # Check for recommendation
            recommendation = None
            if 'Yes, I recommend this product' in full_text:
                recommendation = True
            elif 'No, I do not recommend this product' in full_text:
                recommendation = False

            # Extract review text (main content)
            text = ""
            text_patterns = [
                r'(?:months?|years?|days?)\s*ago\s*\n(.*?)(?:Yes, I recommend|Helpful\?|Report)',
                r'(?:' + re.escape(title) +
                r')\s*\n.*?\n(.*?)(?:Yes, I recommend|Helpful\?)',
                r'\n([^{}\n]{50,500})\s*(?:Yes, I recommend|Helpful\?|Report)'
            ]

            for pattern in text_patterns:
                if pattern:
                    text_match = re.search(
                        pattern, full_text, re.DOTALL | re.IGNORECASE)
                    if text_match:
                        potential_text = text_match.group(1).strip()
                        potential_text = re.sub(r'\s+', ' ', potential_text)
                        if len(potential_text) > 10:
                            text = potential_text
                            print(f"✅ Found review text: {text[:50]}...")
                            break

            # Alternative text extraction if patterns failed
            if not text:
                lines = [line.strip()
                         for line in full_text.split('\n') if line.strip()]
                for line in lines:
                    if (len(line) > 30 and
                        'stars' not in line.lower() and
                        'helpful' not in line.lower() and
                        'recommend' not in line.lower() and
                            'employee review' not in line.lower()):
                        text = line
                        print(f"✅ Found alternative text: {text[:50]}...")
                        break

            # Only return if we have meaningful content
            if text or title or rating > 0:
                return Review(
                    review_id=f"selenium_review_{index}",
                    author=author,
                    rating=rating,
                    title=title,
                    text=text,
                    date=date,
                    source="selenium",
                    verified_purchase=verified_purchase,
                    recommendation=recommendation
                )

        except Exception as e:
            print(f"⚠️ Error extracting review {index}: {e}")

        return None

    def scrape_product_reviews(self, product_id: str, max_reviews: int = 50) -> Product:
        """
        Scrape reviews for a single product using Selenium.

        Args:
            product_id: Product ID to scrape
            max_reviews: Maximum number of reviews to extract

        Returns:
            Product object with scraped reviews
        """
        print(f"🔄 Starting Selenium scrape for product: {product_id}")

        # Create product object
        product = Product(
            product_id=product_id,
            name=f"Product {product_id}"
        )

        # Get product URL
        product_url = self.get_product_url(product_id)
        if not product_url:
            print("❌ Could not find product URL")
            return product

        product.url = product_url
        self.driver = self.setup_driver()

        try:
            # Navigate to product page
            print(f"🌐 Loading page: {product_url}")
            self.driver.get(product_url)

            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)

            # Find reviews section
            reviews_section = None
            review_selectors = [
                "#BVRRContainer",
                ".bv-content-container",
                "[data-bv-show='reviews']",
                ".reviews-section"
            ]

            for selector in review_selectors:
                try:
                    reviews_section = self.driver.find_element(
                        By.CSS_SELECTOR, selector)
                    print(f"✅ Found reviews section: {selector}")
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);", reviews_section)
                    time.sleep(2)
                    break
                except:
                    continue

            if not reviews_section:
                print("⚠️ No reviews section found")
                return product

            # Try to load reviews by clicking rating elements
            rating_elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".bv-rnr__rpifwc-2")
            for element in rating_elements[:2]:  # Try first 2 elements
                try:
                    if element.is_displayed():
                        print("🔄 Clicking rating element to load reviews")
                        self.driver.execute_script(
                            "arguments[0].click();", element)
                        time.sleep(5)
                        break
                except:
                    continue

            # Extract reviews
            print("🔍 Waiting for reviews to load...")
            time.sleep(5)

            # Find review elements
            review_selectors = [
                "div:has([aria-label*='stars'])",
                ".bv-rnr__sc-1jy9jb6-0",
                ".bv-content-review",
                "[data-bv-type='review']"
            ]

            review_elements = []
            for selector in review_selectors:
                try:
                    elements = self.driver.find_elements(
                        By.CSS_SELECTOR, selector)
                    if elements:
                        print(
                            f"✅ Found {len(elements)} elements with selector: {selector}")

                        # Validate elements contain review content
                        valid_reviews = []
                        for elem in elements:
                            elem_text = elem.text.strip()
                            if (len(elem_text) > 100 and
                                ('out of' in elem_text.lower() and 'stars' in elem_text.lower()) and
                                ('helpful' in elem_text.lower() or 'recommend' in elem_text.lower()) and
                                    'select to rate' not in elem_text.lower()):
                                valid_reviews.append(elem)

                        if valid_reviews:
                            review_elements = valid_reviews
                            print(
                                f"✅ Validated {len(valid_reviews)} actual review elements")
                            break
                except Exception as e:
                    print(f"⚠️ Error with selector {selector}: {e}")
                    continue

            # Extract review data
            extracted_reviews = []
            for i, review_elem in enumerate(review_elements[:max_reviews]):
                review_data = self.extract_review_data(review_elem, i)
                if review_data:
                    extracted_reviews.append(review_data)

            # Remove duplicates
            unique_reviews = []
            seen_reviews = set()

            for review in extracted_reviews:
                review_key = f"{review.author}:{review.title}:{review.text[:100]}"
                if review_key not in seen_reviews:
                    seen_reviews.add(review_key)
                    unique_reviews.append(review)
                    product.add_review(review)

            duplicates_removed = len(extracted_reviews) - len(unique_reviews)
            if duplicates_removed > 0:
                print(f"📝 Removed {duplicates_removed} duplicate reviews")

            print(
                f"✅ Successfully extracted {len(unique_reviews)} unique reviews")

        except Exception as e:
            print(f"❌ Error during scraping: {e}")

        finally:
            if self.driver:
                self.driver.quit()

        return product

    def scrape_multiple_products(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape reviews for multiple products.

        Args:
            product_ids: List of product IDs to scrape

        Returns:
            List of scraping results
        """
        results = []

        print(
            f"🚀 Starting batch Selenium scraping for {len(product_ids)} products")

        for i, product_id in enumerate(product_ids):
            print(f"\n[{i+1}/{len(product_ids)}] Processing: {product_id}")

            try:
                product = self.scrape_product_reviews(product_id)

                result = {
                    'product_id': product_id,
                    'status': 'success' if product.reviews else 'no_reviews',
                    'reviews_count': len(product.reviews),
                    'product': product,
                    'url': product.url
                }

            except Exception as e:
                result = {
                    'product_id': product_id,
                    'status': 'error',
                    'error': str(e),
                    'reviews_count': 0
                }

            results.append(result)

            # Rate limiting between products
            if i < len(product_ids) - 1:
                time.sleep(self.config.SELENIUM_DELAY)

        successful = len([r for r in results if r['status'] == 'success'])
        print(
            f"\n📊 Selenium scraping complete: {successful}/{len(product_ids)} successful")

        return results
