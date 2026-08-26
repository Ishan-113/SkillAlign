import sqlite3
import csv
from pathlib import Path
from contextlib import asynccontextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "sih134.db"
DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "sample_data.csv"


async def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            skills TEXT NOT NULL,
            experience_years INTEGER,
            location TEXT,
            salary_range TEXT,
            posting_date TEXT,
            job_type TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            results_summary TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM jobs")
    count = cursor.fetchone()[0]

    if count == 0 and DATA_PATH.exists():
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute(
                    """INSERT INTO jobs (job_id, title, company, skills, experience_years,
                       location, salary_range, posting_date, job_type)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        int(row["job_id"]),
                        row["title"],
                        row["company"],
                        row["skills"],
                        int(row["experience_years"]),
                        row["location"],
                        row["salary_range"],
                        row["posting_date"],
                        row["job_type"],
                    ),
                )

    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn
