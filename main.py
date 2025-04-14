import json
import logging
import argparse
from crawler import Crawler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def save_results(results, output_file="output.json"):
    """
    Save the results to a JSON file.
    
    Args:
        results (dict): The results to save
        output_file (str): The path to the output file
    """
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {output_file}")

def main():
    """Main entry point for the crawler."""
    parser = argparse.ArgumentParser(description='E-commerce Product URL Crawler')
    
    parser.add_argument('--domains', type=str, nargs='+',
                      help='List of domains to crawl (default: predefined list)')
    
    parser.add_argument('--max-pages', type=int, default=100,
                      help='Maximum number of pages to crawl per domain (default: 100)')
    
    parser.add_argument('--concurrency', type=int, default=5,
                      help='Maximum number of concurrent requests (default: 5)')
    
    parser.add_argument('--respect-robots', action='store_true',
                      help='Respect robots.txt (default: True)')
    
    parser.add_argument('--output', type=str, default='output.json',
                      help='Output file path (default: output.json)')
    
    args = parser.parse_args()
    
    # Default domains if none provided
    default_domains = [
        'https://www.virgio.com/',
        'https://www.tatacliq.com/',
        'https://nykaafashion.com/',
        'https://www.westside.com/'
    ]
    
    domains = args.domains if args.domains else default_domains
    
    # Initialize the crawler
    crawler = Crawler(
        domains=domains,
        max_pages_per_domain=args.max_pages,
        respect_robots_txt=args.respect_robots,
        concurrency=args.concurrency
    )
    
    # Run the crawler
    logger.info("Starting the crawler...")
    results = crawler.crawl()
    
    # Save the results
    save_results(results, args.output)
    
    # Print summary
    total_products = sum(len(urls) for urls in results.values())
    logger.info(f"Crawling completed. Found {total_products} product URLs across {len(domains)} domains.")
    
    for domain, urls in results.items():
        logger.info(f"{domain}: {len(urls)} product URLs")

if __name__ == "__main__":
    main() 