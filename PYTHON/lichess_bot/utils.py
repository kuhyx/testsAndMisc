import logging
import time


def backoff_sleep(current_backoff: int, base: float = 0.5, cap: float = 8.0) -> int:
    """Sleep with exponential backoff. Returns the next backoff step.

    - current_backoff: number of consecutive failures
    - base: base delay in seconds
    - cap: maximum delay in seconds
    """
    delay = min(cap, base * (2 ** current_backoff))
    logging.info(f"Backing off for {delay:.1f}s")
    time.sleep(delay)
    return min(current_backoff + 1, 10)
