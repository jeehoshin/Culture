import asyncio

from app.config import get_settings
from app.sync import sync_manager


async def main() -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_server_key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SECRET_KEY are required")
    await sync_manager.run(settings)
    print(sync_manager.state)
    if sync_manager.state["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
