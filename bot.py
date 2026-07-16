import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
from datetime import datetime, timedelta
import os

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "8845489970:AAEMyJIpvqcaUpCK1rYdjea0Uyg3mCMzhTI"
ADMIN_ID = 8591759620
ADDRESS = "г. Минусинск, ул. Кызыльская 8а"
# =======================

bot = telebot.TeleBot(TOKEN)
user_data = {}

# ===== ХРАНИЛИЩЕ В ПАМЯТИ =====
bookings = []
users = []

def add_user(user_id):
    if user_id not in users:
        users.append(user_id)

def is_slot_available(date, time):
    for b in bookings:
        if b["date"] == date and b["time"] == time:
            return False
    return True

def has_user_booking_today(user_id, date):
    for b in bookings:
        if b.get('user_id') == user_id and b['date'] == date:
            return True
    return False

def add_booking(name, people, phone, date, time, user_id):
    bookings.append({
        "name": name,
        "people": people,
        "phone": phone,
        "date": date,
        "time": time,
        "user_id": user_id
    })

def get_available_dates(days_ahead=4):
    dates = []
    today = datetime.now()
    for i in range(days_ahead):
        date = today + timedelta(days=i)
        date_str = date.strftime("%d.%m (%a)")
        dates.append(date_str)
    return dates

def is_valid_phone(phone):
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    if cleaned.startswith('8'):
        cleaned = '+7' + cleaned[1:]
    elif cleaned.startswith('7'):
        cleaned = '+' + cleaned
    elif not cleaned.startswith('+') and cleaned.startswith('9'):
        cleaned = '+7' + cleaned
    elif not cleaned.startswith('+'):
        return False
    if cleaned.startswith('+7'):
        rest = cleaned[2:]
        if len(rest) == 10 and rest.isdigit():
            if rest.startswith('9'):
                return True
    return False

def get_all_slots(date):
    all_times = ["12:00", "15:00", "18:00", "21:00"]
    slots = {}
    for t in all_times:
        occupied = False
        for b in bookings:
            if b["date"] == date and b["time"] == t:
                occupied = True
                break
        slots[t] = occupied
    return slots

# ===== КОМАНДЫ =====
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "📖 **ИНСТРУКЦИЯ ПО КОМАНДАМ:**\n\n"
        "🔹 `/start` — начать запись на квест\n"
        "🔹 `/cancel` — отменить свою запись\n"
        "🔹 `/help` — показать эту инструкцию\n\n"
        "👻 *Остальные команды доступны только администратору.*"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    add_user(user_id)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔮 Начать запись", callback_data="book"))
    bot.send_message(
        message.chat.id,
        "👻 Добро пожаловать в квест!\nНажми кнопку, чтобы записаться.\n\n"
        "📖 Если нужна помощь — напиши /help",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "book")
def ask_name(call):
    bot.send_message(call.message.chat.id, "Введи своё имя:")
    bot.register_next_step_handler(call.message, ask_people)

def ask_people(message):
    user_id = message.chat.id
    user_data[user_id] = {'name': message.text}
    bot.send_message(user_id, "Сколько вас человек? (1-10):")
    bot.register_next_step_handler(message, ask_phone)

def ask_phone(message):
    user_id = message.chat.id
    try:
        people = int(message.text)
        if people < 1 or people > 10:
            bot.send_message(user_id, "❌ Введи число от 1 до 10.")
            bot.register_next_step_handler(message, ask_phone)
            return
    except:
        bot.send_message(user_id, "❌ Это не число. Попробуй ещё раз.")
        bot.register_next_step_handler(message, ask_phone)
        return
    user_data[user_id]['people'] = people
    bot.send_message(user_id, "📱 Введи номер телефона (пример: +7 999 123 45 67):")
    bot.register_next_step_handler(message, ask_date)

