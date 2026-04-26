# admin_server.py
# Web-based Admin Interface (Bonus Requirement I).
# Provides a premium dashboard for viewing stats, logs, managing cache,
# and configuring blacklist/whitelist rules in real-time.

import http.server
import json
import socketserver
import threading
import os
import re
import config
from cache_manager import CacheManager
from stats_manager import stats_manager
from logger import log_error


class AdminHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP request handler for the admin interface.
    Serves the single-page dashboard at '/' and exposes a JSON API.
    """

    def _check_auth(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            return False
        
        import base64
        try:
            auth_type, encoded_creds = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                return False
            decoded_creds = base64.b64decode(encoded_creds).decode('utf-8')
            username, password = decoded_creds.split(':', 1)
            return username == config.ADMIN_USER and password == config.ADMIN_PASS
        except Exception:
            return False

    def _require_auth(self):
        if not self._check_auth():
            self.send_response(401)
            # Send standard JSON 401 to let the frontend UI handle the login overlay gracefully
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success": false, "message": "Unauthorized"}')
            return False
        return True

    # -------------------------------------------------------------------------
    # GET Endpoints
    # -------------------------------------------------------------------------
    def do_GET(self):
        # Serve the HTML dashboard without auth so the UI can draw the login page internally
        if self.path == '/':
            self._serve_html(self._get_dashboard_html())
            return
        elif self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
            
        if not self._require_auth():
            return

        if self.path == '/api/stats':
            cache = CacheManager()
            data = stats_manager.get_stats()
            data['cache_disk'] = cache.get_cache_stats()
            self._serve_json(data)
        elif self.path == '/api/logs':
            logs = []
            if os.path.exists(config.LOG_FILE):
                with open(config.LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                    logs = f.readlines()[-100:]
            self._serve_json(logs)
        elif self.path == '/api/config':
            self._serve_json({
                'blacklist': config.BLACKLIST,
                'whitelist': config.WHITELIST,
                'cache_enabled': config.CACHE_ENABLED,
                'default_cache_ttl': config.DEFAULT_CACHE_TTL,
                'proxy_port': config.PROXY_PORT,
            })
        elif self.path == '/api/cache/entries':
            cache = CacheManager()
            self._serve_json(cache.get_all_entries())
        else:
            self.send_error(404, "Not Found")

    # -------------------------------------------------------------------------
    # POST Endpoints
    # -------------------------------------------------------------------------
    def do_POST(self):
        if not self._require_auth():
            return

        if self.path == '/api/cache/clear':
            cache = CacheManager()
            count = cache.clear()
            self._serve_json({'success': True, 'cleared': count, 'message': f'Cleared {count} cache entries.'})

        elif self.path == '/api/config':
            body = self._read_body()
            if body is None:
                return
            try:
                payload = json.loads(body)
                blacklist = payload.get('blacklist', config.BLACKLIST)
                whitelist = payload.get('whitelist', config.WHITELIST)

                # Persist to config.py
                self._update_config_file(blacklist, whitelist)

                # Update in-memory config
                config.BLACKLIST = blacklist
                config.WHITELIST = whitelist

                self._serve_json({'success': True, 'message': 'Configuration updated and saved.'})
            except (json.JSONDecodeError, TypeError) as e:
                self._serve_json({'success': False, 'message': f'Invalid JSON: {e}'}, status=400)
        else:
            self.send_error(404, "Not Found")

    # -------------------------------------------------------------------------
    # DELETE Endpoints
    # -------------------------------------------------------------------------
    def do_DELETE(self):
        if not self._require_auth():
            return

        if self.path == '/api/cache/entries':
            body = self._read_body()
            if body is None:
                return
            try:
                payload = json.loads(body)
                url = payload.get('url')
                if not url:
                    self._serve_json({'success': False, 'message': 'Missing URL'}, status=400)
                    return
                cache = CacheManager()
                success = cache.delete(url)
                if success:
                    self._serve_json({'success': True, 'message': 'Cache entry deleted.'})
                else:
                    self._serve_json({'success': False, 'message': 'Entry not found.'}, status=404)
            except Exception as e:
                self._serve_json({'success': False, 'message': f'Invalid JSON: {e}'}, status=400)
        else:
            self.send_error(404, "Not Found")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _read_body(self):
        """Reads and returns the request body, or None on error."""
        try:
            length = int(self.headers.get('Content-Length', 0))
            return self.rfile.read(length).decode('utf-8')
        except Exception as e:
            self._serve_json({'success': False, 'message': str(e)}, status=400)
            return None

    def _serve_html(self, html):
        body = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _serve_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _update_config_file(self, blacklist, whitelist):
        """Rewrites BLACKLIST and WHITELIST in config.py for persistence."""
        try:
            with open('config.py', 'r') as f:
                content = f.read()

            bl_str = repr(blacklist)
            wl_str = repr(whitelist)

            content = re.sub(r'BLACKLIST\s*=\s*\[.*?\]', f'BLACKLIST = {bl_str}', content, flags=re.DOTALL)
            content = re.sub(r'WHITELIST\s*=\s*\[.*?\]', f'WHITELIST = {wl_str}', content, flags=re.DOTALL)

            with open('config.py', 'w') as f:
                f.write(content)
        except Exception as e:
            log_error(f"Failed to persist config changes: {e}")

    def log_message(self, format, *args):
        """Silence default stdout logging from the built-in HTTP server."""
        pass

    def _get_dashboard_html(self):
        try:
            with open("dashboard.html", "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            from logger import log_error
            log_error(f"Failed to load dashboard.html: {e}")
            return "<html><body><h1>Error loading dashboard template.</h1></body></html>"


def start_admin_server(port=8889):
    """Starts the admin HTTP server on a background thread."""
    handler = AdminHandler
    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"[*] Admin Interface started on http://localhost:{port}")
            httpd.serve_forever()
    except Exception as e:
        log_error(f"Failed to start admin server: {e}")


if __name__ == "__main__":
    start_admin_server()
