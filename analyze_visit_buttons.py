#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
import re
from urllib.parse import parse_qs, urlparse, unquote
import html as html_lib


# Helper functions
def is_valid_source_url(url: str) -> bool:
    try:
        if not url or not url.startswith('http'):
            return False
        domain = urlparse(url).netloc.lower()
        # Skip search engines and social sites
        skip = [
            'google.com', 'gstatic.com', 'googleusercontent.com', 'bing.com', 'yahoo.com', 'duckduckgo.com',
            'facebook.com', 'twitter.com', 'instagram.com', 'pinterest.com', 'youtube.com', 'tiktok.com',
        ]
        return not any(s in domain for s in skip)
    except Exception:
        return False


async def accept_consent_if_present(page) -> None:
    try:
        selectors = [
            'button:has-text("I agree")',
            'button:has-text("Accept all")',
            '#L2AGLb',
            'button[aria-label*="Accept"]',
            'button:has-text("הסכמה")',  # Hebrew example
        ]
        for sel in selectors:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                await page.wait_for_timeout(500)
                break
    except Exception:
        pass


def extract_real_url_from_google_href(href: str) -> str | None:
    try:
        if not href:
            return None
        if 'imgrefurl=' in href:
            m = re.search(r'imgrefurl=([^&]+)', href)
            if m:
                return unquote(m.group(1))
        if 'url=' in href:
            m = re.search(r'[?&]url=([^&]+)', href)
            if m:
                return unquote(m.group(1))
        # If already direct and not google
        if href.startswith('http') and 'google.' not in href:
            return href
    except Exception:
        pass
    return None


async def extract_from_panel_interactively(page) -> set:
    collected = set()
    try:
        # Prefer encrypted thumbnails to simulate clicks
        thumb_selectors = [
            'img[src^="https://encrypted-tbn0.gstatic.com/images"]',
            'div.isv-r img',
            'img',
        ]
        images = []
        for sel in thumb_selectors:
            images = await page.query_selector_all(sel)
            if images:
                break
        images = images[:10]

        for idx, img in enumerate(images):
            try:
                await img.click()
                await page.wait_for_timeout(1200)

                # Try direct Visit link
                visit_selectors = [
                    'a:has-text("Visit")',
                    '[role="button"]:has-text("Visit")',
                    'a[href*="imgres"]',
                ]
                hrefs = []
                for sel in visit_selectors:
                    els = await page.query_selector_all(sel)
                    for el in els:
                        href = await el.get_attribute('href')
                        if href:
                            hrefs.append(href)

                # Fallback: collect all anchor hrefs in DOM
                if not hrefs:
                    all_hrefs = await page.evaluate("""
                        () => Array.from(document.querySelectorAll('a'))
                          .map(a => a.getAttribute('href'))
                          .filter(Boolean)
                    """)
                    hrefs.extend(all_hrefs or [])

                # Extract real URLs from href candidates
                for href in hrefs:
                    real = extract_real_url_from_google_href(href)
                    if real and is_valid_source_url(real):
                        collected.add(real)

                # Stop early if enough
                if len(collected) >= 5:
                    break
            except Exception:
                continue
    except Exception:
        pass
    return collected


