# 🤖 DevOps Quiz Bot

A Telegram bot for daily IT quizzes focused on **DevOps, Python, and SQL**.

The bot automatically publishes one quiz every day at **12:00** and sends a reminder at **11:55** to chats where at least one user has subscribed to notifications.

---

## ✨ Features

- 📚 Daily IT quizzes
- 🐍 Python questions
- 🐳 DevOps questions
- 🗄️ SQL questions
- ⏰ Daily quiz at 12:00
- 🔔 Reminder 5 minutes before the quiz
- 👥 Works directly in Telegram chats and groups
- 🔔 Per-user subscription system
- 💾 SQLite database for subscriptions
- ✅ Single-answer questions
- ☑️ Multiple-answer questions
- 💡 Explanations for quiz answers
- 🚂 Railway deployment support
- 📦 JSON-based quiz database
- 🔄 Automatic quiz scheduling with APScheduler

---

## 🧠 How It Works

The bot does not generate quizzes when a user presses a button.

Instead, quizzes are published automatically according to the schedule.

### User flow

```text
/start
   │
   ▼
🔔 Подписаться
   │
   ▼
User is subscribed
   │
   ├── 11:55 → 🔔 Reminder
   │
   └── 12:00 → 📝 Daily Quiz
````

The quiz is published **directly in the chat where the bot is installed**.

If several users are subscribed in the same chat, the bot still sends only **one quiz**, not one quiz per user.

For example:

```text
DevOps Chat

👤 User 1 → subscribed
👤 User 2 → subscribed
👤 User 3 → not subscribed

             ↓

11:55
⏳ Quiz starts in 5 minutes!

12:00
📝 One quiz is published in the chat
```

---

## 🔔 Subscription System

The bot uses a per-user, per-chat subscription model.

A subscription is stored as:

```text
chat_id + user_id
```

This allows the same user to have different subscription states in different chats.

For example:

```text
User #123

DevOps Group  → subscribed
Python Group  → not subscribed
Private Chat  → subscribed
```

### Subscribe

The user presses:

```text
🔔 Подписаться
```

The subscription is stored in SQLite.

The button then changes to:

```text
🔕 Вы подписаны
```

### Unsubscribe

The user can press:

```text
🔕 Вы подписаны
```

to unsubscribe.

---

## ⏰ Schedule

The bot uses `APScheduler`.

| Time  | Action                  |
| ----- | ----------------------- |
| 11:55 | Reminder                |
| 12:00 | Daily quiz              |
| 13:00 | Clear active poll cache |

Timezone:

```text
Europe/Moscow
```

The schedule is configured in `bot.py`:

```python
scheduler = AsyncIOScheduler(
    timezone="Europe/Moscow"
)
```

---

## 📝 Quiz Format

Questions are stored in `quizzes.json`.

Example:

```json
[
  {
    "topic": "Python",
    "question": "What will this code print?",
    "options": [
      "10",
      "20",
      "30",
      "Error"
    ],
    "correct_indexes": [1],
    "explanation": "The expression evaluates to 20."
  }
]
```

### Multiple correct answers

Multiple-answer questions are supported.

Example:

```json
{
  "topic": "Python",
  "question": "Which of these are Python data types?",
  "options": [
    "list",
    "Docker",
    "dict",
    "tuple"
  ],
  "correct_indexes": [0, 2, 3],
  "explanation": "list, dict and tuple are built-in Python data types."
}
```

The bot automatically determines whether a question has one or multiple correct answers.

```python
is_multiple = len(correct_answers) > 1
```

---

## 📂 Project Structure

```text
devops-quiz-bot/
│
├── bot.py
├── quizzes.json
├── requirements.txt
├── README.md
├── .gitignore
│
└── bot.db
```

`bot.db` is created automatically when the bot starts.

---

## 🗄️ Database

SQLite is used to store user subscriptions.

The database contains the following table:

```sql
CREATE TABLE subscriptions (
    chat_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (chat_id, user_id)
);
```

The bot automatically creates the database and table during startup.

---

## ⚙️ Requirements

Python 3.11+ is recommended.

Main dependencies:

```text
aiogram
APScheduler
```

Example `requirements.txt`:

```text
aiogram
APScheduler
```

---

## 🚀 Local Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/devops-quiz-bot.git
cd devops-quiz-bot
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

### Linux/macOS

```bash
source venv/bin/activate
```

### Windows

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Variables

The bot token must be provided through an environment variable.

```text
BOT_TOKEN
```

### Linux/macOS

```bash
export BOT_TOKEN="YOUR_BOT_TOKEN"
```

### Windows PowerShell

```powershell
$env:BOT_TOKEN="YOUR_BOT_TOKEN"
```

Then start the bot:

```bash
python bot.py
```

---

## 🚂 Railway Deployment

The bot is designed to run on [Railway](https://railway.app/).

### 1. Push the project to GitHub

```bash
git add .
git commit -m "Initial bot version"
git push
```

### 2. Create a Railway project

Create a new Railway project and deploy the GitHub repository.

### 3. Add environment variable

In Railway:

```text
Variables
```

Add:

```text
BOT_TOKEN=YOUR_BOT_TOKEN
```

Do **not** put the token directly into `bot.py`.

The application reads it using:

```python
API_TOKEN = os.getenv("BOT_TOKEN")
```

If the variable is missing, the bot will stop with:

```text
RuntimeError: BOT_TOKEN не задан
```

### 4. Start command

Railway can run the bot with:

```bash
python bot.py
```

---

## 📢 Adding the Bot to a Group

1. Add the bot to the Telegram group.
2. Give it the required permissions.
3. Run:

```text
/start
```

4. Press:

```text
🔔 Подписаться
```

The user will then receive the scheduled quiz notifications in that group.

---

## 🧩 Bot Commands

Currently the main command is:

```text
/start
```

It displays the subscription interface.

Quizzes are **not manually generated by users**.

They are published automatically at 12:00.

---

## 🔀 Quiz Types

### Single correct answer

Telegram Quiz mode is used:

```python
type="quiz"
correct_option_id=correct_answers[0]
```

Telegram automatically highlights the correct answer after the user answers.

### Multiple correct answers

Telegram regular poll mode is used:

```python
type="regular"
allows_multiple_answers=True
```

The bot compares the user's selected options with `correct_indexes`.

It then sends:

```text
🎉 Правильно!

