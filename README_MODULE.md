# Canadian Tire Scraper Module

A comprehensive Python module for scraping product reviews and pricing data from Canadian Tire's website using both API and Selenium fallback methods.

## 🌟 Features

- **API-based Review Scraping**: Fast extraction using Bazaarvoice API
- **Price Data Collection**: Real-time pricing via Canadian Tire's internal API  
- **Selenium Fallback**: Web scraping for products without API reviews
- **Organized Data Storage**: Structured JSON exports with organized folders
- **Duplicate Detection**: Automatic removal of duplicate reviews
- **Multilingual Support**: Handles English and French reviews
- **Batch Processing**: Efficient bulk operations with threading
- **Resume Functionality**: Continue failed scraping operations
- **Product Discovery**: Automatic product finding across categories
- **Statistics Tracking**: Monitor scraping progress and success rates

## 📁 Project Structure

```
canadiantire_scraper/
├── __init__.py              # Module initialization
├── __main__.py              # Module runner
├── cli.py                   # Command-line interface
├── orchestrator.py          # Main coordination class
├── models/
│   ├── __init__.py
│   └── product.py           # Data models (Product, Review, PriceInfo)
├── scrapers/
│   ├── __init__.py
│   ├── review_scraper.py    # API-based review scraping
│   ├── price_scraper.py     # Price data collection
│   └── selenium_scraper.py  # Selenium fallback scraper
└── utils/
    ├── __init__.py
    ├── config.py            # Configuration and settings
    ├── data_manager.py      # Data storage and organization
    └── product_searcher.py  # Product discovery utilities
```

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install requests selenium python-dotenv

# Download ChromeDriver and ensure it's in your PATH
```

### 2. Configuration

Create a `.env` file in your project root:

```env
BV_BFD_TOKEN=your_bazaarvoice_token_here
OCP_APIM_SUBSCRIPTION_KEY=your_canadiantire_api_key_here
```

### 3. Basic Usage

```python
from canadiantire_scraper import CanadianTireScraper

# Initialize scraper
scraper = CanadianTireScraper()

# Scrape a single product
result = scraper.scrape_single_product("0304426P")
print(f"Found {result['reviews_count']} reviews")

# Search for products
products = scraper.product_searcher.search_products("power tools", max_products=20)
print(f"Found {len(products)} products")
```

## 📖 Detailed Usage

### Command Line Interface

The module includes a comprehensive CLI for all operations:

```bash
# Scrape a single product
python -m canadiantire_scraper single 0304426P

# Discover and scrape 100 products automatically
python -m canadiantire_scraper discover --total 100

# Batch scrape from a product list file
python -m canadiantire_scraper batch --file products.json

# Resume failed scraping operations
python -m canadiantire_scraper resume

# Search for products
python -m canadiantire_scraper search --term "kitchen appliances" --max-results 50

# Show scraping statistics
python -m canadiantire_scraper stats
```

### Python API

#### Single Product Scraping

```python
from canadiantire_scraper import CanadianTireScraper

scraper = CanadianTireScraper()

# Scrape with all features
result = scraper.scrape_single_product(
    product_id="0304426P",
    product_name="Subaru Ice Scraper",
    include_price=True,           # Fetch price data
    use_selenium_fallback=True    # Use Selenium if API fails
)

print(f"Status: {result['status']}")
print(f"Reviews: {result['reviews_count']} via {result['reviews_source']}")
print(f"Files saved: {result['files_saved']}")
```

#### Batch Processing

```python
# Define products to scrape
products = [
    {"product_id": "0304426P", "name": "Subaru Ice Scraper"},
    {"product_id": "0396567P", "name": "Simoniz Air Dryer"},
    {"product_id": "0508732P", "name": "B-Toys Fishing Playset"}
]

# Batch scrape with threading
results = scraper.scrape_multiple_products(
    product_list=products,
    include_price=True,
    use_selenium_fallback=True,
    max_workers=3,
    batch_size=50
)
```

#### Product Discovery

```python
# Automatically discover and scrape products
results = scraper.discover_and_scrape(
    total_products=200,
    include_price=True,
    filter_existing=True  # Skip already scraped products
)
```

#### Price-Only Scraping

```python
# Just get pricing information
product_ids = ["0304426P", "0396567P", "0508732P"]
price_results = scraper.price_scraper.scrape_multiple_prices(product_ids)

for result in price_results:
    if result['status'] == 'success':
        price_info = result['price_info']
        print(f"{result['product_id']}: ${price_info.current_price} CAD")
