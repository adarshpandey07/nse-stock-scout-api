"""Test newer Supabase pooler URL format."""
from sqlalchemy import create_engine, text
import urllib.parse

ref = "kuqusavgjwortbnioghd"
passwords = ["Mahakal@121.", "Mahakal@121"]

urls = []
for pwd in passwords:
    pwd_enc = urllib.parse.quote_plus(pwd)
    # New format: [ref].pooler.supabase.com
    urls.append((f"postgresql://postgres.{ref}:{pwd_enc}@{ref}.pooler.supabase.com:6543/postgres", f"new-pooler:6543 pwd=...{pwd[-3:]}"))
    urls.append((f"postgresql://postgres.{ref}:{pwd_enc}@{ref}.pooler.supabase.com:5432/postgres", f"new-pooler:5432 pwd=...{pwd[-3:]}"))
    # Also try supavisor format
    urls.append((f"postgresql://postgres.{ref}:{pwd_enc}@{ref}.supabase.com:6543/postgres", f"supabase:6543 pwd=...{pwd[-3:]}"))

for url, label in urls:
    print(f"\nTrying {label}...")
    try:
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_user"))
            print(f"  SUCCESS! User: {result.fetchone()[0]}")
            # Print the working URL pattern
            safe_url = url.split("@")[1]
            print(f"  Host: {safe_url}")
            break
    except Exception as e:
        err = str(e)[:120]
        print(f"  FAILED: {err}")
else:
    print("\n>>> All new pooler formats failed too")
