"""
A telegram bot that provides world cup status update.
API: worldcup26.ir
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from constants import FLAGS


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

BASE_URL      = "https://worldcup26.ir"
POLL_INTERVAL = 60 # 1 minute

SUBSCRIBERS_FILE = Path("subscribers.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")],
)
log = logging.getLogger(__name__)

subscribers: set[int] = set(json.loads(SUBSCRIBERS_FILE.read_text())) if SUBSCRIBERS_FILE.exists() else set()

def save_subscribers():
    SUBSCRIBERS_FILE.write_text(json.dumps(list(subscribers)))


tracked: dict[str, dict] = {}


def flag(name: str) -> str:
    return FLAGS.get(name, "🏳️")


def score_line(home: str, away: str, hg: int, ag: int) -> str:
    return f"{flag(home)} {hg} - {ag} {flag(away)}"


# API
def get_all_games() -> list[dict]:
    try:
        r = requests.get(f"{BASE_URL}/get/games", timeout=15)
        r.raise_for_status()
        return r.json().get("games", [])
    except Exception as e:
        log.error("Error %s", e)
        return []


def parse_game(g: dict) -> dict:
    return {
        "id":       str(g.get("id", g.get("_id", ""))),
        "home":     g.get("home_team_name_en", ""),
        "away":     g.get("away_team_name_en", ""),
        "hg":       int(g.get("home_score") or 0),
        "ag":       int(g.get("away_score") or 0),
        "finished": str(g.get("finished", "")).upper() == "TRUE",
        "live":     str(g.get("time_elapsed", "")).lower() not in ("", "finished", "null", "none"),
        "date":     g.get("local_date", ""),
        "elapsed":  g.get("time_elapsed", ""),
    }


def is_today(date_str: str) -> bool:
    if not date_str:
        return False

    today = datetime.now()
    formats = [
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d %H:%M",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.year == today.year and dt.month == today.month and dt.day == today.day
        except ValueError:
            continue

    log.error("Unknown date format received from API: '%s'", date_str)
    return False


async def broadcast(app: Application, text: str):
    for chat_id in list(subscribers):
        try:
            await app.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            log.warning("Error%s: %s", chat_id, e)


async def process_games(app: Application, games: list[dict]):
    for raw in games:
        g = parse_game(raw)
        gid = g["id"]
        if not gid:
            continue
        if not g["live"] and not g["finished"]:
            continue

        log.info("بازی %s: %s vs %s | %d-%d | live=%s finished=%s elapsed=%s",
                 gid, g["home"], g["away"], g["hg"], g["ag"],
                 g["live"], g["finished"], g["elapsed"])

        prev = tracked.get(gid)

        if prev is None:
            tracked[gid] = g
            log.info("بازی %s اولین بار دیده شد", gid)
            continue

        if g["hg"] != prev["hg"] or g["ag"] != prev["ag"]:
            log.info("گل! %s %d-%d %s", g["home"], g["hg"], g["ag"], g["away"])
            await broadcast(app, score_line(g["home"], g["away"], g["hg"], g["ag"]))

        if not prev["finished"] and g["finished"]:
            log.info("بازی %s تموم شد", gid)
            await broadcast(app, f"Game is over, final result:\n{score_line(g['home'], g['away'], g['hg'], g['ag'])}")

        tracked[gid] = g


def build_schedule(games: list[dict]) -> str:
    todays = [parse_game(g) for g in games if is_today(g.get("local_date", ""))]

    if not todays:
        return "..."

    lines = ["📅 بازی‌های امروز جام جهانی ۲۰۲۶:\n"]
    for g in todays:
        if g["finished"]:
            lines.append(f"✅ {score_line(g['home'], g['away'], g['hg'], g['ag'])}")
        elif g["live"]:
            lines.append(f"🔴 ({g['elapsed']}'): {score_line(g['home'], g['away'], g['hg'], g['ag'])}")
        else:
            t = g["date"][11:16] if len(g["date"]) > 11 else ""
            lines.append(f"🕐 {t}  {flag(g['home'])} {g['home']} vs {g['away']} {flag(g['away'])}")
    return "\n".join(lines)


async def poll_loop(app: Application):
    while True:
        games = await asyncio.to_thread(get_all_games)
        
        log.info("%d game recieved", len(games))
        if games:
            await process_games(app, games)
            
        await asyncio.sleep(POLL_INTERVAL)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    save_subscribers()

    await update.message.reply_text("""✅ عضو شدی! نتایج زنده جام جهانی ۲۰۲۶ رو برات میفرستم.
                                    @theComputerphile :چنل من

                                    
                                    /stop :برای لغو عضویت""")

    games = await asyncio.to_thread(get_all_games)
    schedule = build_schedule(games)
    await update.message.reply_text(schedule)


async def stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    subscribers.discard(update.effective_chat.id)
    save_subscribers()
    await update.message.reply_text("❌ عضویتت لغو شد.")

async def post_init(app: Application):
    asyncio.create_task(poll_loop(app))


if __name__ == "__main__":
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    log.info("Bot started✅")
    app.run_polling()
