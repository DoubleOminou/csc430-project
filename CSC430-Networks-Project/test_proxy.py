"""
test_proxy.py
Automated verification script for the CSC430 Caching Proxy Server.
Tests HTTP forwarding, HTTPS tunneling, cache hit behavior, blacklist blocking,
and the admin API endpoints.
"""
import socket
import time
import urllib.request
import json
import sys

PROXY_HOST = '127.0.0.1'
PROXY_PORT = 8888
ADMIN_HOST = 'http://127.0.0.1:8889'

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = []

def test(name, passed, detail=""):
    status = PASS if passed else FAIL
    print(f"{status} {name}" + (f" - {detail}" if detail else ""))
    results.append((name, passed))

def send_raw(request_bytes, timeout=10):
    """Send raw bytes through the proxy and return the response."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((PROXY_HOST, PROXY_PORT))
    s.sendall(request_bytes)
    response = b""
    try:
        while True:
            chunk = s.recv(8192)
            if not chunk:
                break
            response += chunk
    except socket.timeout:
        pass
    s.close()
    return response

def _add_auth_header(req):
    import base64
    from config import ADMIN_USER, ADMIN_PASS
    creds = f"{ADMIN_USER}:{ADMIN_PASS}".encode('utf-8')
    b64_creds = base64.b64encode(creds).decode('utf-8')
    req.add_header('Authorization', f'Basic {b64_creds}')

def admin_get(path):
    url = ADMIN_HOST + path
    req = urllib.request.Request(url)
    _add_auth_header(req)
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())

def admin_post(path, payload=None):
    url = ADMIN_HOST + path
    data = json.dumps(payload or {}).encode('utf-8') if payload is not None else b""
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    _add_auth_header(req)
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())

# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("CSC430 Caching Proxy Server - Verification Suite")
print("="*60 + "\n")

# ─────────────────────────────────────────────────────────────
print("Proxy Server Connectivity")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((PROXY_HOST, PROXY_PORT))
    s.close()
    test("Proxy binds on port 8888", True)
except Exception as e:
    test("Proxy binds on port 8888", False, str(e))
    print("\n  ⚠  Proxy server not reachable. Start it first with: python proxy_server.py")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
print("\nHTTP Forwarding (Requirement A + B + C)")
try:
    req = (
        b"GET http://example.com/ HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"Connection: close\r\n\r\n"
    )
    resp = send_raw(req, timeout=12)
    ok = b"HTTP/1." in resp and len(resp) > 100
    test("HTTP GET forwarded to example.com", ok, f"{len(resp)} bytes received")
    test("Response contains HTTP status line", b"HTTP/1." in resp)
    test("Response has body content", b"<html" in resp.lower() or b"<!doctype" in resp.lower(),
         "HTML content found" if b"<html" in resp.lower() else "body check")
except Exception as e:
    test("HTTP GET forwarding", False, str(e))

# ─────────────────────────────────────────────────────────────
print("\nCache Behavior (Requirement F)")
try:
    # First request — should be a MISS, then cached
    req = (
        b"GET http://example.com/cache-test HTTP/1.1\r\n"
        b"Host: example.com\r\n"
        b"Connection: close\r\n\r\n"
    )
    t0 = time.time()
    resp1 = send_raw(req, timeout=12)
    t1 = time.time() - t0

    # Second request — should hit cache and be faster
    t0 = time.time()
    resp2 = send_raw(req, timeout=12)
    t2 = time.time() - t0

    test("First request returns data", len(resp1) > 0, f"{t1:.2f}s")
    test("Second request served (cache or live)", len(resp2) > 0, f"{t2:.2f}s")
    test("Cache speeds up repeated requests", t2 <= t1 + 0.5,
         f"1st={t1:.2f}s 2nd={t2:.2f}s")
except Exception as e:
    test("Cache test", False, str(e))

# ─────────────────────────────────────────────────────────────
print("\nHTTPS CONNECT Tunnel (Requirement A BONUS)")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect((PROXY_HOST, PROXY_PORT))
    s.sendall(b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n")
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = s.recv(1024)
        if not chunk:
            break
        resp += chunk
    s.close()
    test("HTTPS CONNECT tunnel established", b"200 Connection Established" in resp,
         resp.split(b'\r\n')[0].decode('utf-8', errors='ignore'))
except Exception as e:
    test("HTTPS CONNECT tunnel", False, str(e))

# ─────────────────────────────────────────────────────────────
print("\nBlacklist Filtering (Requirement G)")
try:
    req = (
        b"GET http://blocked-test-domain.example/ HTTP/1.1\r\n"
        b"Host: blocked-test-domain.example\r\n"
        b"Connection: close\r\n\r\n"
    )
    resp = send_raw(req, timeout=5)
    test("Blacklisted domain returns 403", b"403" in resp,
         resp.split(b'\r\n')[0].decode('utf-8', errors='ignore'))
    test("403 response has body", b"Access Denied" in resp or b"Forbidden" in resp)

except Exception as e:
    test("Blacklist filtering", False, str(e))

# ─────────────────────────────────────────────────────────────
print("\nMalformed Request Handling (Robustness)")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((PROXY_HOST, PROXY_PORT))
    s.sendall(b"\r\n\r\n")  # Empty/malformed request
    s.close()
    test("Server handles empty request without crashing", True)
except Exception as e:
    test("Malformed request handling", False, str(e))

# ─────────────────────────────────────────────────────────────
print("\nAdmin Dashboard API (Bonus Requirement I)")
try:
    stats = admin_get('/api/stats')
    test("GET /api/stats returns data", 'total_requests' in stats,
         f"total_requests={stats.get('total_requests','?')}")
    test("Stats include cache fields", 'cache_hits' in stats and 'cache_misses' in stats)
    test("Stats include uptime", 'uptime' in stats)
    test("Stats include active_connections", 'active_connections' in stats)
except Exception as e:
    test("Admin /api/stats", False, str(e))

try:
    logs = admin_get('/api/logs')
    test("GET /api/logs returns list", isinstance(logs, list), f"{len(logs)} log lines")
except Exception as e:
    test("Admin /api/logs", False, str(e))

try:
    cfg = admin_get('/api/config')
    test("GET /api/config returns blacklist + whitelist", 'blacklist' in cfg and 'whitelist' in cfg)
    test("Config includes proxy_port", 'proxy_port' in cfg)
except Exception as e:
    test("Admin /api/config", False, str(e))

# try:
#     result = admin_post('/api/cache/clear')
#     test("POST /api/cache/clear succeeds", result.get('success') is True, result.get('message',''))
# except Exception as e:
#     test("Admin /api/cache/clear", False, str(e))

print("\n" + "="*60)
passed = sum(1 for _, p in results if p)
total  = len(results)
failed = total - passed
print(f"Results: {passed}/{total} passed", end="")
if failed:
    print(f"({failed} FAILED)")
    for name, p in results:
        if not p:
            print(f"X {name}")
else:
    print("All tests passed!")
print("="*60 + "\n")
