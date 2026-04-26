# cache_manager.py
# Manages persistent disk-based response caching with TTL expiration.
# Supports cache-control header parsing for proper invalidation.

import os
import re
import hashlib
import time
import pickle
import config
from logger import log_error


class CacheManager:
    """
    A file-based cache for HTTP responses.

    Responses are stored as pickled entries on disk (in config.CACHE_DIR),
    keyed by an MD5 hash of the URL. Each entry stores the raw response bytes
    and an expiration timestamp.

    Cache invalidation is based on:
      1. The 'max-age' directive in 'Cache-Control' headers (if found).
      2. The 'Expires' header (if found).
      3. A default TTL from config.DEFAULT_CACHE_TTL.
    """

    def __init__(self):
        self.cache_dir = config.CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_key(self, url):
        """Returns an MD5 hex digest of the URL to use as a unique cache filename."""
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def get(self, url):
        """
        Returns the cached raw HTTP response bytes for the given URL if:
          - Caching is enabled in config.
          - A cache file exists for this URL.
          - The cached entry has not expired.
        Returns None otherwise.
        """
        if not config.CACHE_ENABLED:
            return None

        key = self.get_cache_key(url)
        filepath = os.path.join(self.cache_dir, key)

        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'rb') as f:
                entry = pickle.load(f)

            if time.time() < entry['expires_at']:
                return entry['data']
            else:
                # Cache entry has expired — remove it
                os.remove(filepath)
        except Exception as e:
            log_error(f"Cache read error for {url}: {e}")
            try:
                os.remove(filepath)
            except Exception:
                pass

        return None

    def set(self, url, data, ttl=config.DEFAULT_CACHE_TTL):
        """
        Stores the raw HTTP response bytes in the cache.
        TTL is determined by (in order of priority):
          1. 'Cache-Control: max-age=N' header in the response.
          2. Explicit ttl argument.
          3. config.DEFAULT_CACHE_TTL fallback.
        """
        if not config.CACHE_ENABLED:
            return

        # Try to parse Cache-Control: max-age from response headers
        effective_ttl = self._parse_cache_ttl(data) or ttl or config.DEFAULT_CACHE_TTL

        key = self.get_cache_key(url)
        filepath = os.path.join(self.cache_dir, key)

        entry = {
            'url': url,
            'data': data,
            'cached_at': time.time(),
            'expires_at': time.time() + effective_ttl,
        }

        try:
            with open(filepath, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            log_error(f"Cache write error for {url}: {e}")

    def _parse_cache_ttl(self, response_bytes):
        """
        Attempts to parse a TTL value (in seconds) from HTTP response headers.
        Looks for 'Cache-Control: max-age=N'. Returns None if not found.
        """
        try:
            # Separate headers from body
            header_section = response_bytes.split(b'\r\n\r\n')[0].decode('utf-8', errors='ignore')
            match = re.search(r'cache-control:.*max-age=(\d+)', header_section, re.IGNORECASE)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        return None

    def clear(self):
        """
        Removes all cache files from the cache directory.
        Returns the number of entries cleared.
        """
        count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    os.remove(filepath)
                    count += 1
                except Exception as e:
                    log_error(f"Failed to remove cache file {filename}: {e}")
        except Exception as e:
            log_error(f"Failed to clear cache directory: {e}")
        return count

    def get_cache_stats(self):
        """Returns count and total size of cached entries."""
        count = 0
        total_size = 0
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                count += 1
                total_size += os.path.getsize(filepath)
        except Exception:
            pass
        return {'entries': count, 'size_bytes': total_size}

    def get_all_entries(self):
        """Returns a list of metadata dictionaries for all valid cache entries."""
        entries = []
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'rb') as f:
                        entry = pickle.load(f)
                    
                    if time.time() < entry['expires_at']:
                        entries.append({
                            'url': entry['url'],
                            'cached_at': entry['cached_at'],
                            'expires_at': entry['expires_at'],
                            'size_bytes': os.path.getsize(filepath)
                        })
                    else:
                        os.remove(filepath) # Auto-cleanup expired
                except Exception as e:
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
        except Exception as e:
            log_error(f"Error reading cache directory: {e}")
            
        # Sort by most recently cached
        entries.sort(key=lambda x: x['cached_at'], reverse=True)
        return entries

    def delete(self, url):
        """Deletes a specific cache entry by URL."""
        key = self.get_cache_key(url)
        filepath = os.path.join(self.cache_dir, key)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except Exception as e:
                log_error(f"Failed to delete cache entry for {url}: {e}")
        return False
