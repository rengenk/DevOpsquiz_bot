import asyncio
import logging
import random
import sqlite3
import json
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)

TOKEN = ''
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "bot.db")
QUIZ_PATH = os.path.join(BASE_DIR, "quizzes.json")

active_polls = {}

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY)"
        )
        conn.commit()


def add_user(chat_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (chat_id) VALUES (?)",
            (chat_id,)
        )
        conn.commit()


def get_users():
    with sqlite3.connect(DB_PATH) as conn:
        return [
            row[0]
            for row in conn.execute(
                "SELECT chat_id FROM users"
            ).fetchall()
        ]


def load_quizzes():
    if not os.path.exists(QUIZ_PATH):
        logging.warning(f"Файл {QUIZ_PATH} не найден!")
        return []

    try:
        with open(QUIZ_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    except Exception as e:
        logging.error(f"Ошибка чтения JSON: {e}")
        return []

def get_main_menu():
    kb = ReplyKeyboardBuilder()

    kb.button(text="DevOps")
    kb.button(text="SQL")
    kb.button(text="Python")
    kb.button(text="Рандом")

    kb.adjust(3, 1)

    return kb.as_markup(resize_keyboard=True)

API_TOKEN = os.getenv("TOKEN")

if not API_TOKEN:
    raise RuntimeError("TOKEN не задан")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

scheduler = AsyncIOScheduler(
    timezone="Europe/Moscow"
)

async def send_quiz_to_chat(chat_id, quiz):
    correct_answers = quiz.get("correct_indexes", [])

    if not correct_answers:
        logging.error(
            f"Пропуск вопроса: отсутствуют correct_indexes: "
            f"{quiz.get('question', 'UNKNOWN')}"
        )
        return False

    options = quiz.get("options", [])

    if any(
        index < 0 or index >= len(options)
        for index in correct_answers
    ):
        logging.error(
            f"Некорректные correct_indexes: "
            f"{correct_answers}"
        )
        return False

    is_multiple = len(correct_answers) > 1

    try:
        poll = await bot.send_poll(
            chat_id=chat_id,
            question=quiz["question"],
            options=options,

            type="quiz",

            allows_multiple_answers=is_multiple,

            correct_option_ids=sorted(correct_answers),

            explanation=quiz.get("explanation"),

            open_period=3600,

            is_anonymous=False
        )

        active_polls[poll.poll.id] = {
            "message_id": poll.message_id,
            "chat_id": chat_id,
            "question": quiz["question"],
            "correct_indexes": correct_answers,
            "explanation": quiz.get("explanation", ""),
            "options": options
        }

        return True

    except Exception as e:
        logging.error(
            f"Ошибка отправки quiz в чат {chat_id}: {e}"
        )
        return False

async def process_quiz_request(
    message: types.Message,
    topic_filter=None
):
    quizzes = load_quizzes()

    if not quizzes:
        await message.answer(
            "Ошибка: база вопросов пуста."
        )
        return

    if topic_filter:
        filtered_quizzes = [
            q for q in quizzes
            if q.get("topic") == topic_filter
        ]
    else:
        filtered_quizzes = quizzes

    if not filtered_quizzes:
        await message.answer(
            f"В базе пока нет вопросов по теме "
            f"'{topic_filter}'."
        )
        return

    for _ in range(5):

        quiz = random.choice(filtered_quizzes)

        if await send_quiz_to_chat(
            message.chat.id,
            quiz
        ):
            return

    await message.answer(
        "Не удалось отправить вопрос "
        "из-за ошибок в базе данных."
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    add_user(message.chat.id)

    await message.answer(
        "Привет! Ты подписался на ежедневный "
        "IT-квиз в 12:00.\n\n"
        "Выбери интересующую тебя тему "
        "на панели ниже, чтобы потренироваться "
        "прямо сейчас 👇",
        reply_markup=get_main_menu()
    )


@dp.message(F.text == "DevOps")
async def menu_devops(message: types.Message):
    await process_quiz_request(
        message,
        topic_filter="DevOps"
    )

@dp.message(F.text == "SQL")
async def menu_sql(message: types.Message):
    await process_quiz_request(
        message,
        topic_filter="SQL"
    )

@dp.message(F.text == "Python")
async def menu_python(message: types.Message):
    await process_quiz_request(
        message,
        topic_filter="Python"
    )

@dp.message(F.text == "Рандом")
async def menu_random(message: types.Message):
    await process_quiz_request(
        message,
        topic_filter=None
    )

@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await process_quiz_request(
        message,
        topic_filter=None
    )

async def send_daily_quiz():

    users = get_users()
    quizzes = load_quizzes()

    if not users:
        logging.info(
            "Нет пользователей для ежедневного квиза."
        )
        return

    if not quizzes:
        logging.warning(
            "База вопросов пуста."
        )
        return

    valid_quiz = None

    for _ in range(5):

        temp_quiz = random.choice(quizzes)

        if temp_quiz.get("correct_indexes"):
            valid_quiz = temp_quiz
            break

    if not valid_quiz:
        logging.error(
            "Не найден корректный вопрос."
        )
        return

    logging.info(
        f"Ежедневный вопрос: "
        f"{valid_quiz['question']}"
    )

    for chat_id in users:

        await send_quiz_to_chat(
            chat_id,
            valid_quiz
        )

async def send_quiz_reminder():

    users = get_users()

    if not users:
        return

    logging.info(
        "Отправка напоминания о квизе в 11:55..."
    )

    reminder_text = (
        "⏳ **Приготовься!**\n"
        "Через 5 минут начнется "
        "ежедневный IT-квиз. Не пропусти!"
    )

    for chat_id in users:

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=reminder_text,
                parse_mode="Markdown"
            )

        except Exception as e:
            logging.error(
                f"Ошибка отправки напоминания "
                f"в чат {chat_id}: {e}"
            )

async def close_daily_quiz_memory():

    logging.info("Очистка кэша активных опросов в 13:00...")

    active_polls.clear()


async def main():

    init_db()

    scheduler.add_job(send_quiz_reminder, "cron", hour=11, minute=55)

    scheduler.add_job(send_daily_quiz, "cron", hour=12, minute=0)

    scheduler.add_job(close_daily_quiz_memory, "cron", hour=13, minute=0)

    scheduler.start()

    logging.info(
        "Бот запущен. "
        "Ежедневный квиз: 12:00 MSK"
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
