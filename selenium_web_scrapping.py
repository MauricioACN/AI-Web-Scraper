#!/usr/bin/env python3
"""
Canadian Tire Reviews Selenium Scraper
Simple fallback scraper for products that don't return reviews via API
"""

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import time
import os
import re


def get_product_url(product_id):
    """
    Get the real product URL using Canadian Tire search API
    """
    search_id = product_id.replace('P', '').replace('p', '')

    search_url = "https://apim.canadiantire.ca/v1/search/v2/search"
    headers = {
        "ocp-apim-subscription-key": "c01ef3612328420c9f5cd9277e815a0e",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    params = {
        "q": search_id,
        "store": "33",
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
            print(
                f"🔍 API Response keys: {list(data.keys()) if data else 'No data'}")

            # Check for redirect URL first (common for direct product searches)
            redirect_url = data.get('redirectUrl', '')
            if redirect_url:
                full_url = f"https://www.canadiantire.ca{redirect_url}"
                print(f"✅ Found redirect URL: {full_url}")
                return full_url

            # Fallback to products search
            products = data.get('products', [])

            if not products:
                print(f"⚠️ No products found in response for {product_id}")
                return None

            if not isinstance(products, list):
                print(f"⚠️ 'products' is not a list: {type(products)}")
                return None

            print(f"🔍 Found {len(products)} products in search results")

            # Look for exact match
            for product in products:
                if product.get('code') == search_id:
                    product_url = product.get('url', '')
                    if product_url:
                        full_url = f"https://www.canadiantire.ca{product_url}"
                        print(f"✅ Found URL: {full_url}")
                        return full_url

            print(f"⚠️ Product {product_id} not found in search results")
        else:
            print(f"❌ Search API error: {resp.status_code}")
            print(f"Response: {resp.text[:200]}...")

    except Exception as e:
        print(f"❌ Error finding URL: {e}")
        import traceback
        traceback.print_exc()

    return None


def setup_selenium_driver():
    """
    Setup Chrome driver with optimized settings for scraping
    """
    options = Options()
    options.add_argument("--headless")  # Run in background
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    return webdriver.Chrome(options=options)


def extract_review_data(review_element, index):
    """
    Extract review data from a review element
    """
    review = {
        'review_id': f"selenium_review_{index}",
        'author': '',
        'rating': 0,
        'title': '',
        'text': '',
        'date': '',
        'source': 'selenium',
        'verified_purchase': False,
        'recommendation': None
    }

    try:
        # Get all text from the review element
        full_text = review_element.text.strip()
        print(f"🔍 Processing review {index}: {full_text[:100]}...")

        # Extract rating from text patterns like "5 out of 5 stars", "3 out of 5 stars"
        rating_pattern = r'(\d+)\s*out of\s*(\d+)\s*stars?'
        rating_match = re.search(rating_pattern, full_text, re.IGNORECASE)
        if rating_match:
            review['rating'] = int(rating_match.group(1))
            print(f"✅ Found rating: {review['rating']}")

        # Extract title (usually after the rating and before author)
        # Pattern: rating line, then title, then author
        lines = full_text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if rating_match and rating_match.group(0) in line:
                # Next non-empty line might be the title
                if i + 1 < len(lines):
                    potential_title = lines[i + 1].strip()
                    # Reasonable title length
                    if potential_title and len(potential_title) < 200:
                        review['title'] = potential_title
                        print(f"✅ Found title: {review['title'][:50]}...")
                        break

        # Extract author (improved patterns for better accuracy)
        author_patterns = [
            r'(?:stars?\.?\s*\n.*?\n)([A-Za-z][A-Za-z\s]{1,25})\s*(?:\n.*?(?:EMPLOYEE|VERIFIED|INCENTIVIZED|months?|years?|days?))',
            r'\n([A-Za-z][A-Za-z\s]{1,25})\s*\n.*?(?:VERIFIED PURCHASER|EMPLOYEE REVIEW)',
            r'\n([A-Za-z][A-Za-z\s]{1,25})\s*(?:VERIFIED|EMPLOYEE|INCENTIVIZED)',
            r'\n([A-Za-z][A-Za-z\s]{1,25})\s*\d+\s*(?:months?|years?|days?)\s*ago'
        ]

        for pattern in author_patterns:
            author_match = re.search(pattern, full_text)
            if author_match:
                potential_author = author_match.group(1).strip()
                # Filter out common non-author words and ensure reasonable length
                excluded_words = ['Employee Review', 'Verified Purchaser',
                                  'Incentivized Review', 'Ice scraper', 'A', 'N']
                if (potential_author and
                    potential_author not in excluded_words and
                    len(potential_author) > 1 and
                    len(potential_author) < 50 and
                        not any(word in potential_author for word in ['scraper', 'thick', 'easily', 'EMPLOYEE', 'VERIFIED'])):
                    review['author'] = potential_author
                    print(f"✅ Found author: {review['author']}")
                    break

        # Extract date (look for time patterns like "5 months ago", "a year ago")
        date_pattern = r'(\d+\s*(?:months?|years?|days?)\s*ago|a\s*(?:month|year|day)\s*ago)'
        date_match = re.search(date_pattern, full_text, re.IGNORECASE)
        if date_match:
            review['date'] = date_match.group(1)
            print(f"✅ Found date: {review['date']}")

        # Check for verified purchase
        if 'Verified Purchaser' in full_text:
            review['verified_purchase'] = True
            print("✅ Verified purchase detected")

        # Check for recommendation
        if 'Yes, I recommend this product' in full_text:
            review['recommendation'] = True
        elif 'No, I do not recommend this product' in full_text:
            review['recommendation'] = False

        # Extract review text (the main content)
        # Try to find the main review text between author and "Helpful?" or similar
        text_patterns = [
            # Pattern 1: After author/date, before "Yes, I recommend" or "Helpful?"
            r'(?:months?|years?|days?)\s*ago\s*\n(.*?)(?:Yes, I recommend|Helpful\?|Report)',
            # Pattern 2: After title, before recommendation
            r'(?:' + re.escape(review.get('title', '')) +
            r')\s*\n.*?\n(.*?)(?:Yes, I recommend|Helpful\?)',
            # Pattern 3: Main content block
            r'\n([^{}\n]{50,500})\s*(?:Yes, I recommend|Helpful\?|Report)'
        ]

        for pattern in text_patterns:
            if pattern:  # Skip empty patterns
                text_match = re.search(
                    pattern, full_text, re.DOTALL | re.IGNORECASE)
                if text_match:
                    potential_text = text_match.group(1).strip()
                    # Clean up the text
                    # Normalize whitespace
                    potential_text = re.sub(r'\s+', ' ', potential_text)
                    if len(potential_text) > 10:  # Must have substantial content
                        review['text'] = potential_text
                        print(f"✅ Found review text: {review['text'][:50]}...")
                        break

        # Alternative text extraction: if no pattern worked, try to get the longest meaningful line
        if not review['text']:
            lines = [line.strip()
                     for line in full_text.split('\n') if line.strip()]
            for line in lines:
                if (len(line) > 30 and
                    'stars' not in line.lower() and
                    'helpful' not in line.lower() and
                    'recommend' not in line.lower() and
                        'employee review' not in line.lower()):
                    review['text'] = line
                    print(
                        f"✅ Found alternative text: {review['text'][:50]}...")
                    break

        # Only return if we have meaningful content
        if review['text'] or review['title'] or review['rating'] > 0:
            return review

    except Exception as e:
        print(f"⚠️ Error extracting review {index}: {e}")

    return None


def scrape_product_reviews(product_id, max_reviews=50):
    """
    Scrape reviews for a single product using Selenium
    """
    print(f"🔄 Starting Selenium scrape for product: {product_id}")

    # Step 1: Get product URL
    product_url = get_product_url(product_id)
    if not product_url:
        return {
            'product_id': product_id,
            'status': 'error',
            'error': 'Could not find product URL',
            'reviews': []
        }

    # Step 2: Setup Selenium
    driver = setup_selenium_driver()
    reviews = []

    try:
        # Step 3: Navigate to product page
        print(f"🌐 Loading page: {product_url}")
        driver.get(product_url)

        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)  # Additional wait for dynamic content

        # Step 4: Find reviews section and try to load full reviews
        reviews_section = None
        review_selectors = [
            "#BVRRContainer",
            ".bv-content-container",
            "[data-bv-show='reviews']",
            ".reviews-section"
        ]

        for selector in review_selectors:
            try:
                reviews_section = driver.find_element(
                    By.CSS_SELECTOR, selector)
                print(f"✅ Found reviews section: {selector}")
                driver.execute_script(
                    "arguments[0].scrollIntoView(true);", reviews_section)
                time.sleep(2)
                break
            except:
                continue

        if not reviews_section:
            print("⚠️ No reviews section found")
            return {
                'product_id': product_id,
                'status': 'no_reviews',
                'reviews': []
            }

        # Extract review summary data first (for modern Bazaarvoice implementations)
        summary_data = {}
        try:
            # Extract overall rating
            rating_selectors = [".bv-content-summary-average",
                                ".bv-average-rating", ".overall-rating"]
            for selector in rating_selectors:
                try:
                    rating_elem = driver.find_element(
                        By.CSS_SELECTOR, selector)
                    rating_text = rating_elem.text.strip()
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        summary_data['overall_rating'] = float(
                            rating_match.group(1))
                        print(
                            f"✅ Found overall rating: {summary_data['overall_rating']}")
                        break
                except:
                    continue

            # Extract total review count
            count_selectors = [".bv-content-summary-count",
                               ".review-count", "text()[contains(., 'Reviews')]"]
            for selector in count_selectors:
                try:
                    if "text()" in selector:
                        # XPath selector for text content
                        elements = driver.find_elements(
                            By.XPATH, f"//*[contains(text(), 'Reviews')]")
                        for elem in elements:
                            count_match = re.search(
                                r'(\d+)\s*Reviews?', elem.text)
                            if count_match:
                                summary_data['total_reviews'] = int(
                                    count_match.group(1))
                                print(
                                    f"✅ Found total reviews: {summary_data['total_reviews']}")
                                break
                    else:
                        count_elem = driver.find_element(
                            By.CSS_SELECTOR, selector)
                        count_match = re.search(r'(\d+)', count_elem.text)
                        if count_match:
                            summary_data['total_reviews'] = int(
                                count_match.group(1))
                            print(
                                f"✅ Found total reviews: {summary_data['total_reviews']}")
                            break
                except:
                    continue

            # Extract rating breakdown (5 stars: 81, 4 stars: 35, etc.)
            rating_breakdown = {}
            try:
                rating_rows = driver.find_elements(
                    By.CSS_SELECTOR, ".bv-content-histogram-row, .rating-breakdown-row")
                for row in rating_rows:
                    row_text = row.text
                    # Look for pattern like "5 stars 81 reviews" or "81 reviews with 5 stars"
                    star_match = re.search(
                        r'(\d+)\s*stars?.*?(\d+)\s*reviews?', row_text, re.IGNORECASE)
                    if star_match:
                        stars = int(star_match.group(1))
                        count = int(star_match.group(2))
                        rating_breakdown[f"{stars}_stars"] = count
                        print(f"✅ Found {stars} stars: {count} reviews")

                if rating_breakdown:
                    summary_data['rating_breakdown'] = rating_breakdown
            except Exception as e:
                print(f"⚠️ Error extracting rating breakdown: {e}")

        except Exception as e:
            print(f"⚠️ Error extracting summary data: {e}")

        # Try to find and click buttons to show individual reviews
        show_reviews_buttons = [
            "button[data-bv-show='reviews']",
            ".bv-show-reviews-button",
            ".bv-content-btn-show-reviews",
            "button[data-bv-action='show-reviews']",
            "a[href*='reviews']",
            ".reviews-link",
            "button:contains('Show all reviews')",
            "a:contains('Read reviews')",
            ".bv-content-btn-pages-show-reviews",
            # Try clicking on rating elements to load reviews
            ".bv-rnr__rpifwc-2",  # Rating breakdown rows
            ".primary-rating-star-container"
        ]

        reviews_loaded = False
        for button_selector in show_reviews_buttons:
            try:
                if ":contains(" in button_selector:
                    # XPath for text content
                    button_text = button_selector.split("'")[1]
                    button = driver.find_element(
                        By.XPATH, f"//button[contains(text(), '{button_text}')]")
                else:
                    buttons = driver.find_elements(
                        By.CSS_SELECTOR, button_selector)
                    if buttons:
                        button = buttons[0]  # Click first available button
                    else:
                        continue

                if button.is_displayed():
                    print(f"🔄 Clicking show reviews button: {button_selector}")
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(5)  # Wait longer for reviews to load

                    # Check if reviews appeared
                    if driver.find_elements(By.CSS_SELECTOR, ".bv-content-review, [data-bv-type='review']"):
                        reviews_loaded = True
                        print("✅ Reviews loaded successfully")
                        break
            except Exception as e:
                print(f"⚠️ Error clicking {button_selector}: {e}")
                continue

        # Step 5: Load more reviews if possible (handle pagination)
        load_attempts = 0
        max_pages = 5  # Limit to avoid infinite loops

        while load_attempts < max_pages:
            try:
                # Look for "Next Reviews" or similar pagination buttons
                next_buttons = [
                    "button:contains('Next Reviews')",
                    "a:contains('Next Reviews')",
                    ".bv-content-btn-pages-load-more",
                    ".bv-content-pagination-next",
                    "[aria-label*='Next']",
                    ".pagination-next"
                ]

                next_clicked = False
                for button_selector in next_buttons:
                    try:
                        if ":contains(" in button_selector:
                            # XPath for text content
                            button_text = button_selector.split("'")[1]
                            next_btn = driver.find_element(
                                By.XPATH, f"//button[contains(text(), '{button_text}')]")
                        else:
                            next_btn = driver.find_element(
                                By.CSS_SELECTOR, button_selector)

                        if next_btn.is_displayed() and next_btn.is_enabled():
                            print(
                                f"🔄 Clicking next page button: {button_selector}")
                            driver.execute_script(
                                "arguments[0].click();", next_btn)
                            time.sleep(3)
                            next_clicked = True
                            break
                    except:
                        continue

                if not next_clicked:
                    print("📄 No more pages available")
                    break

                load_attempts += 1
                print(f"📄 Loaded page {load_attempts + 1}")

            except Exception as e:
                print(f"⚠️ Error loading more reviews: {e}")
                break

        # Step 6: Extract reviews
        print("🔍 Waiting for reviews to load...")
        time.sleep(5)  # Wait longer for dynamic content

        # Try multiple review selectors based on what we saw in the example
        review_selectors = [
            ".bv-content-review",           # Standard Bazaarvoice review
            "[data-bv-type='review']",      # Alternative Bazaarvoice
            ".bv-content-review-wrapper",   # Wrapper elements
            ".bv-review",                   # Generic review class
            ".review-item",                 # Review item
            ".review",                      # Simple review class
            # New selectors based on the structure shown
            "[data-testid*='review']",      # Test ID based selectors
            ".bv-rnr__sc-1jy9jb6-0",      # Specific Bazaarvoice classes we saw
            "div[role='article']",          # ARIA role based
            # Look for containers that have star ratings and text
            "div:has(.bv-content-rating)",  # Containers with ratings
            "div:has([aria-label*='stars'])"  # Containers with star elements
        ]

        review_elements = []
        for selector in review_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(
                        f"✅ Found {len(elements)} elements with selector: {selector}")
                    # Validate that these are actually review elements
                    valid_reviews = []
                    for elem in elements:
                        elem_text = elem.text.strip()
                        # Check if element contains review-like content (more specific criteria)
                        if (len(elem_text) > 100 and  # Longer text threshold
                            # Must have rating
                            ('out of' in elem_text.lower() and 'stars' in elem_text.lower()) and
                            # Must have review actions
                            ('helpful' in elem_text.lower() or 'recommend' in elem_text.lower()) and
                            'select to rate' not in elem_text.lower() and  # Exclude rating interface
                                'this action will open' not in elem_text.lower()):  # Exclude form prompts
                            valid_reviews.append(elem)
                            print(
                                f"✅ Valid review element: {elem_text[:100]}...")

                    if valid_reviews:
                        review_elements = valid_reviews
                        print(
                            f"✅ Validated {len(valid_reviews)} actual review elements")
                        break
                else:
                    print(f"⚠️ No elements found with selector: {selector}")
            except Exception as e:
                print(f"⚠️ Error with selector {selector}: {e}")
                continue

        # Debug: Show what's actually in the reviews section
        if not review_elements:
            print("🔍 Debugging: Let's see what's in the reviews section...")
            try:
                reviews_html = reviews_section.get_attribute('innerHTML')[
                    :2000]
                print(f"Reviews section HTML sample: {reviews_html}")

                # Try to find any element that might be a review
                all_elements = reviews_section.find_elements(
                    By.CSS_SELECTOR, "*")
                print(
                    f"🔍 Found {len(all_elements)} total elements in reviews section")

                # Look for elements with 'review' in class or id
                potential_reviews = []
                for elem in all_elements[:20]:  # Check first 20 elements
                    class_name = elem.get_attribute('class') or ''
                    elem_id = elem.get_attribute('id') or ''
                    tag = elem.tag_name
                    if 'review' in class_name.lower() or 'review' in elem_id.lower():
                        potential_reviews.append(
                            f"{tag}.{class_name}#{elem_id}")

                if potential_reviews:
                    print(
                        f"🔍 Potential review elements: {potential_reviews[:10]}")
                else:
                    print("🔍 No obvious review elements found")

                # Try to extract summary information instead
                print("🔍 Attempting to extract summary information...")

                # Look for overall rating in the text
                page_text = driver.find_element(By.TAG_NAME, "body").text
                rating_match = re.search(
                    r'Overall Rating\s*(\d+\.?\d*)', page_text)
                if rating_match:
                    overall_rating = float(rating_match.group(1))
                    summary_data['overall_rating'] = overall_rating
                    print(
                        f"✅ Extracted overall rating from text: {overall_rating}")

                # Look for total reviews count
                reviews_count_match = re.search(r'(\d+)\s*Reviews', page_text)
                if reviews_count_match:
                    total_reviews = int(reviews_count_match.group(1))
                    summary_data['total_reviews'] = total_reviews
                    print(
                        f"✅ Extracted total reviews from text: {total_reviews}")

                # Extract rating breakdown from text
                rating_breakdown = {}
                # Look for patterns like "2 reviews with 5 stars" in the HTML/text
                star_patterns = re.findall(
                    r'(\d+)\s*reviews? with (\d+)\s*stars?', page_text, re.IGNORECASE)
                for count, stars in star_patterns:
                    rating_breakdown[f"{stars}_stars"] = int(count)
                    print(f"✅ Extracted {stars} stars: {count} reviews")

                # Also try alternative pattern like "5 stars 2 reviews" or just number extraction from HTML
                # Try to find the actual count from the HTML structure
                try:
                    rating_elements = driver.find_elements(
                        By.CSS_SELECTOR, ".bv-rnr__rpifwc-2")
                    for elem in rating_elements:
                        elem_text = elem.text
                        # Look for star rating in the element
                        star_match = re.search(r'(\d+)\s*stars?', elem_text)
                        if star_match:
                            stars = star_match.group(1)
                            # Find count elements within this rating row
                            count_elements = elem.find_elements(
                                By.CSS_SELECTOR, ".primary-rating-count span, [aria-hidden='true']")
                            for count_elem in count_elements:
                                count_text = count_elem.text.strip()
                                if count_text.isdigit():
                                    count = int(count_text)
                                    rating_breakdown[f"{stars}_stars"] = count
                                    print(
                                        f"✅ Extracted from HTML {stars} stars: {count} reviews")
                                    break
                except Exception as html_e:
                    print(f"⚠️ Error extracting from HTML elements: {html_e}")

                if rating_breakdown:
                    summary_data['rating_breakdown'] = rating_breakdown

                # Extract AI summary if available
                summary_match = re.search(
                    r'Summary of Reviews.*?AI-generated.*?\n(.*?)(?:Show more|Helpful)', page_text, re.DOTALL)
                if summary_match:
                    ai_summary = summary_match.group(1).strip()
                    summary_data['ai_summary'] = ai_summary
                    print(f"✅ Extracted AI summary: {ai_summary[:100]}...")

            except Exception as debug_e:
                print(f"Debug error: {debug_e}")

        print(f"📝 Found {len(review_elements)} review elements")

        # Extract data from each review
        extracted_reviews = []
        for i, review_elem in enumerate(review_elements[:max_reviews]):
            review_data = extract_review_data(review_elem, i)
            if review_data:
                extracted_reviews.append(review_data)

        # Remove duplicates based on text content and author combination
        unique_reviews = []
        seen_reviews = set()

        for review in extracted_reviews:
            # Create a unique identifier for the review
            review_key = f"{review.get('author', '')}:{review.get('title', '')}:{review.get('text', '')[:100]}"
            if review_key not in seen_reviews:
                seen_reviews.add(review_key)
                unique_reviews.append(review)

        print(
            f"📝 Removed {len(extracted_reviews) - len(unique_reviews)} duplicate reviews")
        extracted_reviews = unique_reviews

        # If no individual reviews found but we have summary data, create a summary response
        if not extracted_reviews and summary_data:
            print("📊 No individual reviews found, but summary data available")
            # Create a synthetic review from summary data
            summary_review = {
                'review_id': 'summary_data',
                'author': 'Summary',
                'rating': summary_data.get('overall_rating', 0),
                'title': 'Product Summary',
                'text': summary_data.get('ai_summary', 'Product has reviews but individual reviews not accessible'),
                'date': '',
                'source': 'selenium_summary',
                'total_reviews': summary_data.get('total_reviews', 0),
                'rating_breakdown': summary_data.get('rating_breakdown', {})
            }
            extracted_reviews.append(summary_review)

        reviews = extracted_reviews
        print(f"✅ Successfully extracted {len(reviews)} reviews")

        return {
            'product_id': product_id,
            'status': 'success',
            'reviews_count': len(reviews),
            'reviews': reviews,
            'url': product_url
        }

    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        return {
            'product_id': product_id,
            'status': 'error',
            'error': str(e),
            'reviews': []
        }

    finally:
        driver.quit()


def scrape_multiple_products(product_ids, save_folder="selenium_reviews"):
    """
    Scrape reviews for multiple products and save results
    """
    print(f"🚀 Starting batch scraping for {len(product_ids)} products")

    # Create save folder
    os.makedirs(save_folder, exist_ok=True)

    results = []
    successful = 0

    for i, product_id in enumerate(product_ids):
        print(f"\n[{i+1}/{len(product_ids)}] Processing: {product_id}")

        result = scrape_product_reviews(product_id)
        results.append(result)

        # Save individual result if successful
        if result['status'] == 'success' and result['reviews']:
            filename = f"{save_folder}/selenium_reviews_{product_id}.json"

            # Format for consistency with API scraper
            formatted_data = {
                "reviews": result['reviews'],
                "highlights": {},
                "features": [],
                "scraped_with": "selenium",
                "product_url": result.get('url', '')
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(formatted_data, f, indent=2, ensure_ascii=False)

            print(f"💾 Saved: {filename}")
            successful += 1

        # Rate limiting
        if i < len(product_ids) - 1:
            time.sleep(2)

    # Save summary
    summary = {
        'total_products': len(product_ids),
        'successful_scrapes': successful,
        'failed_scrapes': len(product_ids) - successful,
        'results': results
    }

    summary_file = f"{save_folder}/selenium_scraping_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Summary: {successful}/{len(product_ids)} successful")
    print(f"💾 Summary saved: {summary_file}")

    return results


def main():
    """
    Main function with interactive menu
    """
    print("🏪 Canadian Tire Selenium Reviews Scraper")
    print("=" * 50)

    choice = input(
        "Choose an option:\n"
        "1: Single product\n"
        "2: Multiple products (comma-separated)\n"
        "3: Load from missing products file\n"
        "Option: "
    )

    if choice == "1":
        # Single product
        product_id = input("Enter product ID (e.g., 0710113P): ").strip()
        if product_id:
            result = scrape_product_reviews(product_id)
            print(f"\n📊 Result: {result['status']}")

            if result['status'] == 'success':
                print(f"Reviews found: {len(result['reviews'])}")
                for i, review in enumerate(result['reviews'][:3]):
                    print(f"\nReview {i+1}:")
                    print(f"  Author: {review['author']}")
                    print(f"  Rating: {review['rating']}")
                    print(f"  Title: {review['title'][:50]}...")
                    print(f"  Text: {review['text'][:100]}...")

                    # Show additional data for summary reviews
                    if review.get('total_reviews'):
                        print(f"  Total Reviews: {review['total_reviews']}")

                    if review.get('rating_breakdown'):
                        print(f"  Rating Breakdown:")
                        for star_rating, count in review['rating_breakdown'].items():
                            stars = star_rating.replace('_stars', '')
                            print(f"    {stars} stars: {count} reviews")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")

    elif choice == "2":
        # Multiple products
        ids_input = input("Enter product IDs (comma-separated): ").strip()
        product_ids = [pid.strip()
                       for pid in ids_input.split(",") if pid.strip()]

        if product_ids:
            scrape_multiple_products(product_ids)

    elif choice == "3":
        # Load from analysis file
        try:
            with open('product_analysis_report.json', 'r') as f:
                data = json.load(f)

            missing_products = data.get('not_in_reviews', [])

            if missing_products:
                print(
                    f"Found {len(missing_products)} products without reviews")
                confirm = input(f"Scrape first 5 products? (y/N): ")

                if confirm.lower() == 'y':
                    scrape_multiple_products(missing_products[:5])
            else:
                print("No missing products found in analysis file")

        except FileNotFoundError:
            print("❌ product_analysis_report.json not found")
        except Exception as e:
            print(f"❌ Error loading file: {e}")

    else:
        print("❌ Invalid option")


if __name__ == "__main__":
    main()
