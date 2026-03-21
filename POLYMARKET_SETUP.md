# Polymarket Trading Module — Setup Guide

## Status: Code Complete, DB Migration Pending

All 17 files written and pushed to GitHub. Tables need to be created in Supabase.

## Step 1: Run Database Migration

Open Supabase SQL Editor for project `kuqusavgjwortbnioghd`:
https://supabase.com/dashboard/project/kuqusavgjwortbnioghd/sql/new

Paste the contents of `scripts/polymarket_migration.sql` and run it.

This creates 7 tables + 9 indexes:
- `pm_config` — Per-user Polymarket settings
- `pm_markets` — Cached market data from Gamma API
- `pm_signals` — Trade signals from scanners
- `pm_orders` — All orders (paper + live)
- `pm_positions` — Open/closed positions
- `pm_pnl_snapshots` — Daily P&L history
- `pm_strategy_stats` — Per-strategy performance

## Step 2: Add Environment Variables

Add to `.env`:
```
POLYMARKET_PRIVATE_KEY=0x...          # MetaMask private key
POLYMARKET_WALLET_ADDRESS=0x...       # MetaMask public address
POLYMARKET_PAPER_MODE=true            # Keep true until tested
ANTHROPIC_API_KEY=sk-ant-...          # Claude API key for AI analyst
```

## Step 3: Install Dependencies

```bash
pip install py-clob-client anthropic web3
```
(Already installed locally)

## Step 4: Test

```bash
# Start server
uvicorn app.main:app --reload

# Sync markets from Polymarket
curl -X POST http://localhost:8000/polymarket/markets/sync -H "Authorization: Bearer <token>"

# Run arb scanner
curl -X POST http://localhost:8000/polymarket/scan/arb -H "Authorization: Bearer <token>"

# Run AI mispricing scanner
curl -X POST http://localhost:8000/polymarket/scan/mispricing -H "Authorization: Bearer <token>"
```

## Step 5: Start Cron Jobs

```bash
python -m scripts.polymarket_cron
```

## Architecture

```
app/services/polymarket/
├── __init__.py              # Re-exports
├── market_service.py        # Gamma API sync, CLOB price fetching
├── order_service.py         # Paper + live order execution
├── position_service.py      # Position tracking, P&L, snapshots
├── ai_analyst.py            # Claude Opus probability estimation
├── risk_manager.py          # Kelly criterion, exposure limits, kill switch
├── settlement_service.py    # Resolution detection
└── scanners/
    ├── arb_scanner.py           # Strategy 1: Sum-to-one arbitrage
    ├── mispricing_scanner.py    # Strategy 2: AI mispricing detection
    ├── news_reaction_scanner.py # Strategy 3: News reaction trading
    └── cross_arb_scanner.py     # Strategy 4: Cross-market (Phase 6)
```

## 4 Strategies

| # | Strategy | Edge | Risk | Target Return |
|---|----------|------|------|---------------|
| 1 | Sum-to-One Arbitrage | YES+NO < $1.00 | Near-zero | 15-25% |
| 2 | AI Mispricing | Claude vs market | Medium | 30-50% |
| 3 | News Reaction | Breaking news speed | Medium-High | 20-40% |
| 4 | Cross-Market Arb | Polymarket vs Kalshi | Low | 40-80% |

## MCP for this DB

Supabase MCP URL: `https://mcp.supabase.com/mcp?project_ref=kuqusavgjwortbnioghd`
Add this to Claude Code MCP settings to run SQL directly.
