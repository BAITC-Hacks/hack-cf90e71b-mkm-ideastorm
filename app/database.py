"""SQLite persistence. Application data stays on this machine."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from app.config import DATABASE_PATH


@contextmanager
def connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def init_db():
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, meeting_date TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS speakers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            speaker_key TEXT NOT NULL, display_name TEXT NOT NULL, UNIQUE(meeting_id, speaker_key)
        );
        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            speaker_key TEXT NOT NULL, start_seconds REAL NOT NULL, end_seconds REAL NOT NULL,
            text TEXT NOT NULL, language TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS action_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            task TEXT NOT NULL, responsible_person TEXT NOT NULL, deadline TEXT NOT NULL, status TEXT NOT NULL,
            source TEXT NOT NULL, confidence REAL NOT NULL
        );
        """)


def seed_demo():
    with connection() as db:
        if db.execute("SELECT 1 FROM meetings LIMIT 1").fetchone():
            return
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        meeting_id = db.execute(
            "INSERT INTO meetings(title, meeting_date, summary, created_at) VALUES(?,?,?,?)",
            ("Q1 product planning: Алматы командасы", today.isoformat(),
             "Команда обсудила запуск клиентского портала, качество казахской локализации и подготовку апрельской демонстрации.\n\nАигерим подготовит обновлённый отчёт до завтра, Азат проверит локализацию до пятницы, а Дана назначит встречу с партнёрами на следующей неделе.", datetime.now().isoformat(timespec="minutes"))).lastrowid
        speakers = [("SPEAKER_00", "Aigerim"), ("SPEAKER_01", "Azat"), ("SPEAKER_02", "Dana")]
        db.executemany("INSERT INTO speakers(meeting_id,speaker_key,display_name) VALUES(?,?,?)",
                       [(meeting_id, *s) for s in speakers])
        segments = [
            ("SPEAKER_00", 0, 8, "Доброе утро, коллеги. Сегодня согласуем план запуска клиентского портала и сроки.", "ru"),
            ("SPEAKER_01", 8, 16, "Алдымен қазақша интерфейсті тексерейік. Кейбір аудармалар әлі дайын емес.", "kk"),
            ("SPEAKER_02", 16, 25, "Согласна. Азамат, осы отчетты ертең сағат үшке дейін дайындап, маған отправьте.", "mixed"),
            ("SPEAKER_01", 25, 34, "Жақсы, бүгін тексеремін. I can send the localization notes by Friday.", "mixed"),
            ("SPEAKER_00", 34, 42, "Отлично. Давайте ещё назначим встречу с партнёрами на следующей неделе.", "ru"),
            ("SPEAKER_02", 42, 50, "Мен серіктестерге хат жазып, кездесуді дүйсенбіге жоспарлаймын.", "kk"),
            ("SPEAKER_00", 50, 57, "Спасибо! Встреча готова, зафиксирую решения и разошлю протокол.", "ru"),
        ]
        db.executemany("INSERT INTO segments(meeting_id,speaker_key,start_seconds,end_seconds,text,language) VALUES(?,?,?,?,?,?)",
                       [(meeting_id, *s) for s in segments])
        actions = [
            ("Подготовить и отправить отчёт по порталу", "Azamat", tomorrow.isoformat() + " 15:00", "In progress", "«осы отчетты ертең сағат үшке дейін дайындап, маған отправьте»", .92),
            ("Проверить казахскую локализацию и отправить заметки", "Azat", (today + timedelta(days=3)).isoformat(), "In progress", "«қазақша интерфейсті тексерейік… I can send the localization notes by Friday»", .88),
            ("Назначить встречу с партнёрами", "Dana", (today + timedelta(days=6)).isoformat(), "In progress", "«встречу с партнёрами на следующей неделе»", .84),
            ("Зафиксировать решения и разослать протокол", "Aigerim", yesterday.isoformat(), "Overdue", "«зафиксирую решения и разошлю протокол»", .81),
            ("Подготовить макет клиентского портала", "Azat", (today - timedelta(days=2)).isoformat(), "Completed", "Макет портала рассмотрен и утверждён на встрече", .96),
        ]
        db.executemany("INSERT INTO action_items(meeting_id,task,responsible_person,deadline,status,source,confidence) VALUES(?,?,?,?,?,?,?)",
                       [(meeting_id, *a) for a in actions])


def rows(query, params=()):
    with connection() as db:
        return [dict(r) for r in db.execute(query, params).fetchall()]


def one(query, params=()):
    with connection() as db:
        row = db.execute(query, params).fetchone()
        return dict(row) if row else None
