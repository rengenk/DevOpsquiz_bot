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

def migrate_old_users_to_subscriptions():
    """Миграция старой таблицы users в новую subscriptions"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Проверяем, существует ли старая таблица users
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            logging.info("Найдена старая таблица users, выполняю миграцию...")
            
            try:
                # Копируем данные из users в subscriptions
                cursor.execute("""
                    INSERT OR IGNORE INTO subscriptions (chat_id, user_id)
                    SELECT chat_id, chat_id as user_id FROM users
                """)
                conn.commit()
                
                # Удаляем старую таблицу
                cursor.execute("DROP TABLE users")
                conn.commit()
                
                logging.info("Миграция успешна")
            except Exception as e:
                logging.error(f"Ошибка при миграции: {e}")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        conn.commit()
    
    # Выполняем миграцию после создания новой таблицы
    migrate_old_users_to_subscriptions()


def subscribe_user(chat_id, user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR IGNORE INTO subscriptions
            (chat_id, user_id)
            VALUES (?, ?)
        """, (chat_id, user_id))
        conn.commit()
        logging.info(f"Пользователь {user_id} подписан на чат {chat_id}")


def unsubscribe_user(chat_id, user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            DELETE FROM subscriptions
            WHERE chat_id = ? AND user_id = ?
        """, (chat_id, user_id))
        conn.commit()
        logging.info(f"Пользователь {user_id} отписан от чата {chat_id}")


def is_subscribed(chat_id, user_id):
    with sqlite3.connect(DB_PATH) as conn:
        result = conn.execute("""
            SELECT 1
            FROM subscriptions
            WHERE chat_id = ? AND user_id = ?
        """, (chat_id, user_id)).fetchone()

    return result is not None


def get_subscribed_chats():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT DISTINCT chat_id
            FROM subscriptions
        """).fetchall()

    chats = [row[0] for row in rows]
    logging.info(f"Найдено {len(chats)} чатов с подписчиками: {chats}")
    return chats


def load_quizzes():
    if not os.path.exists(QUIZ_PATH):
        logging.warning(f"Файл {QUIZ_PATH} не найден!")
        return []

    try:
        with open(QUIZ_PATH, 'r', encoding='utf-8') as f:
            quizzes = json.load(f)
            logging.info(f"Загружено {len(quizzes)} вопросов")
            return quizzes

    except Exception as e:
        logging.error(f"Ошибка чтения JSON: {e}")
        return []

def get_main_menu(subscribed=False):
    kb = ReplyKeyboardBuilder()

    if subscribed:
        kb.button(text="🔕 Вы подписаны")
    else:
        kb.button(text="🔔 Подписаться")

    kb.adjust(1)

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

        logging.info(f"Квиз отправлен в чат {chat_id}")
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

    chat_id = message.chat.id
    user_id = message.from_user.id

    subscribed = is_subscribed(
        chat_id,
        user_id
    )

    await message.answer(
        "🤖 DevOps Quiz Bot\n\n"
        "Каждый день в 12:00 в этом чате "
        "появляется новый IT-квиз.\n\n"
        "За 5 минут до начала, в 11:55, "
        "я отправлю уведомление.\n\n"
        "Нажмите кнопку ниже, чтобы подписаться "
        "на уведомления.",
        reply_markup=get_main_menu(subscribed)
    )

@dp.message(F.text == "🔔 Подписаться")
async def subscribe_handler(message: types.Message):

    chat_id = message.chat.id
    user_id = message.from_user.id

    subscribe_user(
        chat_id,
        user_id
    )

    await message.answer(
        "✅ Вы подписались на уведомления!\n\n"
        "⏰ Напоминание — 11:55\n"
        "📝 Квиз — 12:00",
        reply_markup=get_main_menu(True)
    )

@dp.message(F.text == "🔕 Вы подписаны")
async def unsubscribe_handler(message: types.Message):

    chat_id = message.chat.id
    user_id = message.from_user.id

    unsubscribe_user(
        chat_id,
        user_id
    )

    await message.answer(
        "🔕 Вы отписались от уведомлений.",
        reply_markup=get_main_menu(False)
    )

async def send_daily_quiz():
    logging.info("Запуск send_daily_quiz")
    
    chats = get_subscribed_chats()
    quizzes = load_quizzes()

    if not chats:
        logging.warning("Нет чатов с подписчиками")
        return

    if not quizzes:
        logging.error("База вопросов пуста")
        return

    logging.info(f"Отправляю квиз в {len(chats)} чатов")
    quiz = random.choice(quizzes)

    for chat_id in chats:
        await send_quiz_to_chat(
            chat_id,
            quiz
        )
    
    logging.info("send_daily_quiz завершена")

async def send_quiz_reminder():
    logging.info("Запуск send_quiz_reminder")
    
    chats = get_subscribed_chats()

    if not chats:
        logging.warning("Нет чатов для отправки напоминания")
        return

    reminder_text = (
        "⏳ <b>Квиз начнётся через 5 минут!</b>\n\n"
        "Приготовьтесь проверить свои знания "
        "по DevOps, Python и SQL."
    )

    logging.info(f"Отправляю напоминание в {len(chats)} чатов")
    
    for chat_id in chats:

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=reminder_text,
                parse_mode="HTML"
            )
            logging.info(f"Напоминание отправлено в чат {chat_id}")

        except Exception as e:
            logging.error(
                f"Ошибка отправки напоминания "
                f"в чат {chat_id}: {e}"
            )
    
    logging.info("send_quiz_reminder завершена")

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

