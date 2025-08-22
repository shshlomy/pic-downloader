"""
Progress tracker implementation following Single Responsibility Principle
"""

import time
from typing import Dict, Any
from ..core.interfaces import IProgressTracker

class ConsoleProgressTracker(IProgressTracker):
    """Console-based progress tracker with detailed logging"""
    
    def __init__(self):
        self.start_time = time.time()
        self.phase_start_time = time.time()
        self.current_phase = "Initialization"
        self.total_downloads = 0
        self.target_downloads = 0
    
    def update_progress(self, downloaded: int, target: int, phase: str):
        """Update progress information"""
        self.total_downloads = downloaded
        self.target_downloads = target
        
        if phase != self.current_phase:
            self._log_phase_completion()
            self.current_phase = phase
            self.phase_start_time = time.time()
        
        # Calculate progress percentage
        if target > 0:
            percentage = (downloaded / target) * 100
            remaining = target - downloaded
            
            # Calculate ETA
            elapsed = time.time() - self.start_time
            if downloaded > 0:
                rate = downloaded / elapsed
                eta_seconds = remaining / rate if rate > 0 else 0
                eta_str = self._format_time(eta_seconds)
            else:
                eta_str = "Calculating..."
            
            print(f"📊 Progress: {downloaded}/{target} ({percentage:.1f}%) - {remaining} remaining - ETA: {eta_str}")
    
    def log_activity(self, message: str, level: str = "INFO"):
        """Log activity messages with appropriate formatting"""
        timestamp = time.strftime("%H:%M:%S")
        
        if level == "ERROR":
            prefix = "❌"
        elif level == "WARNING":
            prefix = "⚠️"
        elif level == "SUCCESS":
            prefix = "✅"
        elif level == "INFO":
            prefix = "ℹ️"
        else:
            prefix = "📝"
        
        print(f"{prefix} [{timestamp}] {message}")
    
    def log_phase_start(self, phase: str, description: str = ""):
        """Log the start of a new phase"""
        self.current_phase = phase
        self.phase_start_time = time.time()
        
        print(f"\n🚀 Starting Phase: {phase}")
        if description:
            print(f"   📋 {description}")
    
    def log_phase_completion(self, phase: str, results: Dict[str, Any]):
        """Log the completion of a phase with results"""
        elapsed = time.time() - self.phase_start_time
        
        print(f"\n✅ Phase Complete: {phase}")
        print(f"   ⏱️  Duration: {self._format_time(elapsed)}")
        
        for key, value in results.items():
            if isinstance(value, (int, float)):
                print(f"   📊 {key}: {value}")
            else:
                print(f"   📋 {key}: {value}")
    
    def log_download_attempt(self, image_url: str, success: bool, details: str = ""):
        """Log individual download attempts"""
        if success:
            self.log_activity(f"Downloaded: {self._truncate_url(image_url)}", "SUCCESS")
        else:
            self.log_activity(f"Failed: {self._truncate_url(image_url)} - {details}", "ERROR")
    
    def log_summary(self):
        """Log final summary of the operation"""
        total_time = time.time() - self.start_time
        
        print(f"\n{'='*70}")
        print(f"📊 DOWNLOAD COMPLETE")
        print(f"{'='*70}")
        print(f"  Base Query: {self.current_phase}")
        print(f"  Images Downloaded: {self.total_downloads}")
        print(f"  Target: {self.target_downloads}")
        print(f"  Total Time: {self._format_time(total_time)}")
        print(f"  Success Rate: {(self.total_downloads/self.target_downloads*100):.1f}%" if self.target_downloads > 0 else "N/A")
        print(f"{'='*70}")
    
    def _log_phase_completion(self):
        """Log completion of current phase"""
        elapsed = time.time() - self.phase_start_time
        print(f"   ⏱️  Phase '{self.current_phase}' completed in {self._format_time(elapsed)}")
    
    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def _truncate_url(self, url: str, max_length: int = 50) -> str:
        """Truncate URL for display"""
        if len(url) <= max_length:
            return url
        return url[:max_length-3] + "..."
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        total_time = time.time() - self.start_time
        
        return {
            "total_time": total_time,
            "total_downloads": self.total_downloads,
            "target_downloads": self.target_downloads,
            "success_rate": (self.total_downloads/self.target_downloads*100) if self.target_downloads > 0 else 0,
            "downloads_per_minute": (self.total_downloads / (total_time / 60)) if total_time > 0 else 0
        }
