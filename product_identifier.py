import logging
import re
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductURLIdentifier:
    """
    Identifies product URLs based on various heuristics such as URL patterns,
    HTML structure, and metadata.
    """
    
    def __init__(self):
        """Initialize the product URL identifier with common patterns"""
        # Common URL patterns for product pages
        self.product_url_patterns = [
            r'/product/',
            r'/products/[^/]+$',  # Matches /products/something but not /products/
            r'/p/[^/]+',
            r'/item/',
            r'/pd/',
            r'/shop/product/',
            r'/catalog/product/',
            r'/detail/',
            r'/details/',
            r'/buy/',
            
            # Common product ID patterns
            r'product[-_]id=',
            r'product[-_]sku=',
            r'item[-_]id=',
            r'sku=',
            
            # Other common patterns
            r'\/[a-zA-Z0-9-]+-p-\d+',  # like /some-product-name-p-12345
            r'\/[a-zA-Z0-9-]+_\d+\.html',  # like /product_name_12345.html
            
            # Site-specific patterns
            r'\/shop\/[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+$',  # Like /shop/category/product-name
            r'\/collections\/[^/]+\/products\/[^/]+$',  # Shopify pattern
            
            # TataCliq specific patterns
            r'/p-\d+',  # TataCliq pattern like /some-product-name/p-12345
            r'\/[a-zA-Z0-9-]+\/p-mp\d+',  # TataCliq marketplace product pattern
            r'c-mp\d+',  # Another TataCliq pattern
            
            # Nykaa Fashion specific patterns
            r'/productdetails/\d+/',
            r'/[a-zA-Z0-9-]+/p/\d+',
        ]
        
        # Patterns to exclude (false positives)
        self.exclusion_patterns = [
            r'^/$',  # Exclude the homepage
            r'/product-category/',
            r'/product-tag/',
            r'/products-list/',
            r'/product-comparison/',
            r'/search',
            r'/cart',
            r'/checkout',
            r'/account',
            r'/login',
            r'/register',
            r'/about',
            r'/contact',
            r'/faq',
            r'/help',
            r'/privacy',
            r'/terms',
            r'/blog',
            r'/news',
            r'/products$',  # Just /products with nothing after it
            r'/product$',   # Just /product with nothing after it
            r'/collections/[^/]+$',  # Collection pages but not product pages
            r'/category/',
            r'/brand/',
            
            # Additional exclusions for false positives
            r'\.js$',
            r'\.css$',
            r'\.png$',
            r'\.jpg$',
            r'\.gif$',
            r'\.ico$',
            r'\.svg$',
            r'\.woff',
            r'\.ttf',
            r'/images/',
            r'/assets/',
            r'/static/',
            r'/media/',
        ]
        
        # Compiled patterns for efficiency
        self.compiled_product_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.product_url_patterns]
        self.compiled_exclusion_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.exclusion_patterns]
        
        # Domain specific product patterns
        self.domain_specific_patterns = {
            'tatacliq.com': [
                re.compile(r'/[a-zA-Z0-9-]+-mmp\d+', re.IGNORECASE),
                re.compile(r'/[a-zA-Z0-9-]+-\d+.html', re.IGNORECASE),
                re.compile(r'/p-mp\d+', re.IGNORECASE)
            ],
            'nykaafashion.com': [
                re.compile(r'/[a-zA-Z0-9-]+-\d+\?', re.IGNORECASE),
                re.compile(r'/p/\d+', re.IGNORECASE),
                re.compile(r'/buy/[a-zA-Z0-9-]+', re.IGNORECASE)
            ]
        }
        
        logger.info("Initialized product URL identifier")
    
    def is_product_url(self, url, html_content=None):
        """
        Check if the given URL is a product URL based on URL patterns and HTML content.
        
        Args:
            url (str): The URL to check
            html_content (str, optional): The HTML content of the URL
            
        Returns:
            bool: True if the URL is a product URL, False otherwise
        """
        # Exclude homepage
        parsed_url = urlparse(url)
        if parsed_url.path == '/' or parsed_url.path == '':
            return False
            
        # Step 1: Check URL patterns
        url_match = self._check_url_patterns(url)
        if url_match is False:  # Definite non-product URL
            return False
        
        # Step 2: Check domain-specific patterns
        domain = parsed_url.netloc
        if any(domain_key in domain for domain_key in self.domain_specific_patterns.keys()):
            for domain_key, patterns in self.domain_specific_patterns.items():
                if domain_key in domain:
                    decoded_url = unquote(url)
                    for pattern in patterns:
                        if pattern.search(decoded_url):
                            logger.debug(f"URL {url} matched domain-specific pattern {pattern.pattern}")
                            return True
        
        # Step 3: If we have HTML content, check for product indicators
        if html_content and not url_match:  # If URL pattern is not definitive, check HTML
            return self._check_html_indicators(html_content, url)
        
        return url_match
    
    def _check_url_patterns(self, url):
        """
        Check if the URL matches common product URL patterns.
        
        Args:
            url (str): The URL to check
            
        Returns:
            bool: True if the URL is likely a product URL, False if definitely not, None if uncertain
        """
        decoded_url = unquote(url)
        path = urlparse(decoded_url).path
        
        # First check exclusion patterns - if any match, it's definitely not a product
        for pattern in self.compiled_exclusion_patterns:
            if pattern.search(decoded_url) or pattern.search(path):
                return False
        
        # Then check product patterns
        for pattern in self.compiled_product_patterns:
            if pattern.search(decoded_url) or pattern.search(path):
                logger.debug(f"URL {url} matched product pattern {pattern.pattern}")
                return True
        
        # No definitive patterns matched
        return None
    
    def _check_html_indicators(self, html_content, url=None):
        """
        Check if the HTML content has indicators of a product page.
        
        Args:
            html_content (str): The HTML content to check
            url (str, optional): The URL for domain-specific checks
            
        Returns:
            bool: True if the content indicates a product page, False otherwise
        """
        if not html_content:
            return False
        
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Domain-specific checks
            if url:
                domain = urlparse(url).netloc
                
                # TataCliq specific checks
                if 'tatacliq.com' in domain:
                    # Check for product schema or specific TataCliq product page elements
                    if soup.find('div', {'class': 'ProductDetailsContainer'}):
                        return True
                    if soup.find('div', {'class': 'PDPDesktop'}):
                        return True
                    if soup.find('div', {'id': 'product-details'}):
                        return True
                        
                    # Check for TataCliq's product JSON data
                    for script in soup.find_all('script'):
                        if script.string and ('productInfo' in script.string or 'productDetails' in script.string):
                            for pattern in [r'"productId"\s*:\s*"([^"]+)"', r'"productSKU"\s*:\s*"([^"]+)"', r'"productName"\s*:\s*"([^"]+)"']:
                                if re.search(pattern, script.string):
                                    return True
                                    
                    # Check the URL for typical TataCliq product URL patterns
                    if '/p-mp' in url or '/c-mp' in url or 'productDetails' in url:
                        return True
                
                # Nykaa Fashion specific checks
                if 'nykaafashion.com' in domain:
                    if soup.find('div', {'class': 'product-info'}):
                        return True
                    if soup.find('div', {'class': 'product-details'}):
                        return True
                    if soup.find('button', {'class': re.compile('add-to-bag', re.IGNORECASE)}):
                        return True
            
            # Check for common product page indicators
            
            # 1. Check for structured product data (microdata, JSON-LD)
            if soup.find('div', {'itemtype': re.compile(r'product', re.IGNORECASE)}):
                return True
            
            schema_script = soup.find('script', {'type': 'application/ld+json'})
            if schema_script and schema_script.string:
                if re.search(r'("@type":\s*"Product"|"@type":\s*"ProductPage")', schema_script.string):
                    return True
            
            # 2. Check for common product page elements
            product_indicators = [
                # Price indicators
                soup.find(text=re.compile(r'(price|cost|mrp)', re.IGNORECASE)),
                soup.find('div', {'class': re.compile(r'(price|cost|mrp)', re.IGNORECASE)}),
                soup.find('span', {'class': re.compile(r'(price|cost|mrp)', re.IGNORECASE)}),
                
                # Add to cart buttons
                soup.find('button', text=re.compile(r'(add|buy|cart|basket)', re.IGNORECASE)),
                soup.find('a', text=re.compile(r'(add|buy|cart|basket)', re.IGNORECASE)),
                soup.find('button', {'class': re.compile(r'(add-to-cart|buy-now|cart-btn)', re.IGNORECASE)}),
                
                # Product specific sections
                soup.find('div', {'id': re.compile(r'(product|item)', re.IGNORECASE)}),
                soup.find('div', {'class': re.compile(r'(product|item)-detail', re.IGNORECASE)}),
                
                # Product description
                soup.find('div', {'class': re.compile(r'description', re.IGNORECASE)}),
                
                # Product specifications
                soup.find('div', {'class': re.compile(r'(spec|specification)', re.IGNORECASE)}),
                
                # Product SKU
                soup.find(text=re.compile(r'(sku|item|product)(\s+|-)code', re.IGNORECASE)),
                
                # Quantity selector (common on product pages)
                soup.find('select', {'name': re.compile(r'(qty|quantity)', re.IGNORECASE)}),
                soup.find('input', {'name': re.compile(r'(qty|quantity)', re.IGNORECASE)}),
                
                # Size/color selection (common on product pages)
                soup.find('div', {'class': re.compile(r'(size|color)-selector', re.IGNORECASE)}),
                soup.find('select', {'name': re.compile(r'(size|color)', re.IGNORECASE)})
            ]
            
            # If we have at least 3 product indicators, it's likely a product page
            if sum(1 for indicator in product_indicators if indicator) >= 3:
                # Additional check to make sure it's not a category page with multiple products
                # Category pages often have product cards with prices and buttons
                # If there are many "Add to cart" buttons, it's likely a category page
                add_to_cart_buttons = soup.find_all(['button', 'a'], text=re.compile(r'(add|buy|cart|basket)', re.IGNORECASE))
                if len(add_to_cart_buttons) > 5:  # If there are many buttons, it's a category page
                    return False
                
                return True
            
            # 3. Check page title and meta description
            title_tag = soup.find('title')
            meta_description = soup.find('meta', {'name': 'description'})
            
            product_title_indicators = [
                r'buy',
                r'price', 
                r'\bproduct\b', 
                r'details',
                r'specifications'
            ]
            
            if title_tag:
                title_text = title_tag.text.lower()
                # Make sure title doesn't indicate a category/list page
                if re.search(r'(list|collection|category|products)', title_text):
                    pass  # Might be a category page
                elif any(re.search(pattern, title_text) for pattern in product_title_indicators):
                    return True
            
            if meta_description and meta_description.get('content'):
                meta_text = meta_description['content'].lower()
                if re.search(r'(buy|price|shop)', meta_text) and not re.search(r'(collection|category)', meta_text):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking HTML indicators: {e}")
            return False 