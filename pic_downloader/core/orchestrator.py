"""
Main orchestrator class following Dependency Inversion Principle and Open/Closed Principle
"""

import asyncio
import threading
from typing import List, Set, Dict, Any, Tuple
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

from .interfaces import (
    ISearchProvider, IImageExtractor, IImageDownloader, 
    IContentFilter, IStorageManager, IDatabaseManager, 
    ISearchStrategy, IProgressTracker, SearchResult, ImageTask, DownloadResult
)

class ImageDownloadOrchestrator:
    """
    Main orchestrator that coordinates all image download operations
    Following Dependency Inversion Principle - depends on abstractions, not concretions
    """
    
    def __init__(
        self,
        search_provider: ISearchProvider,
        image_extractor: IImageExtractor,
        image_downloader: IImageDownloader,
        content_filter: IContentFilter,
        storage_manager: IStorageManager,
        database_manager: IDatabaseManager,
        search_strategy: ISearchStrategy,
        progress_tracker: IProgressTracker,
        max_workers: int = 8,
        config=None
    ):
        # Dependencies injected through constructor (Dependency Inversion)
        self.search_provider = search_provider
        self.image_extractor = image_extractor
        self.image_downloader = image_downloader
        self.content_filter = content_filter
        self.storage_manager = storage_manager
        self.database_manager = database_manager
        self.search_strategy = search_strategy
        self.progress_tracker = progress_tracker
        
        # Configuration
        self.max_workers = max_workers
        self.config = config or self._create_default_config()
        
        # Thread-safe tracking
        self.lock = threading.Lock()
        self.downloaded_hashes = set()
        self.processed_urls = set()  # Track processed URLs to prevent duplicates
        self.new_downloads = 0
        self.skipped_duplicates = 0
        
        # Load existing hashes
        self._load_existing_hashes()
    
    def _create_default_config(self):
        """Create default configuration if none provided"""
        from ..config.settings import ConfigurationManager
        return ConfigurationManager()
    
    def _load_existing_hashes(self):
        """Load existing image hashes from database"""
        self.downloaded_hashes = self.database_manager.get_existing_hashes()
        self.progress_tracker.log_activity(f"Loaded {len(self.downloaded_hashes)} existing image hashes", "INFO")
    
    async def download_images(self, base_query: str, max_images: int) -> Dict[str, Any]:
        """
        Main method to download images following the orchestrated workflow
        """
        self.progress_tracker.log_phase_start("Initialization", f"Starting download for '{base_query}' - Target: {max_images} images")
        
        # Create search entry
        search_id = self.database_manager.create_search(base_query)
        
        # Phase 1: Base Query Search
        self.progress_tracker.log_phase_start("Base Query Search", f"Searching for '{base_query}'")
        base_result = await self.search_provider.search(base_query)
        
        if base_result.urls:
            self.progress_tracker.log_activity(f"Found {len(base_result.urls)} unique source websites", "INFO")
            
            # Limit URLs based on target images - be more aggressive for large targets
            if max_images <= 20:
                max_urls_needed = min(len(base_result.urls), max(10, max_images * 2))
            elif max_images <= 100:
                max_urls_needed = min(len(base_result.urls), max(50, max_images * 3))
            else:
                # For large targets like 500, be much more aggressive
                max_urls_needed = min(len(base_result.urls), max(200, max_images * 4))
            
            limited_urls = set(list(base_result.urls)[:max_urls_needed])
            
            self.progress_tracker.log_activity(f"Limiting to {len(limited_urls)} most relevant URLs", "INFO")
            new_count = self.database_manager.store_urls(search_id, limited_urls)
            self.progress_tracker.log_activity(f"Stored {new_count} new URLs", "INFO")
        else:
            self.progress_tracker.log_activity("No URLs found in base search", "WARNING")
            return self._create_result_dict(base_query, 0, 0, "No URLs found")
        
        # Phase 2: Process Base Query URLs
        self.progress_tracker.log_phase_start("Base Query Processing", "Processing websites from base query")
        base_downloads = await self._process_urls_phase(search_id, max_images, "base query")
        
        # Phase 3: Check if we need variations
        if self.new_downloads < max_images:
            remaining_needed = max_images - self.new_downloads
            self.progress_tracker.log_activity(f"Base query yielded {self.new_downloads} images, need {remaining_needed} more", "INFO")
            
            # Try remaining unvisited URLs first
            remaining_downloads = await self._try_remaining_urls(search_id, remaining_needed)
            
            # If still need more, generate variations - be more aggressive for large targets
            if self.new_downloads < max_images:
                if max_images <= 20:
                    should_vary = self.search_strategy.should_generate_variations(self.new_downloads, max_images)
                elif max_images <= 100:
                    should_vary = self.new_downloads < max_images * 0.7  # Generate if less than 70%
                else:
                    should_vary = self.new_downloads < max_images * 0.8  # Generate if less than 80%
                
                if should_vary:
                    variation_downloads = await self._process_variations(base_query, search_id, max_images)
                else:
                    variation_downloads = 0
                    self.progress_tracker.log_activity("Skipping variations - target reached or threshold not met", "INFO")
            else:
                variation_downloads = 0
        else:
            remaining_downloads = 0
            variation_downloads = 0
        
        # Final summary
        self.progress_tracker.log_summary()
        
        return self._create_result_dict(
            base_query, 
            self.new_downloads, 
            self.skipped_duplicates,
            f"Base: {base_downloads}, Remaining: {remaining_downloads}, Variations: {variation_downloads}"
        )
    
    async def _process_urls_phase(self, search_id: int, max_images: int, phase_name: str) -> int:
        """Process URLs in a specific phase with parallel processing"""
        phase_downloads = 0
        
        # Get more unvisited URLs for large targets
        if max_images <= 20:
            url_limit = 50
        elif max_images <= 100:
            url_limit = 100
        else:
            url_limit = 200  # For large targets like 500
        
        unvisited = self.database_manager.get_unvisited_urls(search_id, limit=url_limit)
        
        if not unvisited:
            return 0
        
        # Smart URL prioritization
        prioritized_urls = self._prioritize_urls(unvisited)
        
        # Process URLs in parallel batches
        if max_images <= 20:
            batch_size = min(self.config.get_config("parallel_url_processing", 10), len(prioritized_urls))
        elif max_images <= 100:
            batch_size = min(self.config.get_config("parallel_url_processing", 15), len(prioritized_urls))
        else:
            # For large targets like 500, use larger batches
            batch_size = min(self.config.get_config("parallel_url_processing", 25), len(prioritized_urls))
        
        batches = [prioritized_urls[i:i + batch_size] for i in range(0, len(prioritized_urls), batch_size)]
        
        for batch in batches:
            if self.new_downloads >= max_images:
                break
            
            batch_tasks = []
            for url_id, url in batch:
                if self.new_downloads >= max_images:
                    break
                
                task = self._process_single_url(url_id, url, max_images)
                batch_tasks.append(task)
            
            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        self.progress_tracker.log_activity(f"Batch processing error: {result}", "ERROR")
                    else:
                        phase_downloads += result
            
            # Reduced delay between batches
            await asyncio.sleep(0.3)  # Reduced from 0.5s to 0.3s
        
        # Debug logging
        self.progress_tracker.log_activity(f"Phase {phase_name}: phase_downloads={phase_downloads}, self.new_downloads={self.new_downloads}", "INFO")
        
        return phase_downloads
    
    async def _process_single_url(self, url_id: int, url: str, max_images: int) -> int:
        """Process a single URL and return number of downloads"""
        self.progress_tracker.log_activity(f"Visiting: {urlparse(url).netloc}", "INFO")
        
        try:
            # Extract images from website
            extracted_url_id, image_urls = await self.image_extractor.extract_images(url, url_id)
            
            if image_urls:
                self.progress_tracker.log_activity(f"Found {len(image_urls)} images", "INFO")
                
                # Download images
                downloads = await self._download_images_batch(image_urls, url_id, max_images)
                
                # Mark URL as visited
                self.database_manager.mark_visited(url_id, len(image_urls))
                
                return downloads
            else:
                self.database_manager.mark_visited(url_id, 0, "No images found")
                return 0
                
        except Exception as e:
            self.progress_tracker.log_activity(f"Error processing {url}: {e}", "ERROR")
            self.database_manager.mark_visited(url_id, 0, str(e))
            return 0
    
    async def _try_remaining_urls(self, search_id: int, remaining_needed: int) -> int:
        """Try to get more images from remaining unvisited URLs"""
        if remaining_needed <= 0:
            return 0
        
        self.progress_tracker.log_phase_start("Remaining URLs", f"Trying remaining unvisited URLs - need {remaining_needed} more")
        
        remaining_unvisited = self.database_manager.get_unvisited_urls(search_id, limit=50)
        additional_downloads = 0
        
        for url_id, url in remaining_unvisited:
            if self.new_downloads >= remaining_needed:
                break
            
            self.progress_tracker.log_activity(f"Visiting: {urlparse(url).netloc}", "INFO")
            
            try:
                extracted_url_id, image_urls = await self.image_extractor.extract_images(url, url_id)
                
                if image_urls:
                    additional_downloads += await self._download_images_batch(image_urls, url_id, remaining_needed)
                    self.database_manager.mark_visited(url_id, len(image_urls))
                else:
                    self.database_manager.mark_visited(url_id, 0, "No images found")
                    
            except Exception as e:
                self.progress_tracker.log_activity(f"Error processing {url}: {e}", "ERROR")
                self.database_manager.mark_visited(url_id, 0, str(e))
        
        return additional_downloads
    
    async def _process_variations(self, base_query: str, search_id: int, max_images: int) -> int:
        """Process search variations"""
        self.progress_tracker.log_phase_start("Search Variations", "Generating and processing search variations")
        
        variations = self.search_strategy.generate_variations(base_query)
        variation_downloads = 0
        
        for variation in variations:
            # Continue processing variations even if we're close to target
            # This ensures we get closer to the requested number
            if self.new_downloads >= max_images * 1.1:  # Allow 10% overage
                break
            
            self.progress_tracker.log_activity(f"Processing variation: '{variation}'", "INFO")
            
            # Search for variation
            variation_result = await self.search_provider.search(variation)
            
            if variation_result.urls:
                # Store URLs for variation - be more aggressive for large targets
                if max_images <= 20:
                    variation_urls = set(list(variation_result.urls)[:15])  # Limit per variation
                elif max_images <= 100:
                    variation_urls = set(list(variation_result.urls)[:50])  # More URLs for medium targets
                else:
                    # For large targets like 500, allow many more URLs per variation
                    variation_urls = set(list(variation_result.urls)[:200])
                
                self.database_manager.store_urls(search_id, variation_urls)
                
                # Process variation URLs
                variation_downloads += await self._process_urls_phase(search_id, max_images, f"variation: {variation}")
        
        return variation_downloads
    
    async def _download_images_batch(self, image_urls: List[str], source_url_id: int, max_images: int) -> int:
        """Download a batch of images"""
        if not image_urls:
            return 0
        
        # Create download tasks
        tasks = []
        for image_url in image_urls:
            # Continue processing until we reach target with buffer
            if self.new_downloads >= max_images * 1.2:  # Allow 20% overage
                break
            
            # Check for duplicates
            if self._is_duplicate_image(image_url):
                self.skipped_duplicates += 1
                continue
            
            # Mark URL as processed
            self.processed_urls.add(image_url)
            
            tasks.append(ImageTask(
                image_url=image_url,
                source_url_id=source_url_id
            ))
        
        if not tasks:
            return 0
        
        # Download images using thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(executor, self._download_single_image, task)
                for task in tasks
            ]
            
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            # Process results
            successful_downloads = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.progress_tracker.log_activity(f"Download error: {result}", "ERROR")
                elif result.success:
                    successful_downloads += 1
                    self._handle_successful_download(result, tasks[i].source_url_id, tasks[i].image_url)
                else:
                    self.progress_tracker.log_activity(f"Download failed: {result.error_message}", "WARNING")
        
        return successful_downloads
    
    def _download_single_image(self, task: ImageTask) -> DownloadResult:
        """Download a single image (synchronous for thread pool)"""
        try:
            # This would need to be adapted for synchronous execution
            # For now, we'll use the async version
            return asyncio.run(self.image_downloader.download_image(task))
        except Exception as e:
            return DownloadResult(
                success=False,
                file_path=None,
                error_message=str(e),
                image_hash=None,
                width=None,
                height=None
            )
    
    def _handle_successful_download(self, result: DownloadResult, source_url_id: int, image_url: str):
        """Handle successful download"""
        with self.lock:
            self.new_downloads += 1
            self.downloaded_hashes.add(result.image_hash)
            
            # Store in database
            success = self.database_manager.store_downloaded_image(
                source_url_id=source_url_id,
                image_url=image_url,  # Use the actual image URL from the task
                image_hash=result.image_hash,
                file_path=str(result.file_path),
                file_size=result.file_path.stat().st_size if result.file_path else 0,
                width=result.width or 0,
                height=result.height or 0,
                is_human=result.is_human,
                content_type=result.content_type
            )
            
            # Debug logging
            if success:
                self.progress_tracker.log_activity(f"✅ Stored in DB: {result.file_path.name} (URL: {image_url[:50]}...)", "INFO")
            else:
                self.progress_tracker.log_activity(f"❌ Failed to store in DB: {result.file_path.name}", "ERROR")
            
            # Log the successful download
            self.progress_tracker.log_download_attempt(f"Image {result.file_path.name}", True)
    
    def _is_duplicate_image(self, image_url: str) -> bool:
        """Check if image is a duplicate"""
        # Check if this exact URL was already processed
        if image_url in self.processed_urls:
            return True
        
        # Check if we have too many duplicates already
        if self.skipped_duplicates > 50:  # Prevent infinite loops
            return True
            
        return False
    
    def _create_result_dict(self, query: str, downloads: int, skipped: int, details: str) -> Dict[str, Any]:
        """Create result dictionary"""
        return {
            "query": query,
            "downloads": downloads,
            "skipped_duplicates": skipped,
            "details": details,
            "performance_metrics": self.progress_tracker.get_performance_metrics()
        }

    def _prioritize_urls(self, urls: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        """Prioritize URLs based on domain performance"""
        if not self.config.get_config("smart_prioritization", True):
            return urls
        
        # Define fast and slow domains based on performance analysis
        fast_domains = {
            'media.gettyimages.com', 'upload.wikimedia.org', 'commons.wikimedia.org',
            'cdn-images.dzcdn.net', 'i.pinimg.com', 'live.staticflickr.com',
            'm.media-amazon.com', 'ssl.gstatic.com', 'pbs.twimg.com'
        }
        
        slow_domains = {
            'www.thierrylebraly.com', 'shop.maiermedia-gmbh.com', 'www.algemeiner.com',
            'thefashioninsider.com', 'www.kveller.com', 'israeled.org'
        }
        
        # Separate URLs by priority
        fast_urls = []
        normal_urls = []
        slow_urls = []
        
        for url_id, url in urls:
            domain = self._extract_domain(url)
            if domain in fast_domains:
                fast_urls.append((url_id, url))
            elif domain in slow_domains:
                slow_urls.append((url_id, url))
            else:
                normal_urls.append((url_id, url))
        
        # Return prioritized list: fast first, then normal, then slow
        return fast_urls + normal_urls + slow_urls
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return "unknown"