```

#### Resume Failed Operations

```python
# Resume previous failed scraping
retry_results = scraper.resume_failed_scraping()
print(f"Retried {len(retry_results)} failed products")
```

### Data Models

The module uses structured data models for type safety and consistency:

```python
from canadiantire_scraper.models.product import Product, Review, PriceInfo

# Access structured data
product = result['product']  # Product object
reviews = product.reviews    # List of Review objects
price_info = product.price_info  # PriceInfo object

# Convert to dictionary for JSON export
product_dict = product.to_dict()
```

## 📊 Data Organization

The scraper organizes data into structured folders:

```
data_review/               # API-scraped reviews
├── reviews_0304426P.json
├── reviews_0396567P.json
└── ...

selenium_reviews/          # Selenium-scraped reviews
├── selenium_reviews_0508732P.json
└── ...

price_data/               # Price information
├── price_0304426P.json
└── ...

summaries/                # Operation summaries
├── batch_scraping_1234567890.json
└── ...
```

### Data Format

Each review file contains:

```json
{
  "product_info": {
    "product_id": "0304426P",
    "name": "Subaru Ice Scraper",
    "category": "Automotive",
    "scraped_at": "2025-08-03T10:30:00"
  },
  "reviews": [
    {
      "review_id": "12345",
      "author": "John D",
      "rating": 5,
      "title": "Great product!",
      "text": "Works perfectly...",
      "date": "2025-07-15",
      "source": "api",
      "verified_purchase": true
    }
  ],
  "highlights": {...},
  "features": [...],
  "scraped_with": "api"
}
```

## ⚙️ Configuration

### Environment Variables

- `BV_BFD_TOKEN`: Bazaarvoice API token for review access
- `OCP_APIM_SUBSCRIPTION_KEY`: Canadian Tire API key for pricing/search

### Customization

```python
from canadiantire_scraper.utils.config import Config

# Modify default settings
Config.DEFAULT_REVIEW_LIMIT = 100
Config.API_DELAY = 1.0  # Slower rate limiting
Config.SELENIUM_OPTIONS.append("--window-size=1920,1080")
```

## 🔧 Advanced Features

### Custom Search Terms

```python
# Modify search categories for discovery
Config.SEARCH_TERMS = [
    "custom category 1",
    "custom category 2",
    # ... your categories
]
```

### Filtering Products

```python
# Search with filters
products = scraper.product_searcher.search_products("tools", max_products=100)

# Apply custom filters
filtered = scraper.product_searcher.filter_products_by_criteria(
    products=products,
    min_rating=4.0,
    min_reviews=10,
    categories=["Tools", "Hardware"]
)
```

### Statistics and Monitoring

```python
# Get detailed statistics
stats = scraper.get_scraping_statistics()
print(f"Total products scraped: {stats['total_scraped_products']}")
print(f"API vs Selenium files: {stats['api_review_files']} vs {stats['selenium_review_files']}")
```

## 🛠️ Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   ```
   ValueError: Missing required environment variables: BV_BFD_TOKEN
   ```
   Solution: Set up your `.env` file with the required tokens

2. **ChromeDriver Issues**
   ```
   WebDriverException: 'chromedriver' executable needs to be in PATH
   ```
   Solution: Install ChromeDriver and add to system PATH

3. **API Rate Limiting**
   - Increase delays in config: `Config.API_DELAY = 2.0`
   - Reduce batch sizes: `batch_size=20`
   - Use fewer workers: `max_workers=1`

4. **No Reviews Found**
   - Ensure Selenium fallback is enabled
   - Check if product actually has reviews on the website
   - Verify product ID format (should end with 'P')

### Debug Mode

```python
# Enable verbose logging for Selenium
scraper = CanadianTireScraper()
scraper.selenium_scraper = SeleniumScraper(headless=False)  # See browser
```

## 📈 Performance Tips

1. **Use appropriate batch sizes** (50-100 products per batch)
2. **Enable price scraping selectively** (it's slower than reviews)
3. **Filter existing products** to avoid re-scraping
4. **Use threading judiciously** (2-3 workers typically optimal)
5. **Monitor rate limits** and adjust delays as needed

## 🤝 Contributing

This module is designed to be easily extensible:

- Add new scrapers in `scrapers/`
- Extend data models in `models/`
- Add utilities in `utils/`
- Enhance CLI commands in `cli.py`

## 📄 License

This project is for educational and research purposes. Please respect Canadian Tire's terms of service and robots.txt when using this scraper.

## 🆘 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the examples in `examples.py`
3. Ensure all dependencies are correctly installed
4. Verify your environment variables are set

## 📝 Examples

See `examples.py` for comprehensive usage examples covering all features of the module.
