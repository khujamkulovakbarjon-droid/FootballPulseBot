import html
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================================================
# FOOTBALL PULSE — football-data.org v4
# =========================================================

BASE = "https://api.football-data.org/v4"
TZ = ZoneInfo("Asia/Tashkent")
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
FOOTBALL_DATA_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN", "").strip()

LEAGUES = {
    "Premier League": {"id": "PL", "flag": "🏴"},
    "LaLiga": {"id": "PD", "flag": "🇪🇸"},
    "Serie A": {"id": "SA", "flag": "🇮🇹"},
    "Bundesliga": {"id": "BL1", "flag": "🇩🇪"},
    "Ligue 1": {"id": "FL1", "flag": "🇫🇷"},
    "Champions League": {"id": "CL", "flag": "🏆"},
}

LIGAS = "🌍 LIGALAR"
GOAL = "⚽️ GOAL"
ASSIST = "🎯 ASSIST"
RESULTS = "📊 NATIJA"
TABLE = "📋 JADVAL"
UPCOMING = "📅 KEYINGI O‘YINLAR"
LIVE = "🔴 LIVE"
BACK = "🔙 ORQAGA"

CACHE = {}


class APIError(Exception):
    """API bilan bog‘liq xatolar."""


def esc(value):
    return html.escape(str(value if value is not None else ""))


def now():
    return datetime.now(TZ)


def dt_text(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ).strftime("%d.%m.%Y %H:%M")
    except (ValueError, TypeError):
        return "—"


def season_for_today():
    """Yevropa mavsumi odatda iyul/avgustda boshlanadi."""
    today = now().date()
    return today.year if today.month >= 7 else today.year - 1


def main_kb():
    return ReplyKeyboardMarkup([[LIGAS]], resize_keyboard=True)


def league_kb():
    return ReplyKeyboardMarkup(
        [[GOAL, ASSIST], [RESULTS, TABLE], [UPCOMING, LIVE], [LIGAS, BACK]],
        resize_keyboard=True,
    )


def leagues_kb():
    names = list(LEAGUES)
    rows = []
    for i in range(0, len(names), 2):
        row = [f"{LEAGUES[names[i]]['flag']} {names[i]}"]
        if i + 1 < len(names):
            row.append(f"{LEAGUES[names[i + 1]]['flag']} {names[i + 1]}")
        rows.append(row)
    rows.append([BACK])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def api_get(endpoint, params=None, ttl=30):
    """football-data.org API so‘rovi va kichik xotira keshi."""
    if not FOOTBALL_DATA_TOKEN:
        raise APIError(".env faylida FOOTBALL_DATA_TOKEN topilmadi.")

    params = params or {}
    cache_key = (
        endpoint,
        tuple(sorted((str(k), str(v)) for k, v in params.items())),
    )
    if cache_key in CACHE:
        created, cached_data = CACHE[cache_key]
        if time.time() - created < ttl:
            return cached_data

    url = f"{BASE}/{endpoint.lstrip('/')}"
    headers = {"X-Auth-Token": FOOTBALL_DATA_TOKEN}

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.get(url, headers=headers, params=params)

        try:
            data = response.json()
        except ValueError:
            data = {}

        print(f"[FOOTBALL-DATA] HTTP {response.status_code} {endpoint}")

        if response.status_code in (401, 403):
            detail = data.get("message") if isinstance(data, dict) else None
            raise APIError(
                f"Token yoki tarif ruxsati xatosi: {detail or response.status_code}. "
                "football-data.org tokeni va tarifini tekshiring."
            )
        if response.status_code == 429:
            raise APIError("API limiti tugadi. Biroz kutib, qayta urinib ko‘ring.")
        if response.status_code != 200:
            detail = data.get("message") if isinstance(data, dict) else None
            raise APIError(
                f"Football-data.org HTTP {response.status_code}: "
                f"{detail or 'noma’lum xato'}"
            )

        CACHE[cache_key] = (time.time(), data)
        return data

    except APIError:
        raise
    except httpx.TimeoutException:
        raise APIError("API serveridan javob olish vaqti tugadi.")
    except httpx.RequestError as exc:
        print("[REQUEST ERROR]", repr(exc))
        raise APIError("Internet yoki API serveriga ulanishda xato.")
    except Exception as exc:
        print("[API ERROR]", repr(exc))
        raise APIError("Kutilmagan API xatosi.")


async def api_data(endpoint, params=None, ttl=30):
    return await api_get(endpoint, params, ttl)


def selected(context):
    name = context.user_data.get("league", "Premier League")
    return name if name in LEAGUES else "Premier League"


