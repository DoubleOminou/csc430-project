import threading
import time
import json
import os

STATS_FILE = 'stats.json'

class StatsManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StatsManager, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'blocked': 0,
            'active_connections': 0,
            'peak_active_connections': 0,
            'start_time': time.time()
        }
        self.lock = threading.Lock()
        self._load()

    def _load(self):
        """Loads persistent stats from disk."""
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, 'r') as f:
                    saved = json.load(f)
                    # Only restore counters, not active state
                    for key in ['total_requests', 'cache_hits', 'cache_misses', 'blocked']:
                        if key in saved:
                            self.stats[key] = saved[key]
            except Exception:
                pass

    def _save(self):
        """Saves persistent stats to disk."""
        try:
            # We only want to save the counters
            to_save = {
                k: v for k, v in self.stats.items() 
                if k in ['total_requests', 'cache_hits', 'cache_misses', 'blocked']
            }
            with open(STATS_FILE, 'w') as f:
                json.dump(to_save, f)
        except Exception:
            pass

    def increment(self, key):
        with self.lock:
            if key in self.stats:
                self.stats[key] += 1
                if key == 'active_connections':
                    if self.stats['active_connections'] > self.stats['peak_active_connections']:
                        self.stats['peak_active_connections'] = self.stats['active_connections']
                elif key != 'active_connections':
                    self._save()

    def decrement(self, key):
        with self.lock:
            if key in self.stats:
                self.stats[key] -= 1
                if key != 'active_connections':
                    self._save()

    def get_stats(self):
        with self.lock:
            current_stats = self.stats.copy()
            current_stats['uptime'] = int(time.time() - self.stats['start_time'])
            return current_stats

stats_manager = StatsManager()
