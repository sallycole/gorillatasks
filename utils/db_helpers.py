
from sqlalchemy.exc import OperationalError
import logging
import time

logger = logging.getLogger(__name__)

def with_db_retry(func):
    """
    Decorator to retry database operations if they fail with connection errors.
    """
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_delay = 0.5  # start with 0.5 seconds
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                # Check if it's a connection error
                if "SSL connection has been closed" in str(e) or "connection has been closed" in str(e):
                    if attempt < max_retries - 1:  # Don't log on the last attempt
                        logger.warning(f"Database connection error, retrying ({attempt+1}/{max_retries}): {str(e)}")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"Failed to connect to database after {max_retries} attempts: {str(e)}")
                        raise
                else:
                    # If it's not a connection error, don't retry
                    raise
    
    return wrapper
