import logging
import time
from functools import wraps
from pathlib import Path


def all_files_in(path, regex):
    for path in Path(path).rglob(regex):
        yield path


def timed(func):
    """This decorator prints the execution time for the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logging.info(
            f"{func.__name__} ran in {round(end - start, 2)}s with args={args};kwargs={kwargs}")
        return result

    return wrapper