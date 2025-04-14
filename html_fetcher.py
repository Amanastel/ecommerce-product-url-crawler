import requests
import logging
import time
import random
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse, urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HTMLFetcher:
    """
    Handles the downloading of HTML content from URLs, with respect to robots.txt
    and rate limiting to be a good web citizen.
    """
    
    def __init__(self, respect_robots_txt=True, delay_min=1, delay_max=3, max_retries=3):
        """
        Initialize the HTML fetcher.
        
        Args:
            respect_robots_txt (bool): Whether to respect robots.txt
            delay_min (float): Minimum delay between requests in seconds
            delay_max (float): Maximum delay between requests in seconds
            max_retries (int): Maximum number of retries for failed requests
        """
        self.respect_robots_txt = respect_robots_txt
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_retries = max_retries
        self.robots_cache = {}  # Cache of RobotFileParser objects
        
        # Multiple user agents to rotate through in case of blocks
        self.user_agents = [
            'ProductURLCrawler/1.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
        ]
        
        # Default headers
        self.default_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Google Chrome";v="91", " Not;A Brand";v="99", "Chromium";v="91"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
        }
        
        # Domain-specific configurations
        self.domain_configs = {
            'nykaafashion.com': {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.google.com/'
                },
                'delay_min': 2,
                'delay_max': 5,
                'timeout': 15
            },
            'tatacliq.com': {
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document',
                    'Referer': 'https://www.google.com/'
                },
                'delay_min': 1.5,
                'delay_max': 4,
                'timeout': 12,
                'visit_homepage_first': True,
                'additional_headers': {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }
        }
        
        logger.info(f"Initialized HTML fetcher with respect_robots_txt={respect_robots_txt}")
    
    def _get_robots_parser(self, domain):
        """
        Get or create a RobotFileParser for the given domain.
        
        Args:
            domain (str): The domain to get the robots.txt for
            
        Returns:
            RobotFileParser: The robots parser for the domain
        """
        if domain in self.robots_cache:
            return self.robots_cache[domain]
        
        parsed_url = urlparse(domain)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        robots_url = urljoin(base_url, "/robots.txt")
        
        parser = RobotFileParser()
        parser.set_url(robots_url)
        
        try:
            parser.read()
            self.robots_cache[domain] = parser
            logger.info(f"Fetched and parsed robots.txt for {domain}")
        except Exception as e:
            logger.error(f"Error parsing robots.txt for {domain}: {e}")
            # If we can't read the robots.txt, assume we can fetch anything
            parser = None
        
        return parser
    
    def _can_fetch(self, url):
        """
        Check if we're allowed to fetch the given URL according to robots.txt.
        
        Args:
            url (str): The URL to check
            
        Returns:
            bool: True if we can fetch the URL, False otherwise
        """
        if not self.respect_robots_txt:
            return True
        
        parsed_url = urlparse(url)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        parser = self._get_robots_parser(domain)
        if parser is None:
            return True
        
        return parser.can_fetch(self.user_agents[0], url)
    
    def _get_domain_config(self, url):
        """
        Get domain-specific configuration for the given URL.
        
        Args:
            url (str): The URL to get the configuration for
            
        Returns:
            dict: The domain-specific configuration
        """
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc
        
        for domain, config in self.domain_configs.items():
            if domain in netloc:
                return config
        
        return None
    
    def fetch(self, url):
        """
        Fetch the HTML content of the given URL.
        
        Args:
            url (str): The URL to fetch
            
        Returns:
            str or None: The HTML content of the URL, or None if the fetch failed
        """
        if not self._can_fetch(url):
            logger.warning(f"Not allowed to fetch {url} according to robots.txt")
            return None
        
        # Get domain-specific configuration if available
        domain_config = self._get_domain_config(url)
        
        # Set delay based on domain config or default
        delay_min = domain_config['delay_min'] if domain_config and 'delay_min' in domain_config else self.delay_min
        delay_max = domain_config['delay_max'] if domain_config and 'delay_max' in domain_config else self.delay_max
        
        # Random delay to be nice to servers
        delay = random.uniform(delay_min, delay_max)
        time.sleep(delay)
        
        # Default timeout
        timeout = domain_config['timeout'] if domain_config and 'timeout' in domain_config else 10
        
        # Try with different user agents if needed
        user_agents_to_try = [domain_config['headers']['User-Agent']] if domain_config and 'headers' in domain_config and 'User-Agent' in domain_config['headers'] else self.user_agents
        
        for attempt in range(self.max_retries):
            try:
                # Rotate user agents on retries
                user_agent = user_agents_to_try[attempt % len(user_agents_to_try)]
                
                # Use domain-specific headers or default headers
                if domain_config and 'headers' in domain_config:
                    headers = domain_config['headers'].copy()
                else:
                    headers = self.default_headers.copy()
                    headers['User-Agent'] = user_agent
                
                logger.info(f"Fetching {url} (attempt {attempt + 1}/{self.max_retries})")
                
                # Set up a session to handle cookies
                session = requests.Session()
                
                # For some domains, first visit the homepage to set cookies
                parsed_url = urlparse(url)
                domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                # Check if we should visit homepage first (either explicit config or for specific domains)
                should_visit_homepage = (
                    (domain_config and 'visit_homepage_first' in domain_config and domain_config['visit_homepage_first']) or
                    'nykaafashion.com' in domain or
                    ('tatacliq.com' in domain and attempt > 0)
                )
                
                if should_visit_homepage:
                    logger.info(f"Visiting homepage first to set cookies for {domain}")
                    try:
                        home_response = session.get(domain, headers=headers, timeout=timeout)
                        # Small delay after visiting homepage
                        time.sleep(1)
                        
                        # For TataCliq, we need to handle possible cookies from the homepage
                        if 'tatacliq.com' in domain:
                            # Update headers with specific values from the homepage response
                            if 'additional_headers' in domain_config:
                                for key, value in domain_config['additional_headers'].items():
                                    headers[key] = value
                            
                            # Make additional pre-requests to typical TataCliq endpoints to simulate regular browsing
                            try:
                                session.get(f"{domain}/login", headers=headers, timeout=timeout/2)
                                time.sleep(0.5)
                                categories = ['/fashion', '/electronics', '/beauty']
                                random_category = random.choice(categories)
                                session.get(f"{domain}{random_category}", headers=headers, timeout=timeout/2)
                            except Exception as e:
                                logger.warning(f"Error during TataCliq pre-requests: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to visit homepage for {domain}: {e}")
                
                # Make the actual request
                response = session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
                        logger.info(f"Successfully fetched {url}")
                        return response.text
                    elif 'tatacliq.com' in domain and ('application/json' in content_type or 'javascript' in content_type):
                        # Special case for TataCliq JSON responses that might contain product information
                        logger.info(f"Fetched non-HTML but potentially useful content from {url}")
                        return response.text
                    else:
                        logger.warning(f"URL {url} is not HTML (Content-Type: {content_type})")
                        return None
                elif response.status_code in (301, 302, 303, 307, 308):
                    logger.warning(f"Redirect from {url} to {response.headers.get('Location')}")
                    # If we want to follow redirects, we could do so here
                    
                else:
                    logger.warning(f"Failed to fetch {url}: Status code {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.error(f"Timeout error fetching {url}")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error fetching {url}: {e}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching {url}: {e}")
                
            # Exponential backoff
            if attempt < self.max_retries - 1:
                backoff_time = (2 ** attempt) * random.uniform(1, 2)
                logger.info(f"Retrying in {backoff_time:.2f} seconds...")
                time.sleep(backoff_time)
        
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None 