# Ecommerce Product URL Crawler

## Overview
The Ecommerce Product URL Crawler is a Python-based web crawler designed to discover product URLs across multiple e-commerce domains. It efficiently navigates through websites, extracts product links, and handles various challenges associated with web scraping.

## Features
- **Scalability**: Handles large websites with deep hierarchies and numerous products.
- **Concurrency**: Supports concurrent requests to improve crawling speed.
- **Robustness**: Implements error handling and retries for failed requests.
- **Customizable**: Allows users to set parameters such as maximum pages to crawl and concurrency levels.
- **Structured Output**: Outputs unique product URLs in a structured JSON format.

## Architecture
The crawler consists of several components:
- **URL Queue Manager**: Manages the queue of URLs to be crawled.
- **HTML Fetcher**: Fetches HTML content from the specified URLs.
- **URL Extractor**: Extracts product URLs from the fetched HTML.
- **Product URL Identifier**: Identifies valid product URLs based on predefined patterns.
- **Result Collector**: Collects and saves the discovered product URLs.

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Amanastel/ecommerce-product-url-crawler.git
   cd ecommerce-product-url-crawler
   ```

2. Set up a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
To run the crawler, use the following command:
```bash
./venv/bin/python main.py --max-pages 30 --concurrency 4
```
- `--max-pages`: The maximum number of pages to crawl.
- `--concurrency`: The number of concurrent requests to make.

## Output
The crawler will generate an `output.json` file containing the discovered product URLs, structured by domain.


## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.
