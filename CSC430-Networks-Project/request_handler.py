# request_handler.py
# Handles parsing, filtering, forwarding, and caching of proxy requests.
# Core logic: HTTP forwarding, HTTPS CONNECT tunneling, cache lookup, blacklist/whitelist filtering.

import socket
import select
import config
from logger import log_request, log_error
from cache_manager import CacheManager
from stats_manager import stats_manager


class RequestHandler:
    """
    Handles a single client connection for the proxy server.
    Responsible for:
      - Parsing the incoming request (method, URL, HTTP version).
      - Checking blacklist/whitelist filtering.
      - Serving from cache or forwarding to the target server.
      - Supporting HTTP (GET/POST/etc.) and HTTPS (CONNECT tunneling).
    """

    def __init__(self, client_socket, client_address):
        self.client_socket = client_socket
        self.client_address = client_address
        self.buffer_size = config.BUFFER_SIZE
        self.cache = CacheManager()
        # Track total and active connections for the stats dashboard
        stats_manager.increment('total_requests')
        stats_manager.increment('active_connections')

    def run(self):
        """Main entry point — receive and dispatch the client request."""
        try:
            # Receive initial request data from client
            request = self.client_socket.recv(self.buffer_size)
            if not request:
                return

            # Parse the request line (e.g., "GET http://example.com/ HTTP/1.1")
            lines = request.split(b'\r\n')
            if not lines:
                return

            first_line = lines[0].decode('utf-8', errors='ignore').strip()
            parts = first_line.split(' ')
            if len(parts) < 3:
                return  # Malformed request line

            method = parts[0]
            url = parts[1]
            http_version = parts[2]

            # --- Requirement G: Blacklist / Whitelist Filtering ---
            if self.is_blocked(url):
                log_request(self.client_address, "BLOCKED", method, url, "403 FORBIDDEN")
                stats_manager.increment('blocked')
                self.client_socket.sendall(
                    b"HTTP/1.1 403 Forbidden\r\n"
                    b"Content-Type: text/html\r\n"
                    b"Connection: close\r\n\r\n"
                    b"<html><body><h1>403 Forbidden</h1>"
                    b"<p>Access Denied: This URL is blacklisted by the proxy.</p></body></html>"
                )
                return

            # --- Requirement F: Cache Check (only for GET) ---
            if method == 'GET':
                cached_data = self.cache.get(url)
                if cached_data:
                    log_request(self.client_address, "CACHE HIT", method, url, "200 OK (cached)")
                    stats_manager.increment('cache_hits')
                    self.client_socket.sendall(cached_data)
                    return
                else:
                    stats_manager.increment('cache_misses')

            # --- Requirement A+B: Dispatch HTTP vs HTTPS ---
            if method == 'CONNECT':
                # HTTPS CONNECT tunnel (Requirement A bonus)
                self.handle_https_tunnel(url, request)
            else:
                # Standard HTTP forwarding
                self.handle_http_request(method, url, request)

        except Exception as e:
            log_error(f"Error in request handler for {self.client_address}: {e}")
        finally:
            stats_manager.decrement('active_connections')
            try:
                self.client_socket.close()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Requirement G: Blacklist / Whitelist
    # -------------------------------------------------------------------------
    def is_blocked(self, url):
        """
        Returns True if the URL is blacklisted or if a whitelist is active
        and the URL is not on it.
        """
        # Check blacklist
        for domain in config.BLACKLIST:
            if domain and domain in url:
                return True

        # If whitelist is non-empty, only allow whitelisted domains
        if config.WHITELIST:
            for domain in config.WHITELIST:
                if domain and domain in url:
                    return False  # Found in whitelist — allow
            return True  # Not found in non-empty whitelist — block

        return False

    # -------------------------------------------------------------------------
    # Requirement A+B+C: HTTP Request Forwarding
    # -------------------------------------------------------------------------
    def handle_http_request(self, method, url, full_request):
        """
        Forwards an HTTP request to the target server and relays the response.
        Modifies headers to set Host correctly and inject 'Connection: close'
        to prevent Keep-Alive from hanging the receive loop.
        """
        try:
            # Extract Host header
            headers = [line.decode('utf-8', errors='ignore') for line in full_request.split(b'\r\n')[1:]]
            host_header = None
            for hdr in headers:
                if hdr.lower().startswith('host:'):
                    host_header = hdr.split(':', 1)[1].strip()
                    break

            # --- Requirement C: Parse host and port from URL ---
            if "://" in url:
                url_no_scheme = url.split("://", 1)[1]
            else:
                url_no_scheme = url

            host_and_port = url_no_scheme.split("/")[0]
            if not host_and_port and host_header:
                host_and_port = host_header

            host_parts = host_and_port.split(":")
            host = host_parts[0]
            port = int(host_parts[1]) if len(host_parts) > 1 else 80

            # --- Requirement C: Modify headers ---
            modified_request = self.modify_headers(full_request, host)

            log_request(self.client_address, (host, port), method, url, "FORWARDING")

            # --- Requirement B: Connect to target server via socket ---
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.settimeout(10)
            target_socket.connect((host, port))

            # Forward the modified request to the target
            target_socket.sendall(modified_request)

            # Receive the full response and relay it back to the client
            full_response = b""
            while True:
                data = target_socket.recv(self.buffer_size)
                if not data:
                    break
                full_response += data
                self.client_socket.sendall(data)

            # --- Requirement F: Cache successful GET responses ---
            if method == 'GET' and full_response.startswith(b"HTTP/"):
                status_line = full_response.split(b'\r\n')[0].decode('utf-8', errors='ignore')
                if '200' in status_line:
                    self.cache.set(url, full_response)
                    log_request(self.client_address, (host, port), method, url, "CACHED")

            target_socket.close()

        except socket.timeout:
            log_error(f"Timeout connecting to target for {url}")
        except Exception as e:
            log_error(f"Failed to forward HTTP request to {url}: {e}")

    # -------------------------------------------------------------------------
    # Requirement C: Header Modification
    # -------------------------------------------------------------------------
    def modify_headers(self, request, host):
        """
        Modifies outgoing HTTP headers as per Requirement C:
        - Ensure 'Host' header is correctly set to the target host.
        - Strip 'Proxy-Connection' header (client-side only).
        - Inject 'Connection: close' to prevent keep-alive from hanging
          our recv loop indefinitely.
        """
        lines = request.split(b'\r\n')
        new_lines = []
        has_connection_close = False

        for line in lines:
            line_str = line.decode('utf-8', errors='ignore')

            # Strip proxy-specific header
            if line_str.lower().startswith("proxy-connection:"):
                continue

            # Override Connection header to force close
            if line_str.lower().startswith("connection:"):
                new_lines.append(b"Connection: close")
                has_connection_close = True
                continue

            # Fix Host header to point to the correct target
            if line_str.lower().startswith("host:"):
                new_lines.append(f"Host: {host}".encode('utf-8'))
                continue

            new_lines.append(line)

        # Inject Connection: close if it wasn't already present
        if not has_connection_close:
            # Insert after the first request line
            new_lines.insert(1, b"Connection: close")

        return b'\r\n'.join(new_lines)

    # -------------------------------------------------------------------------
    # Requirement A (HTTPS) + H (BONUS): HTTPS Tunneling via CONNECT
    # -------------------------------------------------------------------------
    def handle_https_tunnel(self, url, full_request):
        """
        Handles HTTPS CONNECT requests by establishing a transparent tunnel
        between the client and target server. No decryption is performed —
        traffic is forwarded as-is (secure tunneling, not MITM).
        """
        try:
            # Parse host:port from the CONNECT target (e.g., "example.com:443")
            parts = url.split(':')
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 443

            log_request(self.client_address, (host, port), "CONNECT", url, "TUNNEL ESTABLISHING")

            # Connect to the target server
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.settimeout(10)
            target_socket.connect((host, port))

            # Inform the client the tunnel is ready
            self.client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            log_request(self.client_address, (host, port), "CONNECT", url, "TUNNEL ACTIVE")

            # Relay data bidirectionally using select() for efficiency
            self.relay_tunnel(self.client_socket, target_socket)

        except socket.timeout:
            log_error(f"Timeout while establishing HTTPS tunnel to {url}")
        except Exception as e:
            log_error(f"Failed to establish HTTPS tunnel to {url}: {e}")

    def relay_tunnel(self, client_sock, target_sock):
        """
        Efficiently relays raw bytes between client and target sockets using
        select() — event-driven I/O that waits for data rather than polling
        with short timeouts, saving CPU and reducing latency.
        """
        sockets = [client_sock, target_sock]
        try:
            while True:
                # Wait until at least one socket has data ready to read
                readable, _, errored = select.select(sockets, [], sockets, 30)

                if errored:
                    break  # A socket has an error condition

                if not readable:
                    break  # 30-second idle timeout — close tunnel

                for sock in readable:
                    try:
                        data = sock.recv(self.buffer_size)
                    except Exception:
                        data = None

                    if not data:
                        # Connection closed on one end — close both sides
                        return

                    # Forward data to the other socket
                    other = target_sock if sock is client_sock else client_sock
                    try:
                        other.sendall(data)
                    except Exception:
                        return

        except Exception:
            pass
        finally:
            try:
                target_sock.close()
            except Exception:
                pass
