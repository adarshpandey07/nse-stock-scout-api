from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://localhost:5432/nse_scanner"
    secret_key: str = "change-me"

    # Supabase REST (primary DB access method)
    vite_supabase_url: str = ""
    vite_supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    admin_email: str = "admin@example.com"
    admin_password: str = "changeme123"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Kite Connect
    kite_api_key: str = ""
    kite_api_secret: str = ""

    # Encryption for stored credentials
    encryption_key: str = ""

    # OpenAI (Aadarsh.AI chat)
    openai_api_key: str = ""

    # Firecrawl (news scraping)
    firecrawl_api_key: str = ""

    # Telegram alerts
    telegram_bot_token: str = ""

    # Polymarket
    polymarket_private_key: str = ""
    polymarket_wallet_address: str = ""
    polymarket_chain_id: int = 137
    polymarket_clob_url: str = "https://clob.polymarket.com"
    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    polymarket_paper_mode: bool = True

    # Anthropic (Claude AI for Polymarket analysis)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-20250514"

    # Free cron secret (for external cron services like cron-job.org)
    cron_secret_key: str = "nss-cron-2026-secret"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
