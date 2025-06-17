# 🤖 Anonymous Questions Bot

<div align="center">

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![aiogram](https://img.shields.io/badge/aiogram-3.4.1-green.svg)](https://docs.aiogram.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.25-blue.svg)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Coverage](https://img.shields.io/badge/coverage-61%25-brightgreen.svg)](https://github.com/your-repo)

A Telegram bot for anonymous questions with advanced admin features

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Testing](#-testing) 

</div>

## 📋 Description

Anonymous Questions Bot is a solution for organizing anonymous feedback in Telegram. The bot allows users to ask questions anonymously, while administrators can manage questions and respond to them through a convenient interface.

### 🎯 Key Benefits

- **Complete anonymity** — admin cannot see who asked the question
- **Spam protection** — built-in moderation algorithms and rate limiting
- **Easy management** — intuitive admin panel with pagination
- **Reliability** — automatic recovery after failures
- **Scalability** — asynchronous architecture based on aiogram 3.4

## ✨ Features

### For Users
- 📝 Send anonymous questions
- 📬 Receive answers via private messages
- 🔄 Ability to ask new questions via button
- 🛡️ Protection from accidentally sending commands as questions

### For Administrators
- 📊 **Statistics** — total questions count, answer percentage
- 📋 **Question management** — view with pagination, answer, delete
- ⭐ **Favorites** — save important questions
- ⚙️ **Settings** — change author name and channel description
- 🔍 **Filtering** — separate lists for unanswered and favorite questions
- 🚨 **Monitoring** — Sentry integration for error tracking

### Technical Features
- 🚀 **Performance** — asynchronous request processing
- 🔒 **Security** — protection from SQL injection, XSS, spam
- 📈 **Scalability** — connection pooling, optimized queries
- 🛡️ **Fault tolerance** — automatic connection recovery
- 📝 **Logging** — detailed logs with rotation
- 🧪 **Testing** — test coverage >70%

## 🚀 Installation

### Requirements

- Python 3.10+
- SQLite or PostgreSQL
- Linux/macOS/Windows

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/anon-questions-bot.git
   cd anon-questions-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings**
   ```bash
   cp .env.example .env
   # Edit parameters in .env file
   ```

5. **Initialize database**
   ```bash
   python reset_database.py
   ```

6. **Start the bot**
   ```bash
   python main.py
   ```

### .env File Configuration

```env
# Required parameters
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz  # Token from @BotFather
ADMIN_ID=123456789                              # Your Telegram ID
BOT_USERNAME=your_bot_username                  # Bot username without @

# Optional parameters
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
MAX_QUESTION_LENGTH=2500            # Maximum question length
MAX_ANSWER_LENGTH=5000              # Maximum answer length
SENTRY_DSN=                         # For error monitoring (optional)
```

## 📖 Usage

### For Users

1. **Getting started**
   ```
   /start - Start the bot
   ```
   
2. **Ask a question**
   - After /start command, just send your question as text
   - Bot will confirm that question was sent to admin
   
3. **Ask another question**
   - After sending a question, click "❓ Ask another question" button
   - Or use /start command again

4. **Receiving answers**
   - When admin answers, you'll receive a notification
   - Message will contain your question and admin's answer

### For Administrators

#### Main Commands

| Command | Description |
|---------|-------------|
| `/start` | Admin panel with quick access |
| `/admin` | Full admin panel with instructions |
| `/pending` | List of unanswered questions |
| `/favorites` | Favorite questions |
| `/stats` | Bot statistics |
| `/settings` | Current settings |
| `/set_author` | Change author name |
| `/set_info` | Change channel description |

#### Managing Questions

1. **Answer a question**
   - Use `/pending` command
   - Click "✉️ Answer" button under the question
   - Send your answer in the next message
   
2. **Add to favorites**
   - Click "⭐ Add to favorites" under the question
   - View favorites: `/favorites`
   
3. **Delete question**
   - Click "🗑️ Delete" under the question
   - Question will be marked as deleted (soft delete)

#### Bot Configuration

```bash
# Change author name
/set_author Channel Name

# Change description
/set_info Description of your channel or project

# View current settings
/settings
```

## 🧪 Testing

### Running Tests

```bash
# Running tests via Python script
python run_tests.py quick      # Quick unit tests
python run_tests.py full       # Full testing with coverage report
python run_tests.py integration # Integration tests only
python run_tests.py handlers   # Handler tests
python run_tests.py models     # Model tests

# Or via Makefile
make test-quick               # Quick unit tests
make test-full                # Full testing with coverage
make test-integration         # Integration tests
make test-handlers            # Handler tests
make test-models              # Model tests
make test-utils               # Utility tests
make test-middleware          # Middleware tests

# Or directly via pytest
python -m pytest Tests/                            # All tests
python -m pytest Tests/ -m unit                    # Unit tests only
python -m pytest Tests/ -m integration             # Integration tests only
python -m pytest Tests/test_handlers.py            # Handler tests only
python -m pytest Tests/ --cov=. --cov-report=html  # Generate coverage report
```

### Test Structure

```
Tests/
├── conftest.py          # Fixtures and configuration
├── test_handlers.py     # Command handler tests
├── test_models.py       # Data model tests
├── test_utils.py        # Utility tests
├── test_middleware.py   # Middleware tests
└── test_integration.py  # Integration tests

```

### Test Categories

- **Quick tests (unit)**: Isolated tests without external dependencies
- **Integration tests**: Tests with real database and component interaction
- **Handler tests**: Testing bot interaction and command processing
- **Model tests**: Testing database operations and models
- **Utility tests**: Testing utility functions and validation
- **Middleware tests**: Testing middleware components

### Code Coverage

After running `make test-full` or `python run_tests.py full`, coverage report is available at `htmlcov/index.html`.

Current code coverage: approximately 61%.

## 🏗️ Architecture

### Project Structure

```
anon-questions-bot/
├── handlers/           # Command and message handlers
│   ├── start.py       # /start command
│   ├── admin.py       # Admin commands
│   ├── questions.py   # Question processing
│   └── admin_states.py # Admin states
├── models/            # Data models
│   ├── database.py    # Database connection
│   ├── questions.py   # Questions model
│   ├── settings.py    # Bot settings
│   └── user_states.py # User states
├── middlewares/       # Middleware handlers
│   ├── rate_limit.py  # Rate limiting
│   └── error_handler.py # Error handling
├── utils/             # Utilities
│   ├── validators.py  # Validation and moderation
│   ├── logger.py      # Logging system
│   └── periodic_tasks.py # Background tasks
├── keyboards/         # Keyboards
│   └── inline.py      # Inline keyboards
├── config.py          # Configuration
├── main.py           # Entry point
└── requirements.txt   # Dependencies
```

### Technology Stack

- **Language**: Python 3.10+
- **Framework**: aiogram 3.4.1
- **Database**: SQLite/PostgreSQL + asyncpg/aiosqlite
- **ORM**: SQLAlchemy 2.0 (async)
- **Testing**: pytest + pytest-asyncio
- **Logging**: Python logging + rotation
- **Monitoring**: Sentry (optional)

## 🚀 Deployment

### Production Readiness

- ✅ Systemd service for auto-start
- ✅ Log rotation
- ✅ Graceful shutdown
- ✅ Automatic DB reconnection
- ✅ All error types handling
- ✅ Sentry monitoring

### Quick Deploy

```bash
# Check deployment readiness
python deployment_check.py

# Prepare for deployment
make deploy

# Install as system service
sudo make service-install
sudo make service-start
```

Detailed deployment guide in [DEPLOY.md](DEPLOY.md)

### Docker Deployment

```bash
# Build Docker image
docker build -t anon-questions-bot .

# Run container
docker-compose up -d
```

## 🔧 Configuration

### Main Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_QUESTION_LENGTH` | 2500 | Maximum question length |
| `MAX_ANSWER_LENGTH` | 5000 | Maximum answer length |
| `RATE_LIMIT_QUESTIONS_PER_HOUR` | 5 | Questions per hour limit |


### Logging

Logs are saved in the `logs/` directory:
- `bot.log` — main bot log
- `admin.log` — admin actions
- `question.log` — question processing

## 🛡️ Security

- 🔒 All data is passed through environment variables
- 🛡️ SQL injection protection via SQLAlchemy ORM
- 🚫 XSS protection through HTML escaping
- ⏱️ Rate limiting for spam protection
- 🔍 All input data validation
- 📝 Suspicious activity logging



## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file

## 👥 Authors

- **Kravchenko Aleksandr** - [Email - kravchenkoaleksandr0506@gmail.com]

## 🙏 Acknowledgments

- [aiogram](https://github.com/aiogram/aiogram) - Excellent framework for Telegram bots
- [SQLAlchemy](https://www.sqlalchemy.org/) - Powerful ORM for Python
- Python and Telegram developer community

---

<div align="center">

**[⬆ Back to top](#-anonymous-questions-bot)**



</div>