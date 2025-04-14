# E-commerce Product URL Crawler

A scalable web crawler designed to discover product URLs across multiple e-commerce websites.

## Overview

This crawler intelligently discovers and extracts product URLs from e-commerce websites. It uses a combination of URL pattern matching, HTML parsing, and parallel processing to efficiently crawl websites and identify product pages.

## Key Features

- **URL Discovery**: Intelligently discovers product pages based on common URL patterns
- **Scalability**: Handles large websites with deep hierarchies and numerous products
- **Performance**: Uses asynchronous processing to minimize runtime
- **Robustness**: Handles various URL structures across different e-commerce platforms

## Architecture

The crawler is built with the following components:

1. **URL Queue Manager**: Maintains a queue of URLs to visit
2. **HTML Fetcher**: Downloads HTML content of each URL
3. **URL Extractor**: Parses HTML content to extract links
4. **Product URL Identifier**: Identifies product URLs based on patterns
5. **Parallel/Async Executor**: Crawls pages in parallel
6. **Result Collector**: Stores found product URLs

## Requirements

- Python 3.8+
- Dependencies specified in `requirements.txt`

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd ecommerce-product-crawler

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

The crawler will process the default list of domains:
- https://www.virgio.com/
- https://www.tatacliq.com/
- https://nykaafashion.com/
- https://www.westside.com/

The results will be saved to `output.json` in the following format:

```json
{
  "https://www.virgio.com": [
    "https://www.virgio.com/product/shirt123",
    "https://www.virgio.com/p/dress456"
  ],
  "https://www.tatacliq.com": [
    "https://www.tatacliq.com/product/item789"
  ]
}
```

## Approach to Finding Product URLs

The crawler uses several heuristics to identify product URLs:

1. **URL Pattern Matching**: Looks for common product URL patterns such as:
   - `/product/`
   - `/p/`
   - `/item/`
   - `/products/`
   - Product ID patterns in URLs

2. **HTML Structure Analysis**: Examines page structure for common product page elements
   
3. **Metadata Inspection**: Checks for product-related metadata in the HTML

The crawler follows a breadth-first approach, starting from the homepage and exploring internal links while prioritizing potential product listing pages.

## Limitations

- Respects robots.txt for ethical crawling
- Uses reasonable delays between requests to avoid overloading servers
- May not identify product URLs with completely custom patterns

## License

MIT # ecommerce-product-url-crawler
