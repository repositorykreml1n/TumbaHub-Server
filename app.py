from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Сюда вставь свои данные из Шага 1
TELEGRAM_TOKEN = '8693862606:AAEvhj2EJeSxHhaw0JopIb_oK-COEZKix1g'
TELEGRAM_CHAT_ID = '8426928414'

@app.route('/')
def home():
    return "TumbaHub Server is running!"

# Эндпоинт, на который будет стучаться твой софт из Roblox
@app.route('/api/log_user', methods=['POST'])
def log_user():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    username = data.get('username', 'Unknown')
    user_id = data.get('userId', 'Unknown')
    job_id = data.get('jobId', 'Unknown') # Можно даже JobId сервера передавать

    # Формируем сообщение
    msg = f"🔥 Новый запуск TumbaHub!\n👤 Ник: {username}\n🆔 ID: {user_id}\n🌍 Сервер: {job_id}"
    
    # Отправляем тебе в Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)