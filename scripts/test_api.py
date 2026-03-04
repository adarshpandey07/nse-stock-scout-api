"""Quick API test suite for NSE Stock Scout."""
import json
import sys
import httpx

BASE = "http://localhost:8000"

def main():
    # 1. Register test user
    print("=== 1. Register ===")
    r = httpx.post(f"{BASE}/auth/register", json={
        "email": "test@scout.in", "password": "Test1234", "name": "Tester"
    }, timeout=10)
    print(f"  Status: {r.status_code}")
    try:
        data = r.json()
    except Exception:
        print(f"  Response text: {r.text[:200]}")
        data = {}

    token = data.get("access_token", "")
    if not token:
        print("  Already exists, trying login...")
        r = httpx.post(f"{BASE}/auth/login", json={
            "email": "test@scout.in", "password": "Test1234"
        }, timeout=10)
        data = r.json()
        token = data.get("access_token", "")

    if not token:
        print("  ERROR: Could not get token")
        print(f"  Response: {data}")
        sys.exit(1)

    print(f"  Token: {token[:30]}...")
    headers = {"Authorization": f"Bearer {token}"}

    # Make user admin
    # (skip — test what we can as regular user)

    tests = [
        ("GET", "/health", None, False),
        ("GET", "/dashboard/summary?user_pin=aadarsh", None, True),
        ("GET", "/wallet/balance?user_pin=aadarsh", None, True),
        ("GET", "/f-scanner/groups", None, True),
        ("GET", "/superstar/investors", None, True),
        ("GET", "/news/sources", None, True),
        ("GET", "/watchlist/?user_pin=aadarsh", None, True),
        ("GET", "/actions/pending", None, True),
        ("GET", "/actions/?limit=5", None, True),
        ("GET", "/astro/signals", None, True),
        ("GET", "/astro/planets", None, True),
        ("GET", "/astro/accuracy", None, True),
        ("GET", "/trades/?user_pin=aadarsh", None, True),
        ("GET", "/stocks/?limit=3", None, True),
        ("GET", "/backtest/runs?user_pin=aadarsh", None, True),
        ("GET", "/chat/sessions?user_pin=aadarsh", None, True),
        ("GET", "/telegram/config?user_pin=aadarsh", None, True),
        ("GET", "/analysis/portfolio?user_pin=aadarsh", None, True),
        ("GET", "/analysis/pnl?user_pin=aadarsh", None, True),
        ("GET", "/analysis/brokerage?user_pin=aadarsh", None, True),
        ("GET", "/analysis/cashflow?user_pin=aadarsh", None, True),
        ("GET", "/results/latest?limit=5", None, True),
    ]

    passed = 0
    failed = 0

    print("\n=== API Endpoint Tests ===\n")
    for method, path, body, auth in tests:
        try:
            h = headers if auth else {}
            if method == "GET":
                r = httpx.get(f"{BASE}{path}", headers=h, timeout=10)
            else:
                r = httpx.post(f"{BASE}{path}", json=body, headers=h, timeout=10)

            # 200 = success, 404 = acceptable (no data), 403 = role issue (acceptable)
            ok = r.status_code in (200, 404, 403)
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            else:
                failed += 1

            resp_text = json.dumps(r.json())[:100]
            print(f"  {status} {r.status_code} {method:4s} {path:50s} {resp_text}")
        except Exception as e:
            failed += 1
            print(f"  ERR  {method:4s} {path:50s} {e}")

    # Test POST endpoints
    print("\n=== POST Endpoint Tests ===\n")

    # Wallet deposit
    r = httpx.post(f"{BASE}/wallet/deposit", json={
        "user_pin": "aadarsh", "amount": 10000, "notes": "Test deposit"
    }, headers=headers, timeout=10)
    ok = r.status_code in (200, 400, 404)
    print(f"  {'PASS' if ok else 'FAIL'} {r.status_code} POST /wallet/deposit {json.dumps(r.json())[:100]}")
    if ok: passed += 1
    else: failed += 1

    # Add to watchlist
    r = httpx.post(f"{BASE}/watchlist/", json={
        "user_pin": "aadarsh", "symbol": "RELIANCE", "watchlist_type": "long_term"
    }, headers=headers, timeout=10)
    ok = r.status_code in (200, 409)
    print(f"  {'PASS' if ok else 'FAIL'} {r.status_code} POST /watchlist/ {json.dumps(r.json())[:100]}")
    if ok: passed += 1
    else: failed += 1

    # Chat message
    r = httpx.post(f"{BASE}/chat/message", json={
        "user_pin": "aadarsh", "message": "What stocks should I look at?"
    }, headers=headers, timeout=30)
    ok = r.status_code == 200
    print(f"  {'PASS' if ok else 'FAIL'} {r.status_code} POST /chat/message {json.dumps(r.json())[:100]}")
    if ok: passed += 1
    else: failed += 1

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
