import asyncio
import json

from flask import Flask
from flask import request, escape
from telethon.sync import TelegramClient

from telegram_utils import migrate_channel_to_supergroup

app = Flask(__name__)
telegram_sessions = []


def initialize_telegram_clients():
    # asyncio.set_event_loop(loop)
    global telegram_sessions
    telegram_sessions = []
    accounts = app.config['ACCOUNTS']
    for account in accounts:
        api_id = account['API_ID']
        api_hash = account['API_HASH']
        phone = account['PHONE']
        print(phone)

        telegram_client = TelegramClient(app.config['SESSION_FOLDER_PATH'] + "/" + phone, api_id, api_hash)
        telegram_client.start()
        if telegram_client.is_user_authorized():
            print('Login success')
            telegram_sessions.append({"phone": phone, "client": telegram_client})
        else:
            print('Login fail due to user not authorized. A code has been sent to ' + phone)
            try:
                telegram_client.send_code_request(phone)
                telegram_client.sign_in(phone, input("Enter the code: "))
            except Exception as e:
                print('Error trying to login with ' + phone)
                print(str(e))
                continue
    return telegram_sessions


def load_config():
    app.config.from_file("config/config.json", load=json.load)


def fahrenheit_from(celsius):
    """Convert Celsius to Fahrenheit degrees."""
    try:
        fahrenheit = float(celsius) * 9 / 5 + 32
        fahrenheit = round(fahrenheit, 3)  # Round to three decimal places
        return str(fahrenheit)
    except ValueError:
        return "invalid input"


@app.route("/migrate-channel")
def migrate_channel():
    channel_title = str(escape(request.args.get("channel_title", "")))
    if channel_title:
        asyncio.set_event_loop(loop)
        initialize_telegram_clients()
        client = telegram_sessions[0]['client']
        migrate_channel_to_supergroup(client, channel_title)
        return "Channel {} has been migrated successfully.".format(channel_title)
    else:
        return "No channel title was specified. Please, add it as a query parameter as ?channel_title=XXX"


@app.route("/")
def index():
    celsius = str(escape(request.args.get("celsius", "")))
    if celsius:
        fahrenheit = fahrenheit_from(celsius)
    else:
        fahrenheit = ""
    return (
            """<form action="" method="get">
                <input type="text" name="celsius">
                <input type="submit" value="Convert">
              </form>"""
            + "Fahrenheit: "
            + fahrenheit
    )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    load_config()
    app.run(host="127.0.0.1", port=8080, debug=True)
