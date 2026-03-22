import logging
import os
from logging.handlers import TimedRotatingFileHandler
from app.core.config import settings

def setup_logging():
    """Configure logging for the application."""
    log_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app.log")
    
    # Create a custom logger
    logger = logging.getLogger("quizzmaster")
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    
    # Avoid duplicate logs if calling setup_logging multiple times
    if logger.handlers:
        return logger

    # Create handlers
    file_handler = TimedRotatingFileHandler(
        log_file, when="midnight", interval=1, backupCount=7
    )
    console_handler = logging.StreamHandler()
    
    # Create formatters and add them to handlers
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(message)s"
    )
    file_handler.setFormatter(log_format)
    console_handler.setFormatter(log_format)
    
    # Add handlers to the logger
    logger.addHandler(file_handler)
    
    # Only add console handler if not already handled by uvicorn or if we want extra info
    if settings.DEBUG:
        logger.addHandler(console_handler)
        
    return logger

# Initialize logger
logger = setup_logging()
