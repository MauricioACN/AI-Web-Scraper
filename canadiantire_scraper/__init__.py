"""
Canadian Tire Scraper Module

A comprehensive Python module for scraping product reviews and pricing data
from Canadian Tire's website using both API and Selenium fallback methods.

Features:
- API-based review scraping using Bazaarvoice
- Price data collection via Canadian Tire's internal API
- Selenium fallback for products without API reviews
- Organized data storage with JSON exports
- Duplicate detection and removal
- Multilingual support (English/French)

Author: AI Web Scraper Team
Version: 2.0.0
"""

from .scrapers.review_scraper import ReviewScraper
from .scrapers.price_scraper import PriceScraper
from .scrapers.selenium_scraper import SeleniumScraper
from .models.product import Product, Review, PriceInfo
from .utils.data_manager import DataManager
from .utils.config import Config

__version__ = "2.0.0"
__author__ = "AI Web Scraper Team"

__all__ = [
    'ReviewScraper',
    'PriceScraper',
    'SeleniumScraper',
    'Product',
    'Review',
    'PriceInfo',
    'DataManager',
    'Config'
]
