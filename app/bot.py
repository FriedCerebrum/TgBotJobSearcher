# app/bot.py
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from hh_parser import HHParser

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

parser = HHParser()

def start(update: Update, context: CallbackContext):
    logger.info("Received /start command")
    update.message.reply_text('Введите название вакансии:')

def handle_message(update: Update, context: CallbackContext):
    query = update.message.text
    logger.info(f"Received message: {query}")
    update.message.reply_text('Ищу вакансии...')

    vacancies = parser.get_vacancies(query)
    parser.save_to_db(vacancies)

    responses = []
    for item in vacancies['items']:
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

    for response in responses:
        update.message.reply_text(response)
        logger.info(f"Responded with vacancy: {response}")

def main():
    logger.info("Starting bot...")
    updater = Updater(os.getenv('TELEGRAM_TOKEN'), use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
