"""Test with psycopg3 which has better IPv6 support."""
import psycopg

host = "db.kuqusavgjwortbnioghd.supabase.co"
passwords = ["Mahakal@121.", "Mahakal@121"]

for pwd in passwords:
    print(f"\nTrying psycopg3 direct connection with password variant...")
    try:
        conn = psycopg.connect(
            host=host, port=5432, dbname="postgres",
            user="postgres", password=pwd,
            connect_timeout=20,
            sslmode="require",
        )
        cur = conn.execute("SELECT current_user, current_database()")
        print(f"  SUCCESS! {cur.fetchone()}")
        conn.close()
        print(f"  WORKING PASSWORD: {pwd}")
        break
    except Exception as e:
        print(f"  FAILED: {str(e)[:200]}")
