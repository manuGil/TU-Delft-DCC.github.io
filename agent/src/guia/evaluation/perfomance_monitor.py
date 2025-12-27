"""
Track system perfomance metrics
"""

import time
import psutil
import functools
from typing import Callable, Dict
import json
from datetime import datetime

class PerfomanceMonitor:
    def __init__(self):
        self.metrics =[]
    
    def measure_perfomance(self, func: Callable) -> Callable:
        """
        Decorator to measure function performance
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Memory before
            process = psutil.Process()
            mem_before = process.memory_info().rss / 1024 /1024 # MB

            # time execution
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            # Memory after
            mem_after = process.memory_info().rss / 1024 / 1024 # MB

            # Record metrics
            metric = {
                'function': func.__name__,
                'timestamp': datetime.now().isoformat(),
                'latency_seconds': end_time - start_time,
                'memory_used_mb': mem_after - mem_before, 
                'memory_total_mb': mem_after
            }

            self.metrics.append(metric)
            return result
        return wrapper
    
    def get_statistics(self) -> Dict:
        """Calculate perfomance statistics"""

        if not self.metrics:
            return {}
        
        latencies = [m['latency_seconds'] for m in self.metrics]
        memory_usage = [m['memory_used_mb'] for m in self.metrics]

        return {
            'total_calls': len(self.metrics),
            'latency': {
                'mean': sum(latencies) / len(latencies),
                'min': min(latencies),
                'max': max(latencies),
                'p50': sorted(latencies)[len(latencies)//2],
                'p95': sorted(latencies)[int(len(latencies)*0.95)] if len(latencies) > 20 else max(latencies)
            },
            'memory': {
                'mean': sum(memory_usage) / len(memory_usage),
                'max': max(memory_usage)
            }

        }
    
    def save_metrics(self, filepath: str):
        """Same metrics to file"""

        with open(filepath) as f:
            json.dump(
                {
                    'metrics': self.metrics,
                    'statistics': self.get_statistics()
                }, f, indent=2
            )