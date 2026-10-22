import os
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

API_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()

async def main():
    if not API_KEY:
        print("XATO: .env ichida API_FOOTBALL_KEY topilmadi.")
        return

    url = "https://v3.football.api-sports.io/status"
    headers = {"x-apisports-key": API_KEY}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, headers=headers)

        print("HTTP:", response.status_code)
        print("API javobi:", response.json())

    except Exception as e:
        print("Ulanish xatosi:", e)

asyncio.run(main())