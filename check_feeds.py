import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 1. The List of Targets
# We included all the Puerto Rico and US sources you mentioned.
URLS = [
    "https://www.elnuevodia.com",
    "https://www.primerahora.com",
    "https://www.metro.pr",
    "https://periodismoinvestigativo.com",
    "https://www.noticel.com",
    "https://radioisla.tv",
    "https://apnews.com",
    "https://www.npr.org",
    "https://www.nytimes.com",
    "https://www.thehill.com",
    "https://www.politico.com",
    "https://www.reuters.com"
]

def find_rss_feed(url):
    print(f"🕵️  Checking {url}...")
    try:
        # Pretend to be a normal browser so they don't block us immediately
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        # If the site is down or blocks us
        if response.status_code != 200:
            return f"❌ Failed to connect (Status: {response.status_code})"
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Strategy 1: Look for the official "RSS Discovery" tag in the HTML head
        # <link rel="alternate" type="application/rss+xml" href="...">
        rss_link = soup.find('link', type='application/rss+xml')
        if rss_link and rss_link.get('href'):
            return f"✅ FOUND RSS: {rss_link['href']}"
            
        # Strategy 2: Look for links that contain 'rss' or 'feed' in the URL text
        # This is a bit of a guess, but often works.
        for link in soup.find_all('a', href=True):
            if '/rss' in link['href'] or '/feed' in link['href']:
                full_link = urljoin(url, link['href'])
                return f"✅ POSSIBLE RSS: {full_link}"
                
        return "⚠️ No obvious feed found (Might need scraping)"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

# 2. Run the Scout
print("--- STARTING FEED SCOUT ---")
for url in URLS:
    result = find_rss_feed(url)
    print(result)
    print("-" * 20)