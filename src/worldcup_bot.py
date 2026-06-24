"""
A telegram bot that provides world cup status update.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from constants import FLAGS


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

FOOTBALL_API_KEY = os.getenv("FB_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
POLL_INTERVAL = 60 # 1 minute

if os.path.exists("/app/data"):
    SUBSCRIBERS_FILE = Path("/app/data/subscribers.json")
else:
    SUBSCRIBERS_FILE = Path("subscribers.json")

if os.path.exists("/app/data"):
    TRACKED_FILE = Path("/app/data/tracked.json")
else:
    TRACKED_FILE = Path("tracked.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", encoding="utf-8")],
)
log = logging.getLogger(__name__)

subscribers: set[int] = set(json.loads(SUBSCRIBERS_FILE.read_text())) if SUBSCRIBERS_FILE.exists() else set()

def save_subscribers():
    SUBSCRIBERS_FILE.write_text(json.dumps(list(subscribers)))


def save_tracked():
    TRACKED_FILE.write_text(json.dumps(tracked))

tracked: dict[str, dict] = json.loads(TRACKED_FILE.read_text()) if TRACKED_FILE.exists() else {}


def flag(name: str) -> str:
    return FLAGS.get(name, "🏳️")


def score_line(home: str, away: str, hg: int, ag: int) -> str:
    return f"{flag(home)} {hg} - {ag} {flag(away)}"


# API
def get_all_games() -> list[dict]:
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    url = f"{BASE_URL}/competitions/2000/matches"
    
    for attempt in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            return r.json().get("matches", [])
        except Exception as e:
            log.error("error %d: %s", attempt + 1, e)
            if attempt < 2:
                time.sleep(3)
    return []


def parse_game(g: dict) -> dict:
    status = g.get("status", "")

    score = g.get("score", {})
    full_time = score.get("fullTime")
    if not full_time:
        full_time = score.get("regularTime") or {}

    home = g.get("homeTeam", {}).get("name", "نامشخص")
    away = g.get("awayTeam", {}).get("name", "نامشخص")

    hg = full_time.get("home") if full_time.get("home") is not None else 0
    ag = full_time.get("away") if full_time.get("away") is not None else 0

    live = status in ["IN_PLAY", "PAUSED"]
    finished = status == "FINISHED"
    
    return {
        "id": str(g.get("id", "")),
        "home": home,
        "away": away,
        "hg": hg,
        "ag": ag,
        "finished": finished,
        "live": live,
        "date": g.get("utcDate", ""),
        "elapsed": "Live" if live else status,
    }




def is_today(date_str: str) -> bool:
    if not date_str:
        return False
    try:
        dt_utc = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
        dt_ir = dt_utc + timedelta(hours=3, minutes=30)
    
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        now_ir = now_utc + timedelta(hours=3, minutes=30)
        
        return dt_ir.date() == now_ir.date()
    except ValueError:
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

        if not gid or g["home"] == "نامشخص" or g["away"] == "نامشخص":
            continue
    
        if not is_today(g["date"]):
            continue

        if not g["live"] and not g["finished"]:
            continue

        log.info("بازی %s: %s vs %s | %d-%d | live=%s finished=%s elapsed=%s",
                 gid, g["home"], g["away"], g["hg"], g["ag"],
                 g["live"], g["finished"], g["elapsed"])

        prev = tracked.get(gid)
        
        if prev is None:
            tracked[gid] = g
            save_tracked()
            log.info("بازی %s اولین بار دیده شد", gid)
            if g["live"] and (g["hg"] > 0 or g["ag"] > 0):
                await broadcast(app, f"🔴 The match has started.\n\n{score_line(g['home'], g['away'], g['hg'], g['ag'])}")
            continue

        if g["hg"] != prev["hg"] or g["ag"] != prev["ag"]:
            
            if g["hg"] == 0 and g["ag"] == 0 and (prev["hg"] > 0 or prev["ag"] > 0):
                continue 

            log.info("گل! %s %d-%d %s", g["home"], g["hg"], g["ag"], g["away"])
            await broadcast(app, f"⚽Goal!\n{g['home']} {flag(g['home'])} {g['hg']} - {g['ag']} {flag(g['away'])} {g['away']}")

        if not prev["finished"] and g["finished"]:
            log.info("بازی %s تموم شد", gid)
            await broadcast(app, f"Match is over, final result:\n\n{score_line(g['home'], g['away'], g['hg'], g['ag'])}")

        tracked[gid] = g
        save_tracked()



def build_schedule(games: list[dict]) -> str:
    todays = []
    for g in games:
        if is_today(g.get("utcDate", g.get("date", ""))):
            parsed = parse_game(g)
            if parsed["home"] != "نامشخص" and parsed["away"] != "نامشخص":
                todays.append(parsed)

    if not todays:
        return "بازی‌ای برای امروز ثبت نشده..."

    lines = ["📅 بازی‌های امروز جام جهانی ۲۰۲۶:\n"]
    for g in todays:
        if g["finished"]:
            lines.append(f"✅ {score_line(g['home'], g['away'], g['hg'], g['ag'])}")
        elif g["live"]:
            lines.append(f"🔴 (Live): {score_line(g['home'], g['away'], g['hg'], g['ag'])}")
        else:
            try:
                dt_utc = datetime.strptime(g["date"], "%Y-%m-%dT%H:%M:%SZ")
                dt_ir = dt_utc + timedelta(hours=3, minutes=30)
                t = dt_ir.strftime("%H:%M")
            except:
                t = "??"
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
    username = update.effective_chat.username or "ندارد"
    first_name = update.effective_chat.first_name or ""
    
    subscribers.add(chat_id)
    save_subscribers()
    log.info("کاربر جدید | id: %s | اسم: %s | @%s", chat_id, first_name, username)
    log.info("کاربر جدید /start زد | chat_id: %s | جمع مشترکین: %d", chat_id, len(subscribers))
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
