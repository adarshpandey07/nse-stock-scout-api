from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class WalletOut(BaseModel):
    user_pin: str
    user_name: str
    balance: Decimal
    total_deposited: Decimal
    total_withdrawn: Decimal

    model_config = {"from_attributes": True}


class WalletTxnRequest(BaseModel):
    user_pin: str
    amount: Decimal
    notes: str = ""


class WalletTxnOut(BaseModel):
    id: str
    user_pin: str
    txn_type: str
    amount: Decimal
    balance_after: Decimal
    reference_id: str
    notes: str
    created_at: datetime

    model_config = {"from_attributes": True}
