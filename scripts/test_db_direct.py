"""Test direct DB connection with IPv4 and SSL."""
import socket
import urllib.parse

# Resolve to IPv4
host = "db.kuqusavgjwortbnioghd.supabase.co"
try:
    ipv4 = socket.getaddrinfo(host, 5432, socket.AF_INET)
    print(f"IPv4 addresses for {host}:")
    for info in ipv4:
        print(f"  {info[4][0]}")
    ip = ipv4[0][4][0]
except Exception as e:
    print(f"IPv4 resolution failed: {e}")
    ip = None

if not ip:
    print("No IPv4, trying IPv6...")
    ipv6 = socket.getaddrinfo(host, 5432, socket.AF_INET6)
    for info in ipv6:
        print(f"  {info[4][0]}")
    ip = None  # Can't use raw IPv6 easily

from sqlalchemy import create_engine, text

passwords = ["Mahakal%40121.", "Mahakal%40121", "Mahakal@121.", "Mahakal@121"]

if ip:
    for pwd in passwords[:2]:
        url = f"postgresql://postgres:{pwd}@{ip}:5432/postgres?sslmode=require"
        print(f"\nTrying direct IPv4 {ip}:5432 with pwd variant...")
        try:
            engine = create_engine(url, pool_pre_ping=True, connect_args={
                "connect_timeout": 15,
                "options": f"-csearch_path=public",
            })
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print(f"  SUCCESS!")
                break
        except Exception as e:
            print(f"  FAILED: {str(e)[:150]}")

# Also try with hostname directly, forcing sslmode
for pwd in passwords[:2]:
    url = f"postgresql://postgres:{pwd}@{host}:5432/postgres"
    print(f"\nTrying hostname {host}:5432...")
    try:
        engine = create_engine(url, pool_pre_ping=True, connect_args={
            "connect_timeout": 20,
        })
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"  SUCCESS!")
            break
    except Exception as e:
        print(f"  FAILED: {str(e)[:150]}")
