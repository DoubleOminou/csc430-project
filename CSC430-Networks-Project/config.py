# config.py
# Central configuration file for the Caching Proxy Server.
# All tuneable settings live here. The admin interface can update
# BLACKLIST and WHITELIST at runtime and will rewrite this file for persistence.

# ── Server Settings ────────────────────────────────────────────────────────────
PROXY_HOST = '127.0.0.1'       # Address to bind the proxy server
PROXY_PORT = 8888               # Port for client connections
BUFFER_SIZE = 8192              # Read buffer size (bytes)
MAX_THREADS = 100               # Max concurrent client threads

# ── Cache Settings ─────────────────────────────────────────────────────────────
CACHE_ENABLED = True            # Toggle caching on/off
DEFAULT_CACHE_TTL = 300         # Default cache lifetime in seconds (5 minutes)
CACHE_DIR = './cache'           # Directory to store cache files

# ── Filtering ──────────────────────────────────────────────────────────────────
BLACKLIST = ['http://blocked-test-domain.example']
# Example: ['ads.example.com', 'tracker.net']
# Requests to any domain in this list will receive a 403 Forbidden response.

WHITELIST = []
# Example: ['google.com', 'github.com']
# If non-empty, ONLY domains in this list are allowed (all others are blocked).
# Leave empty to allow all non-blacklisted traffic.

# ── Logging ────────────────────────────────────────────────────────────────────
LOG_FILE = 'proxy.log'          # Path to the log file
STDOUT_LOGGING = True           # Also print logs to stdout

# ── Admin Interface ────────────────────────────────────────────────────────────
ADMIN_PORT = 8889               # Port for the web admin dashboard

# ── Credentials ────────────────────────────────────────────────────────────────
import os

ADMIN_USER = 'admin'
ADMIN_PASS = 'password'

try:
    if os.path.exists('.env'):
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    if key == 'ADMIN_USER':
                        ADMIN_USER = val
                    elif key == 'ADMIN_PASS':
                        ADMIN_PASS = val
except Exception:
    pass

