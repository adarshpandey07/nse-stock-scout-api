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

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