def ask_date(message):
    user_id = message.chat.id
    phone = message.text.strip()
    if not is_valid_phone(phone):
        bot.send_message(user_id, "❌ Номер похож на телефон? Введи ещё раз.")
        bot.register_next_step_handler(message, ask_date)
        return
    user_data[user_id]['phone'] = phone
    available_dates = get_available_dates(days_ahead=4)
    markup = InlineKeyboardMarkup()
    for date_str in available_dates:
        markup.add(InlineKeyboardButton(f"📅 {date_str}", callback_data=f"date_{date_str}"))
    bot.send_message(user_id, "Выбери дату:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("date_"))
def ask_time(call):
    user_id = call.message.chat.id
    date = call.data.split("_")[1]
    user_data[user_id]['date'] = date
    if has_user_booking_today(user_id, date):
        bot.send_message(user_id, "⚠️ Ты уже записан на этот день.")
        return
    all_times = ["12:00", "15:00", "18:00", "21:00"]
    available_times = []
    for t in all_times:
        if is_slot_available(date, t):
            available_times.append(t)
    if not available_times:
        bot.send_message(user_id, "😔 На этот день все слоты заняты.")
        return
    markup = InlineKeyboardMarkup()
    for t in available_times:
        markup.add(InlineKeyboardButton(f"🕐 {t}", callback_data=f"time_{t}"))
    bot.send_message(user_id, "Выбери свободное время:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))
def finish(call):
    user_id = call.message.chat.id
    time = call.data.split("_")[1]
    date = user_data[user_id]['date']
    if not is_slot_available(date, time):
        bot.send_message(user_id, "⚠️ Это время уже занято.")
        return
    if has_user_booking_today(user_id, date):
        bot.send_message(user_id, "⚠️ Ты уже записан на этот день.")
        return
    name = user_data[user_id]['name']
    people = user_data[user_id]['people']
    phone = user_data[user_id]['phone']
    add_booking(name, people, phone, date, time, user_id)
    bot.send_message(
        ADMIN_ID,
        f"🆕 НОВАЯ ЗАПИСЬ!\n\n"
        f"👤 Имя: {name}\n"
        f"👥 Человек: {people}\n"
        f"📱 Телефон: {phone}\n"
        f"📅 Дата: {date}\n"
        f"🕐 Время: {time}"
    )
    bot.send_message(
        user_id,
        f"✅ ТЫ ЗАПИСАН НА КВЕСТ!\n\n"
        f"👤 Имя: {name}\n"
        f"👥 Человек: {people}\n"
        f"📱 Телефон: {phone}\n"
        f"📅 Дата: {date}\n"
        f"🕐 Время: {time}\n\n"
        f"📍 {ADDRESS}\n"
        f"⚠️ Приходи за 15 минут до начала.\n\n"
        f"Приготовься... Мы тебя уже ждём... 👻"
    )

@bot.message_handler(commands=['cancel'])
def cancel_booking(message):
    user_id = message.chat.id
    user_bookings = [b for b in bookings if b.get('user_id') == user_id]
    if not user_bookings:
        bot.send_message(user_id, "📭 У тебя нет активных записей.")
        return
    text = "Твои записи:\n\n"
    for i, b in enumerate(user_bookings, 1):
        text += f"{i}. {b['date']} в {b['time']} ({b['people']} чел.)\n"
    text += "\nВведи номер записи для отмены:"
    bot.send_message(user_id, text)
    bot.register_next_step_handler(message, process_cancel, user_bookings)

def process_cancel(message, user_bookings):
    user_id = message.chat.id
    try:
        num = int(message.text.strip())
        if num < 1 or num > len(user_bookings):
            bot.send_message(user_id, "❌ Введи номер из списка.")
            bot.register_next_step_handler(message, process_cancel, user_bookings)
            return
    except ValueError:
        bot.send_message(user_id, "❌ Введи число.")
        bot.register_next_step_handler(message, process_cancel, user_bookings)
        return
    global bookings
    booking_to_remove = user_bookings[num - 1]
    bookings = [b for b in bookings if not (b['date'] == booking_to_remove['date'] and b['time'] == booking_to_remove['time'] and b.get('user_id') == user_id)]
    bot.send_message(user_id, f"✅ Запись на {booking_to_remove['date']} в {booking_to_remove['time']} отменена.")

@bot.message_handler(commands=['slots'])
def show_slots(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ У тебя нет доступа.")
        return
    available_dates = get_available_dates(days_ahead=4)
    markup = InlineKeyboardMarkup()
    for date_str in available_dates:
        markup.add(InlineKeyboardButton(f"📅 {date_str}", callback_data=f"slots_{date_str}"))
    bot.send_message(message.chat.id, "Выбери дату:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("slots_"))
def show_slots_detail(call):
    if call.message.chat.id != ADMIN_ID:
        bot.send_message(call.message.chat.id, "⛔ У тебя нет доступа.")
        return
    date = call.data.split("_")[1]
    slots = get_all_slots(date)
    text = f"📋 РАСПИСАНИЕ НА {date}:\n\n"
    for time, occupied in slots.items():
        status = "🔴 ЗАНЯТО" if occupied else "🟢 СВОБОДНО"
        text += f"{time} — {status}\n"
    bot.send_message(call.message.chat.id, text)

@bot.message_handler(commands=['bookings'])
def show_bookings(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ У тебя нет доступа.")
        return
    if not bookings:
        bot.send_message(message.chat.id, "📭 Пока нет записей.")
        return
    text = "📋 СПИСОК ЗАПИСЕЙ:\n\n"
    for i, b in enumerate(bookings, 1):
        people = b.get('people', '?')
        phone = b.get('phone', 'не указан')
        text += f"{i}. {b['name']} ({people} чел.) — {b['date']} в {b['time']}\n"
        text += f"   📱 {phone}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['broadcast'])
def broadcast_start(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ У тебя нет доступа.")
        return
    bot.send_message(message.chat.id, "📨 Введи текст для рассылки:")
    bot.register_next_step_handler(message, process_broadcast)

def process_broadcast(message):
    if message.chat.id != ADMIN_ID:
        return
    text = message.text
    if not users:
        bot.send_message(ADMIN_ID, "📭 Нет пользователей.")
        return
    bot.send_message(ADMIN_ID, f"📤 Рассылка для {len(users)} пользователей...")
    success = 0
    for user_id in users:
        try:
            bot.send_message(user_id, f"📢 СООБЩЕНИЕ ОТ КВЕСТА:\n\n{text}")
            success += 1
        except:
            pass
    bot.send_message(ADMIN_ID, f"✅ Отправлено {success} из {len(users)}.")

@bot.message_handler(commands=['clear'])
def clear_bookings(message):
    if message.chat.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ У тебя нет доступа.")
        return
    global bookings
    bookings = []
    bot.send_message(message.chat.id, "🗑️ Все записи удалены.")

print("✅ Бот запущен и готов к работе!")
bot.polling(non_stop=True)