async def error_msg(update, message):
    if update.effective_message:
        await update.effective_message.reply_text(
            f"❌ {esc(message)}", parse_mode=ParseMode.HTML
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["league"] = "Premier League"
    await update.effective_message.reply_text(
        "⚽️ <b>FOOTBALL PULSE</b>\n\n"
        "Futbol botiga xush kelibsiz! 👋\n\n"
        "🌍 6 ta musobaqa\n🔴 LIVE natijalar\n📊 Natijalar\n📋 Jadval\n"
        "⚽️ Goal\n🎯 Assist\n📅 Keyingi o‘yinlar\n\n"
        "Boshlash uchun 🌍 <b>LIGALAR</b> ni bosing.",
        reply_markup=main_kb(),
        parse_mode=ParseMode.HTML,
    )


async def leagues_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🌍 <b>LIGALAR</b>\n\nLigani tanlang:",
        reply_markup=leagues_kb(),
        parse_mode=ParseMode.HTML,
    )


async def choose(update: Update, context: ContextTypes.DEFAULT_TYPE, name):
    context.user_data["league"] = name
    await update.effective_message.reply_text(
        f"{LEAGUES[name]['flag']} <b>{esc(name)}</b>\n\nBo‘limni tanlang:",
        reply_markup=league_kb(),
        parse_mode=ParseMode.HTML,
    )


async def tops(update: Update, context: ContextTypes.DEFAULT_TYPE, kind):
    name = selected(context)
    league_id = LEAGUES[name]["id"]
    season = season_for_today()
    title = "TOP SCORERS" if kind == "goal" else "TOP ASSISTS"
    icon = "⚽️" if kind == "goal" else "🎯"

    await update.effective_message.reply_text("⏳ Ma’lumot yuklanmoqda...")
    try:
        data = await api_data(
            f"competitions/{league_id}/scorers",
            {"season": season, "limit": 20},
            3600,
        )
        rows = data.get("scorers") or []
        lines = [
            f"{icon} <b>{esc(name)} — {title}</b>",
            f"🏆 Mavsum: <b>{season}/{season + 1}</b>",
            "",
        ]

        if kind == "assist":
            # Ba’zi tarif/musobaqalarda assists maydoni berilmasligi mumkin.
            assist_rows = [row for row in rows if row.get("assists") is not None]
            assist_rows.sort(key=lambda row: row.get("assists") or 0, reverse=True)
            if not assist_rows:
                lines.append(
                    "Bu API javobida assist statistikasi mavjud emas. "
                    "Bepul tarif yoki tanlangan musobaqa assists ma’lumotini bermasligi mumkin."
                )
            else:
                for i, row in enumerate(assist_rows[:20], 1):
                    player = row.get("player") or {}
                    team = row.get("team") or {}
                    lines.append(
                        f"<b>{i}.</b> {esc(player.get('name') or 'Noma’lum')} — "
                        f"<b>{esc(row.get('assists', 0))}</b> 🎯 "
                        f"<i>{esc(team.get('name') or '—')}</i>"
                    )
        else:
            if not rows:
                lines.append("Bu musobaqa/mavsum uchun to‘purarlar topilmadi.")
            for i, row in enumerate(rows[:20], 1):
                player = row.get("player") or {}
                team = row.get("team") or {}
                goals = row.get("goals")
                if goals is None:
                    continue
                lines.append(
                    f"<b>{i}.</b> {esc(player.get('name') or 'Noma’lum')} — "
                    f"<b>{esc(goals)}</b> ⚽️ "
                    f"<i>{esc(team.get('name') or '—')}</i>"
                )

        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML
        )
    except APIError as exc:
        await error_msg(update, exc)


def fixture_line(item, live=False):
    home = item.get("homeTeam") or {}
    away = item.get("awayTeam") or {}
    score = item.get("score") or {}
    full_time = score.get("fullTime") or {}
    home_score = full_time.get("home")
    away_score = full_time.get("away")

    score_text = (
        f"{home_score} : {away_score}"
        if home_score is not None and away_score is not None
        else "— : —"
    )
    minute = item.get("minute")
    live_text = f" ({minute}′)" if live and minute else ""
    icon = "🔴" if live else "⚽️"

    return (
        f"{icon} {esc(home.get('shortName') or home.get('name') or '—')} "
        f"<b>{score_text}</b> "
        f"{esc(away.get('shortName') or away.get('name') or '—')}"
        f"{esc(live_text)}"
    )


async def show_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = selected(context)
    league_id = LEAGUES[name]["id"]
    await update.effective_message.reply_text("⏳ 🔴 LIVE yuklanmoqda...")
    try:
        data = await api_data("matches", {"status": "IN_PLAY"}, 15)
        matches = [
            item for item in (data.get("matches") or [])
            if (item.get("competition") or {}).get("code") == league_id
        ]
        lines = [f"🔴 <b>{esc(name)} — LIVE</b>", ""]
        if not matches:
            lines.append("Hozir bu musobaqada jonli o‘yin topilmadi.")
        for item in matches[:20]:
            lines.extend([
                f"<b>{dt_text(item.get('utcDate'))}</b>",
                fixture_line(item, True),
                "",
            ])
        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML
        )
    except APIError as exc:
        await error_msg(update, exc)


