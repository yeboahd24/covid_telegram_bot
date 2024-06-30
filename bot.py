import logging
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from graph import create_bar_chart, create_pie_chart
import matplotlib.pyplot as plt
import pandas as pd
import io
import sqlite3
from datetime import time
import pytz


# Initialize database
class DatabaseManager:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS subscribers
                             (user_id INTEGER PRIMARY KEY)""")
        self.conn.commit()

    def add_subscriber(self, user_id):
        self.cursor.execute("INSERT OR IGNORE INTO subscribers VALUES (?)", (user_id,))
        self.conn.commit()

    def remove_subscriber(self, user_id):
        self.cursor.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_subscribers(self):
        self.cursor.execute("SELECT user_id FROM subscribers")
        return [row[0] for row in self.cursor.fetchall()]


# Fetch data
class DataFetcher:
    def __init__(self):
        self.session = requests.Session()

    def fetch_covid_data(self):
        url = "https://disease.sh/v3/covid-19/all"
        response = self.session.get(url)
        return response.json()


# Bot commands
class BotCommands:
    def __init__(self, db_manager, data_fetcher):
        self.db_manager = db_manager
        self.data_fetcher = data_fetcher

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Welcome to the COVID-19 Info Bot! Use /help to see available commands."
        )

    async def help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        help_text = """
        Available commands:
        /world - Get worldwide COVID-19 statistics with a pie chart
        /today - Get summary of daily new cases
        /[country] - Get statistics for a specific country with a bar chart (e.g., /usa, /india)
        /history [country] [days] - Get historical data chart (default: worldwide, 30 days)
        /subscribe - Subscribe to daily updates
        /unsubscribe - Unsubscribe from daily updates
        """
        await update.message.reply_text(help_text)

    async def world(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        data = self.data_fetcher.fetch_covid_data()

        message = f"Worldwide COVID-19 Statistics:\nTotal Cases: {data['cases']:,}\nTotal Deaths: {data['deaths']:,}\nTotal Recovered: {data['recovered']:,}"
        await update.message.reply_text(message)

        # Create and send a pie chart
        chart_data = {
            "Active": data["active"],
            "Recovered": data["recovered"],
            "Deaths": data["deaths"],
        }
        chart = create_pie_chart(chart_data, "Worldwide COVID-19 Cases Distribution")
        await update.message.reply_photo(chart)

    async def country(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        country_name = update.message.text[1:].lower()
        url = f"https://disease.sh/v3/covid-19/countries/{country_name}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            message = f"COVID-19 Statistics for {data['country']}:\nTotal Cases: {data['cases']:,}\nTotal Deaths: {data['deaths']:,}\nTotal Recovered: {data['recovered']:,}"
            await update.message.reply_text(message)

            # Create and send a bar chart
            chart_data = {
                "Total Cases": data["cases"],
                "Active Cases": data["active"],
                "Recovered": data["recovered"],
                "Deaths": data["deaths"],
            }
            chart = create_bar_chart(
                chart_data, f'COVID-19 Statistics for {data["country"]}'
            )
            await update.message.reply_photo(chart)
        else:
            await update.message.reply_text("Country not found or data unavailable.")

    async def today(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        data = self.data_fetcher.fetch_covid_data()

        message = f"Today's COVID-19 Statistics:\nNew Cases: {data['todayCases']:,}\nNew Deaths: {data['todayDeaths']:,}\nNew Recovered: {data['todayRecovered']:,}"
        await update.message.reply_text(message)

    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        country_name = context.args[0] if context.args else "all"
        days = int(context.args[1]) if len(context.args) > 1 else 30

        url = (
            f"https://disease.sh/v3/covid-19/historical/{country_name}?lastdays={days}"
        )
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            if country_name == "all":
                cases = data["cases"]
                deaths = data["deaths"]
                recovered = data["recovered"]
            else:
                cases = data["timeline"]["cases"]
                deaths = data["timeline"]["deaths"]
                recovered = data["timeline"]["recovered"]

            df = pd.DataFrame(
                {"Cases": cases, "Deaths": deaths, "Recovered": recovered}
            )

            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df["Cases"], label="Cases")
            plt.plot(df.index, df["Deaths"], label="Deaths")
            plt.plot(df.index, df["Recovered"], label="Recovered")
            plt.title(f"COVID-19 History for {country_name.capitalize()}")
            plt.xlabel("Date")
            plt.ylabel("Count")
            plt.legend()
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            plt.close()

            await update.message.reply_photo(buf)
        else:
            await update.message.reply_text("Data not available or country not found.")

        # Function to add a subscriber

    def add_subscriber(self, user_id):
        conn = sqlite3.connect("subscribers.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO subscribers VALUES (?)", (user_id,))
        conn.commit()
        conn.close()

    # Function to remove a subscriber
    def remove_subscriber(self, user_id):
        conn = sqlite3.connect("subscribers.db")
        c = conn.cursor()
        c.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    # Function to get all subscribers
    def get_subscribers(self):
        conn = sqlite3.connect("subscribers.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM subscribers")
        subscribers = [row[0] for row in c.fetchall()]
        conn.close()
        return subscribers

    # Modify the subscribe function
    async def subscribe(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user_id = update.effective_user.id
        self.add_subscriber(user_id)
        await update.message.reply_text("You've been subscribed to daily updates!")

    # Modify the unsubscribe function
    async def unsubscribe(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        user_id = update.effective_user.id
        self.remove_subscriber(user_id)
        await update.message.reply_text("You've been unsubscribed from daily updates.")

    async def send_daily_update(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        data = self.data_fetcher.fetch_covid_data()
        message = f"Daily COVID-19 Update:\nNew Cases: {data['todayCases']:,}\nNew Deaths: {data['todayDeaths']:,}\nNew Recovered: {data['todayRecovered']:,}"

        subscribers = self.db_manager.get_subscribers()
        for user_id in subscribers:
            try:
                await context.bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                logging.error(f"Failed to send update to user {user_id}: {e}")
                print(f"Failed to send update to user {user_id}: {e}")



# Main function
def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    TOKEN = os.getenv("BOT_TOKEN")

    db_manager = DatabaseManager("subscribers.db")
    data_fetcher = DataFetcher()
    bot_commands = BotCommands(db_manager, data_fetcher)

    application = Application.builder().token(TOKEN).build()

    application.job_queue.run_daily(
        bot_commands.send_daily_update, time=time(hour=8, minute=0, tzinfo=pytz.UTC)
    )

    application.add_handler(CommandHandler("start", bot_commands.start))
    application.add_handler(CommandHandler("help", bot_commands.help))
    application.add_handler(CommandHandler("subscribe", bot_commands.subscribe))
    application.add_handler(CommandHandler("unsubscribe", bot_commands.unsubscribe))
    application.add_handler(CommandHandler("history", bot_commands.history))
    application.add_handler(CommandHandler("country", bot_commands.country))
    application.add_handler(CommandHandler("today", bot_commands.today))
    application.add_handler(CommandHandler("world", bot_commands.world))
    application.run_polling()


if __name__ == "__main__":
    main()
