import logging
import requests
import time
from django.conf import settings
from urllib.parse import urlparse, urljoin
import time
         
# Define file extensions to ignore (images, pdfs, etc.)
IGNORE_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.rar', '.tar', '.gz', '.mp3', '.mp4', '.avi', '.mov', '.wmv',
    '.css', '.js', '.ico', '.xml', '.txt',
    '.tex', '.py', '.bx2', '.tar.bz2', '.bz2'
)

def is_file_url(link_url):
    """Check if URL points to a file we want to ignore"""
    if not link_url:
        return True
    
    # Parse the URL and get the path
    parsed = urlparse(link_url)
    path = parsed.path.lower()
    
    # Check if path ends with any ignored extension
    return any(path.endswith(ext) for ext in IGNORE_EXTENSIONS)

def scrape_url(url):
    start_time = time.time()
    seen_urls = set()
    
    # Parse the base URL to get netloc for comparison
    base_parsed = urlparse(url)
    base_netloc = base_parsed.netloc

    #
    # Use Crawl4AI to crawl the page and print URLs, title, and description
    #
    try:

        CRAWL4AI_URL = getattr(settings, "CRAWL4AI_URL", "http://crawl4ai:11235")

        # Initialize default values
        title = "No title found"
        description = None
        urls_from_crawl4ai = []
        crawl4ai_payload = {
            "urls": [url],
            "crawler_config": {
                "type": "CrawlerRunConfig", 
                "params": {
                    "stream": False,
                    "cache_mode": "disabled",
                    "exclude_external_links": True,
                    "remove_overlay_elements": True,
                    "word_count_threshold": 5,
                }
            },
            "browser_config": {
                "type": "BrowserConfig",
                "params": {
                    "headless": True,
                    "text_mode": True,
                    "user_agent_mode": "random",
                }
            }
        }
        
        # Retry mechanism for requests.post
        max_retries = 3
        retry_delay_seconds = 1
        
        for attempt in range(max_retries):
            try:
                crawl4ai_response = requests.post(
                    f"{CRAWL4AI_URL}/crawl",
                    json=crawl4ai_payload,
                    timeout=30,
                )
                
                # Check if we got a 500 error
                if crawl4ai_response.status_code == 500:
                    if attempt < max_retries - 1:  # Don't sleep on the last attempt
                        logging.warning(f"Attempt {attempt + 1} failed with 500 error, retrying in {retry_delay_seconds} seconds...")
                        time.sleep(retry_delay_seconds)
                        continue
                    else:
                        crawl4ai_response.raise_for_status()  # This will raise the 500 error
                
                # If we get here, the request succeeded or failed with a non-500 error
                crawl4ai_response.raise_for_status()
                break  # Success, exit the retry loop
                
            except requests.exceptions.HTTPError as e:
                if crawl4ai_response.status_code == 500 and attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed with 500 error, retrying in {retry_delay_seconds} seconds...")
                    time.sleep(retry_delay_seconds)
                    continue
                else:
                    raise  # Re-raise for non-500 errors or final attempt
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed with network error, retrying in {retry_delay_seconds} seconds...")
                    time.sleep(retry_delay_seconds)
                    continue
                else:
                    raise  # Re-raise on final attempt
        
        crawl4ai_data = crawl4ai_response.json()
        
        # crawl4ai_data should contain results for each URL
        if crawl4ai_data.get("success") and crawl4ai_data.get("results"):
            result = crawl4ai_data["results"][0]  # Get first result
            print("Crawl4AI Result:")
            print("URL:", result.get("url"))
            
            # Extract title and description
            title = result.get("metadata", {}).get("title") or "No title found"
            description = result.get("metadata", {}).get("description")
            
            print("Title:", title)
            print("Description:", description)
            
            # Filter internal links to exclude files
            internal_links = result.get("links", {}).get("internal", [])
            urls_from_crawl4ai = []
            
            for link in internal_links:
                href = link.get("href")
                if href and not is_file_url(href):
                    # Handle relative URLs (starting with /)
                    if href.startswith('/'):
                        # Convert relative to absolute URL
                        absolute_href = urljoin(url, href)
                    elif not url.endswith(href):
                        # If URL doesn't end with href, use urljoin
                        absolute_href = urljoin(url, href)
                    else:
                        # Keep href as is if URL already ends with it
                        absolute_href = href
                    
                    # Parse the href to check netloc
                    parsed_href = urlparse(absolute_href)
                    
                    # Skip if different netloc (external links)
                    if parsed_href.netloc != base_netloc:
                        continue
                    
                    # Remove fragment and query params for deduplication
                    clean_url = f"{parsed_href.scheme}://{parsed_href.netloc}{parsed_href.path}"
                    
                    # Skip root path and duplicates
                    if parsed_href.path != "/" and clean_url not in seen_urls:
                        urls_from_crawl4ai.append(clean_url)  # Add the cleaned URL without query params
                        seen_urls.add(clean_url)
            
            #
            # Merge the two lists of URLs
            #
            urls = urls_from_crawl4ai

            #
            # Print the results
            print("Filtered URLs:", urls)

            status_code = result.get("status_code")
            redirected_url = result.get("redirected_url")
            final_url = result.get("url")

            # If Crawl4AI followed a redirect, prefer redirected_url; fall back to result.url
            # when it differs from the requested URL.
            if not redirected_url and final_url:
                requested = urlparse(url)
                landed = urlparse(final_url)
                requested_norm = f"{requested.scheme}://{requested.netloc}{requested.path or '/'}".rstrip('/').lower()
                landed_norm = f"{landed.scheme}://{landed.netloc}{landed.path or '/'}".rstrip('/').lower()
                if landed_norm and landed_norm != requested_norm:
                    redirected_url = final_url

            # Return tuple instead of dictionary to match the calling code
            return (
                title,
                description,
                urls,
                status_code,
                redirected_url,
                time.time() - start_time,
            )
        else:
            raise Exception("No results from Crawl4AI")
    except Exception as e:
        logging.error(f"Error scraping the page: {e}")
        # Return tuple with default values on error
        return (
            "No title found",  # title
            None,               # description
            [],                 # urls
            0,                  # http_status
            None,               # redirected_url
            time.time() - start_time,  # duration
        )