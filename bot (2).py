import telebot

TOKEN = "8845489970:AAEMyJIpvqcaUpCK1rYdjea0Uyg3mCMzhTI"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Бот работает! Тест пройден.")

print("✅ Бот запущен и готов к работе!")
bot.polling(non_stop=True)