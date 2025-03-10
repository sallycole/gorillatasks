from utils.timezone import now_in_utc, to_user_timezone, from_user_timezone
import logging
from functools import wraps
from sqlalchemy.exc import OperationalError
import time

logger = logging.getLogger(__name__)

def with_db_retry(func):
    """Decorator to retry database operations if they fail due to connection issues"""
    @wraps(func)
    def wrapper_function(*args, **kwargs):
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Failed after {max_retries} retries: {str(e)}")
                    raise
                logger.warning(f"Database operation failed, retrying ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(1)  # Wait before retrying

    return wrapper_function