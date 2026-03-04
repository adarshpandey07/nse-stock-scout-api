"""Test DB connection using service role JWT as password."""
from sqlalchemy import create_engine, text
import urllib.parse

# Service role JWT from .env
jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt1cXVzYXZnandvcnRibmlvZ2hkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc0NjU4MCwiZXhwIjoyMDg3MzIyNTgwfQ.1f_SLNtAqdKc7gLQfpZhiFoyA5Y1c7rs2EAcev2zsGc"
jwt_encoded = urllib.parse.quote_plus(jwt)

urls = [
    # Pooler with JWT as password (transaction mode)
    f"postgresql://postgres.kuqusavgjwortbnioghd:{jwt_encoded}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres",
    # Pooler with JWT as password (session mode)
    f"postgresql://postgres.kuqusavgjwortbnioghd:{jwt_encoded}@aws-0-ap-south-1.pooler.supabase.com:5432/postgres",
]

for i, url in enumerate(urls):
    port = "6543" if "6543" in url else "5432"
    print(f"\n[{i+1}] Pooler port {port} with JWT password...")
    try:
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_user, current_database()"))
            row = result.fetchone()
            print(f"    SUCCESS! User: {row[0]}, DB: {row[1]}")
            print(f"    PORT: {port}")
            break
    except Exception as e:
        err = str(e)[:200]
        print(f"    FAILED: {err}")
else:
    print("\n>>> JWT auth also failed")
