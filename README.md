# ⚽ World Cup 2026 Live Scores & Schedule Telegram Bot

This project is a Python-based Telegram bot that automatically fetches live scores, match schedules, and the status of the FIFA World Cup 2026 using an international API. It broadcasts real-time updates to subscribed users. The bot is fully optimized for a seamless deployment on **Railway**.

---

## ✨ Features
- 🔄 **Auto-Updates:** Automatically monitors match statuses in customizable intervals (every 60 seconds).
- 📅 **Today's Match Schedules:** Displays the complete list of today's matches with precise timing converted to **Iran Time (UTC+3:30)**.
- 🔴 **Live Commentary/Reports:** Displays real-time goals and statuses of ongoing matches (Live).
- 💾 **Persistent Subscriber Database:** Saves subscribed user IDs into a `json` file on a persistent storage disk (Volume) to prevent data loss after server restarts or re-deployments.
- 🌍 **High Stability:** Powered by the reliable `football-data.org` API, bypassing any local hosting restrictions or datacenter IP blocks.

---

## 🛠 Prerequisites

To run this project, you will need:
- Python (version 3.8 or higher)
- A Telegram Bot Token (obtained from [@BotFather](https://t.me/BotFather))
- A Football-Data API Key (obtained from [football-data.org](https://www.football-data.org/))
- python-telegram-bot, requests, python-dotenv libraries

### Required Python Libraries:
```bash
pip install requirements.txt
```
## 🔑 Environment Variables
The project requires two environment variables to function. Create a .env file in the root directory of your project or define these variables in your **Railway** dashboard:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
FOOTBALL_API_KEY=your_football_data_api_key_here
```
## 📦 Deployment & Setup
### 1. Local Execution:
Ensure your environment variables are configured, then run the main script:
```bash
python worldcup_bot.py
```
*Note:* For local execution, the subscriber database will be created in the root directory as subscribers.json.
### 2. Deploying on Railway (with Persistent Volume):
Since Railway containers have ephemeral file systems, follow these steps to prevent your subscriber list from being wiped during updates:
 1. In your Railway project dashboard, click **New** and select **Volume**.
 2. Set the **Mount Path** exactly to /app/data.
 3. Go to your Bot Service settings, and click **Attach Volume** to connect the newly created disk.
 4. Input your TELEGRAM_BOT_TOKEN and FOOTBALL_API_KEY in the service variables section.
 5. Deploy your project.
## 📂 Subscriber Database Structure
The bot intelligently detects its environment to determine where to store data:
 * **On Server (Railway):** /app/data/subscribers.json
 * **On Local System:** ./subscribers.json
## 🔗 Direct Bot Start Link
You can [Click Here](https://t.me/worldcupstatusbot?start=welcome) for testing the robot.

## 🧑🏻‍💻 Creator

Developed with ❤️ by **Amin**
- **Telegram channel:** [@theComputerphile](https://t.me/theComputerphile)

- **GitHub:** [aminbaghaeidev](https://github.com/aminbaghaeidev)

