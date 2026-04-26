import socket
import threading
import sys
import config
from logger import log_error, log_request
from request_handler import RequestHandler
from admin_server import start_admin_server

class ProxyServer:
    def __init__(self, host=config.PROXY_HOST, port=config.PROXY_PORT):
        self.host = host
        self.port = port
        self.server_socket = None

    def start(self):
        try:
            # Start Admin Interface in a separate thread
            admin_thread = threading.Thread(target=start_admin_server, args=(8889,), daemon=True)
            admin_thread.start()

            # Create a TCP socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow address reuse
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Bind and Listen
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(config.MAX_THREADS)
            
            print(f"[*] Proxy Server started on {self.host}:{self.port}")
            
            while True:
                # Accept incoming client connection
                client_socket, client_address = self.server_socket.accept()
                
                # Create a new thread for each client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True # Ensure thread closes when main program exits
                client_thread.start()
                
        except KeyboardInterrupt:
            print("\n[*] Shutting down proxy server...")
            if self.server_socket:
                self.server_socket.close()
            sys.exit(0)
        except Exception as e:
            log_error(f"Failed to start server: {e}")
            if self.server_socket:
                self.server_socket.close()
            sys.exit(1)

    def handle_client(self, client_socket, client_address):
        """Dispatches the client connection to the handler."""
        handler = RequestHandler(client_socket, client_address)
        handler.run()

if __name__ == "__main__":
    proxy = ProxyServer()
    proxy.start()
