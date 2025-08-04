"""
Configuration module for Canadian Tire Scraper

Contains all configuration constants, API endpoints, and settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class containing all scraper settings."""

    # API Configuration
    BV_BFD_TOKEN = os.getenv("BV_BFD_TOKEN")
    OCP_APIM_SUBSCRIPTION_KEY = os.getenv("OCP_APIM_SUBSCRIPTION_KEY")

    # API Endpoints
    REVIEWS_API_URL = "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/cv2/resources/data/reviews.json"
    HIGHLIGHTS_API_URL = "https://rh.nexus.bazaarvoice.com/highlights/v3/1/canadiantire-ca/{product_id}"
    FEATURES_API_URL = "https://apps.bazaarvoice.com/bfd/v1/clients/canadiantire-ca/api-products/sentiments/resources/sentiment/v1/features"
    SEARCH_API_URL = "https://apim.canadiantire.ca/v1/search/v2/search"
    PRICE_API_URL = "https://apim.canadiantire.ca/v1/product/api/v2/product/sku/PriceAvailability"

    # Default Headers
    BASE_HEADERS = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "bv-bfd-token": BV_BFD_TOKEN,
        "origin": "https://www.canadiantire.ca",
        "referer": "https://www.canadiantire.ca/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "ocp-apim-subscription-key": OCP_APIM_SUBSCRIPTION_KEY
    }

    # Price API Headers - exactly as in original script
    PRICE_HEADERS = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "ocp-apim-subscription-key": OCP_APIM_SUBSCRIPTION_KEY,
        "bannerId": "CTR",
        "baseSiteId": "CTR",
        "content-type": "application/json",
        "origin": "https://www.canadiantire.ca",
        "referer": "https://www.canadiantire.ca/"
    }

    # Scraping Configuration
    DEFAULT_REVIEW_LIMIT = 50
    DEFAULT_BATCH_SIZE = 50
    DEFAULT_MAX_WORKERS = 3
    DEFAULT_STORE_ID = "33"

    # Rate Limiting
    API_DELAY = 0.5  # seconds between API calls
    BATCH_DELAY = 30  # seconds between batches
    SELENIUM_DELAY = 2  # seconds between selenium operations

    # File Paths
    DEFAULT_REVIEW_FOLDER = "data_review"
    DEFAULT_PRICE_FOLDER = "price_data"
    DEFAULT_SELENIUM_FOLDER = "selenium_reviews"
    DEFAULT_SUMMARY_FOLDER = "summaries"

    # Search Terms for Mass Scraping
    SEARCH_TERMS = [
        "power tools", "hand tools", "kitchen appliances", "bathroom fixtures",
        "outdoor furniture", "camping gear", "fitness equipment", "automotive parts",
        "home security", "lighting fixtures", "storage solutions", "cleaning supplies",
        "pet supplies", "baby products", "seasonal decorations", "plumbing supplies",
        "electrical components", "paint supplies", "flooring materials", "window treatments",
        "garage organization", "lawn care", "snow removal", "pool supplies",
        "workshop equipment", "safety gear", "heating cooling", "smart home devices"
    ]

    # Selenium Configuration
    SELENIUM_OPTIONS = [
        "--headless",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--disable-blink-features=AutomationControlled",
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]

    @classmethod
    def validate_config(cls):
        """Validate that required configuration is present."""
        missing = []

        if not cls.BV_BFD_TOKEN:
            missing.append("BV_BFD_TOKEN")
        if not cls.OCP_APIM_SUBSCRIPTION_KEY:
            missing.append("OCP_APIM_SUBSCRIPTION_KEY")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}")

        return True
