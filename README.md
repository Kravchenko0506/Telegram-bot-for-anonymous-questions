# Anonymous Questions Bot

Telegram bot for anonymous questions. Users ask questions, admin answers — nobody knows who asked.

## Features

**For users:**
- Send anonymous questions
- Receive answers in private chat
- Protection from accidentally sending commands as questions

**For admin:**
- View questions with pagination
- Answer via buttons or reply
- Favorites, statistics, backups
- Configure limits via commands

## Quick Start

```bash
# Clone
git clone https://github.com/Kravchenko0506/Telegram-bot-for-anonymous-questions.git
cd Telegram-bot-for-anonymous-questions

# Configure
cp .env.example .env
# Fill in BOT_TOKEN, ADMIN_ID, BOT_USERNAME, BACKUP_RECIPIENT_ID

# Run
docker-compose up -d
```


## Admin Commands

| Command | Description |
|---------|-------------|
| `/start` | Admin panel |
| `/pending` | Unanswered questions |
| `/favorites` | Favorites |
| `/answered` | Answered |
| `/stats` | Statistics |
| `/limits` | Manage limits |
| `/backup_me` | Backup to self |
| `/health` | Bot status |

## Structure

```
├── handlers/       # Command handlers
├── models/         # DB models (SQLAlchemy async)
├── middlewares/    # Rate limiting, error handling
├── utils/          # Validation, backups, logging
├── keyboards/      # Inline keyboards
├── config.py       # Configuration from .env
└── main.py         # Entry point
```

## Configuration

Main parameters in `.env`:

```env
BOT_TOKEN=...              # Token from @BotFather
ADMIN_ID=123456789         # Your Telegram ID
BOT_USERNAME=my_bot        # Bot username without @
BACKUP_RECIPIENT_ID=...    # Who receives backups

# Optional
MIN_QUESTION_LENGTH=5
MAX_QUESTION_LENGTH=2500
RATE_LIMIT_QUESTIONS_PER_HOUR=500
LOG_LEVEL=INFO
```

Full list — in `.env.example`.

## Tech Stack

- Python 3.10+
- aiogram 3.x
- SQLAlchemy 2.0 (async)
- SQLite (aiosqlite)
- Docker

## License

MIT