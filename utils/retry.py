"""
utils/retry.py
--------------
Exponential backoff retry decorator.

Exponential backoff kya hota hai?
  - Jab API fail kare, turant dobara mat try karo
  - Thoda wait karo, phir try karo
  - Har baar wait time double karo
  - Max tries ke baad error throw karo

Example:
  Attempt 1 fails → wait 2s
  Attempt 2 fails → wait 4s
  Attempt 3 fails → wait 8s
  Attempt 4 fails → raise Exception
"""

import time
import functools
from utils.logger import get_logger

logger = get_logger("retry")


def retry_with_backoff(max_retries: int = 3, base_delay: float = 2.0, exceptions=(Exception,)):
    """
    Decorator factory — kisi bhi function par lagao, auto-retry milega.

    Parameters:
        max_retries  : kitni baar retry karna hai
        base_delay   : pehle wait ka time (seconds), baad mein double hota hai
        exceptions   : kis exception par retry karna hai

    Usage:
        @retry_with_backoff(max_retries=3, base_delay=2)
        def call_crm_api(data):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        logger.info(f"✅ '{func.__name__}' succeeded on attempt {attempt}")
                    return result

                except exceptions as e:
                    last_exception = e
                    wait_time = base_delay ** attempt  # 2^1=2, 2^2=4, 2^3=8 seconds

                    if attempt < max_retries:
                        logger.warning(
                            f"⚠️  '{func.__name__}' failed (attempt {attempt}/{max_retries}). "
                            f"Retrying in {wait_time:.1f}s... Error: {e}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"❌ '{func.__name__}' failed after {max_retries} attempts. "
                            f"Giving up. Last error: {e}"
                        )

            # Saare retries exhaust — error raise karo
            raise Exception(
                f"Max retries ({max_retries}) exceeded for '{func.__name__}': {last_exception}"
            )

        return wrapper
    return decorator
