import telebot
import json
from telebot.handler_backends import State, StatesGroup
from telebot.custom_filters import StateFilter
from db import init_db, save_ticket, get_open_tickets
from config import BOT_TOKEN, ADMIN_IDS, MAIN_MENU

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Определение состояний (для отслеживания диалога)
class TicketStates(StatesGroup):
    waiting_for_sales_description = State()
    waiting_for_tech_description = State()

# Загрузка FAQ с обработкой ошибок
try:
    with open('faq.json', 'r', encoding='utf-8') as f:
        FAQ = json.load(f)
except FileNotFoundError:
    print("Файл faq.json не найден! Создаю пустой словарь.")
    FAQ = {}
except json.JSONDecodeError as e:
    print(f"Ошибка чтения faq.json: {e}")
    FAQ = {}

# Регистрация кастомных фильтров
bot.add_custom_filter(StateFilter(bot))

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False
    )
    for row in MAIN_MENU:
        markup.row(*row)
    bot.send_message(
        message.chat.id,
        "Здравствуйте! Я бот техподдержки магазина «Продаём всё на свете».\n"
        "Выберите действие:",
        reply_markup=markup
    )

# Раздел FAQ
@bot.message_handler(func=lambda m: m.text == "Часто задаваемые вопросы")
def faq(message):
    if not FAQ:
        bot.send_message(message.chat.id, "База знаний пока пуста.")
        return

    response = "Часто задаваемые вопросы:\n\n"
    for question in FAQ.keys():
        response += f"• {question}\n"
    response += "\nНапишите интересующий вопрос полностью."
    bot.send_message(message.chat.id, response)

@bot.message_handler(func=lambda m: m.text in FAQ)
def answer_faq(message):
    bot.send_message(
        message.chat.id,
        f"Ответ:\n{FAQ[message.text]}",
        parse_mode='Markdown'
    )

# Сообщение о проблеме
@bot.message_handler(func=lambda m: m.text == "Сообщить о проблеме")
def report_problem(message):
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )
    markup.row("Отдел продаж", "Техническая поддержка")
    bot.send_message(
        message.chat.id,
        "Куда направить запрос?",
        reply_markup=markup
    )

# Направление в отдел продаж
@bot.message_handler(func=lambda m: m.text == "Отдел продаж")
def sales_problem(message):
    bot.send_message(
        message.chat.id,
        "Напишите ваш вопрос или проблему. Мы передадим его в отдел продаж."
    )
    bot.set_state(message.from_user.id, TicketStates.waiting_for_sales_description, message.chat.id)

# Направление в тех. поддержку
@bot.message_handler(func=lambda m: m.text == "Техническая поддержка")
def tech_problem(message):
    bot.send_message(
        message.chat.id,
        "Опишите техническую проблему. Мы передадим её программистам."
    )
    bot.set_state(message.from_user.id, TicketStates.waiting_for_tech_description, message.chat.id)

# Обработка описания проблемы для отдела продаж
@bot.message_handler(state=TicketStates.waiting_for_sales_description)
def save_sales_ticket(message):
    try:
        username = message.from_user.username or "нет_ника"
        full_name = message.from_user.first_name or "не указано"

        ticket_id = save_ticket(
            message.from_user.id,
            username,
            full_name,
            'sales',
            message.text
        )

        bot.send_message(
            message.chat.id,
            f"Ваше обращение №{ticket_id} передано в отдел продаж.\n"
            "Мы ответим в ближайшее время.",
            parse_mode='Markdown'
        )
        bot.delete_state(message.from_user.id, message.chat.id)
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Произошла ошибка при сохранении обращения: {str(e)}",
            parse_mode='Markdown'
        )

# Обработка описания технической проблемы
@bot.message_handler(state=TicketStates.waiting_for_tech_description)
def save_tech_ticket(message):
    try:
        username = message.from_user.username or "нет_ника"
        full_name = message.from_user.first_name or "не указано"

        ticket_id = save_ticket(
            message.from_user.id,
            username,
            full_name,
            'tech',
            message.text
        )

        bot.send_message(
            message.chat.id,
            f"Ваше обращение №{ticket_id} передано программистам.\n"
            "Мы исправим проблему в ближайшее время.",
            parse_mode='Markdown'
        )
        bot.delete_state(message.from_user.id, message.chat.id)
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Произошла ошибка при сохранении обращения: {str(e)}",
            parse_mode='Markdown'
        )

# Админ-команда для просмотра обращений
@bot.message_handler(
    func=lambda m: m.from_user.id in ADMIN_IDS and m.text.startswith('/tickets')
)
def admin_tickets(message):
    parts = message.text.split()
    category = parts[1].lower() if len(parts) > 1 else None

    # Валидация категории
    if category and category not in ['sales', 'tech']:
        bot.send_message(
            message.chat.id,
            "Допустимые категории: sales, tech",
            parse_mode='Markdown'
        )
        return

    tickets = get_open_tickets(category)

    if not tickets:
        bot.send_message(
            message.chat.id,
            "Нет открытых обращений.",
            parse_mode='Markdown'
        )
        return

    text = "Открытые обращения:\n\n"
    for tid, uid, msg in tickets:
        text += f'{tid} от пользователя {uid}:\n{msg}\n\n'

    bot.send_message(
        message.chat.id,
        text,
        parse_mode='Markdown'
    )

# Хэндлер для неизвестных сообщений (должен быть ПОСЛЕДНИМ!)
@bot.message_handler(func=lambda m: True)
def handle_unknown_text(message):
    # Если пользователь в процессе создания тикета, игнорируем
    current_state = bot.get_state(message.from_user.id, message.chat.id)
    if current_state:
        return
    
    # Если это не FAQ и не пункт меню
    menu_items = [item for row in MAIN_MENU for item in row] + ["Отдел продаж", "Техническая поддержка"]
    if message.text in menu_items or message.text in FAQ:
        return
    
    bot.send_message(
        message.chat.id,
        "Не понял ваш запрос. Воспользуйтесь кнопками меню или напишите /start для перезагрузки.",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )

# Запуск бота
if __name__ == '__main__':
    try:
        init_db()
        print("База данных инициализирована")
        print("Бот запущен...")
        bot.polling(
            none_stop=True,
            timeout=60,
            allowed_updates=['message', 'callback_query']
        )
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")
 
