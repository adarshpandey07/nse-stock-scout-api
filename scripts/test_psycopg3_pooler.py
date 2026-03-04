"""Test psycopg3 with pooler - different auth handling."""
import psycopg

ref = "kuqusavgjwortbnioghd"
host = f"aws-0-ap-south-1.pooler.supabase.com"
passwords = ["Mahakal@121.", "Mahakal@121", "mahakal@121.", "mahakal@121"]

for pwd in passwords:
    for port in [6543, 5432]:
        print(f"Trying port {port}, pwd=...{pwd[-4:]}...", end=" ")
        try:
            conn = psycopg.connect(
                host=host, port=port, dbname="postgres",
                user=f"postgres.{ref}", password=pwd,
                connect_timeout=10,
            )
            cur = conn.execute("SELECT 1")
            print(f"SUCCESS!")
            conn.close()
            break
        except Exception as e:
            msg = str(e)[:80]
            print(f"FAIL: {msg}")
    else:
        continue
    break
else:
    # Try with channel_binding=disable (some Supavisor versions need it)
    print("\nTrying with channel_binding disabled...")
    for pwd in ["Mahakal@121.", "Mahakal@121"]:
        print(f"  pwd=...{pwd[-4:]}...", end=" ")
        try:
            conn = psycopg.connect(
                host=host, port=6543, dbname="postgres",
                user=f"postgres.{ref}", password=pwd,
                connect_timeout=10,
                channel_binding="disable",
            )
            cur = conn.execute("SELECT 1")
            print(f"SUCCESS!")
            conn.close()
            break
        except Exception as e:
            msg = str(e)[:80]
            print(f"FAIL: {msg}")
