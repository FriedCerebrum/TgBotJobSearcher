# app/hh_parser.py
import requests
import os
import psycopg2
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HHParser:
    def __init__(self):
        retries = 5
        while retries > 0:
            try:
                logger.info("Trying to connect to the database...")
                self.db_conn = psycopg2.connect(
                    host=os.getenv('DB_HOST'),
                    port=os.getenv('DB_PORT'),
                    database=os.getenv('DB_NAME'),
                    user=os.getenv('DB_USER'),
                    password=os.getenv('DB_PASSWORD')
                )
                logger.info("Successfully connected to the database")
                break
            except psycopg2.OperationalError as e:
                logger.error(f"Unable to connect to the database, retrying in 5 seconds... ({retries} retries left)")
                logger.error(e)
                time.sleep(5)
                retries -= 1
        else:
            raise Exception("Could not connect to the database after several attempts.")

    def get_vacancies(self, query, employment_type=None, salary=None):
        url = "https://api.hh.ru/vacancies"
        params = {
            "text": query,
            "employment_type": employment_type,
            "salary": salary
        }
        response = requests.get(url, params=params)
        return response.json()

    def save_to_db(self, vacancies):
        cursor = self.db_conn.cursor()
        for vacancy in vacancies['items']:
            skills = ', '.join(skill['name'] for skill in vacancy.get('key_skills', []))
            employment_type = vacancy.get('employment', {}).get('name', '')
            salary = vacancy.get('salary')
            salary_from = salary.get('from') if salary else None
            try:
                cursor.execute(
                    """
                    INSERT INTO vacancies (title, skills, employment_type, salary, updated_at)
                    VALUES (%s, %s, %s, %s, now())
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        skills = EXCLUDED.skills,
                        employment_type = EXCLUDED.employment_type,
                        salary = EXCLUDED.salary,
                        updated_at = now();
                    """,
                    (vacancy['name'], skills, employment_type, salary_from)
                )
                logger.info(f"Saved vacancy '{vacancy['name']}' to the database")
            except Exception as e:
                logger.error(f"Error saving vacancy '{vacancy['name']}' to the database")
                logger.error(e)
        self.db_conn.commit()
        cursor.close()

    def parse_and_save(self, query, employment_type=None, salary=None):
        vacancies = self.get_vacancies(query, employment_type, salary)
        self.save_to_db(vacancies)
