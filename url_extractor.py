import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class URLExtractor:
    """
    Extracts URLs from HTML content, converting relative URLs to absolute ones
    and filtering for internal links.
    """
    
    def __init__(self):
        """Initialize the URL extractor"""
        logger.info("Initialized URL extractor")
    
    def extract_urls(self, html_content, base_url):
        """
        Extract all URLs from the given HTML content.
        
        Args:
            html_content (str): The HTML content to parse
            base_url (str): The base URL to resolve relative URLs against
            
        Returns:
            list: A list of extracted URLs
        """
        if not html_content:
            logger.warning("No HTML content to extract URLs from")
            return []
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            domain = urlparse(base_url).netloc
            
            urls = []
            
            # Extract URLs from anchor tags
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                absolute_url = urljoin(base_url, href)
                
                # Skip fragment identifiers and javascript links
                if self._is_valid_url(absolute_url, domain):
                    urls.append(absolute_url)
            
            # Extract URLs from other tags that might contain URLs
            # For example, <link>, <script>, etc.
            for tag in soup.find_all(['link', 'script', 'img'], src=True):
                src = tag.get('src')
                if src:
                    absolute_url = urljoin(base_url, src)
                    if self._is_valid_url(absolute_url, domain):
                        urls.append(absolute_url)
            
            # Extract URLs from CSS and other resources
            for tag in soup.find_all(['link'], href=True):
                href = tag.get('href')
                if href:
                    absolute_url = urljoin(base_url, href)
                    if self._is_valid_url(absolute_url, domain):
                        urls.append(absolute_url)
            
            # Extract URLs from JSON-LD scripts - often contains product data
            for script in soup.find_all('script', type='application/ld+json'):
                if script.string:
                    self._extract_urls_from_json(script.string, base_url, domain, urls)
            
            # Extract URLs from other embedded scripts (common in modern e-commerce)
            for script in soup.find_all('script'):
                if script.string:
                    # Look for URLs in JavaScript variables
                    self._extract_urls_from_script(script.string, base_url, domain, urls)
            
            # TataCliq specific - extract from window.__INITIAL_STATE__
            for script in soup.find_all('script'):
                if script.string and 'window.__INITIAL_STATE__' in script.string:
                    self._extract_urls_from_initial_state(script.string, base_url, domain, urls)
            
            # TataCliq specific - check for product links in specific format
            if 'tatacliq.com' in domain:
                # Look for product URL patterns in meta tags
                for meta in soup.find_all('meta', {'property': 'og:url'}):
                    if meta.get('content'):
                        url = meta.get('content')
                        if '/p-mp' in url or '/c-mp' in url:
                            absolute_url = urljoin(base_url, url)
                            if self._is_valid_url(absolute_url, domain):
                                urls.append(absolute_url)
                
                # Look for alternative pages from canonical link
                canonical = soup.find('link', {'rel': 'canonical'})
                if canonical and canonical.get('href'):
                    absolute_url = urljoin(base_url, canonical.get('href'))
                    if self._is_valid_url(absolute_url, domain):
                        urls.append(absolute_url)
                
                # Extract from TataCliq's categories which often lead to product pages
                for a_tag in soup.find_all('a'):
                    if a_tag.get('href') and (
                        '/c-' in a_tag.get('href') or 
                        'category' in a_tag.get('href') or
                        '/brand/' in a_tag.get('href')
                    ):
                        absolute_url = urljoin(base_url, a_tag.get('href'))
                        if self._is_valid_url(absolute_url, domain):
                            urls.append(absolute_url)
            
            # Remove duplicates while preserving order
            unique_urls = []
            seen = set()
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            logger.info(f"Extracted {len(unique_urls)} unique URLs from {base_url}")
            return unique_urls
            
        except Exception as e:
            logger.error(f"Error extracting URLs from {base_url}: {e}")
            return []
    
    def _extract_urls_from_json(self, json_string, base_url, domain, urls):
        """
        Extract URLs from a JSON string.
        
        Args:
            json_string (str): The JSON string to parse
            base_url (str): The base URL to resolve relative URLs against
            domain (str): The domain to check against
            urls (list): The list to add extracted URLs to
        """
        try:
            data = json.loads(json_string)
            self._extract_urls_from_json_object(data, base_url, domain, urls)
        except json.JSONDecodeError:
            # Not valid JSON, try to extract using regex
            self._extract_urls_from_text_with_regex(json_string, base_url, domain, urls)
    
    def _extract_urls_from_json_object(self, obj, base_url, domain, urls):
        """
        Recursively extract URLs from a JSON object.
        
        Args:
            obj: The JSON object to parse (dict, list, or primitive)
            base_url (str): The base URL to resolve relative URLs against
            domain (str): The domain to check against
            urls (list): The list to add extracted URLs to
        """
        if isinstance(obj, dict):
            for k, v in obj.items():
                # If the key suggests it might be a URL
                if isinstance(k, str) and any(url_key in k.lower() for url_key in ['url', 'link', 'href', 'src']):
                    if isinstance(v, str) and (v.startswith('/') or v.startswith('http')):
                        absolute_url = urljoin(base_url, v)
                        if self._is_valid_url(absolute_url, domain):
                            urls.append(absolute_url)
                
                # Recurse into the value
                self._extract_urls_from_json_object(v, base_url, domain, urls)
        
        elif isinstance(obj, list):
            for item in obj:
                self._extract_urls_from_json_object(item, base_url, domain, urls)
    
    def _extract_urls_from_script(self, script_content, base_url, domain, urls):
        """
        Extract URLs from a script tag content.
        
        Args:
            script_content (str): The script content to parse
            base_url (str): The base URL to resolve relative URLs against
            domain (str): The domain to check against
            urls (list): The list to add extracted URLs to
        """
        # Look for URL patterns in the script
        self._extract_urls_from_text_with_regex(script_content, base_url, domain, urls)
        
        # Look for JSON objects in the script that might contain URLs
        # Common patterns like "url:" or "link:"
        json_patterns = [
            r'"url"\s*:\s*"([^"]+)"',
            r'"link"\s*:\s*"([^"]+)"',
            r'"href"\s*:\s*"([^"]+)"',
            r'"src"\s*:\s*"([^"]+)"',
            r'"pdpUrl"\s*:\s*"([^"]+)"',  # TataCliq specific
            r'"productUrl"\s*:\s*"([^"]+)"'  # Common in e-commerce
        ]
        
        for pattern in json_patterns:
            for match in re.finditer(pattern, script_content):
                url = match.group(1)
                absolute_url = urljoin(base_url, url)
                if self._is_valid_url(absolute_url, domain):
                    urls.append(absolute_url)
    
    def _extract_urls_from_initial_state(self, script_content, base_url, domain, urls):
        """
        Extract URLs from TataCliq's window.__INITIAL_STATE__ script.
        
        Args:
            script_content (str): The script content to parse
            base_url (str): The base URL to resolve relative URLs against
            domain (str): The domain to check against
            urls (list): The list to add extracted URLs to
        """
        try:
            # Find the INITIAL_STATE value using regex
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});\s*', script_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                # Clean up any JS specific syntax that might cause JSON parsing issues
                json_str = re.sub(r'undefined', '"undefined"', json_str)
                # Try to parse it
                try:
                    data = json.loads(json_str)
                    self._extract_urls_from_json_object(data, base_url, domain, urls)
                except json.JSONDecodeError:
                    # Fallback to regex if the JSON is malformed
                    self._extract_urls_from_text_with_regex(json_str, base_url, domain, urls)
        except Exception as e:
            logger.warning(f"Error extracting URLs from INITIAL_STATE: {e}")
    
    def _extract_urls_from_text_with_regex(self, text, base_url, domain, urls):
        """
        Extract URLs from text using regex.
        
        Args:
            text (str): The text to parse
            base_url (str): The base URL to resolve relative URLs against
            domain (str): The domain to check against
            urls (list): The list to add extracted URLs to
        """
        # Pattern for absolute URLs
        absolute_url_pattern = r'https?://[^\s\'"<>)]+[a-zA-Z0-9]'
        # Pattern for relative URLs
        relative_url_pattern = r'[\'"/][^\s\'"<>)]+\.(html|php|aspx|jsp)[^\s\'"<>)]*'
        # Pattern for TataCliq product URLs
        tatacliq_product_pattern = r'/[a-zA-Z0-9-]+/p-mp\d+'
        
        # Extract absolute URLs
        for match in re.finditer(absolute_url_pattern, text):
            url = match.group(0)
            if self._is_valid_url(url, domain):
                urls.append(url)
        
        # Extract relative URLs
        for match in re.finditer(relative_url_pattern, text):
            url = match.group(0).strip('\'"')
            absolute_url = urljoin(base_url, url)
            if self._is_valid_url(absolute_url, domain):
                urls.append(absolute_url)
        
        # Extract TataCliq product URLs if the domain is tatacliq.com
        if 'tatacliq.com' in domain:
            for match in re.finditer(tatacliq_product_pattern, text):
                url = match.group(0)
                absolute_url = urljoin(base_url, url)
                if self._is_valid_url(absolute_url, domain):
                    urls.append(absolute_url)
    
    def _is_valid_url(self, url, domain):
        """
        Check if a URL is valid and belongs to the same domain.
        
        Args:
            url (str): The URL to check
            domain (str): The domain to check against
            
        Returns:
            bool: True if the URL is valid, False otherwise
        """
        parsed = urlparse(url)
        
        # Skip URLs without a netloc (like javascript: or mailto: links)
        if not parsed.netloc:
            return False
        
        # Skip URLs that don't use http or https
        if not parsed.scheme in ('http', 'https'):
            return False
        
        # Skip URLs with fragments
        if parsed.fragment:
            url = url.split('#')[0]
            if not url:
                return False
        
        # Only return URLs from the same domain
        return parsed.netloc == domain 