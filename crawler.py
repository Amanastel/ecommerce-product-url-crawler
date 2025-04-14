import logging
import asyncio
import time
import random
from tqdm import tqdm
from urllib.parse import urlparse
import aiohttp
from aiohttp import ClientSession

from url_queue import URLQueue
from html_fetcher import HTMLFetcher
from url_extractor import URLExtractor
from product_identifier import ProductURLIdentifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Crawler:
    """
    Main crawler class that orchestrates the crawling process.
    """
    
    def __init__(self, domains, max_pages_per_domain=100, respect_robots_txt=True, concurrency=5, delay_min=0.5, delay_max=1.5):
        """
        Initialize the crawler with a list of domains.
        
        Args:
            domains (list): List of domains to crawl
            max_pages_per_domain (int): Maximum number of pages to crawl per domain
            respect_robots_txt (bool): Whether to respect robots.txt
            concurrency (int): Maximum number of concurrent requests
            delay_min (float): Minimum delay between requests
            delay_max (float): Maximum delay between requests
        """
        self.domains = domains
        self.max_pages_per_domain = max_pages_per_domain
        self.respect_robots_txt = respect_robots_txt
        self.concurrency = concurrency
        self.delay_min = delay_min
        self.delay_max = delay_max
        
        self.html_fetcher = HTMLFetcher(
            respect_robots_txt=respect_robots_txt,
            delay_min=delay_min,
            delay_max=delay_max
        )
        self.url_extractor = URLExtractor()
        self.product_identifier = ProductURLIdentifier()
        
        self.results = {}  # Domain -> list of product URLs
        
        logger.info(f"Initialized crawler with {len(domains)} domains")
    
    async def crawl_domain(self, domain):
        """
        Crawl a single domain.
        
        Args:
            domain (str): The domain to crawl
            
        Returns:
            list: A list of product URLs found on the domain
        """
        url_queue = URLQueue(domain)
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.concurrency)
        
        # Create a list to hold the tasks
        tasks = []
        
        # Create a progress bar
        pbar = tqdm(total=self.max_pages_per_domain, desc=f"Crawling {domain}")
        
        # Crawler function
        async def process_url(url):
            async with semaphore:
                try:
                    # Fetch HTML content
                    html_content = self.html_fetcher.fetch(url)
                    if not html_content:
                        return
                    
                    # Check if the URL is a product URL
                    if self.product_identifier.is_product_url(url, html_content):
                        logger.info(f"Found product URL: {url}")
                        url_queue.add_product_url(url)
                    
                    # Extract URLs
                    urls = self.url_extractor.extract_urls(html_content, url)
                    
                    # Add extracted URLs to the queue
                    priority_urls = []  # URLs that might be product pages
                    regular_urls = []   # Other URLs
                    
                    for extracted_url in urls:
                        # Prioritize URLs that might be product pages
                        if any(pattern.search(extracted_url) for pattern in self.product_identifier.compiled_product_patterns):
                            priority_urls.append(extracted_url)
                        else:
                            regular_urls.append(extracted_url)
                    
                    # Add priority URLs first
                    for url in priority_urls:
                        url_queue.add_url(url, high_priority=True)
                        
                    # Then add regular URLs
                    for url in regular_urls:
                        url_queue.add_url(url)
                    
                    # Update progress bar
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
        
        # Process URLs from the queue until we hit the maximum
        pages_crawled = 0
        pending_tasks = set()
        
        # Start with the initial URL
        initial_url = url_queue.get_next()
        if initial_url:
            task = asyncio.create_task(process_url(initial_url))
            pending_tasks.add(task)
            task.add_done_callback(pending_tasks.discard)
            pages_crawled += 1
        
        # Continue processing URLs until we hit the limit or run out of URLs
        while pages_crawled < self.max_pages_per_domain and (url_queue.has_next() or pending_tasks):
            # If we have capacity and URLs, start more tasks
            while url_queue.has_next() and pages_crawled < self.max_pages_per_domain and len(pending_tasks) < self.concurrency:
                url = url_queue.get_next()
                if url:
                    # Add a small random delay between requests to avoid overwhelming the server
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    task = asyncio.create_task(process_url(url))
                    pending_tasks.add(task)
                    task.add_done_callback(pending_tasks.discard)
                    pages_crawled += 1
            
            # Wait a bit if we have pending tasks
            if pending_tasks:
                await asyncio.sleep(0.1)
            elif not url_queue.has_next():
                break  # No more URLs to process
        
        # Wait for all remaining tasks to complete
        if pending_tasks:
            await asyncio.gather(*pending_tasks)
        
        # Close the progress bar
        pbar.close()
        
        # Get the product URLs
        product_urls = url_queue.get_product_urls()
        logger.info(f"Found {len(product_urls)} product URLs on {domain}")
        
        return product_urls
    
    async def _crawl_with_retries(self, domain, max_retries=2):
        """
        Crawl a domain with retries if no product URLs are found.
        
        Args:
            domain (str): The domain to crawl
            max_retries (int): Maximum number of retries if no product URLs are found
            
        Returns:
            list: A list of product URLs found on the domain
        """
        product_urls = await self.crawl_domain(domain)
        
        # If no product URLs were found and we have retries left, try again with different settings
        retry_count = 0
        while len(product_urls) == 0 and retry_count < max_retries:
            retry_count += 1
            logger.info(f"No product URLs found for {domain}. Retrying with different settings (attempt {retry_count}/{max_retries})...")
            
            # Adjust settings for retries - increase max pages and delay
            old_max_pages = self.max_pages_per_domain
            old_delay_min = self.html_fetcher.delay_min
            old_delay_max = self.html_fetcher.delay_max
            
            # Use more aggressive settings for retries
            self.max_pages_per_domain = int(self.max_pages_per_domain * 1.5)  # Increase max pages
            self.html_fetcher.delay_min = old_delay_min * 1.5  # Increase delay to avoid rate limiting
            self.html_fetcher.delay_max = old_delay_max * 1.5
            
            # Try again
            product_urls = await self.crawl_domain(domain)
            
            # Restore original settings
            self.max_pages_per_domain = old_max_pages
            self.html_fetcher.delay_min = old_delay_min
            self.html_fetcher.delay_max = old_delay_max
        
        return product_urls
    
    async def crawl_all_domains(self):
        """
        Crawl all domains.
        
        Returns:
            dict: A dictionary mapping domains to lists of product URLs
        """
        tasks = []
        
        # Create a task for each domain
        for domain in self.domains:
            task = asyncio.create_task(self._crawl_with_retries(domain))
            tasks.append((domain, task))
        
        # Wait for all tasks to complete
        for domain, task in tasks:
            try:
                product_urls = await task
                self.results[domain] = product_urls
            except Exception as e:
                logger.error(f"Error crawling domain {domain}: {e}")
                self.results[domain] = []
        
        return self.results
    
    def crawl(self):
        """
        Crawl all domains synchronously.
        
        Returns:
            dict: A dictionary mapping domains to lists of product URLs
        """
        start_time = time.time()
        logger.info(f"Starting crawler with {len(self.domains)} domains")
        
        # Run the crawler
        asyncio.run(self.crawl_all_domains())
        
        # Check if any domains failed to return product URLs
        domains_without_products = [domain for domain, urls in self.results.items() if len(urls) == 0]
        if domains_without_products:
            logger.warning(f"Failed to find product URLs for: {', '.join(domains_without_products)}")
            
            # Try a different approach for failed domains - crawl them one by one with longer timeouts
            logger.info("Attempting to crawl failed domains sequentially with longer timeouts...")
            
            # Override HTML fetcher with longer timeouts and more retries
            old_fetcher = self.html_fetcher
            self.html_fetcher = HTMLFetcher(
                respect_robots_txt=self.respect_robots_txt,
                delay_min=self.delay_min * 2,
                delay_max=self.delay_max * 2,
                max_retries=5
            )
            
            # Crawl failed domains sequentially
            for domain in domains_without_products:
                logger.info(f"Attempting sequential crawl for {domain}")
                try:
                    product_urls = asyncio.run(self.crawl_domain(domain))
                    self.results[domain] = product_urls
                except Exception as e:
                    logger.error(f"Sequential crawl for {domain} failed: {e}")
            
            # Restore original HTML fetcher
            self.html_fetcher = old_fetcher
        
        # Log results
        total_products = sum(len(urls) for urls in self.results.values())
        logger.info(f"Crawler finished in {time.time() - start_time:.2f} seconds")
        logger.info(f"Found {total_products} product URLs across {len(self.domains)} domains")
        
        return self.results 