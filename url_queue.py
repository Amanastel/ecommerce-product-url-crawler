from collections import deque
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class URLQueue:
    """
    Manages a queue of URLs to be crawled, while tracking visited URLs to avoid duplicates.
    Implements a breadth-first crawling strategy with prioritization.
    """
    
    def __init__(self, domain):
        """
        Initialize the URL queue with a starting domain.
        
        Args:
            domain (str): The domain to crawl
        """
        self.domain = domain
        self.base_url = self._format_domain(domain)
        self.high_priority_queue = deque([])
        self.regular_queue = deque([self.base_url])
        self.visited = set()
        self.discovered_product_urls = set()
        logger.info(f"Initialized URL queue for domain: {self.domain}")
    
    def _format_domain(self, domain):
        """Format the domain to have a consistent structure"""
        if not domain.startswith(('http://', 'https://')):
            domain = 'https://' + domain
        return domain.rstrip('/')
    
    def add_url(self, url, high_priority=False):
        """
        Add a URL to the queue if it hasn't been visited yet.
        
        Args:
            url (str): The URL to add
            high_priority (bool): Whether to add to the high priority queue
        """
        if url not in self.visited and url not in self.high_priority_queue and url not in self.regular_queue:
            parsed = urlparse(url)
            domain_parsed = urlparse(self.base_url)
            
            # Only add URLs from the same domain
            if parsed.netloc == domain_parsed.netloc:
                if high_priority:
                    self.high_priority_queue.append(url)
                else:
                    self.regular_queue.append(url)
    
    def add_product_url(self, url):
        """
        Add a URL to the discovered product URLs set.
        
        Args:
            url (str): The product URL to add
        """
        self.discovered_product_urls.add(url)
        logger.debug(f"Added product URL: {url}")
    
    def has_next(self):
        """Check if there are more URLs to process"""
        return len(self.high_priority_queue) > 0 or len(self.regular_queue) > 0
    
    def get_next(self):
        """
        Get the next URL to process and mark it as visited.
        Process high priority queue first, then regular queue.
        
        Returns:
            str: The next URL to process
        """
        if not self.has_next():
            return None
        
        # Process high priority queue first
        if self.high_priority_queue:
            url = self.high_priority_queue.popleft()
        else:
            url = self.regular_queue.popleft()
            
        self.visited.add(url)
        return url
    
    def get_product_urls(self):
        """
        Get all discovered product URLs.
        
        Returns:
            list: A list of product URLs
        """
        return list(self.discovered_product_urls)
    
    def size(self):
        """Get the current queue size (both queues)"""
        return len(self.high_priority_queue) + len(self.regular_queue)
    
    def high_priority_size(self):
        """Get the high priority queue size"""
        return len(self.high_priority_queue)
    
    def regular_size(self):
        """Get the regular queue size"""
        return len(self.regular_queue)
    
    def visited_count(self):
        """Get the count of visited URLs"""
        return len(self.visited)
    
    def product_count(self):
        """Get the count of discovered product URLs"""
        return len(self.discovered_product_urls) 