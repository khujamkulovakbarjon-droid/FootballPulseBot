import os
import httpx

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# SOZLAMALAR (SETTINGS)
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "").strip()

API_URL = "https://api.football-data.org/v4"

# Ligalar lug'ati (Tugma nomi -> API kodi)
LEAGUES = {
    "🇪🇸 La Liga": "PD",
    "🏴 Premier League": "PL",
    "🇮🇹 Serie A": "SA",
    "🇩🇪 Bundesliga": "BL1",
    "🇫🇷 Ligue 1": "FL1",
    "🏆 Champions League": "CL",
}

DEFAULT_LEAGUE = "PD"  # Boshlang'ich default liga (La Liga)


# =========================
# TUGMALAR (KEYBOARDS)
# =========================

def start_keyboard():
    return ReplyKeyboardMarkup(
        [["▶️ START"]],
        resize_keyboard=True
    )


def main_keyboard():
    keyboard = [
        ["🔴 LIVE", "🏆 NATIJALAR"],
        ["📅 KEYINGI O‘YINLAR", "📊 LIGA JADVALI"],
        ["🥅 TOP SCORERS", "🌍 LIGALAR"],
        ["⬅️ BACK"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def leagues_keyboard():
    keyboard = [
        ["🇪🇸 La Liga", "🏴 Premier League"],
        ["🇮🇹 Serie A", "🇩🇪 Bundesliga"],
        ["🇫🇷 Ligue 1", "🏆 Champions League"],
        ["⬅️ BACK"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# =========================
# ASYNC API CLIENT
# =========================

async def api_get(endpoint: str, params: dict = None):
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{API_URL}{endpoint}",
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()


# =========================
# BOT HANDLERS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ FOOTBALL PULSE ⚡\n\n"
        "Assalomu alaykum!\n"
        "Futbol olamidagi barcha ma'lumotlar bir joyda. 🔥\n\n"
        "👇 Boshlash uchun tugmani bosing:",
        reply_markup=start_keyboard()
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 FOOTBALL PULSE — ASOSIY MENYU\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=main_keyboard()
    )


async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 ASOSIY MENYU",
        reply_markup=main_keyboard()
    )


async def live_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = await api_get("/matches")
        matches = data.get("matches", [])

        live = [
            m for m in matches
            if m.get("status") in ["IN_PLAY", "PAUSED"]
        ]

        if not live:
            await update.message.reply_text("🔴 LIVE\n\nHozircha jonli o‘yin topilmadi. ⚽")
            return

        text = "🔴 LIVE HISOB\n\n"
        for match in live:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            score = match.get("score", {}).get("fullTime", {})

            home_score = score.get("home", 0)
            away_score = score.get("away", 0)

            text += f"⚽ {home}\n   {home_score} : {away_score}\n⚽ {away}\n\n"

        await update.message.reply_text(text)

    except Exception as e:
        print("LIVE ERROR:", e)
        await update.message.reply_text("❌ LIVE ma'lumotlarini olishda xatolik yuz berdi.")


async def finished_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = await api_get("/matches")
        matches = data.get("matches", [])

        finished = [
            m for m in matches
            if m.get("status") == "FINISHED"
        ]
        if not finished:
            await update.message.reply_text("🏆 YAKUNLANGAN NATIJALAR\n\nHozircha natijalar topilmadi.")
            return

        text = "🏆 YAKUNLANGAN NATIJALAR\n\n"
        for match in finished[:20]:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            score = match.get("score", {}).get("fullTime", {})

            home_score = score.get("home", "-")
            away_score = score.get("away", "-")

            text += f"⚽ {home} {home_score} : {away_score} {away}\n\n"

        await update.message.reply_text(text)

    except Exception as e:
        print("FINISHED ERROR:", e)
        await update.message.reply_text("❌ Yakunlangan o‘yinlarni olishda xatolik yuz berdi.")


async def upcoming_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = await api_get("/matches")
        matches = data.get("matches", [])

        upcoming = [
            m for m in matches
            if m.get("status") == "SCHEDULED"
        ]

        if not upcoming:
            await update.message.reply_text("📅 KEYINGI O‘YINLAR\n\nHozircha o‘yinlar topilmadi.")
            return

        text = "📅 KEYINGI O‘YINLAR\n\n"
        for match in upcoming[:15]:
            home = match["homeTeam"]["name"]
            away = match["awayTeam"]["name"]
            date_str = match.get("utcDate", "").replace("T", " ")[:16]

            text += f"⚽ {home} — {away}\n🕐 {date_str} (UTC)\n\n"

        await update.message.reply_text(text)

    except Exception as e:
        print("UPCOMING ERROR:", e)
        await update.message.reply_text("❌ Keyingi o‘yinlarni olishda xatolik yuz berdi.")


async def leagues(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 LIGALAR\n\n"
        "Jadval yoki To'purarlarni ko'rmoqchi bo'lgan ligani tanlang:",
        reply_markup=leagues_keyboard()
    )


async def select_league(update: Update, context: ContextTypes.DEFAULT_TYPE):
    league_name = update.message.text
    league_code = LEAGUES.get(league_name)

    if not league_code:
        return

    # Foydalanuvchi tanlagan ligani context.user_data ichida saqlaymiz
    context.user_data["selected_league_code"] = league_code
    context.user_data["selected_league_name"] = league_name

    await update.message.reply_text(
        f"✅ Tanlandi: {league_name}\n\n"
        "Endi asosiy menyudagi '📊 LIGA JADVALI' yoki '🥅 TOP SCORERS' "
        "bo'limlaridan foydalanishingiz mumkin.",
        reply_markup=main_keyboard()
    )


async def league_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    league_code = context.user_data.get("selected_league_code", DEFAULT_LEAGUE)
    league_name = context.user_data.get("selected_league_name", "🇪🇸 La Liga")

    try:
        data = await api_get(f"/competitions/{league_code}/standings")
        standings = data.get("standings", [])

        if not standings:
            await update.message.reply_text(f"📊 {league_name} uchun jadval topilmadi.")
            return

        # Ko'pincha birinchi element 'TOTAL' turnir jadvali bo'ladi
        table = standings[0].get("table", [])
        text = f"📊 JADVAL — {league_name.upper()}\n\n"

        for row in table:
            pos = row.get("position")
            team = row["team"]["name"]
            pts = row.get("points", 0)
            played = row.get("playedGames", 0)

            text += f"{pos}. {team} — {pts} ochko ({played} o'yin)\n"

        await update.message.reply_text(text)

    except Exception as e:
        print("TABLE ERROR:", e)
        await update.message.reply_text(f"❌ {league_name} jadvalini olishda xatolik yuz berdi.")


async def top_scorers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    league_code = context.user_data.get("selected_league_code", DEFAULT_LEAGUE)
    league_name = context.user_data.get("selected_league_name", "🇪🇸 La Liga")

    try:
        data = await api_get(f"/competitions/{league_code}/scorers")
        scorers = data.get("scorers", [])
        if not scorers:
            await update.message.reply_text(f"🥅 {league_name} uchun to'purarlar ma'lumoti topilmadi.")
            return

        text = f"🥅 TOP SCORERS — {league_name.upper()}\n\n"
        for i, item in enumerate(scorers[:10], 1):
            player_name = item["player"]["name"]
            team_name = item["team"]["name"]
            goals = item.get("goals", 0)

            text += f"{i}. {player_name}\n   ⚽ {goals} gol — {team_name}\n\n"

        await update.message.reply_text(text)

    except Exception as e:
        print("SCORERS ERROR:", e)
        await update.message.reply_text(f"❌ {league_name} to'purarlarini olishda xatolik yuz berdi.")


# =========================
# DASTURNI ISHGA TUSHIRISH
# =========================

def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN topilmadi! .env faylini tekshiring.")
    if not FOOTBALL_API_KEY:
        raise ValueError("❌ FOOTBALL_API_KEY topilmadi! .env faylini tekshiring.")

    app = (
    Application.builder()
    .token(BOT_TOKEN)
    .connect_timeout(60)
    .read_timeout(60)
    .write_timeout(60)
    .pool_timeout(60)
    .build()
)

    # Buyruqlar
    app.add_handler(CommandHandler("start", start))

    # Matnli tugmalar (Main menu & Navigation)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^▶️ START$"), main_menu))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🔴 LIVE$"), live_matches))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🏆 NATIJALAR$"), finished_matches))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📅 KEYINGI O‘YINLAR$"), upcoming_matches))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📊 LIGA JADVALI$"), league_table))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🥅 TOP SCORERS$"), top_scorers))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🌍 LIGALAR$"), leagues))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^⬅️ BACK$"), back))

    # Ligalarni tanlash
    league_regex = f"^({'|'.join(LEAGUES.keys())})$"
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(league_regex), select_league))

    print("⚽️ Football Pulse muvaffaqiyatli ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()