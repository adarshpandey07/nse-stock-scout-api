"""
F1/F2/F3 Fundamental Scanner

F1 (Value): PE, PB, Dividend Yield
F2 (Quality): ROE, ROCE, D/E
F3 (Growth): Revenue growth, Profit growth, Promoter holding

All conditions in a group must pass. Stocks passing all 3 groups generate action items.
"""
import logging
from datetime import date, datetime, timezone

from supabase import Client

from app.services.activity import log_activity

logger = logging.getLogger(__name__)

OPERATORS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}


def _evaluate_condition(fund: dict, field: str, operator: str, value: float) -> bool:
    actual = fund.get(field)
    if actual is None:
        return False
    op_fn = OPERATORS.get(operator)
    if not op_fn:
        return False
    try:
        return op_fn(float(actual), float(value))
    except (TypeError, ValueError):
        return False


def _evaluate_group(fund: dict, criteria: list[dict]) -> tuple[bool, float]:
    if not criteria:
        return True, 100.0
    passed = 0
    for c in criteria:
        if _evaluate_condition(fund, c["field_name"], c["operator"], float(c["value"])):
            passed += 1
    all_pass = passed == len(criteria)
    score = (passed / len(criteria)) * 100
    return all_pass, round(score, 2)


def run_f_scanner(db: Client, scan_date: date | None = None) -> dict:
    if scan_date is None:
        scan_date = date.today()

    all_criteria = db.table("f_criteria_config").select("*").eq("enabled", True).execute().data
    groups = {"F1": [], "F2": [], "F3": []}
    for c in all_criteria:
        if c.get("criteria_group") in groups:
            groups[c["criteria_group"]].append(c)

    criteria_snapshot = {}
    for g, clist in groups.items():
        criteria_snapshot[g] = [
            {"name": c["condition_name"], "field": c["field_name"], "op": c["operator"], "value": float(c["value"])}
            for c in clist
        ]

    all_fundamentals = db.table("stock_fundamentals").select("*").execute().data

    f1_pass_count = f2_pass_count = f3_pass_count = all_pass_count = 0
    results = []

    for fund in all_fundamentals:
        f1_ok, f1_score = _evaluate_group(fund, groups["F1"])
        f2_ok, f2_score = _evaluate_group(fund, groups["F2"])
        f3_ok, f3_score = _evaluate_group(fund, groups["F3"])

        if f1_ok:
            f1_pass_count += 1
        if f2_ok:
            f2_pass_count += 1
        if f3_ok:
            f3_pass_count += 1

        overall_score = round((f1_score + f2_score + f3_score) / 3, 2)

        db.table("stock_fundamentals").update({
            "f1_status": f1_ok, "f2_status": f2_ok, "f3_status": f3_ok,
            "f1_score": f1_score, "f2_score": f2_score, "f3_score": f3_score,
            "overall_score": overall_score,
            "last_calculated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("symbol", fund["symbol"]).execute()

        if f1_ok and f2_ok and f3_ok:
            all_pass_count += 1
            results.append({
                "symbol": fund["symbol"], "f1_score": f1_score, "f2_score": f2_score,
                "f3_score": f3_score, "overall_score": overall_score,
                "pe": fund.get("pe"), "roe": fund.get("roe"),
                "current_price": fund.get("current_price", 0),
            })

    run_row = {
        "run_date": str(scan_date),
        "criteria_snapshot": criteria_snapshot,
        "total_stocks": len(all_fundamentals),
        "f1_pass": f1_pass_count,
        "f2_pass": f2_pass_count,
        "f3_pass": f3_pass_count,
        "all_pass": all_pass_count,
        "results": results,
    }
    run_result = db.table("f_scan_runs").insert(run_row).execute()
    run = run_result.data[0] if run_result.data else run_row

    log_activity(db, event_type="f_scan_completed", entity_type="f_scanner",
                 entity_id=run.get("id", ""),
                 message=f"F-Scanner: {all_pass_count}/{len(all_fundamentals)} passed all 3 groups",
                 status="completed", metadata_json={
                     "f1_pass": f1_pass_count, "f2_pass": f2_pass_count,
                     "f3_pass": f3_pass_count, "all_pass": all_pass_count
                 })
    return run
