"""
Logging configuration for KIGate API
Implements file logging with daily rotation and Sentry integration
"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


class LoggingConfig:
    """Configuration and initialization for application logging"""
    
    _initialized = False
    _sentry_initialized = False
    
    @classmethod
    def setup_logging(cls, log_dir: str = "Logs", log_level: int = logging.INFO):
        """
        Setup file logging with daily rotation and 7-day retention
        
        Args:
            log_dir: Directory to store log files
            log_level: Logging level (default: INFO)
        """
        if cls._initialized:
            return
        
        # Create logs directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler with daily rotation and 7-day retention
        log_file = log_path / "kigate.log"
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when='midnight',  # Rotate at midnight
            interval=1,  # Every 1 day
            backupCount=7,  # Keep 7 days of logs
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        cls._initialized = True
        root_logger.info("Logging system initialized with file rotation")
    
    @classmethod
    def setup_sentry(cls, dsn: Optional[str] = None, environment: str = "production", 
                    traces_sample_rate: float = 0.1):
        """
        Setup Sentry for error tracking
        
        Args:
            dsn: Sentry DSN (Data Source Name)
            environment: Environment name (production, staging, development)
            traces_sample_rate: Percentage of transactions to capture (0.0 to 1.0)
        """
        if cls._sentry_initialized or not dsn:
            return
        
        try:
            # Setup Sentry with FastAPI integration
            sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                traces_sample_rate=traces_sample_rate,
                integrations=[
                    FastApiIntegration(),
                    SqlalchemyIntegration(),
                    LoggingIntegration(
                        level=logging.ERROR,  # Send ERROR and above to Sentry
                        event_level=logging.ERROR  # Create events for ERROR and above
                    ),
                ],
                # Send default PII (Personally Identifiable Information)
                send_default_pii=False,
                # Include local variables in stack traces
                attach_stacktrace=True,
                # Maximum breadcrumbs to capture
                max_breadcrumbs=50,
            )
            
            cls._sentry_initialized = True
            logging.getLogger(__name__).info(f"Sentry initialized for environment: {environment}")
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to initialize Sentry: {str(e)}")
    
    @classmethod
    def is_sentry_enabled(cls) -> bool:
        """Check if Sentry is enabled and initialized"""
        return cls._sentry_initialized
    
    @classmethod
    def capture_exception(cls, exception: Exception, context: Optional[dict] = None):
        """
        Manually capture an exception to Sentry
        
        Args:
            exception: The exception to capture
            context: Additional context information
        """
        if cls._sentry_initialized:
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                sentry_sdk.capture_exception(exception)