async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = selected(context)
    league_id = LEAGUES[name]["id"]
    today = now().date()
    start_date = today - timedelta(days=1)
    await update.effective_message.reply_text("⏳ 📊 Natijalar yuklanmoqda...")
    try:
        data = await api_data(
            f"competitions/{league_id}/matches",
            {"dateFrom": start_date.isoformat(), "dateTo": today.isoformat()},
            30,
        )
        matches = [
            item for item in (data.get("matches") or [])
            if item.get("status") == "FINISHED"
        ]
        matches.sort(key=lambda item: item.get("utcDate") or "", reverse=True)
        lines = [f"📊 <b>{esc(name)} — NATIJALAR</b>", ""]
        if not matches:
            lines.append("Kecha va bugun yakunlangan o‘yinlar topilmadi.")
        for item in matches[:15]:
            lines.extend([
                f"<b>{dt_text(item.get('utcDate'))}</b>",
                fixture_line(item),
                "",
            ])
        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML
        )
    except APIError as exc:
        await error_msg(update, exc)


async def show_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = selected(context)
    league_id = LEAGUES[name]["id"]
    today = now().date()
    end_date = today + timedelta(days=14)
    await update.effective_message.reply_text("⏳ 📅 Keyingi o‘yinlar yuklanmoqda...")
    try:
        data = await api_data(
            f"competitions/{league_id}/matches",
            {"dateFrom": today.isoformat(), "dateTo": end_date.isoformat()},
            60,
        )
        matches = [
            item for item in (data.get("matches") or [])
            if item.get("status") in {"SCHEDULED", "TIMED"}
        ]
        matches.sort(key=lambda item: item.get("utcDate") or "")
        lines = [f"📅 <b>{esc(name)} — KEYINGI O‘YINLAR</b>", ""]
        if not matches:
            lines.append("Keyingi 14 kun uchun o‘yin topilmadi.")
        for item in matches[:15]:
            lines.extend([
                f"<b>{dt_text(item.get('utcDate'))}</b>",
                fixture_line(item),
                "",
            ])
        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML
        )
    except APIError as exc:
        await error_msg(update, exc)


async def show_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = selected(context)
    league_id = LEAGUES[name]["id"]
    season = season_for_today()
    await update.effective_message.reply_text("⏳ 📋 Jadval yuklanmoqda...")
    try:
        data = await api_data(
            f"competitions/{league_id}/standings",
            {"season": season},
            3600,
        )
        groups = data.get("standings") or []
        total_group = next(
            (group for group in groups if group.get("type") == "TOTAL"),
            groups[0] if groups else {},
        )
        table = total_group.get("table") or []
        lines = [f"📋 <b>{esc(name)} — JADVAL</b>", ""]
        if not table:
            lines.append("Jadval topilmadi. API tarifini yoki mavsumni tekshiring.")
        for row in table[:30]:
            team = row.get("team") or {}
            lines.append(
                f"<b>{row.get('position', '?')}.</b> "
                f"{esc(team.get('shortName') or team.get('name') or '—')} — "
                f"<b>{row.get('points', 0)} ochko</b> | "
                f"O‘yin: {row.get('playedGames', 0)} | "
                f"GD: {row.get('goalDifference', 0)}"
            )
        await update.effective_message.reply_text(
            "\n".join(lines), parse_mode=ParseMode.HTML
        )
    except APIError as exc:
        await error_msg(update, exc)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "⚙️ <b>Football Pulse holati</b>\n"
        f"Telegram token: {'✅ bor' if BOT_TOKEN else '❌ yo‘q'}\n"
        f"Football-data token: {'✅ bor' if FOOTBALL_DATA_TOKEN else '❌ yo‘q'}",
        parse_mode=ParseMode.HTML,
    )


async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.text:
        return
    text_value = message.text.strip()

    if text_value == LIGAS:
        return await leagues_menu(update, context)
    if text_value == BACK:
        context.user_data["league"] = "Premier League"
        return await message.reply_text("Asosiy menyu:", reply_markup=main_kb())
    if text_value == GOAL:
        return await tops(update, context, "goal")
    if text_value == ASSIST:
        return await tops(update, context, "assist")
    if text_value == RESULTS:
        return await show_results(update, context)
    if text_value == TABLE:
        return await show_table(update, context)
    if text_value == UPCOMING:
        return await show_upcoming(update, context)
    if text_value == LIVE:
        return await show_live(update, context)

    for name, info in LEAGUES.items():
        if text_value in {f"{info['flag']} {name}", name}:
            return await choose(update, context, name)

    await message.reply_text(
        "Menyudan bo‘lim yoki liga tanlang.", reply_markup=main_kb()
    )


async def post_init(application: Application):
    print("Football Pulse ishga tushdi.")
    print(f"Football-data token mavjud: {'ha' if bool(FOOTBALL_DATA_TOKEN) else 'yo‘q'}")


def main():
    if not BOT_TOKEN:
        raise SystemExit("XATO: .env faylida BOT_TOKEN topilmadi.")
    if not FOOTBALL_DATA_TOKEN:
        raise SystemExit("XATO: .env faylida FOOTBALL_DATA_TOKEN topilmadi.")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))
    print("Bot polling boshlandi...")
    application.run_polling()


if __name__ == "__main__":
    main()
