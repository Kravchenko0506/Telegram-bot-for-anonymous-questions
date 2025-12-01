"""Implements an admin panel: question management, 
bot settings, statistics, and backup."""

from __future__ import annotations

from aiogram import Router, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from datetime import datetime
from sqlalchemy import select, func
import math

from config import (
    ADMIN_ID,
    ERROR_ADMIN_ONLY,
    SUCCESS_ADDED_TO_FAVORITES,
    SUCCESS_REMOVED_FROM_FAVORITES,
    SUCCESS_QUESTION_DELETED,
    ERROR_QUESTION_NOT_FOUND,
    SUCCESS_SETTING_UPDATED,
    ERROR_SETTING_UPDATE,
    ERROR_INVALID_VALUE,
    QUESTIONS_PER_PAGE,
    BACKUP_RECIPIENT_ID,
)
from models.database import async_session
from models.questions import Question
from keyboards.inline import (
    get_admin_question_keyboard,
    get_favorite_question_keyboard,
    get_answered_question_keyboard,
    get_stats_keyboard,
    get_clear_confirmation_keyboard,
    get_pagination_keyboard,
)
from utils.logging_setup import get_logger
from handlers.admin_states import start_answer_mode, cancel_answer_mode
from models.settings import SettingsManager
from utils.runtime import uptime, format_timedelta
from utils.time_helper import format_admin_time
from typing import Dict

router = Router()
logger = get_logger(__name__)


