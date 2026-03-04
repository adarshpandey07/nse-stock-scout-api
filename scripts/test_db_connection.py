"""Test different DB connection strings to find one that works."""
import sys
sys.path.insert(0, ".")

urls = [
    # Direct connection with Mahakal@121.
    "postgresql://postgres:Mahakal%40121.@db.kuqusavgjwortbnioghd.supabase.co:5432/postgres",
    # Direct connection without trailing dot
    "postgresql://postgres:Mahakal%40121@db.kuqusavgjwortbnioghd.supabase.co:5432/postgres",
    # Pooler with project ref in username
    "postgresql://postgres.kuqusavgjwortbnioghd:Mahakal%40121.@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
    # Pooler without trailing dot
    "postgresql://postgres.kuqusavgjwortbnioghd:Mahakal%40121@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
    # Session mode pooler (port 5432)
    "postgresql://postgres.kuqusavgjwortbnioghd:Mahakal%40121.@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
]

from sqlalchemy import create_engine, text

for i, url in enumerate(urls):
    safe = url.replace("Mahakal%40121", "****").replace("Mahakal%40121.", "****.")
    print(f"\n[{i+1}] Trying: {safe}")
    try:
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 8})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as ok"))
            row = result.fetchone()
            print(f"    SUCCESS! Result: {row}")
            print(f"\n>>> WORKING URL index: {i+1}")
            print(f">>> URL: {url}")
            break
    except Exception as e:
        err = str(e)[:150]
        print(f"    FAILED: {err}")
else:
    print("\n>>> ALL CONNECTIONS FAILED")
