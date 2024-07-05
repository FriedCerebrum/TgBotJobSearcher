import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from hh_parser import HHParser
from cities import CITY_IDS  # Импортируем словарь городов из внешнего файла

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = HHParser()

# Состояния для ConversationHandler
CHOOSING, SETTING_SALARY, SETTING_LOCATION, SETTING_VACANCY_COUNT, SETTING_EMPLOYMENT = range(5)

# Используем контекст для хранения настроек для каждого пользователя
def get_user_settings(context, user_id):
    parser = context.bot_data['parser']
    settings = parser.get_user_settings(user_id)
    context.chat_data['settings'] = settings
    return settings

def save_user_settings(context, user_id, settings):
    parser = context.bot_data['parser']
    parser.save_user_settings(user_id, settings)

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    get_user_settings(context, user_id)
    update.message.reply_text('Введите название вакансии или используйте /settings для настройки параметров поиска.')

def settings(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_settings = get_user_settings(context, user_id)

    settings_text = (
        f"Текущие настройки поиска:\n"
        f"Количество вакансий: {user_settings['vacancy_count']}\n"
        f"Минимальная зарплата: {user_settings['salary_min']}\n"
        f"Локация: {next((k for k, v in CITY_IDS.items() if v == user_settings['location']), 'Не установлена')}\n"
        f"Занятость: {'Полная' if user_settings['employment_type'] == 'full' else 'Неполная' if user_settings['employment_type'] == 'part' else 'Не установлена'}\n"
    )

    keyboard = [
        [InlineKeyboardButton("Количество вакансий", callback_data='set_vacancy_count')],
        [InlineKeyboardButton("Минимальная зарплата", callback_data='set_min_salary')],
        [InlineKeyboardButton("Локация поиска", callback_data='set_location')],
        [InlineKeyboardButton("Занятость", callback_data='set_employment')],
        [InlineKeyboardButton("Назад", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        update.callback_query.edit_message_text(settings_text + '\nВыберите параметр для настройки:', reply_markup=reply_markup)
    else:
        update.message.reply_text(settings_text + '\nВыберите параметр для настройки:', reply_markup=reply_markup)

    return CHOOSING

def set_vacancy_count(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    logger.info("Setting vacancy count selected")
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_settings')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text('Введите количество вакансий, которые вы хотите видеть за раз:', reply_markup=reply_markup)
    return SETTING_VACANCY_COUNT

def set_min_salary(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    logger.info("Setting minimum salary selected")
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_settings')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text('Введите минимальную зарплату:', reply_markup=reply_markup)
    return SETTING_SALARY

def set_location(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    logger.info("Setting location selected")
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_settings')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text('Введите локацию для поиска:', reply_markup=reply_markup)
    return SETTING_LOCATION

def set_employment(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    logger.info("Setting employment selected")
    keyboard = [
        [InlineKeyboardButton("Полная занятость", callback_data='full')],
        [InlineKeyboardButton("Неполная занятость", callback_data='part')],
        [InlineKeyboardButton("Назад", callback_data='back_to_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text('Выберите тип занятости:', reply_markup=reply_markup)
    return SETTING_EMPLOYMENT

def go_back_to_settings(update: Update, context: CallbackContext):
    logger.info("Going back to settings")
    return settings(update, context)

def go_back_to_main(update: Update, context: CallbackContext):
    logger.info("Going back to main menu")
    query = update.callback_query
    query.answer()
    query.edit_message_text('Меню закрыто.')
    return ConversationHandler.END

def handle_vacancy_count(update: Update, context: CallbackContext):
    try:
        count = int(update.message.text)
        user_settings = get_user_settings(context, update.effective_user.id)
        user_settings['vacancy_count'] = count
        save_user_settings(context, update.effective_user.id, user_settings)
        update.message.reply_text(f'Количество вакансий установлено на {count}.')
        return CHOOSING
    except ValueError:
        update.message.reply_text('Пожалуйста, введите числовое значение.')
        return SETTING_VACANCY_COUNT

def handle_min_salary(update: Update, context: CallbackContext):
    try:
        min_salary = int(update.message.text)
        user_settings = get_user_settings(context, update.effective_user.id)
        user_settings['salary_min'] = min_salary
        save_user_settings(context, update.effective_user.id, user_settings)
        update.message.reply_text(f'Минимальная зарплата установлена на {min_salary}.')
        return CHOOSING
    except ValueError:
        update.message.reply_text('Пожалуйста, введите числовое значение.')
        return SETTING_SALARY

def handle_location(update: Update, context: CallbackContext):
    location = update.message.text
    user_settings = get_user_settings(context, update.effective_user.id)
    user_settings['location'] = CITY_IDS.get(location, None)
    if user_settings['location'] is None:
        update.message.reply_text(f'Неизвестная локация: {location}. Пожалуйста, введите корректное название города.')
        return SETTING_LOCATION
    else:
        save_user_settings(context, update.effective_user.id, user_settings)
        update.message.reply_text(f'Локация поиска установлена на {location}.')
        return CHOOSING

def handle_employment(update: Update, context: CallbackContext):
    query = update.callback_query
    user_settings = get_user_settings(context, update.effective_user.id)
    user_settings['employment_type'] = query.data
    save_user_settings(context, update.effective_user.id, user_settings)
    employment_text = 'полная занятость' if query.data == 'full' else 'неполная занятость'
    query.edit_message_text(f"Тип занятости установлен на {employment_text}.")
    return CHOOSING


def handle_message(update: Update, context: CallbackContext):
    query = update.message.text
    user_id = update.effective_user.id
    logger.info(f"Received message: {query}")
    update.message.reply_text('Ищу вакансии...')

    user_settings = get_user_settings(context, user_id)
    logger.info(f"User settings used for search: {user_settings}")
    vacancies = parser.get_vacancies(query, employment_type=user_settings['employment_type'], salary=user_settings['salary_min'], location=user_settings['location'])
    parser.save_to_db(vacancies)

    responses = []
    count = 0
    for item in vacancies.get('items', []):
        if user_settings['location'] and str(user_settings['location']) not in item.get('area', {}).get('id', ''):
            continue
        if count >= user_settings['vacancy_count']:
            break
        title = item['name']
        skills = ', '.join(skill['name'] for skill in item.get('key_skills', [])) if item.get('key_skills') else 'Не указаны'
        employment_type = item.get('employment', {}).get('name', 'Не указано')
        salary = f"{item['salary']['from']} {item['salary']['currency']}" if item.get('salary') else 'Не указана'
        location = item.get('area', {}).get('name', 'Не указана')
        experience = item.get('experience', {}).get('name', 'Не указан')
        url = item.get('alternate_url', 'Ссылка не указана')

        response = (f"Название: {title}\n"
                    f"Навыки: {skills}\n"
                    f"Формат работы: {employment_type}\n"
                    f"Зарплата: {salary}\n"
                    f"Локация: {location}\n"
                    f"Уровень опыта: {experience}\n"
                    f"Ссылка на вакансию: {url}\n")
        responses.append(response)
        count += 1

    for response in responses:
        update.message.reply_text(response)
        logger.info(f"Responded with vacancy: {response}")

def main():
    parser = HHParser()

    updater = Updater(os.getenv('TELEGRAM_TOKEN'), use_context=True)
    dp = updater.dispatcher
    dp.bot_data['parser'] = parser

    # Регистрация команд для меню команд в Telegram
    updater.bot.set_my_commands([
        BotCommand("start", "Запустить бота"),
        BotCommand("settings", "Настройки поиска")
    ])

    settings_handler = ConversationHandler(
        entry_points=[CommandHandler('settings', settings)],
        states={
            CHOOSING: [
                CallbackQueryHandler(set_vacancy_count, pattern='set_vacancy_count'),
                CallbackQueryHandler(set_min_salary, pattern='set_min_salary'),
                CallbackQueryHandler(set_location, pattern='set_location'),
                CallbackQueryHandler(set_employment, pattern='set_employment'),
                CallbackQueryHandler(go_back_to_main, pattern='back_to_main')
            ],
            SETTING_VACANCY_COUNT: [
                MessageHandler(Filters.text & ~Filters.command, handle_vacancy_count),
                CallbackQueryHandler(go_back_to_settings, pattern='back_to_settings')
            ],
            SETTING_SALARY: [
                MessageHandler(Filters.text & ~Filters.command, handle_min_salary),
                CallbackQueryHandler(go_back_to_settings, pattern='back_to_settings')
            ],
            SETTING_LOCATION: [
                MessageHandler(Filters.text & ~Filters.command, handle_location),
                CallbackQueryHandler(go_back_to_settings, pattern='back_to_settings')
            ],
            SETTING_EMPLOYMENT: [
                CallbackQueryHandler(handle_employment, pattern='^(full|part)$'),
                CallbackQueryHandler(go_back_to_settings, pattern='back_to_settings')
            ]
        },
        fallbacks=[CommandHandler('settings', settings)]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(settings_handler)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
