import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from hh_parser import HHParser
from cities import CITY_IDS  # Импортируем словарь городов из внешнего файла

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = HHParser()

# Состояния для ConversationHandler
CHOOSING, SETTING_SALARY, SETTING_LOCATION, SETTING_VACANCY_COUNT = range(4)

# Используем контекст для хранения настроек для каждого пользователя
def get_user_settings(context):
    if 'settings' not in context.chat_data:
        context.chat_data['settings'] = {
            'vacancy_count': 5,
            'salary_min': None,
            'location': None,
        }
    logger.info(f"User settings: {context.chat_data['settings']}")
    return context.chat_data['settings']

def start(update: Update, context: CallbackContext):
    logger.info("Received /start command")
    update.message.reply_text(
        'Введите название вакансии или используйте /settings для настройки параметров поиска.'
    )

def settings(update: Update, context: CallbackContext):
    logger.info("Received /settings command")
    keyboard = [
        [InlineKeyboardButton("Количество вакансий", callback_data='set_vacancy_count')],
        [InlineKeyboardButton("Минимальная зарплата", callback_data='set_min_salary')],
        [InlineKeyboardButton("Локация поиска", callback_data='set_location')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Выберите параметр для настройки:', reply_markup=reply_markup)
    return CHOOSING

def set_vacancy_count(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    logger.info("Setting vacancy count selected")
    query.edit_message_text('Введите количество вакансий, которые вы хотите видеть за раз:')
    return SETTING_VACANCY_COUNT

def set_min_salary(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    logger.info("Setting minimum salary selected")
    query.edit_message_text('Введите минимальную зарплату:')
    return SETTING_SALARY

def set_location(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    logger.info("Setting location selected")
    query.edit_message_text('Введите локацию для поиска:')
    return SETTING_LOCATION

def handle_vacancy_count(update: Update, context: CallbackContext):
    logger.info("Handling vacancy count input")
    try:
        count = int(update.message.text)
        user_settings = get_user_settings(context)
        user_settings['vacancy_count'] = count
        update.message.reply_text(f'Количество вакансий установлено на {count}.')
    except ValueError:
        update.message.reply_text('Пожалуйста, введите числовое значение.')
    logger.info(f"Updated user settings: {user_settings}")
    return ConversationHandler.END

def handle_min_salary(update: Update, context: CallbackContext):
    logger.info("Handling minimum salary input")
    user_settings = get_user_settings(context)
    try:
        min_salary = int(update.message.text)
        user_settings['salary_min'] = min_salary
        update.message.reply_text(f'Минимальная зарплата установлена на {min_salary}.')
    except ValueError:
        update.message.reply_text('Пожалуйста, введите числовое значение.')
    logger.info(f"Updated user settings: {user_settings}")
    return ConversationHandler.END

def handle_location(update: Update, context: CallbackContext):
    logger.info("Handling location input")
    location = update.message.text
    user_settings = get_user_settings(context)
    user_settings['location'] = CITY_IDS.get(location, None)
    if user_settings['location'] is None:
        update.message.reply_text(f'Неизвестная локация: {location}. Пожалуйста, введите корректное название города.')
    else:
        update.message.reply_text(f'Локация поиска установлена на {location}.')
    logger.info(f"Updated user settings: {user_settings}")
    return ConversationHandler.END

def handle_message(update: Update, context: CallbackContext):
    query = update.message.text
    logger.info(f"Received message: {query}")
    update.message.reply_text('Ищу вакансии...')

    user_settings = get_user_settings(context)
    logger.info(f"User settings used for search: {user_settings}")
    vacancies = parser.get_vacancies(query, salary=user_settings['salary_min'], location=user_settings['location'])
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
    logger.info("Starting bot...")
    updater = Updater(os.getenv('TELEGRAM_TOKEN'), use_context=True)

    dp = updater.dispatcher

    settings_handler = ConversationHandler(
        entry_points=[CommandHandler('settings', settings)],
        states={
            CHOOSING: [
                CallbackQueryHandler(set_vacancy_count, pattern='set_vacancy_count'),
                CallbackQueryHandler(set_min_salary, pattern='set_min_salary'),
                CallbackQueryHandler(set_location, pattern='set_location')
            ],
            SETTING_VACANCY_COUNT: [MessageHandler(Filters.text & ~Filters.command, handle_vacancy_count)],
            SETTING_SALARY: [MessageHandler(Filters.text & ~Filters.command, handle_min_salary)],
            SETTING_LOCATION: [MessageHandler(Filters.text & ~Filters.command, handle_location)]
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
