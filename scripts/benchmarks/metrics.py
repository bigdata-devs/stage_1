import time
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO)

def measure_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time
        
        logging.info(f"[{func.__name__}] executed in {elapsed_time:.4f} segundos")
        
        return result 
    return wrapper
