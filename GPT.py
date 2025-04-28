import logging
import os
import uuid
import json
import requests
import threading
from flask import Flask, request
from serpapi import GoogleSearch
import telebot

# === CONFIG ===
# SerpAPI
SERPAPI_API_KEY = '6d0a7a50c12a63f7340b7986b2b10eaad1bd5af1833348893a94bb73294cd7d5'

# Telegram
TELEGRAM_TOKEN = "7592947166:AAF3bK6pjHLZsIWRQ7kOZ-dy68L6Jx9zLfM"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Facebook
VERIFY_TOKEN = "EAATikPMEVT0BOygB7fEPdgiaAxcbPwus5EJi5zrneeUdFFJlURZAkhY4IiBCxxBQXzTjGdji62c9FtPTfDwK7JREgU6sqra8SAnxnqdbRR2LEoe8foU4wsiqPocjaVakAZAW4bzQCNy9xrDGAjR2BVgH88aVdZCuHsRjjh6HJuCxACN4YIgw4luWHBHCtZA1DQdncA8dQ0FxzBOuvpg5Gz44pSzjnE4Tvuiedgpn8M9ZAZAelSJRQORynZCaa6IMFWVFh0BarUgowZDZD"  # <-- inserisci il tuo verify token qui
PAGE_ACCESS_TOKEN = "1375012087158077"  # <-- inserisci il tuo page access token qui

# === SERPAPI FUNCTION ===
def search_google(query):
    client = GoogleSearch({
        "api_key": SERPAPI_API_KEY,
        "engine": "google",
        "q": query,
    })
    result = client.get_dict()
    return result

# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=['search'])
def handle_telegram_search(message):
    query = message.text.replace('/search', '').strip()
    if not query:
        bot.reply_to(message, "Please provide a search query.")
        return

    results = search_google(query)
    if 'organic_results' in results:
        reply = ""
        for result in results['organic_results'][:3]:
            reply += f"{result.get('title')}\n{result.get('link')}\n\n"
    else:
        reply = "No results found."

    bot.send_message(message.chat.id, reply)

@bot.message_handler(func=lambda message: True)
def handle_telegram_echo(message):
    user_msg = message.text
    reply = f"GPT: {user_msg}"
    bot.send_message(message.chat.id, reply)

# === FACEBOOK FUNCTIONS ===
app = Flask(__name__)

def send_fb_message(recipient_id, message_text):
    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    })
    response = requests.post('https://graph.facebook.com/v12.0/me/messages', params=params, headers=headers, data=data)
    return response.json()

@app.route('/', methods=['GET'])
def verify():
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge')
    return 'Verification token mismatch', 403

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    for entry in data.get('entry', []):
        messaging = entry.get('messaging', [])
        for message_event in messaging:
            sender_id = message_event['sender']['id']
            if 'message' in message_event and 'text' in message_event['message']:
                text = message_event['message']['text']

                if text.startswith('/search'):
                    query = text.replace('/search', '').strip()
                    if query:
                        results = search_google(query)
                        if 'organic_results' in results:
                            reply = ""
                            for result in results['organic_results'][:3]:
                                reply += f"{result.get('title')}\n{result.get('link')}\n\n"
                        else:
                            reply = "No results found."
                    else:
                        reply = "Please provide a search query."
                    send_fb_message(sender_id, reply)
                else:
                    reply = f"GPT: {text}"
                    send_fb_message(sender_id, reply)
    return "ok", 200

# === THREADS ===
def start_telegram_bot():
    logging.info("Starting Telegram bot...")
    bot.infinity_polling()

def start_flask_server():
    logging.info("Starting Flask server...")
    # debug=False perché siamo in thread secondario
    app.run(host="0.0.0.0", port=5000, debug=False)

# === MAIN ===
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Avvia Telegram bot in un thread
    telegram_thread = threading.Thread(target=start_telegram_bot)
    telegram_thread.start()

    # Avvia Flask server nel thread principale
    start_flask_server()

