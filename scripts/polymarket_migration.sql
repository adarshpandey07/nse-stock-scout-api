-- Polymarket Trading Module — Database Migration
-- Run this in Supabase SQL Editor for the NSE Stock Scout project

-- 1. pm_config — Per-user Polymarket settings
CREATE TABLE IF NOT EXISTS pm_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pin TEXT NOT NULL UNIQUE,
    wallet_address TEXT,
    private_key_encrypted TEXT,
    proxy_wallet_address TEXT,
    chain_id INTEGER DEFAULT 137,
    paper_mode BOOLEAN DEFAULT true,
    max_position_usd NUMERIC DEFAULT 50,
    max_total_exposure_usd NUMERIC DEFAULT 500,
    kelly_fraction NUMERIC DEFAULT 0.25,
    auto_trade BOOLEAN DEFAULT false,
    strategies_enabled JSONB DEFAULT '["arb"]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. pm_markets — Cached market data from Gamma API
CREATE TABLE IF NOT EXISTS pm_markets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condition_id TEXT NOT NULL UNIQUE,
    question TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT '',
    end_date TIMESTAMPTZ,
    tokens JSONB NOT NULL DEFAULT '[]'::jsonb,
    volume_24h NUMERIC DEFAULT 0,
    liquidity NUMERIC DEFAULT 0,
    yes_price NUMERIC,
    no_price NUMERIC,
    spread NUMERIC,
    active BOOLEAN DEFAULT true,
    resolution_source TEXT DEFAULT '',
    tags JSONB DEFAULT '[]'::jsonb,
    last_synced_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. pm_signals — Trade signals from scanners
CREATE TABLE IF NOT EXISTS pm_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condition_id TEXT NOT NULL,
    strategy TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side TEXT NOT NULL,
    recommended_price NUMERIC NOT NULL,
    recommended_size NUMERIC NOT NULL,
    estimated_edge NUMERIC,
    ai_probability NUMERIC,
    market_probability NUMERIC,
    confidence TEXT DEFAULT 'medium',
    reasoning TEXT DEFAULT '',
    news_context TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    action_centre_id UUID,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. pm_orders — All orders (paper + live)
CREATE TABLE IF NOT EXISTS pm_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pin TEXT NOT NULL,
    signal_id UUID REFERENCES pm_signals(id),
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    side TEXT NOT NULL,
    price NUMERIC NOT NULL,
    size NUMERIC NOT NULL,
    order_type TEXT DEFAULT 'GTC',
    paper_mode BOOLEAN DEFAULT true,
    clob_order_id TEXT,
    status TEXT DEFAULT 'pending',
    filled_size NUMERIC DEFAULT 0,
    avg_fill_price NUMERIC,
    fee_paid NUMERIC DEFAULT 0,
    tx_hash TEXT,
    error_message TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 5. pm_positions — Open/closed positions
CREATE TABLE IF NOT EXISTS pm_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pin TEXT NOT NULL,
    condition_id TEXT NOT NULL,
    token_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    question TEXT NOT NULL,
    size NUMERIC NOT NULL DEFAULT 0,
    avg_entry_price NUMERIC NOT NULL DEFAULT 0,
    current_price NUMERIC DEFAULT 0,
    cost_basis NUMERIC DEFAULT 0,
    market_value NUMERIC DEFAULT 0,
    unrealized_pnl NUMERIC DEFAULT 0,
    unrealized_pnl_pct NUMERIC DEFAULT 0,
    strategy TEXT DEFAULT '',
    paper_mode BOOLEAN DEFAULT true,
    status TEXT DEFAULT 'open',
    resolved_outcome TEXT,
    realized_pnl NUMERIC DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_pin, token_id, paper_mode)
);

-- 6. pm_pnl_snapshots — Daily P&L history
CREATE TABLE IF NOT EXISTS pm_pnl_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pin TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    total_invested NUMERIC DEFAULT 0,
    total_market_value NUMERIC DEFAULT 0,
    total_unrealized_pnl NUMERIC DEFAULT 0,
    total_realized_pnl NUMERIC DEFAULT 0,
    open_positions INTEGER DEFAULT 0,
    strategy_breakdown JSONB DEFAULT '{}'::jsonb,
    paper_mode BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_pin, snapshot_date, paper_mode)
);

-- 7. pm_strategy_stats — Per-strategy performance
CREATE TABLE IF NOT EXISTS pm_strategy_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_pin TEXT NOT NULL,
    strategy TEXT NOT NULL,
    total_signals INTEGER DEFAULT 0,
    signals_executed INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_invested NUMERIC DEFAULT 0,
    total_returned NUMERIC DEFAULT 0,
    net_pnl NUMERIC DEFAULT 0,
    win_rate NUMERIC DEFAULT 0,
    avg_edge_realized NUMERIC DEFAULT 0,
    paper_mode BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_pin, strategy, paper_mode)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pm_markets_active ON pm_markets(active) WHERE active = true;
CREATE INDEX IF NOT EXISTS idx_pm_markets_condition ON pm_markets(condition_id);
CREATE INDEX IF NOT EXISTS idx_pm_signals_status ON pm_signals(status);
CREATE INDEX IF NOT EXISTS idx_pm_signals_strategy ON pm_signals(strategy);
CREATE INDEX IF NOT EXISTS idx_pm_orders_user ON pm_orders(user_pin);
CREATE INDEX IF NOT EXISTS idx_pm_orders_status ON pm_orders(status);
CREATE INDEX IF NOT EXISTS idx_pm_positions_user_status ON pm_positions(user_pin, status);
CREATE INDEX IF NOT EXISTS idx_pm_pnl_user_date ON pm_pnl_snapshots(user_pin, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_pm_stats_user ON pm_strategy_stats(user_pin);
