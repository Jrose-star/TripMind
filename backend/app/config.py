"""全局配置：从环境变量 / .env 读取。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。所有敏感信息走环境变量，禁止硬编码。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"

    # 可观测
    langsmith_api_key: str = ""
    langsmith_project: str = "travel-agent"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # 数据层
    postgres_dsn: str = ""
    redis_url: str = ""

    # MCP
    mcp_server_url: str = ""
    amap_api_key: str = ""
    weather_api_key: str = ""

    # 服务
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"


settings = Settings()
