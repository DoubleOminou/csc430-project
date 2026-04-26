# CSC 430 — Caching Proxy Server

**Lebanese American University | Department of Computer Science and Mathematics**  
**Spring 2025-2026 | Design Project**

---

## Overview

A fully-featured caching HTTP/HTTPS proxy server implemented in Python using raw socket programming. It supports concurrent client connections via multi-threading, on-disk response caching, URL filtering (blacklist/whitelist), structured logging, and a web-based admin dashboard.

---

## Architecture

```
proxy_server.py      — Entry point. Starts the proxy and admin server.
request_handler.py   — Core per-request logic: parse, filter, cache, forward.
cache_manager.py     — Disk-based cache with TTL and Cache-Control header support.
stats_manager.py     — Thread-safe singleton for live statistics.
admin_server.py      — Web-based admin dashboard (Bonus Requirement I).
logger.py            — Structured request and error logging.
config.py            — All tuneable settings.
```

---

## Requirements Covered

| Requirement | Status | Notes |
|---|---|---|
| A. Basic Proxy (HTTP + HTTPS) | ✅ Done | HTTP forwarding + HTTPS CONNECT tunnel |
| B. Socket Programming | ✅ Done | Raw TCP sockets throughout |
| C. Request Parsing & Header Modification | ✅ Done | `modify_headers()` in `request_handler.py` |
| D. Threading | ✅ Done | One daemon thread per client |
| E. Logging | ✅ Done | Timestamped logs to file + stdout |
| F. Content Caching | ✅ Done | Disk cache with TTL + Cache-Control max-age |
| G. Blacklist / Whitelist | ✅ Done | Configurable in `config.py` or via Dashboard |
| H. HTTPS Proxy (Bonus) | ✅ Done | CONNECT tunneling via `select()`-based relay |
| I. Admin Interface (Bonus) | ✅ Done | Premium SPA dashboard at `localhost:8889` |

---

## Running the Server

```bash
python proxy_server.py
```

- Proxy listens on `localhost:8888`
- Admin dashboard at `http://localhost:8889`

---

## Configuring Your Browser

Set your browser to use a manual HTTP/HTTPS proxy:

- **Host:** `127.0.0.1`
- **Port:** `8888`

Or use `curl`:
```bash
# HTTP test
curl -x http://127.0.0.1:8888 http://example.com

# HTTPS test
curl -x http://127.0.0.1:8888 https://example.com
```

---

## Admin Dashboard Features

| Tab | Features |
|---|---|
| 📊 Dashboard | Live stats: total requests, cache hits/misses, blocked count, active connections, cache hit rate bar |
| 🗄 Cache | Disk usage, entry count, TTL, one-click Clear All |
| 🔒 Security Rules | Add/remove blacklist and whitelist domains, save to disk |
| 📋 Live Logs | Color-coded log stream (hits = green, misses = yellow, blocked = red, tunnels = purple) |

---

## Cache Behavior

- **Storage:** Files in `./cache/`, keyed by MD5 hash of the URL.
- **TTL:** Reads `Cache-Control: max-age=N` from responses; falls back to `DEFAULT_CACHE_TTL` (300s).
- **Invalidation:** Expired entries are removed on next access.
- **Scope:** Only `GET` requests returning `200 OK` are cached.

---

## Logging Format

```
[2026-04-14 12:00:00] 127.0.0.1:52341 -> example.com:80 | GET | http://example.com/ | FORWARDING
[2026-04-14 12:00:01] 127.0.0.1:52342 -> example.com:80 | GET | http://example.com/ | 200 OK (cached)
[2026-04-14 12:00:02] 127.0.0.1:52343 -> BLOCKED | GET | http://ads.tracker.net/ | 403 FORBIDDEN
```

---

## Dependencies

No external dependencies required. Uses only Python standard library:
- `socket`, `select`, `threading`, `http.server`, `socketserver`
- `hashlib`, `pickle`, `logging`, `json`, `re`, `os`

---

## Notes

- **Connection: close** is injected into all forwarded HTTP requests to prevent keep-alive from hanging the receive loop.
- **HTTPS tunneling** uses `select.select()` for efficient, event-driven bidirectional relay — no busy-polling.
- **Blacklist/Whitelist** changes made in the admin UI are persisted back to `config.py` immediately.
- Code comments indicate which team member contributed each part (as per project requirement).
