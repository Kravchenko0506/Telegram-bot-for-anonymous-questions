# 📝 Configuration Parameters for Anonymous Questions Bot

This document contains all configuration parameters for the bot, categorized by function. These parameters can be configured through environment variables or `.env` file.

## 🔑 Basic Parameters (Required)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `BOT_TOKEN` | string | - | Bot token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | integer | - | Telegram ID of the administrator |
| `BOT_USERNAME` | string | - | Bot username without @ symbol |

## 📊 Administration Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `QUESTIONS_PER_PAGE` | integer | 5 | Number of questions per page in admin panel |
| `MAX_PAGES_TO_SHOW` | integer | 100 | Maximum number of pages to display |
| `ADMIN_AUTO_REFRESH` | boolean | false | Automatic refresh of lists after actions |
| `SHOW_QUESTION_PREVIEW_LENGTH` | integer | 200 | Length of question preview in admin panel |

## 💬 Message Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MAX_QUESTION_LENGTH` | integer | 2500 | Maximum question length in characters |
| `MAX_ANSWER_LENGTH` | integer | 6000 | Maximum answer length in characters |
| `DEFAULT_AUTHOR_NAME` | string | "Автор канала" | Default author name |
| `DEFAULT_AUTHOR_INFO` | string | "Здесь можно задать анонимный вопрос" | Default author information |

## 📝 Logging System

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `LOG_LEVEL` | string | "INFO" | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FORMAT` | string | "%(asctime)s - %(name)s - %(levelname)s - %(message)s" | Logging format string |
| `LOG_TO_FILE` | boolean | true | Whether to save logs to file |
| `LOG_FILE_PATH` | string | "/data/bot.log" | Path to log file |
| `LOG_MAX_SIZE_MB` | integer | 10 | Maximum log file size in MB before rotation |
| `LOG_BACKUP_COUNT` | integer | 5 | Number of log backup files to keep |
| `DEBUG_MODE` | boolean | false | Debug mode (more detailed logging) |
| `VERBOSE_DATABASE_LOGS` | boolean | false | Verbose logging of database operations |

## 🔒 Security and Limitations

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `RATE_LIMIT_QUESTIONS_PER_HOUR` | integer | 500 | Maximum number of questions per hour from one user |
| `RATE_LIMIT_COOLDOWN_SECONDS` | integer | 5 | Minimum time between questions in seconds |

## 🔍 Monitoring and Error Tracking (Sentry)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SENTRY_DSN` | string | null | DSN for Sentry integration |
| `SENTRY_ENVIRONMENT` | string | "production" | Environment for Sentry (development/staging/production) |
| `SENTRY_RELEASE` | string | null | Release version for Sentry |
| `SENTRY_SAMPLE_RATE` | float | 1.0 | Error sampling rate (0.0 - 1.0) |
| `SENTRY_TRACES_SAMPLE_RATE` | float | 0.1 | Performance trace sampling rate (0.0 - 1.0) |
| `ENABLE_PERFORMANCE_MONITORING` | boolean | false | Enable performance monitoring |

## 💌 Message Templates

| Parameter | Type | Description |
|-----------|------|-------------|
| `WELCOME_MESSAGE_TEMPLATE` | string | Welcome message template with formatting for author name and information |
| `SUCCESS_QUESTION_SENT` | string | Message about successful question submission |
| `SUCCESS_ANSWER_SENT` | string | Message about successful answer sending |
| `SUCCESS_ADDED_TO_FAVORITES` | string | Message about adding to favorites |
| `SUCCESS_REMOVED_FROM_FAVORITES` | string | Message about removing from favorites |
| `SUCCESS_QUESTION_DELETED` | string | Message about deleting a question |
| `SUCCESS_SETTING_UPDATED` | string | Message about updating a setting |

## ❌ Error Messages

| Parameter | Type | Description |
|-----------|------|-------------|
| `ERROR_MESSAGE_TOO_LONG` | string | Error for too long message |
| `ERROR_MESSAGE_EMPTY` | string | Error for empty message |
| `ERROR_ADMIN_ONLY` | string | Error when attempting to use admin command |
| `ERROR_DATABASE` | string | Error when working with database |
| `ERROR_QUESTION_NOT_FOUND` | string | Error when question is not found |
| `ERROR_ALREADY_ANSWERED` | string | Error when trying to answer a question again |
| `ERROR_SETTING_UPDATE` | string | Error when updating a setting |
| `ERROR_INVALID_VALUE` | string | Error for invalid value |
| `ERROR_RATE_LIMIT` | string | Template for rate limit exceeded message |

## 👨‍💼 Administrative Messages

| Parameter | Type | Description |
|-----------|------|-------------|
| `ADMIN_NEW_QUESTION` | string | New question notification template |
| `ADMIN_NO_PENDING_QUESTIONS` | string | Message for no pending questions |
| `ADMIN_NO_FAVORITES` | string | Message for no favorite questions |
| `USER_ANSWER_RECEIVED` | string | Template for user notification about receiving an answer |
| `USER_QUESTION_PROCESSING` | string | Message about question processing |

## 🛠️ Configuration Helper Functions

| Function | Description |
|----------|-------------|
| `get_env_var(key, default=None, required=True)` | Get environment variable with validation |
| `get_env_int(key, default=None, required=True)` | Get integer environment variable |
| `get_bot_link(unique_id)` | Generate bot link with tracking identifier |
| `validate_config()` | Validate all configuration parameters | 