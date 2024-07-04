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

    response = '\n'.join([f"{item['name']} - {item['salary']['from']} {item['salary']['currency']}"
                          if item.get('salary') else f"{item['name']} - Зарплата не указана"
                          for item in vacancies['items']])
    update.message.reply_text(response)
    logger.info("Responded with vacancies")

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
