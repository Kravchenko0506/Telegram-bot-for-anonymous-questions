"""
Questions Handler - Simplified Version

Direct database operations without service layer.
"""

from aiogram import Router
from aiogram.types import Message
from datetime import datetime
import re

from config import (
    ADMIN_ID, 
    MAX_QUESTION_LENGTH,
    ERROR_MESSAGE_TOO_LONG,
    ERROR_MESSAGE_EMPTY,
    SUCCESS_QUESTION_SENT,
    ADMIN_NEW_QUESTION,
    ERROR_DATABASE,
    USER_ANSWER_RECEIVED
)
from models.database import async_session
from models.questions import Question
from keyboards.inline import get_admin_question_keyboard
from utils.logger import get_question_logger
from sqlalchemy import select

router = Router()
logger = get_question_logger()


@router.message()
async def question_handler(message: Message):
    """Handle incoming questions from users."""
    user_id = message.from_user.id
    
    # Skip admin messages
    if user_id == ADMIN_ID:
        if message.reply_to_message:
            await handle_admin_reply(message)
        return
    
    # Validate message content
    if not message.text or not message.text.strip():
        await message.answer(ERROR_MESSAGE_EMPTY)
        logger.warning(f"Empty question attempt from user {user_id}")
        return
    
    question_text = message.text.strip()
    
    # Check question length
    if len(question_text) > MAX_QUESTION_LENGTH:
        await message.answer(ERROR_MESSAGE_TOO_LONG)
        logger.warning(f"Question too long from user {user_id}: {len(question_text)} chars")
        return
    
    try:
        # Save question to database
        async with async_session() as session:
            question = Question.create_new(
                text=question_text,
                user_id=user_id,
                unique_id=None
            )
            session.add(question)
            await session.commit()
            await session.refresh(question)
            
            question_id = question.id
        
        logger.info(f"Question saved: ID={question_id}, user_id={user_id}")
        
        # Send notification to admin
        admin_message = ADMIN_NEW_QUESTION.format(
            question_id=question_id,
            question_text=question_text,
            created_at=datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        
        keyboard = get_admin_question_keyboard(question_id)
        await message.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=keyboard
        )
        
        # Confirm to user
        await message.answer(SUCCESS_QUESTION_SENT)
        logger.info(f"Question {question_id} notifications sent successfully")
        
    except Exception as e:
        await message.answer(ERROR_DATABASE)
        logger.error(f"Error processing question from user {user_id}: {e}")


async def handle_admin_reply(message: Message):
    """Handle admin replies to questions."""
    reply_text = message.reply_to_message.text or ""
    if not reply_text.startswith("❓") or "вопрос #" not in reply_text:
        return
    
    try:
        # Extract question ID
        match = re.search(r"вопрос #(\d+):", reply_text)
        if not match:
            return
        
        question_id = int(match.group(1))
        answer_text = message.text.strip()
        
        if not answer_text:
            await message.answer("❌ Ответ не может быть пустым.")
            return
        
        # Get question and save answer
        async with async_session() as session:
            question = await session.get(Question, question_id)
            if not question or question.is_deleted:
                await message.answer("❌ Вопрос не найден.")
                return
            
            # Save answer
            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            await session.commit()
            
            # Send answer to user
            user_message = USER_ANSWER_RECEIVED.format(
                question=question.text,
                answer=answer_text
            )
            
            try:
                await message.bot.send_message(
                    chat_id=question.user_id,
                    text=user_message
                )
                await message.answer("✅ Ответ отправлен пользователю!")
                logger.info(f"Answer sent for question {question_id}")
                
            except Exception as e:
                await message.answer("✅ Ответ сохранен, но не удалось отправить пользователю.")
                logger.error(f"Failed to send answer to user: {e}")
        
    except Exception as e:
        await message.answer("❌ Ошибка при обработке ответа.")
        logger.error(f"Error processing admin reply: {e}")