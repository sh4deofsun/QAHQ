import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

class Logger:
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize logger with optional log file path
        
        Args:
            log_file: Path to log file (default: logs/YYYY-MM-DD.log in same directory as script)
        """
        # Create logger
        self.logger = logging.getLogger('fastapi')
        self.logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        if log_file is None:
            log_dir = Path(__file__).parent / 'logs'
            log_dir.mkdir(exist_ok=True)
            current_date = datetime.now().strftime('%Y-%m-%d')
            log_file = str(log_dir / f'{current_date}.log')

        # Create handlers
        file_handler = logging.FileHandler(log_file)
        console_handler = logging.StreamHandler()
        
        # Create formatters and add it to handlers
        log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(log_format)
        console_handler.setFormatter(log_format)
        
        # Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        """Log info level message"""
        self.logger.info(message)
        
    def error(self, message: str):
        """Log error level message"""
        self.logger.error(message)
        
    def warning(self, message: str):
        """Log warning level message"""
        self.logger.warning(message)
        
    def debug(self, message: str):
        """Log debug level message"""
        self.logger.debug(message)

