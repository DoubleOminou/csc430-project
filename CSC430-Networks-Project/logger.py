import logging
from datetime import datetime
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler() if config.STDOUT_LOGGING else logging.NullHandler()
    ]
)

def log_request(client_addr, target_addr, method, url, status="PENDING"):
    """
    Logs proxy request details as per Requirement E.
    Format: [Timestamp] ClientIP:Port -> TargetHost:Port | Method | URL | Status
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    client_str = f"{client_addr[0]}:{client_addr[1]}"
    target_str = f"{target_addr[0]}:{target_addr[1]}" if isinstance(target_addr, tuple) else target_addr
    
    msg = f"[{timestamp}] {client_str} -> {target_str} | {method} | {url} | {status}"
    logging.info(msg)

def log_error(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.error(f"[{timestamp}] ERROR: {msg}")