✅ Правильные ответы:
• Answer 1
• Answer 2

💡 Объяснение:
...
```

---

## 🧹 Active Polls

The bot temporarily stores active polls in memory:

```python
active_polls = {}
```

Poll information includes:

* poll ID
* message ID
* chat ID
* question
* options
* correct answers
* explanation

The cache is cleared at 13:00:

```python
active_polls.clear()
```

---

## 📚 Adding New Questions

Open:

```text
quizzes.json
```

and add a new object.

Example:

```json
{
  "topic": "DevOps",
  "question": "Which tools are commonly used for container orchestration?",
  "options": [
    "Kubernetes",
    "Docker Compose",
    "Photoshop",
    "Excel"
  ],
  "correct_indexes": [0, 1],
  "explanation": "Kubernetes and Docker Compose are commonly used to manage containers."
}
```

Remember:

`correct_indexes` uses **zero-based indexing**.

For example:

```text
options:
0 → Kubernetes
1 → Docker Compose
2 → Photoshop
3 → Excel
```

Therefore:

```json
"correct_indexes": [0, 1]
```

means that both Kubernetes and Docker Compose are correct.

---

## ⚠️ Important JSON Rules

`quizzes.json` must contain a JSON array:

```json
[
  {
    "topic": "Python",
    "question": "...",
    "options": ["...", "..."],
    "correct_indexes": [0],
    "explanation": "..."
  }
]
```

Not:

```json
{
  "topic": "Python"
}
```

Also make sure:

* JSON uses double quotes
* there are no trailing commas
* `correct_indexes` contains valid option indexes
* every question has at least one correct answer
* `options` is not empty

---

## 🛠️ Troubleshooting

### `RuntimeError: BOT_TOKEN не задан`

The `BOT_TOKEN` environment variable is missing.

Check Railway:

```text
Variables → BOT_TOKEN
```

---

### `Ошибка: база вопросов пуста`

Check that:

```text
quizzes.json
```

exists in the project root.

Expected structure:

```text
project/
├── bot.py
├── quizzes.json
└── requirements.txt
```

Also make sure `quizzes.json` contains a valid JSON array.

---

### Bot starts but doesn't send quizzes

Check:

1. The bot is running.
2. The bot is added to the chat.
3. At least one user subscribed.
4. `quizzes.json` contains valid questions.
5. Railway logs show the scheduler started.
6. The timezone is correct.

---

## 🔒 Security

Never commit your Telegram bot token to GitHub.

Do not write:

```python
API_TOKEN = "123456:ABC..."
```

Use:

```python
API_TOKEN = os.getenv("BOT_TOKEN")
```

and store the token in Railway environment variables.

If a bot token has been exposed publicly, revoke it through **BotFather** and generate a new one.

---

## 📄 License

This project is provided for educational and personal use.

Feel free to modify and extend it for your own Telegram bot projects.