async def analyze_google_images():
    """Analyze Google Images page structure to understand Visit buttons"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        try:
            # Go to Google Images for Michael Jordan
            await page.goto("https://www.google.com/search?q=michael+jordan&tbm=isch", timeout=30000)
            # Accept consent if shown
            await accept_consent_if_present(page)
            await page.wait_for_selector('img', timeout=10000)
            await page.wait_for_timeout(2000)
            
            # Scroll to load more images
            for _ in range(2):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(1000)
            
            # Get the full HTML to analyze
            html_content = await page.content()
            # Save HTML for inspection
            with open('google_images_debug.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Saved HTML to google_images_debug.html (length: {len(html_content)} chars)")
            
            # Normalize/cleanup for regex parsing
            html_content = html_lib.unescape(html_content)
            
            print("=== ANALYZING PAGE STRUCTURE ===")
            
            # Look for imgres URLs (these contain the Visit button destinations)
            imgres_pattern = r'imgres\?imgurl=([^&]+)&imgrefurl=([^&]+)'
            imgres_matches = re.findall(imgres_pattern, html_content)
            
            print(f"Found {len(imgres_matches)} imgres links")
            
            for i, (img_url, ref_url) in enumerate(imgres_matches[:5]):
                print(f"\nResult {i+1}:")
                print(f"  Image URL: {unquote(img_url)[:80]}...")
                print(f"  Source URL: {unquote(ref_url)[:80]}...")
            
            # Look for data attributes that might contain URLs
            data_patterns = [
                r'data-ou="([^"]*)"',  # Original URL
                r'data-src="([^"]*)"',  # Data source
                r'data-ri="([^"]*)"',   # Result index
            ]
            
            for pattern_name, pattern in zip(['data-ou', 'data-src', 'data-ri'], data_patterns):
                matches = re.findall(pattern, html_content)
                print(f"\n{pattern_name} matches: {len(matches)}")
                if matches:
                    for match in matches[:3]:
                        print(f"  {match[:60]}...")
            
            # Look for specific visit button elements
            visit_patterns = [
                r'<a[^>]*href="([^"]*imgres[^"]*)"[^>]*>.*?visit.*?</a>',
                r'<div[^>]*data-ved="([^"]*)"[^>]*>.*?visit.*?</div>',
            ]
            
            for i, pattern in enumerate(visit_patterns):
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                print(f"\nVisit pattern {i+1}: {len(matches)} matches")
                for match in matches[:2]:
                    print(f"  {match[:80]}...")

            # Extract original website URLs explicitly (multiple strategies)
            print("\n=== EXTRACTING ORIGINAL WEBSITE URLs (STATIC HTML) ===")
            original_urls = set()

            # Strategy A: href with imgrefurl param
            a_imgref_pattern = r"href=\"([^\"]*imgres[^\"]*imgrefurl=([^&\"']+)[^\"]*)\""
            a_imgref_matches = re.findall(a_imgref_pattern, html_content)
            for full, ref in a_imgref_matches:
                try:
                    url = unquote(ref)
                    if is_valid_source_url(url):
                        original_urls.add(url)
                except Exception:
                    pass

            # Strategy B: any imgrefurl= occurrences in the HTML
            loose_imgref_pattern = r"imgrefurl=([^&\"']+)"
            for ref in re.findall(loose_imgref_pattern, html_content):
                try:
                    url = unquote(ref)
                    if is_valid_source_url(url):
                        original_urls.add(url)
                except Exception:
                    pass

            # Strategy C: generic url= param inside hrefs
            a_url_param_pattern = r"href=\"[^\"]*[?&]url=([^&\"']+)"
            for u in re.findall(a_url_param_pattern, html_content):
                try:
                    url = unquote(u)
                    if is_valid_source_url(url):
                        original_urls.add(url)
                except Exception:
                    pass

            # Strategy D: JS data structures ("imgrefurl", "ru")
            js_patterns = [
                r'"imgrefurl":"([^"]+)"',
                r'"ru":"([^"]+)"',
            ]
            for pat in js_patterns:
                for u in re.findall(pat, html_content):
                    try:
                        url = unquote(u)
                        if is_valid_source_url(url):
                            original_urls.add(url)
                    except Exception:
                        pass

            # Print summary (static phase)
            print(f"Found {len(original_urls)} original website URLs (static)")
            for i, url in enumerate(list(original_urls)[:5], 1):
                print(f"  {i}. {urlparse(url).netloc} -> {url[:100]}...")

            # Strategy E: Look for any HTTP URLs in the HTML that aren't Google/Bing
            print("\n=== LOOKING FOR ANY EXTERNAL URLS ===")
            all_urls_pattern = r'https?://[^\s"\'<>]+'
            all_urls = re.findall(all_urls_pattern, html_content)
            external_count = 0
            for url in all_urls:
                # Clean Google tracking parameters
                clean_url = url
                if '&sa=' in clean_url or '&ved=' in clean_url or '&usg=' in clean_url:
                    clean_url = re.sub(r'&(sa|ved|usg)=[^&]*', '', clean_url)
                clean_url = clean_url.replace('&amp;', '&').strip()
                
                if is_valid_source_url(clean_url):
                    original_urls.add(clean_url)
                    external_count += 1
            print(f"Found {external_count} external URLs from {len(all_urls)} total URLs")
            
            # Interactive extraction: click thumbnails and read panel links
            print("\n=== INTERACTIVE EXTRACTION FROM PANEL ===")
            panel_urls = await extract_from_panel_interactively(page)
            for u in panel_urls:
                if is_valid_source_url(u):
                    original_urls.add(u)

            print(f"Found {len(panel_urls)} original website URLs (interactive panel)")

            # Final summary
            print(f"\n=== COMBINED ORIGINAL WEBSITE URLs ===")
            print(f"Total unique: {len(original_urls)}")
            for i, url in enumerate(list(original_urls)[:10], 1):
                print(f"  {i}. {urlparse(url).netloc} -> {url[:120]}...")
            
            await browser.close()
            
        except Exception as e:
            print(f"Error: {e}")
            await browser.close()


if __name__ == "__main__":
    asyncio.run(analyze_google_images())