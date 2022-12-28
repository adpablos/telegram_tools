from flask import Flask
from flask import request, escape
import json
from telethon.sync import TelegramClient
import asyncio

app = Flask(__name__)

clients = []

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


@app.route("/get_me", methods=['GET'])
def get_me():
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    with open('config/config.json', 'r', encoding='utf-8') as f:
        config = json.loads(f.read())
    accounts = config['accounts']
    api_id = accounts[0]['api_id']
    api_hash = accounts[0]['api_hash']
    phone = accounts[0]['phone']
    print(phone)
    telegram_client = TelegramClient(config['session_folder_path'] + "/" + phone, api_id, api_hash, loop=loop)
    telegram_client.start()
    return {"MyTelegramAccount started": telegram_client}


def fahrenheit_from(celsius):
    """Convert Celsius to Fahrenheit degrees."""
    try:
        fahrenheit = float(celsius) * 9 / 5 + 32
        fahrenheit = round(fahrenheit, 3)  # Round to three decimal places
        return str(fahrenheit)
    except ValueError:
        return "invalid input"


def generate_session(configuration):
    sessions = []
    accounts = configuration['accounts']
    for account in accounts:
        api_id = account['api_id']
        api_hash = account['api_hash']
        phone = account['phone']
        print(phone)

        telegram_client = TelegramClient(configuration['session_folder_path'] + "/" + phone, api_id, api_hash)
        telegram_client.start()
        if telegram_client.is_user_authorized():
            print('Login success')
            sessions.append({"phone": phone, "client": telegram_client})
        else:
            print('Login fail due to user not authorized. A code has been sent to ' + phone)
            try:
                telegram_client.send_code_request(phone)
                telegram_client.sign_in(phone, input("Enter the code: "))
            except Exception as e:
                print('Error trying to login with ' + phone)
                print(str(e))
                continue
    return sessions


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
