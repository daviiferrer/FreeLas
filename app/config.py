import asyncio
from typing import AsyncGenerator

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://freelaas:freelaas123@db:5432/freelaas"

    DASHSCOPE_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    MODEL_SCANNER: str = "qwen2.5-7b-instruct-1m"
    MODEL_ANALYST: str = "qwen-plus-2025-07-28"
    MODEL_STRATEGIST: str = "qwen3-max"

    SCRAPE_INTERVAL_MINUTES: int = 3
    SCRAPE_MAX_PAGES: int = 3
    SCRAPE_DELAY_MIN: int = 10
    SCRAPE_DELAY_MAX: int = 20
    TIME_FILTER_MINUTES: int = 60

    LOG_LEVEL: str = "INFO"

    # WAHA Integration
    WAHA_API_URL: str = "http://localhost:3000"
    WAHA_SESSION: str = "default"
    WAHA_API_KEY: str = ""
    WAHA_PHONE_NUMBER: str = ""

    # Action System — Kill Switch
    AUTO_ACTION_ENABLED: bool = False  # True = Playwright envia após aprovação

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


class EventBus:
    """Simple async event bus for SSE real-time streaming to dashboard."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.remove(queue)

    async def publish(self, event_type: str, data: dict):
        import json
        payload = {"type": event_type, **data}
        for queue in self._subscribers:
            await queue.put(json.dumps(payload, ensure_ascii=False))


event_bus = EventBus()
