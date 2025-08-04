# AI-Web-Scraper

A comprehensive web scraping solution for extracting product data, reviews, and pricing information from the Canadian Tire website using API integration and data migration to MongoDB.

## 📊 Project Results
- **404 products** collected
- **~19,000 reviews** extracted  
- **338 price records** gathered
- Data successfully migrated to MongoDB

## � Process

The project began with scraping the Canadian Tire website to collect product data and reviews. During this process, we discovered several key insights:

1. **No CAPTCHA Protection**: Canadian Tire does not implement CAPTCHA validation, allowing large-scale data collection without interruption.

2. **Bazaarvoice Integration**: The website uses **Bazaarvoice**, a third-party platform specializing in user-generated content display, particularly product reviews.

3. **Dynamic Element Challenges**: We encountered difficulties interacting with certain dynamic elements, such as buttons with changing labels, which required significant time and effort to understand.

Based on these findings, we pivoted to directly using the **Bazaarvoice** and **Canadian Tire APIs**, which provided more reliable access to product data, reviews, and pricing information.

## 🛠️ Methodology

Our approach combined web scraping, reverse-engineering API calls, and structured data migration:

1. **Website Analysis**: Analyzed the site structure to understand how product data and reviews were displayed
2. **API Discovery**: Identified Bazaarvoice APIs and Canadian Tire's product/pricing APIs through reverse engineering
3. **Direct API Integration**: Implemented direct API requests for improved speed and reduced complexity
4. **Data Structuring**: Organized extracted data into JSON files with validation for consistency
5. **Database Migration**: Used automated scripts to load data into MongoDB with:
   - Data cleaning and validation
   - Date format conversion
   - Duplicate detection and removal

## � Key Assumptions

- **Search Coverage**: Approximately 20-30 keywords were used in the Canadian Tire search engine
- **Unique Review IDs**: Each review was expected to have a unique identifier
- **Product ID Format**: Product IDs were assumed to follow a consistent format pattern
- **Price Validation**: Only pricing values greater than zero were considered valid data

## 🏗️ Technical Architecture

- **Web Scraping**: Selenium and API integration
- **Data Storage**: MongoDB with optimized indexing
- **Data Processing**: Python-based ETL pipeline
- **APIs Used**: Bazaarvoice review API, Canadian Tire product/search APIs  
