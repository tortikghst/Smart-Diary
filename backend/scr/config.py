from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigSettings(BaseSettings):
    # === НАСТРОЙКИ POSTGRESQL ===
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_PORT: int = 5432
    DB_HOST: str = "127.0.0.1"

    # === НАСТРОЙКИ REDIS ===
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379

    # === НАСТРОЙКИ БЕЗОПАСНОСТИ (JWT) ===
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 43200

    # === НАСТРОЙКИ ИНФРАСТРУКТУРЫ ===
    MAX_BOT_TOKEN: str = "mock_bot_token_for_hackathon"
    SCHOOL_TZ: str = "Europe/Kirov"

    # === НАСТРОЙКИ ИИ (LLM) ===
    # Флаг: True — стабильный мок (без интернета), False — реальный запрос к Caila
    USE_MOCK_LLM: bool = True
    
    # Новые настройки для Caila / OpenRouter
    LLM_API_KEY: str = "1000310301.347685.pXA1D1frd5cVwywD8tojtRWR2WTrPxHOgIP8nswR"
    LLM_MODEL: str = "qwen/qwen3.7-flash"

    # Старые настройки YandexGPT (оставлены на случай, если где-то в коде на них остались ссылки)
    YANDEX_API_KEY: str = "mock_key"
    YANDEX_FOLDER_ID: str = "mock_folder"
    YANDEX_MODEL_NAME: str = "yandexgpt-lite"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Создаем один глобальный объект настроек для всего проекта
settings = ConfigSettings()