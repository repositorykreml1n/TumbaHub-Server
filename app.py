from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Твои данные
TELEGRAM_TOKEN = '8693862606:AAEvhj2EJeSxHhaw0JopIb_oK-COEZKix1g'
TELEGRAM_CHAT_ID = '8426928414'

# Очередь команд
commands_queue = {}

@app.route('/')
def home():
    return "TumbaHub Server is running!"

@app.route('/api/log_user', methods=['POST'])
def log_user():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    username = data.get('username', 'Unknown')
    user_id = data.get('userId', 'Unknown')
    
    if username not in commands_queue:
        commands_queue[username] = []

    msg = f"🔥 Новый запуск TumbaHub!\n👤 Ник: {username}\n🆔 ID: {user_id}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

    return jsonify({"status": "success"})

@app.route('/api/get_command', methods=['GET'])
def get_command():
    username = request.args.get('username')
    
    if username in commands_queue and len(commands_queue[username]) > 0:
        cmd = commands_queue[username].pop(0)
        return jsonify({"status": "success", "command": cmd})
    
    return jsonify({"status": "empty"})

@app.route('/api/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    
    if update and "message" in update and "text" in update["message"]:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"]["text"]
        
        if chat_id == TELEGRAM_CHAT_ID:
            parts = text.split(' ')
            if len(parts) >= 2:
                action = parts[0] # Например, /kick
                target_user = parts[1] # Ник игрока
                
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                    
                commands_queue[target_user].append(action)
                
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                              json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ Команда {action} отправлена игроку {target_user}"})
            else:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                              json={"chat_id": TELEGRAM_CHAT_ID, "text": "⚠️ Используй формат: /команда НикИгрока\nПример: /kick Player1"})

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
