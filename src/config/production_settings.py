#!/usr/bin/env python3
"""
Production Settings for CV-Library Scraper
Optimized configurations for production deployment with enhanced performance and reliability.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ProductionConfig:
    """Production-optimized configuration settings."""
    
    # Performance Settings
    MAX_RETRY_ATTEMPTS: int = 3  # Number of retry attempts for failed operations
    BASE_RETRY_DELAY: float = 1.0  # Base delay for exponential backoff (seconds)
    MAX_RETRY_DELAY: float = 10.0  # Maximum retry delay (seconds)
    
    # Timeout Optimizations
    PAGE_LOAD_TIMEOUT: int = 15  # Maximum time to wait for page loads
    ELEMENT_TIMEOUT: int = 8  # Maximum time to wait for elements
    DOWNLOAD_TIMEOUT: int = 30  # Maximum time to wait for downloads
    QUICK_TIMEOUT: int = 3  # Quick operations timeout
    
    # Rate Limiting (Anti-Detection)
    MIN_DELAY_BETWEEN_REQUESTS: float = 0.8  # Minimum delay between requests
    MAX_DELAY_BETWEEN_REQUESTS: float = 2.0  # Maximum delay between requests
    BURST_PROTECTION_DELAY: float = 5.0  # Delay after rapid operations
    
    # Resource Management
    MAX_MEMORY_USAGE_MB: int = 2048  # Maximum memory usage before cleanup
    CLEANUP_INTERVAL: int = 50  # Number of operations before cleanup
    MAX_LOG_FILE_SIZE_MB: int = 100  # Maximum log file size
    
    # Browser Optimizations
    HEADLESS_PRODUCTION: bool = False  # Run headless in production
    DISABLE_IMAGES: bool = True  # Disable image loading for speed
    DISABLE_CSS: bool = False  # Keep CSS for element detection reliability
    MAX_BROWSER_INSTANCES: int = 1  # Single browser instance for sequential processing
    
    # Logging Configuration
    PRODUCTION_LOG_LEVEL: str = "INFO"  # Production logging level
    ENABLE_PERFORMANCE_LOGGING: bool = True  # Enable performance metrics
    LOG_ROTATION: bool = True  # Enable log rotation
    
    # Data Quality & Validation
    MIN_DATA_COMPLETENESS: float = 0.7  # Minimum acceptable data completeness
    ENABLE_DATA_VALIDATION: bool = True  # Enable data validation
    SKIP_INCOMPLETE_PROFILES: bool = False  # Skip profiles with low completeness
    
    # Session Management
    SESSION_PERSISTENCE: bool = True  # Enable session persistence
    AUTO_SESSION_RECOVERY: bool = True  # Enable automatic session recovery
    SESSION_HEALTH_CHECK_INTERVAL: int = 10  # Check session health every N operations


class ProductionOptimizer:
    """Production optimization utilities."""
    
    def __init__(self, config: ProductionConfig = None):
        self.config = config or ProductionConfig()
        self.setup_logging()
        
    def setup_logging(self):
        """Configure production-optimized logging."""
        log_level = getattr(logging, self.config.PRODUCTION_LOG_LEVEL.upper(), logging.INFO)
        
        # Configure handlers
        handlers = [logging.StreamHandler()]
        
        if self.config.LOG_ROTATION:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                'production.log', 
                maxBytes=self.config.MAX_LOG_FILE_SIZE_MB * 1024 * 1024, 
                backupCount=3
            )
            handlers.append(file_handler)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        # Suppress verbose third-party logging
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
    def get_browser_options(self) -> Dict[str, Any]:
        """Get production-optimized browser options."""
        options = {
            'headless': self.config.HEADLESS_PRODUCTION,
            'disable_images': self.config.DISABLE_IMAGES,
            'disable_css': self.config.DISABLE_CSS,
            'page_load_strategy': 'eager',  # Don't wait for all resources
            'arguments': [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--memory-pressure-off',
                '--aggressive-cache-discard',
                '--enable-aggressive-domstorage-flushing'
            ]
        }
        
        if self.config.DISABLE_IMAGES:
            options['arguments'].extend([
                '--blink-settings=imagesEnabled=false'
            ])
            
        return options
        
    def calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = min(
            self.config.BASE_RETRY_DELAY * (2 ** attempt),
            self.config.MAX_RETRY_DELAY
        )
        return delay
        
    def should_cleanup_memory(self, operations_count: int) -> bool:
        """Determine if memory cleanup is needed."""
        return operations_count % self.config.CLEANUP_INTERVAL == 0
        
    def get_optimized_timeouts(self) -> Dict[str, float]:
        """Get production-optimized timeout settings."""
        return {
            'page_load': self.config.PAGE_LOAD_TIMEOUT,
            'element_wait': self.config.ELEMENT_TIMEOUT,
            'download': self.config.DOWNLOAD_TIMEOUT,
            'quick': self.config.QUICK_TIMEOUT
        }


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_time': 0.0,
            'avg_time_per_operation': 0.0,
            'memory_usage_mb': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        self.start_time = None
        
    def start_operation(self):
        """Start timing an operation."""
        import time
        self.start_time = time.time()
        
    def end_operation(self, success: bool = True):
        """End timing an operation and update metrics."""
        if self.start_time:
            import time
            operation_time = time.time() - self.start_time
            self.metrics['total_operations'] += 1
            self.metrics['total_time'] += operation_time
            
            if success:
                self.metrics['successful_operations'] += 1
            else:
                self.metrics['failed_operations'] += 1
                
            self.metrics['avg_time_per_operation'] = (
                self.metrics['total_time'] / self.metrics['total_operations']
            )
            
            self.start_time = None
            
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        success_rate = (
            self.metrics['successful_operations'] / max(self.metrics['total_operations'], 1)
        ) * 100
        
        return {
            'total_operations': self.metrics['total_operations'],
            'success_rate': f"{success_rate:.1f}%",
            'avg_time_per_operation': f"{self.metrics['avg_time_per_operation']:.2f}s",
            'total_time': f"{self.metrics['total_time']:.2f}s",
            'failed_operations': self.metrics['failed_operations']
        }


# Production configuration instance
PRODUCTION_CONFIG = ProductionConfig()
PRODUCTION_OPTIMIZER = ProductionOptimizer(PRODUCTION_CONFIG)
PERFORMANCE_MONITOR = PerformanceMonitor() 