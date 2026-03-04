"""Wallet service — balance, deposit, withdraw, transactions."""
from datetime import datetime, timezone
from decimal import Decimal

from supabase import Client

from app.services.activity import log_activity


def get_wallet(db: Client, user_pin: str) -> dict:
    result = db.table("user_wallets").select("*").eq("user_pin", user_pin).limit(1).execute()
    if not result.data:
        raise ValueError(f"No wallet for user_pin={user_pin}")
    return result.data[0]


def deposit(db: Client, user_pin: str, amount: Decimal, notes: str = "") -> dict:
    wallet = get_wallet(db, user_pin)
    new_balance = float(wallet["balance"]) + float(amount)
    new_deposited = float(wallet.get("total_deposited", 0)) + float(amount)

    db.table("user_wallets").update({
        "balance": new_balance,
        "total_deposited": new_deposited,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", wallet["id"]).execute()

    txn = db.table("user_wallets").insert({
        "user_pin": user_pin,
        "txn_type": "deposit",
        "amount": float(amount),
        "balance_after": new_balance,
        "notes": notes,
    }).execute()

    log_activity(db, event_type="wallet_deposit", entity_type="wallet", entity_id=user_pin,
                 message=f"Deposited {amount}", status="completed",
                 metadata_json={"amount": float(amount), "balance_after": new_balance})

    return txn.data[0] if txn.data else {}


def withdraw(db: Client, user_pin: str, amount: Decimal, notes: str = "") -> dict:
    wallet = get_wallet(db, user_pin)
    balance = float(wallet["balance"])
    if balance < float(amount):
        raise ValueError(f"Insufficient balance: {balance} < {amount}")

    new_balance = balance - float(amount)
    new_withdrawn = float(wallet.get("total_withdrawn", 0)) + float(amount)

    db.table("user_wallets").update({
        "balance": new_balance,
        "total_withdrawn": new_withdrawn,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", wallet["id"]).execute()

    txn = db.table("user_wallets").insert({
        "user_pin": user_pin,
        "txn_type": "withdraw",
        "amount": float(amount),
        "balance_after": new_balance,
        "notes": notes,
    }).execute()

    log_activity(db, event_type="wallet_withdraw", entity_type="wallet", entity_id=user_pin,
                 message=f"Withdrew {amount}", status="completed",
                 metadata_json={"amount": float(amount), "balance_after": new_balance})

    return txn.data[0] if txn.data else {}


def get_transactions(db: Client, user_pin: str, limit: int = 50) -> list[dict]:
    result = (
        db.table("user_wallets")
        .select("*")
        .eq("user_pin", user_pin)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data
