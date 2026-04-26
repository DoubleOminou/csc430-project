# CSC430 Project

## Features Implemented
- **Core Proxy**: Handles HTTP GET/POST and HTTPS CONNECT tunneling using raw sockets.
- **Multithreading**: Supports simultaneous client connections with thread management.
- **Custom Logging**: Structured logs tracking Client IP, Target, Method, URL, and Status.
- **Content Caching**: Persistent file-based caching with TTL mechanism.
- **Filtering**: domain-based Blacklist/Whitelist system.
- **Admin Dashboard (Bonus)**: A premium, dark-mode web interface for real-time stats and logs.

## Project Structure
- `proxy_server.py`: Main entry point and listener.
- `request_handler.py`: Logic for parsing, filtering, and forwarding.
- `cache_manager.py`: Persistent caching logic.
- `stats_manager.py`: Real-time statistics tracking.
- `admin_server.py`: HTTP server for the dashboard.
- `config.py`: Centralized configuration.
- `logger.py`: Request logging utility.

## Verification Results

### Proxy Functionality (HTTP)
Verified using `curl -x http://localhost:8888 -I http://example.com`:
```text
HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
...
```

### Admin Interface
The dashboard is accessible at `http://localhost:8889` and provides a live view of:
- Total Request Count
- Cache Hits/Misses
- Blocked Requests
- Active Connections
- Live Log Tail

> [!TIP]
> To test the **Blacklist**, add a domain to the `BLACKLIST` array in `config.py` and restart the server.

---
**Status: Complete**
The server is currently running in the background for your review.
