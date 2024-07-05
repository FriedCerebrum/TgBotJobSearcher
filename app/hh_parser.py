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

    def get_vacancies(self, query, employment_type=None, salary=None, location=None):
        url = "https://api.hh.ru/vacancies"
        params = {
            "text": query,
            "employment": employment_type,  # Указание типа занятости
            "salary": salary,
            "area": location
        }
        logger.info(f"Fetching vacancies with query: {query}, employment: {employment_type}, salary: {salary}, location: {location}")
        response = requests.get(url, params=params)
        logger.info(f"Received response: {response.json()}")
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

    def parse_and_save(self, query, employment_type=None, salary=None, location=None):
        vacancies = self.get_vacancies(query, employment_type, salary, location)
        self.save_to_db(vacancies)

    def get_user_settings(self, user_id):
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT vacancy_count, salary_min, location, employment_type FROM user_settings WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        cursor.close()
        if result:
            return {
                'vacancy_count': result[0],
                'salary_min': result[1],
                'location': result[2],
                'employment_type': result[3]
            }
        else:
            return {
                'vacancy_count': 5,
                'salary_min': None,
                'location': None,
                'employment_type': None
            }

    def save_user_settings(self, user_id, settings):
        cursor = self.db_conn.cursor()
        cursor.execute("""
            INSERT INTO user_settings (user_id, vacancy_count, salary_min, location, employment_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                vacancy_count = EXCLUDED.vacancy_count,
                salary_min = EXCLUDED.salary_min,
                location = EXCLUDED.location,
                employment_type = EXCLUDED.employment_type
        """, (user_id, settings['vacancy_count'], settings['salary_min'], settings['location'], settings['employment_type']))
        self.db_conn.commit()
        cursor.close()