import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import datetime
import random
import requests
import threading
import os
from flask import Flask

# ========== БЕЗОПАСНО: токен из переменных окружения ==========
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    print("❌ ОШИБКА: Не установлена переменная TELEGRAM_TOKEN")
    exit(1)

# FILE_ID танца (это не секрет, можно оставить в коде)
GIF_FILE_ID = "BQACAgIAAxkBAAMOad51eUa6dcMo2lXWlPSja4nbhYUAAi6eAAJ8DPBKGYw4Hma4qZs7BA"

# API ключ GIPHY (тоже из переменных окружения, опционально)
GIPHY_API_KEY = os.environ.get('GIPHY_API_KEY', '')
# ================================================================

bot = telebot.TeleBot(TOKEN)

# Flask приложение для health check
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

threading.Thread(target=run_flask, daemon=True).start()

# База данных
conn = sqlite3.connect('mood.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS moods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        mood TEXT,
        note TEXT,
        date DATE
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        time TEXT,
        active INTEGER DEFAULT 1
    )
''')
conn.commit()

# Клавиатуры
main_keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
main_keyboard.add(
    KeyboardButton("😊 Настроение"),
    KeyboardButton("📝 Дневник"),
    KeyboardButton("⏰ Напоминание"),
    KeyboardButton("💫 Совет дня"),
    KeyboardButton("🐒 Обезьянка"),
    KeyboardButton("📊 Статистика"),
    KeyboardButton("🎁 Твой танец"),
    KeyboardButton("📜 Цитата дня")
)

moods = ["😊 Отлично", "🙂 Хорошо", "😐 Нормально", "😔 Плохо", "😢 Ужасно"]
mood_keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
for mood in moods:
    mood_keyboard.add(KeyboardButton(mood))
mood_keyboard.add(KeyboardButton("🔙 Назад"))

# ========== ФУНКЦИЯ ДЛЯ ПОИСКА ГИФОК ==========
def search_gif(query, limit=1):
    if not GIPHY_API_KEY:
        return None
    url = "https://api.giphy.com/v1/gifs/search"
    params = {
        "api_key": GIPHY_API_KEY,
        "q": query,
        "limit": limit,
        "rating": "g"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("data"):
            gif_url = random.choice(data["data"])["images"]["original"]["url"]
            return gif_url
        return None
    except:
        return None

def send_animal_gif(chat_id, animal):
    gif_url = search_gif(animal)
    if gif_url:
        try:
            bot.send_animation(chat_id, gif_url, caption=f"🐒 *Вот тебе {animal}!* 🐒", parse_mode="Markdown")
            return True
        except:
            pass
    fallback_messages = [
        f"🐒 *{animal.capitalize()} шлёт тебе улыбку!*",
        f"🐵 *{animal.capitalize()} говорит:* Ты классная!",
        f"🙈 *{animal.capitalize()} кричит:* ТЫ СПРАВИШЬСЯ!"
    ]
    bot.send_message(chat_id, random.choice(fallback_messages), parse_mode="Markdown")

# ========== ЦИТАТЫ ==========
famous_quotes = [
    {"text": "Будь тем изменением, которое хочешь видеть в мире.", "author": "Махатма Ганди"},
    {"text": "Ты никогда не пересечёшь океан, если не решишься потерять берег из виду.", "author": "Христофор Колумб"},
    {"text": "Единственный способ делать великую работу — любить то, что ты делаешь.", "author": "Стив Джобс"},
    {"text": "Не ждите. Время никогда не будет идеальным.", "author": "Наполеон Хилл"},
    {"text": "Ты можешь быть ранен, но не сломлен.", "author": "Нельсон Мандела"},
    {"text": "Счастье не в том, чтобы делать всегда, что хочешь, а в том, чтобы всегда хотеть того, что делаешь.", "author": "Лев Толстой"},
    {"text": "Не сравнивай себя с другими. Это оскорбление самому себе.", "author": "Альберт Эйнштейн"},
    {"text": "Твоё время ограничено, не трать его на чужую жизнь.", "author": "Стив Джобс"},
]

# ========== СОВЕТЫ ==========
tips = {
    "😊 Отлично": ["✨ Ты сегодня на пике!", "💪 Поделись позитивом!"],
    "🙂 Хорошо": ["🌸 Хороший день — фундамент!", "📖 Запиши, что было хорошим!"],
    "😐 Нормально": ["🌿 Нормально — это тоже хорошо!", "🎯 Поставь маленькую цель!"],
    "😔 Плохо": ["☁️ Плохие дни проходят!", "💜 Позволь себе отдохнуть!"],
    "😢 Ужасно": ["🫂 Обними себя. Ты справишься!", "🌟 Напомни себе о хорошем!"]
}

def send_gif(chat_id, caption=None):
    try:
        bot.send_animation(chat_id, GIF_FILE_ID, caption=caption, parse_mode="Markdown")
    except:
        bot.send_message(chat_id, caption if caption else "💃", parse_mode="Markdown")

def get_mood_emoji(mood):
    emojis = {"😊 Отлично": "✨", "🙂 Хорошо": "🌸", "😐 Нормально": "🌿", "😔 Плохо": "☁️", "😢 Ужасно": "🌧️"}
    return emojis.get(mood, "⭐")

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.first_name
    send_gif(message.chat.id, f"✨ *Привет, {user_name}!* ✨")
    
    congratulation = (
        f"🎉 *{user_name}, поздравляю!* 🎉\n\n"
        f"Поздравляю с прохождением 26-го уровня симуляции!\n\n"
        f"В награду выдаю тебе бесконечный заряд пофигизма и портальную пушку в сторону счастья.\n\n"
        f"Желаю, чтобы драмы растворялись кислотой, а приключения были эпичнее, "
        f"чем попытка приготовить ужин из инопланетных щупалец. 🛸🍝"
    )
    bot.send_message(message.chat.id, congratulation, parse_mode="Markdown")
    
    send_gif(message.chat.id, "💃 *А это — твой танец!* ✨")
    
    welcome = (
        "💡 *А теперь — знакомство с ботом*\n\n"
        "😊 *Настроение* — запиши, как ты себя чувствуешь\n"
        "📝 *Дневник* — добавь заметку\n"
        "🐒 *Обезьянка* — поднимет настроение\n"
        "📜 *Цитата дня* — мудрость великих\n"
        "📊 *Статистика* — график настроения\n"
        "🎁 *Твой танец* — напоминание о силе\n\n"
        "👇 *Начни с выбора настроения!*"
    )
    bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=main_keyboard)

@bot.message_handler(func=lambda message: message.text == "🔙 Назад")
def back_to_main(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=main_keyboard)

@bot.message_handler(func=lambda message: message.text == "😊 Настроение")
def ask_mood(message):
    bot.send_message(message.chat.id, "Как ты себя чувствуешь?", reply_markup=mood_keyboard)

@bot.message_handler(func=lambda message: message.text in moods)
def save_mood(message):
    mood = message.text
    user_id = message.from_user.id
    today = datetime.date.today()
    
    cursor.execute("SELECT id FROM moods WHERE user_id=? AND date=?", (user_id, today))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("UPDATE moods SET mood=? WHERE user_id=? AND date=?", (mood, user_id, today))
        msg = "Обновила твоё настроение 💜"
    else:
        cursor.execute("INSERT INTO moods (user_id, mood, date) VALUES (?, ?, ?)", (user_id, mood, today))
        msg = "Запомнила твоё настроение 💜"
    
    conn.commit()
    tip = random.choice(tips.get(mood, ["Ты прекрасна!"]))
    bot.send_message(message.chat.id, f"{msg}\n\n{tip}", reply_markup=main_keyboard)
    
    if mood in ["😔 Плохо", "😢 Ужасно"]:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("💃 Хочу танец!", callback_data="dance"),
            InlineKeyboardButton("🐒 Хочу обезьянку!", callback_data="monkey")
        )
        bot.send_message(message.chat.id, "Хочешь поднять настроение?", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "📝 Дневник")
def ask_for_note(message):
    msg = bot.send_message(message.chat.id, "✏️ Напиши свои мысли:")
    bot.register_next_step_handler(msg, save_note)

def save_note(message):
    note = message.text
    user_id = message.from_user.id
    today = datetime.date.today()
    
    cursor.execute("UPDATE moods SET note=? WHERE user_id=? AND date=?", (note, user_id, today))
    if cursor.rowcount == 0:
        cursor.execute("INSERT INTO moods (user_id, note, date) VALUES (?, ?, ?)", (user_id, note, today))
    conn.commit()
    bot.send_message(message.chat.id, "📝 Заметка сохранена!", reply_markup=main_keyboard)

@bot.message_handler(func=lambda message: message.text == "💫 Совет дня")
def daily_tip(message):
    quote = random.choice(famous_quotes)
    tip_text = f"📜 *Мудрость дня*\n\n«{quote['text']}»\n\n— *{quote['author']}*"
    bot.send_message(message.chat.id, tip_text, parse_mode="Markdown", reply_markup=main_keyboard)

@bot.message_handler(func=lambda message: message.text == "📜 Цитата дня")
def random_quote(message):
    quote = random.choice(famous_quotes)
    quote_text = f"📜 *«{quote['text']}»*\n\n— *{quote['author']}*"
    bot.send_message(message.chat.id, quote_text, parse_mode="Markdown", reply_markup=main_keyboard)

@bot.message_handler(func=lambda message: message.text == "🐒 Обезьянка")
def send_monkey(message):
    send_animal_gif(message.chat.id, "обезьянка")

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_stats(message):
    user_id = message.from_user.id
    cursor.execute(
        "SELECT mood, COUNT(*) FROM moods WHERE user_id=? AND date >= date('now', '-30 days') GROUP BY mood",
        (user_id,)
    )
    data = cursor.fetchall()
    
    if not data:
        bot.send_message(message.chat.id, "📭 Пока нет статистики.", reply_markup=main_keyboard)
        return
    
    stats_text = "📊 *Твоё настроение за 30 дней:*\n\n"
    total = 0
    for mood, count in data:
        emoji = get_mood_emoji(mood)
        stats_text += f"{mood} {emoji} ×{count}\n"
        total += count
    stats_text += f"\n📈 *Всего записей:* {total}"
    bot.send_message(message.chat.id, stats_text, parse_mode="Markdown", reply_markup=main_keyboard)

@bot.message_handler(func=lambda message: message.text == "🎁 Твой танец")
def send_dance(message):
    send_gif(message.chat.id, "💃 *Ты — яркая, живая, настоящая!* ✨")

@bot.callback_query_handler(func=lambda call: call.data == "dance")
def dance_callback(call):
    send_gif(call.message.chat.id, "💃 Твой танец ждёт тебя!")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "monkey")
def monkey_callback(call):
    send_animal_gif(call.message.chat.id, "обезьянка")
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("✨ Бот запущен на Render!")
    print(f"🤖 Токен: {'✅ загружен' if TOKEN else '❌ отсутствует'}")
    print(f"🐒 GIPHY API: {'✅' if GIPHY_API_KEY else '❌ (только текст)'}")
    bot.infinity_polling()