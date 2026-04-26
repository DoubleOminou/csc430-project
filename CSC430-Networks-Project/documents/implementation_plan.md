# Proxy Server Improvement Plan

We will improve the existing caching proxy server to fully satisfy all requirements and provide a highly premium, fully-functional system.

## User Review Required
None of these changes are destructive. The proxy server is functioning, but it lacks robustness and the admin dashboard needs critical features and a visual overhaul. Please review the proposed changes.

## Proposed Changes

### Core Proxy Logic
Ensure the proxy correctly forwards HTTP and HTTPS requests without freezing, and handles the flow of data efficiently.

#### [MODIFY] [request_handler.py](file:///d:/Projects/CSC430-Networks-Project/request_handler.py)
- **Fix HTTP Keep-Alive Hang**: Inject `Connection: close` when forwarding requests. Currently, HTTP 1.1 uses keep-alive by default, so reading responses in a `while` loop hangs until the remote server times out. 
- **Efficient HTTPS Tunneling**: Rewrite the `relay_tunnel` method to use standard OS `select.select()` instead of using short-duration timeouts. `select` uses event-driven reading/writing, meaning it waits for data to arrive rather than continually polling. This drastically improves CPU usage and network latency during CONNECT tunnels.
- **Robust Parsing**: Guard against malformed bytes when decoding headers (`.decode('utf-8', errors='ignore')` instead of crashing).

### Admin Interface & Configuration
The PDF requirement dictates an interface for "viewing and managing logs, cache entries, and blacklist/whitelist configurations". The current implementation only *views* stats. I will add full management capabilities and significantly boost the visual aesthetics.

#### [MODIFY] [admin_server.py](file:///d:/Projects/CSC430-Networks-Project/admin_server.py)
- **Premium UI Overhaul**: Redesign the entire interface. Use modern glassmorphism, smooth micro-animations, vibrant gradients, and premium modern typography (Inter). 
- **Interactive Management Tabs**: Create "Dashboard", "Cache Management", and "Security Rules" tabs inside the single page application.
- **API Endpoints**: 
    - `POST /api/cache/clear`: Clear the proxy cache.
    - `GET /api/config`: Return current blacklist and whitelist.
    - `POST /api/config`: Update the blacklist and whitelist arrays in-memory and write them back into `config.py` for persistence.

#### [MODIFY] [config.py](file:///d:/Projects/CSC430-Networks-Project/config.py)
- Minor adjustments to formatting so the admin server can seamlessly read and rewrite the block arrays.

#### [MODIFY] [cache_manager.py](file:///d:/Projects/CSC430-Networks-Project/cache_manager.py)
- Ensure the cache clearing function correctly reports statistics afterwards.

## Verification Plan
### Automated Tests
- Run `curl -x localhost:8888 http://example.com` to test HTTP.
- Run `curl -p -x localhost:8888 https://example.com` to test HTTPS.

### Manual Verification
- View the UI dashboard. Verify the new premium UI with dark mode, aesthetic colors, and charts/stats.
- Test clearing the cache from the dashboard.
- Test adding domains to the blacklist and confirm access to them through the proxy is rejected.
