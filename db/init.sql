-- db/init.sql
CREATE TABLE IF NOT EXISTS vacancies (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    skills TEXT,
    employment_type VARCHAR(50),
    salary INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidates (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255),
    skills TEXT,
    desired_position VARCHAR(255),
    employment_type VARCHAR(50),
    expected_salary INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id BIGINT PRIMARY KEY,
    vacancy_count INTEGER,
    salary_min INTEGER,
    location INTEGER,
    employment_type VARCHAR(50)
);

