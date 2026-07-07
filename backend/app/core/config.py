from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Security — no defaults, startup fails if unset
    secret_key: str
    access_token_expire_minutes: int = 60

    database_url: str = "sqlite:///./data/qahq.db"
    artifacts_dir: Path = Path("data/artifacts")
    log_dir: Path = Path("data/logs")

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # LDAP — disabled when server url is empty
    ldap_server_url: str = ""
    ldap_use_ssl: bool = False
    ldap_bind_dn: str = ""
    ldap_bind_password: str = ""
    ldap_search_base: str = ""
    ldap_user_filter: str = "(uid={username})"
    ldap_default_role: str = "qa"

    # MCP — disabled when api key is empty
    mcp_api_key: str = ""

    # First-run admin seed
    admin_username: str = ""
    admin_password: str = ""

    # Worker health
    heartbeat_timeout_seconds: int = 90
    heartbeat_check_interval_seconds: int = 30


settings = Settings()
