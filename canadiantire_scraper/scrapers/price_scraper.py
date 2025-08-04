"""
Price Scraper for Canadian Tire

Handles price and inventory data collection using Canadian Tire's internal API.
"""

import requests
import time
from typing import List, Dict, Any, Optional

from ..models.product import PriceInfo
from ..utils.config import Config


class PriceScraper:
    """Scraper for product pricing data using Canadian Tire's internal API."""

    def __init__(self):
        """Initialize the price scraper."""
        self.config = Config()
        self.config.validate_config()

    def fetch_product_price(self, product_id: str, store_id: str = None) -> Optional[PriceInfo]:
        """
        Fetch price and inventory data for a product using the exact same logic as original script.

        Args:
            product_id: Product ID to fetch price for (e.g., "0304426P")
            store_id: Store ID for location-specific pricing (default: "33")

        Returns:
            PriceInfo object or None if fetch failed
        """
        if store_id is None:
            store_id = "33"  # Default store ID from original script

        # Clean product ID (remove 'P' suffix if present) - same as original
        clean_product_id = product_id.replace('P', '').replace('p', '')

        url = "https://apim.canadiantire.ca/v1/product/api/v2/product/sku/PriceAvailability"

        # URL parameters - exactly as in original script
        params = {
            "lang": "en_CA",
            "storeId": store_id,
            "cache": "true",
            "pCode": f"{clean_product_id}p"
        }

        # Request body - exactly as in original script
        request_body = {
            "skus": [
                {
                    "code": clean_product_id  # No 'p' suffix, no storeId
                }
            ]
        }

        print(f"💰 Fetching price for product: {product_id}")

        try:
            # Use POST request with params and JSON body - same as original
            response = requests.post(
                url,
                headers=self.config.PRICE_HEADERS,
                params=params,
                json=request_body,
                timeout=30
            )

            if response.status_code != 200:
                print(
                    f"❌ Price API Error {response.status_code}: {response.text[:200]}")
                return None

            data = response.json()

            # Extract price data from response - adapted from original script logic
            if not data or 'skus' not in data or not data['skus']:
                print(f"⚠️ No price data found for {product_id}")
                return None

            sku_data = data['skus'][0]  # First (and should be only) SKU

            # Parse pricing information using original script field names
            current_price = None
            original_price = None
            sale_price = None

            # Extract current price (main price field from original)
            if 'currentPrice' in sku_data and sku_data['currentPrice']:
                price_obj = sku_data['currentPrice']
                if isinstance(price_obj, dict) and 'value' in price_obj:
                    current_price = float(price_obj['value'])
                elif isinstance(price_obj, (int, float)):
                    current_price = float(price_obj)

            # Extract original price if on sale
            if 'originalPrice' in sku_data and sku_data['originalPrice']:
                original_price = float(sku_data['originalPrice'])

            # Check if on sale
            is_on_sale = sku_data.get('isOnSale', False)
            if is_on_sale and original_price and current_price:
                sale_price = current_price

            # Inventory information using original script field names
            in_stock = sku_data.get('sellable', False)
            inventory_count = None

            # Try to get quantity from fulfillment.availability.quantity
            fulfillment = sku_data.get('fulfillment', {})
            availability = fulfillment.get('availability', {})
            if 'quantity' in availability:
                inventory_count = availability['quantity']

            # Store availability information
            store_availability = {
                'store_shelf_location': sku_data.get('storeShelfLocation', 'N/A'),
                'urgent_low_stock': sku_data.get('isUrgentLowStock', False),
                'warranty': sku_data.get('warrantyMessage', 'N/A')
            }

            price_info = PriceInfo(
                product_id=product_id,
                current_price=current_price,
                original_price=original_price,
                sale_price=sale_price,
                in_stock=in_stock,
                inventory_count=inventory_count,
                store_availability=store_availability
            )

            price_display = f"${current_price}" if current_price else "N/A"
            print(
                f"✅ Price fetched: {price_display} CAD (In stock: {in_stock})")
            return price_info

        except Exception as e:
            print(f"❌ Error fetching price for {product_id}: {e}")
            return None

    def scrape_multiple_prices(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape prices for multiple products.

        Args:
            product_ids: List of product IDs to fetch prices for

        Returns:
            List of price scraping results
        """
        results = []

        print(
            f"💰 Starting batch price scraping for {len(product_ids)} products")

        for i, product_id in enumerate(product_ids):
            print(f"\n[{i+1}/{len(product_ids)}] Processing: {product_id}")

            try:
                price_info = self.fetch_product_price(product_id)

                if price_info:
                    result = {
                        'product_id': product_id,
                        'status': 'success',
                        'price_info': price_info
                    }
                else:
                    result = {
                        'product_id': product_id,
                        'status': 'no_data'
                    }

            except Exception as e:
                result = {
                    'product_id': product_id,
                    'status': 'error',
                    'error': str(e)
                }

            results.append(result)

            # Rate limiting between requests
            if i < len(product_ids) - 1:
                time.sleep(self.config.API_DELAY)

        successful = len([r for r in results if r['status'] == 'success'])
        print(
            f"\n📊 Price scraping complete: {successful}/{len(product_ids)} successful")

        return results

    def get_price_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics from price scraping results.

        Args:
            results: List of price scraping results

        Returns:
            Summary statistics dictionary
        """
        successful_results = [r for r in results if r['status'] == 'success']

        if not successful_results:
            return {
                'total_products': len(results),
                'successful': 0,
                'average_price': None,
                'min_price': None,
                'max_price': None,
                'in_stock_count': 0
            }

        prices = []
        in_stock_count = 0

        for result in successful_results:
            price_info = result['price_info']
            if price_info.current_price:
                prices.append(price_info.current_price)
            if price_info.in_stock:
                in_stock_count += 1

        return {
            'total_products': len(results),
            'successful': len(successful_results),
            'average_price': sum(prices) / len(prices) if prices else None,
            'min_price': min(prices) if prices else None,
            'max_price': max(prices) if prices else None,
            'in_stock_count': in_stock_count,
            'in_stock_percentage': (in_stock_count / len(successful_results)) * 100 if successful_results else 0
        }
