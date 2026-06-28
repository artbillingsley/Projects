# src/lib/retry.py
from __future__ import annotations

import random
import time
from typing import Any, Callable, Tuple, Type


def retry_with_backoff(
    fn: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
) -> Any:
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except retry_on as e:
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.25)
            time.sleep(delay + jitter)
