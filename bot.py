from flask import Flask, request
import requests
import time
import threading
from datetime import datetime, timedelta

app = Flask(__name__)

BOT_TOKEN = "8874942259:AAFrl1tjVSHG1RKZ1I9ZV7oJ2gsAfdj8vIVs"
CHANNEL_ID = "@morich_z"
DEFAULT_DELAY_MINUTES = 120
TEMPLATE_TEXT = "⏰ Время вышло! Это задание не активно."

scheduled_tasks = {}

def send_telegram_request(method, params):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        response = requests.post(url, json=params, timeout=30)
        return response.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.route("/", methods=["GET"])
def index():
    return "Бот работает на Render!", 200

# ВОТ ЭТОТ ОБРАБОТЧИК БЫЛ ПРОПУЩЕН — Я ЕГО ДОБАВИЛ
@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    webhook_url = "https://telegram-bot-581e.onrender.com/"
    result = send_telegram_request("setWebhook", {"url": webhook_url})
    if result.get("ok"):
        return f"✅ Webhook установлен! Ответ: {result}", 200
    else:
        return f"❌ Ошибка: {result}", 500

@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return "OK", 200
            
        message = data["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "")
        
        if text == "/start":
            send_telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": "📢 Бот запущен! Отправьте текст для публикации."
            })
            return "OK", 200
            
        if text.startswith("/settime"):
            parts = text.split()
            if len(parts) == 2 and parts[1].isdigit():
                global DEFAULT_DELAY_MINUTES
                DEFAULT_DELAY_MINUTES = int(parts[1])
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"⏱ Задержка: {DEFAULT_DELAY_MINUTES} мин."
                })
            else:
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ Используйте: /settime 15"
                })
            return "OK", 200
            
        if text.startswith("/template"):
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                global TEMPLATE_TEXT
                TEMPLATE_TEXT = parts[1]
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"✅ Шаблон: {TEMPLATE_TEXT}"
                })
            else:
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ Укажите текст"
                })
            return "OK", 200
            
        if text == "/cancel":
            if user_id in scheduled_tasks:
                del scheduled_tasks[user_id]
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": "❌ Задача отменена"
                })
            else:
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": "Нет активных задач"
                })
            return "OK", 200
            
        if not text.startswith("/"):
            result = send_telegram_request("sendMessage", {
                "chat_id": CHANNEL_ID,
                "text": text
            })
            
            if result.get("ok"):
                msg_id = result["result"]["message_id"]
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"✅ Опубликовано! ID: {msg_id}"
                })
                
                if user_id in scheduled_tasks:
                    del scheduled_tasks[user_id]
                
                scheduled_tasks[user_id] = {
                    "chat_id": CHANNEL_ID,
                    "message_id": msg_id,
                    "delay": DEFAULT_DELAY_MINUTES * 60,
                    "text": TEMPLATE_TEXT
                }
                
                def replace_task():
                    task_data = scheduled_tasks.get(user_id)
                    if not task_data:
                        return
                    time.sleep(task_data["delay"])
                    try:
                        send_telegram_request("editMessageText", {
                            "chat_id": task_data["chat_id"],
                            "message_id": task_data["message_id"],
                            "text": task_data["text"]
                        })
                        print(f"✅ Сообщение {task_data['message_id']} заменено")
                    except Exception as e:
                        print(f"Ошибка замены: {e}")
                    finally:
                        if user_id in scheduled_tasks:
                            del scheduled_tasks[user_id]
                
                thread = threading.Thread(target=replace_task)
                thread.daemon = True
                thread.start()
                
                replace_time = datetime.now() + timedelta(minutes=DEFAULT_DELAY_MINUTES)
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"⏳ Замена через {DEFAULT_DELAY_MINUTES} мин.\n⏰ Примерно: {replace_time.strftime('%H:%M:%S')}"
                })
            else:
                send_telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"❌ Ошибка: {result.get('description', 'Неизвестно')}"
                })
        
        return "OK", 200
        
    except Exception as e:
        print(f"Ошибка: {e}")
        return "Error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