@router.callback_query(lambda c: c.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    """Ignore non-clickable button press."""
    await callback.answer()


# Inline callback handling
async def handle_question_action(callback: CallbackQuery, action: str, qid: int) -> bool:
    """Execute a single question action; return True if handled."""
    async with async_session() as session:
        question = await session.get(Question, qid)
        if not question or question.is_deleted:
            await callback.answer(ERROR_QUESTION_NOT_FOUND, show_alert=True)
            return True
        if action == "answer":
            await start_answer_mode(callback, qid, question)
            return True
        if action == "favorite":
            question.is_favorite = not question.is_favorite
            await session.commit()
            await callback.answer(
                SUCCESS_ADDED_TO_FAVORITES if question.is_favorite else SUCCESS_REMOVED_FROM_FAVORITES
            )
            try:
                await callback.message.edit_reply_markup(
                    reply_markup=get_admin_question_keyboard(
                        qid, is_favorite=question.is_favorite)
                )
            except Exception:
                pass
            return True
        if action == "remove_favorite":
            question.is_favorite = False
            await session.commit()
            await callback.answer("⭐ Убрано из избранного")
            try:
                await callback.message.edit_text(
                    f"⭐ <s>{(callback.message.text or '').strip()}</s>\n\n<i>Убрано из избранного</i>",
                    reply_markup=None,
                )
            except Exception:
                pass
            return True
        if action == "delete":
            question.is_deleted = True
            question.deleted_at = datetime.utcnow()
            await session.commit()
            await callback.answer(SUCCESS_QUESTION_DELETED)
            try:
                orig = callback.message.text or ""
                await callback.message.edit_text(
                    f"🗑️ <s>{orig}</s>\n\n<i>Вопрос удалён</i>", reply_markup=None
                )
            except Exception:
                pass
            return True
    return False


@router.callback_query(lambda c: c.from_user.id == ADMIN_ID)
async def admin_question_callback(callback: CallbackQuery) -> None:
    """Admin inline entrypoint: pagination / bulk clear / question actions."""
    try:
        data = callback.data or ""

    # Pagination
        if data.startswith(("pending_page:", "favorites_page:", "answered_page:")):
            prefix, raw_page = data.split(":", 1)
            try:
                page = int(raw_page)
            except ValueError:
                await callback.answer("❌ Страница", show_alert=True)
                return
            list_type = prefix.replace("_page", "")
            await show_questions_page(callback.message, list_type, page, edit_message=True)
            await callback.answer()
            return
        if data == "clear_all_questions":
            await callback.message.edit_text(
                "⚠️ Удалить ВСЕ вопросы? Это необратимо.",
                reply_markup=get_clear_confirmation_keyboard(),
            )
            return
        if data == "confirm_clear_all":
            await handle_clear_all_questions(callback)
            return
        if data == "cancel_clear":
            await callback.message.edit_text("❌ Отменено", reply_markup=None)
            await callback.answer("Отменено")
            return
        if ":" not in data:
            await callback.answer("❌ Некорректные данные", show_alert=True)
            return
        action, raw_id = data.split(":", 1)
        try:
            qid = int(raw_id)
        except ValueError:
            await callback.answer("❌ Некорректный ID", show_alert=True)
            return

        if action == "cancel_answer":
            await cancel_answer_mode(callback)
            return
        if not await handle_question_action(callback, action, qid):
            await callback.answer("❌ Неизвестное действие", show_alert=True)
    except Exception as e:  # pragma: no cover - defensive
        await callback.answer("❌ Ошибка", show_alert=True)
        logger.error(f"admin callback error: {e}")


# Question list rendering
async def show_questions_page(
    message: Message,
    list_type: str,
    page: int = 0,
    edit_message: bool = False,
) -> None:
    try:
        async with async_session() as session:
            filters = [Question.is_deleted.is_(False)]
            if list_type == "pending":
                filters += [Question.answer.is_(None),
                            Question.is_favorite.is_(False)]
                title = "⏳ <b>Неотвеченные</b>"
                kb_type = "pending"
                order_by = [Question.created_at.desc()]
            elif list_type == "favorites":
                filters += [Question.is_favorite.is_(True)]
                title = "⭐ <b>Избранные</b>"
                kb_type = "favorites"
                order_by = [Question.created_at.desc()]
            elif list_type == "answered":
                filters += [Question.answer.is_not(None)]
                title = "✅ <b>Отвеченные</b>"
                kb_type = "answered"
                order_by = [Question.answered_at.desc(),
                            Question.created_at.desc()]
            else:
                await message.answer("❌ Неизвестный тип списка")
                return

            total_q = (await session.execute(select(func.count(Question.id)).where(*filters))).scalar() or 0
            if total_q == 0:
                empty_map = {
                    "pending": "⏳ Нет неотвеченных вопросов.",
                    "favorites": "⭐ Нет избранных вопросов.",
                    "answered": "✅ Нет отвеченных вопросов.",
                }
                txt = empty_map[list_type]
                if edit_message:
                    await message.edit_text(txt, reply_markup=None)
                else:
                    await message.answer(txt)
                return

            total_pages = math.ceil(total_q / QUESTIONS_PER_PAGE)
            page = max(0, min(page, total_pages - 1))
            offset = page * QUESTIONS_PER_PAGE
            rows = (
                (await session.execute(
                    select(Question)
                    .where(*filters)
                    .order_by(*order_by)
                    .offset(offset)
                    .limit(QUESTIONS_PER_PAGE)
                ))
                .scalars()
                .all()
            )
            qs = [
                {
                    "id": q.id,
                    "text": q.text if isinstance(q.text, str) else "",
                    "answer": q.answer if isinstance(q.answer, str) else None,
                    "is_favorite": bool(q.is_favorite),
                    "created_at": q.created_at,
                    "answered_at": q.answered_at,
                }
                for q in rows
            ]

        header = f"{title}\n\n📊 Стр. {page + 1}/{total_pages} | Всего: {total_q}"
        top_kb = (
            get_pagination_keyboard(page, total_pages, f"{list_type}_page")
            if total_pages > 1
            else None
        )
        if edit_message:
            await message.edit_text(header, reply_markup=top_kb)
        else:
            await message.answer(header, reply_markup=top_kb)

        for q in qs:
            created = format_admin_time(q["answered_at"] or q["created_at"])
            text = q["text"] or "(empty)"
            if list_type == "pending":
                fav = "⭐ " if q["is_favorite"] else ""
                body = f"❓ <b>{fav}Вопрос #{q['id']}</b>\n\n{text}\n\n📅 {created}"
                kb = get_admin_question_keyboard(q["id"], q["is_favorite"])
            elif list_type == "favorites":
                status = "✅ Отвечен" if q["answer"] else "⏳ Ожидает"
                body = f"⭐ <b>Вопрос #{q['id']}</b>\n\n{text}\n\n📅 {created} | {status}"
                if q["answer"]:
                    body += f"\n\n💬 <b>Ответ:</b>\n{q['answer']}"
                kb = get_favorite_question_keyboard(
                    q["id"], is_answered=bool(q["answer"]))
            else:  # answered
                fav = "⭐ " if q["is_favorite"] else ""
                body = (
                    f"✅ <b>{fav}Вопрос #{q['id']}</b>\n\n{text}\n\n📅 {created}\n\n"
                    f"💬 <b>Ответ:</b>\n{q['answer']}"
                )
                kb = get_answered_question_keyboard(q["id"], q["is_favorite"])
            await message.answer(body, reply_markup=kb)

        if total_pages > 1:
            await message.answer(
                f"📄 Навигация ({page + 1}/{total_pages})",
                reply_markup=get_pagination_keyboard(
                    page, total_pages, f"{list_type}_page"),
            )
        logger.info(f"{list_type} page {page + 1}/{total_pages} ({len(qs)})")
    except Exception as e:
        err = "❌ Ошибка списка"
        if edit_message:
            await message.edit_text(err, reply_markup=None)
        else:
            await message.answer(err)
        logger.error(f"{list_type} list error: {e}")


async def handle_clear_all_questions(callback: CallbackQuery) -> None:
    try:
        async with async_session() as session:
            qs = (await session.execute(select(Question).where(Question.is_deleted.is_(False)))).scalars().all()
            now = datetime.utcnow()
            for q in qs:
                q.is_deleted = True
                q.deleted_at = now
            await session.commit()
        await callback.message.edit_text(f"✅ Удалено: {len(qs)}", reply_markup=None)
        await callback.answer("Готово")
        logger.warning(f"mass delete {len(qs)}")
    except Exception as e:
        await callback.message.edit_text("❌ Ошибка очистки", reply_markup=None)
        await callback.answer("Ошибка", show_alert=True)
        logger.error(f"clear all error: {e}")


@router.message(Command("pending"))
async def pending_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    await show_questions_page(message, "pending")


@router.message(Command("favorites"))
async def favorites_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    await show_questions_page(message, "favorites")


@router.message(Command("answered"))
async def answered_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    await show_questions_page(message, "answered")


async def get_question_stats() -> Dict[str, int | float]:
    async with async_session() as session:
        total = (await session.execute(select(func.count(Question.id)).
                                       where(Question.is_deleted.is_(False)))).scalar() or 0
        answered = (await session.execute(select(func.count(Question.id)).
                                          where(Question.is_deleted.is_(False),
                                                Question.answer.is_not(None)))).scalar() or 0
        pending = (await session.execute(select(func.count(Question.id)).
                                         where(Question.is_deleted.is_(False),
                                               Question.answer.is_(None)))).scalar() or 0
        favs = (await session.execute(select(func.count(Question.id)).
                                      where(Question.is_deleted.is_(False),
                                      Question.is_favorite.is_(True)))).scalar() or 0
        deleted = (await session.execute(select(func.count(Question.id)).
                                         where(Question.is_deleted.is_(True)))).scalar() or 0
    rate = round((answered / total * 100), 1) if total else 0.0
    return {"total": total, "answered": answered, "pending": pending, "favs": favs, "deleted": deleted, "rate": rate}


@router.message(Command("stats"))
async def stats_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    try:
        s = await get_question_stats()
        text = (
            "📊 <b>Статистика</b>\n\n"
            f"Всего: {s['total']}\n"
            f"Отвечено: {s['answered']}\n"
            f"Ожидают: {s['pending']}\n"
            f"Избранные: {s['favs']}\n"
            f"Удалено: {s['deleted']}\n\n"
            f"Процент ответов: {s['rate']}%"
        )
        await message.answer(text, reply_markup=get_stats_keyboard())
    except Exception as e:
        await message.answer("❌ Ошибка статистики")
        logger.error(f"stats error: {e}")


@router.message(Command("set_author"))
async def set_author_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        current = await SettingsManager.get_author_name()
        await message.answer(f"Текущее имя: <b>{current}</b>\n\nВведите команду:\n/set_author после нее новое имя")
        return
    new_name = parts[1].strip()
    if not new_name:
        await message.answer(ERROR_INVALID_VALUE)
        return
    try:
        await SettingsManager.set_author_name(new_name)
        await message.answer(SUCCESS_SETTING_UPDATED.format(setting="имя автора", value=new_name))
    except Exception as e:
        await message.answer(ERROR_SETTING_UPDATE)
        logger.error(f"set_author error: {e}")


@router.message(Command("set_info"))
async def set_info_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        current = await SettingsManager.get_author_info()
        await message.answer(f"Текущее описание:\n<b>{current}</b>\n\nВведите команду:\n/set_info после нее новое описание")
        return
    new_info = parts[1].strip()
    if not new_info:
        await message.answer(ERROR_INVALID_VALUE)
        return
    try:
        await SettingsManager.set_author_info(new_info)
        await message.answer(SUCCESS_SETTING_UPDATED.format(setting="описание канала", value=new_info))
    except Exception as e:
        await message.answer(ERROR_SETTING_UPDATE)
        logger.error(f"set_info error: {e}")


@router.message(Command("settings"))
async def settings_command(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    try:
        name = await SettingsManager.get_author_name()
        info = await SettingsManager.get_author_info()
        text = (
            "⚙️ <b>Информация об обо мне</b>\n\n"
            f"<b>Имя автора:</b>\n{name}\n"
            f"<i>Изменить:</i> /set_author\n\n"
            f"<b>Описание:</b>\n{info}\n"
            f"<i>Изменить:</i> /set_info"
        )
        await message.answer(text)
    except Exception as e:
        await message.answer("❌ Ошибка настроек")
        logger.error(f"settings error: {e}")


def get_questions_per_page() -> int:
    return QUESTIONS_PER_PAGE


async def handle_backup_command(message: Message, bot: Bot, recipient_id: int) -> None:
    status = await message.answer("🔄 Бекап...")
    try:
        from utils.telegram_backup import create_and_send_backup
        ok = await create_and_send_backup(recipient_id, bot)
        await status.edit_text("✅ Отправлено." if ok else "❌ Не удалось.")
    except Exception as e:
        await status.edit_text(f"❌ Ошибка: {e}")
        logger.error(f"backup error: {e}")


@router.message(Command("backup"))
async def cmd_create_backup(message: Message, bot: Bot) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    await handle_backup_command(message, bot, BACKUP_RECIPIENT_ID)


@router.message(Command("backup_me"))
async def cmd_backup_to_me(message: Message, bot: Bot) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    await handle_backup_command(message, bot, message.from_user.id)


@router.message(Command("backup_to"))
async def cmd_backup_to_user(message: Message, bot: Bot) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Используйте: /backup_to USER_ID")
        return
    try:
        recipient_id = int(parts[1])
        if recipient_id <= 0:
            await message.answer("ID должен быть > 0")
            return
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    await handle_backup_command(message, bot, recipient_id)


@router.message(Command("backup_info"))
async def cmd_backup_info(message: Message) -> None:
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    try:
        from config import BACKUP_ENABLED, BACKUP_RECIPIENT_ID, BACKUP_STORAGE_DIR
        status = "✅ Включена" if BACKUP_ENABLED else "❌ Отключена"
        parts = ["📦 <b>Бекапы</b>", f"Статус: {status}"]
        if BACKUP_ENABLED:
            parts += [
                f"Получатель: {BACKUP_RECIPIENT_ID}",
                f"Каталог: {BACKUP_STORAGE_DIR}",
                "Содержимое: БД, логи",
                "Команды: Отправить копию админу /backup \n"
                "Отправить копию себе /backup_me \n"
                "Отправить копию другому пользователю /backup_to \n"
                "Информация о бэкапах /backup_info",
            ]
        else:
            parts.append("Включить: BACKUP_ENABLED=true")
        await message.answer("\n".join(parts))
    except Exception as e:
        await message.answer("❌ Ошибка информации")
        logger.error(f"backup_info error: {e}")


@router.message(Command("health"))
async def health_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(ERROR_ADMIN_ONLY)
        return
    try:
        up = format_timedelta(uptime())
        from models.database import check_db_connection
        db_ok = await check_db_connection()
        status = (
            f"🩺 <b>Состояние бота</b>\n"
            f"⏱ Время работы: {up}\n"
            f"💾 База данных: {'OK' if db_ok else 'FAIL'}"
        )
        await message.answer(status)
    except Exception as e:
        await message.answer("❌ Health check error")
        logger.error(f"Health command error: {e}")
