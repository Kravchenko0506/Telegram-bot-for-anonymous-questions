# services/question_service.py
"""
Сервис для работы с вопросами в базе данных.

Этот модуль содержит функции для выполнения CRUD операций с вопросами:
- Создание новых вопросов
- Получение вопросов по различным критериям
- Обновление статусов вопросов (избранное, удаление)
- Добавление ответов к вопросам

Все функции являются асинхронными и используют SQLAlchemy ORM
для взаимодействия с PostgreSQL базой данных.
"""

from typing import Optional, List, Union
from datetime import datetime

from models.database import async_session
from models.questions import Question
from sqlalchemy import select, update, delete, and_, desc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload
from utils.logger import get_question_logger

# Получаем логгер для этого модуля
logger = get_question_logger()


async def add_question(
    text: str, 
    user_id: Optional[int] = None,
    unique_id: Optional[str] = None
) -> Optional[Question]:
    """
    Добавляет новый вопрос в базу данных.
    
    Args:
        text (str): Текст вопроса. Обязательный параметр.
        user_id (Optional[int]): Telegram ID пользователя, задавшего вопрос.
                                Может быть None для анонимных вопросов.
        unique_id (Optional[str]): Уникальный идентификатор из start параметра.
                                  Используется для отслеживания источника вопроса.
    
    Returns:
        Optional[Question]: Созданный объект Question при успехе, None при ошибке.
        
    Raises:
        Все исключения обрабатываются внутри функции и логируются.
        
    Example:
        >>> question = await add_question("Как дела?", user_id=12345, unique_id="abc123")
        >>> if question:
        ...     print(f"Вопрос создан с ID: {question.id}")
    """
    # Валидация входных данных
    if not text or not text.strip():
        logger.warning("Попытка создать вопрос с пустым текстом")
        return None
        
    if len(text.strip()) > 4000:  # Лимит Telegram на длину сообщения
        logger.warning(f"Попытка создать вопрос длиннее 4000 символов: {len(text)} символов")
        return None
    
    async with async_session() as session:
        try:
            # Создаем новый объект вопроса
            question = Question(
                text=text.strip(),
                user_id=user_id,
                unique_id=unique_id,
                created_at=datetime.utcnow()
            )
            
            session.add(question)
            await session.commit()
            await session.refresh(question)
            
            logger.info(
                f"Вопрос успешно добавлен в БД: ID={question.id}, "
                f"user_id={user_id}, unique_id={unique_id}, "
                f"text_length={len(text)}"
            )
            return question
            
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Ошибка целостности при добавлении вопроса: {e}")
            return None
            
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Ошибка БД при добавлении вопроса: {e}")
            return None
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Неожиданная ошибка при добавлении вопроса: {e}")
            return None


async def get_question_by_id(question_id: int) -> Optional[Question]:
    """
    Получает вопрос по его уникальному идентификатору.
    
    Args:
        question_id (int): Уникальный идентификатор вопроса в БД.
        
    Returns:
        Optional[Question]: Объект Question если найден, None если не найден или ошибка.
        
    Example:
        >>> question = await get_question_by_id(123)
        >>> if question:
        ...     print(f"Найден вопрос: {question.text}")
        ... else:
        ...     print("Вопрос не найден")
    """
    if not isinstance(question_id, int) or question_id <= 0:
        logger.warning(f"Некорректный ID вопроса: {question_id}")
        return None
    
    async with async_session() as session:
        try:
            stmt = select(Question).where(
                and_(
                    Question.id == question_id,
                    Question.is_deleted == False
                )
            )
            result = await session.execute(stmt)
            question = result.scalar_one_or_none()
            
            if question:
                logger.debug(f"Вопрос найден по ID {question_id}")
            else:
                logger.debug(f"Вопрос с ID {question_id} не найден или удален")
                
            return question
            
        except SQLAlchemyError as e:
            logger.error(f"Ошибка БД при получении вопроса {question_id}: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении вопроса {question_id}: {e}")
            return None


async def mark_favorite(question_id: int, is_favorite: bool = True) -> bool:
    """
    Помечает вопрос как избранный или убирает из избранного.
    
    Args:
        question_id (int): ID вопроса для изменения статуса.
        is_favorite (bool): True - добавить в избранное, False - убрать из избранного.
        
    Returns:
        bool: True если операция успешна, False при ошибке.
        
    Example:
        >>> success = await mark_favorite(123, True)
        >>> if success:
        ...     print("Вопрос добавлен в избранное")
    """
    if not isinstance(question_id, int) or question_id <= 0:
        logger.warning(f"Некорректный ID вопроса для избранного: {question_id}")
        return False
    
    async with async_session() as session:
        try:
            # Проверяем, существует ли вопрос
            question_exists = await session.execute(
                select(Question.id).where(
                    and_(
                        Question.id == question_id,
                        Question.is_deleted == False
                    )
                )
            )
            
            if not question_exists.scalar_one_or_none():
                logger.warning(f"Попытка изменить избранное для несуществующего вопроса {question_id}")
                return False
            
            # Обновляем статус избранного
            stmt = update(Question).where(
                Question.id == question_id
            ).values(
                is_favorite=is_favorite,
                updated_at=datetime.utcnow()
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                action = "добавлен в избранное" if is_favorite else "убран из избранного"
                logger.info(f"Вопрос {question_id} {action}")
                return True
            else:
                logger.warning(f"Не удалось изменить статус избранного для вопроса {question_id}")
                return False
                
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Ошибка БД при изменении избранного для вопроса {question_id}: {e}")
            return False
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Неожиданная ошибка при изменении избранного для вопроса {question_id}: {e}")
            return False


async def delete_question(question_id: int, hard_delete: bool = False) -> bool:
    """
    Удаляет вопрос из системы (мягкое или жесткое удаление).
    
    Args:
        question_id (int): ID вопроса для удаления.
        hard_delete (bool): False - мягкое удаление (помечает как удаленный),
                           True - жесткое удаление (полностью удаляет из БД).
                           
    Returns:
        bool: True если операция успешна, False при ошибке.
        
    Note:
        По умолчанию используется мягкое удаление для возможности восстановления.
        Жесткое удаление следует использовать только в исключительных случаях.
        
    Example:
        >>> success = await delete_question(123)  # Мягкое удаление
        >>> success = await delete_question(123, hard_delete=True)  # Жесткое удаление
    """
    if not isinstance(question_id, int) or question_id <= 0:
        logger.warning(f"Некорректный ID вопроса для удаления: {question_id}")
        return False
    
    async with async_session() as session:
        try:
            if hard_delete:
                # Жесткое удаление - полностью удаляем из БД
                stmt = delete(Question).where(Question.id == question_id)
                delete_type = "жестко удален"
            else:
                # Мягкое удаление - помечаем как удаленный
                stmt = update(Question).where(
                    Question.id == question_id
                ).values(
                    is_deleted=True,
                    deleted_at=datetime.utcnow()
                )
                delete_type = "помечен как удаленный"
            
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Вопрос {question_id} {delete_type}")
                return True
            else:
                logger.warning(f"Вопрос {question_id} не найден для удаления")
                return False
                
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Ошибка БД при удалении вопроса {question_id}: {e}")
            return False
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Неожиданная ошибка при удалении вопроса {question_id}: {e}")
            return False


async def get_favorite_questions(limit: int = 50, offset: int = 0) -> List[Question]:
    """
    Возвращает список избранных вопросов с пагинацией.
    
    Args:
        limit (int): Максимальное количество вопросов для возврата (по умолчанию 50).
        offset (int): Количество вопросов для пропуска (для пагинации).
        
    Returns:
        List[Question]: Список избранных вопросов, отсортированный по дате создания (новые первые).
        
    Note:
        Возвращает только неудаленные вопросы.
        
    Example:
        >>> favorites = await get_favorite_questions(limit=10)
        >>> for question in favorites:
        ...     print(f"ID: {question.id}, Текст: {question.text[:50]}...")
    """
    if limit <= 0 or limit > 100:  # Ограничиваем максимальный лимит
        limit = 50
        logger.warning(f"Лимит избранных вопросов скорректирован до {limit}")
    
    if offset < 0:
        offset = 0
        logger.warning("Offset для избранных вопросов скорректирован до 0")
    
    async with async_session() as session:
        try:
            stmt = select(Question).where(
                and_(
                    Question.is_favorite == True,
                    Question.is_deleted == False
                )
            ).order_by(
                desc(Question.created_at)
            ).limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            questions = result.scalars().all()
            
            logger.info(f"Получено {len(questions)} избранных вопросов (limit={limit}, offset={offset})")
            return list(questions)
            
        except SQLAlchemyError as e:
            logger.error(f"Ошибка БД при получении избранных вопросов: {e}")
            return []
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении избранных вопросов: {e}")
            return []


async def answer_question(question_id: int, answer_text: str) -> bool:
    """
    Сохраняет ответ на вопрос в базу данных.
    
    Args:
        question_id (int): ID вопроса для ответа.
        answer_text (str): Текст ответа.
        
    Returns:
        bool: True если ответ успешно сохранен, False при ошибке.
        
    Note:
        Если на вопрос уже есть ответ, он будет перезаписан.
        
    Example:
        >>> success = await answer_question(123, "Спасибо за вопрос! Ответ: ...")
        >>> if success:
        ...     print("Ответ сохранен")
    """
    # Валидация входных данных
    if not isinstance(question_id, int) or question_id <= 0:
        logger.warning(f"Некорректный ID вопроса для ответа: {question_id}")
        return False
        
    if not answer_text or not answer_text.strip():
        logger.warning(f"Попытка сохранить пустой ответ для вопроса {question_id}")
        return False
        
    if len(answer_text.strip()) > 4000:  # Лимит Telegram
        logger.warning(f"Ответ слишком длинный для вопроса {question_id}: {len(answer_text)} символов")
        return False
    
    async with async_session() as session:
        try:
            # Проверяем, существует ли вопрос
            question_exists = await session.execute(
                select(Question.id).where(
                    and_(
                        Question.id == question_id,
                        Question.is_deleted == False
                    )
                )
            )
            
            if not question_exists.scalar_one_or_none():
                logger.warning(f"Попытка ответить на несуществующий вопрос {question_id}")
                return False
            
            # Сохраняем ответ
            stmt = update(Question).where(
                Question.id == question_id
            ).values(
                answer=answer_text.strip(),
                answered_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Ответ сохранен для вопроса {question_id}, длина ответа: {len(answer_text)} символов")
                return True
            else:
                logger.warning(f"Не удалось сохранить ответ для вопроса {question_id}")
                return False
                
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Ошибка БД при сохранении ответа для вопроса {question_id}: {e}")
            return False
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Неожиданная ошибка при сохранении ответа для вопроса {question_id}: {e}")
            return False


async def get_unanswered_questions(limit: int = 20) -> List[Question]:
    """
    Возвращает список неотвеченных вопросов.
    
    Args:
        limit (int): Максимальное количество вопросов (по умолчанию 20).
        
    Returns:
        List[Question]: Список неотвеченных вопросов, отсортированный по дате создания.
        
    Example:
        >>> unanswered = await get_unanswered_questions()
        >>> print(f"Неотвеченных вопросов: {len(unanswered)}")
    """
    if limit <= 0 or limit > 100:
        limit = 20
        logger.warning(f"Лимит неотвеченных вопросов скорректирован до {limit}")
    
    async with async_session() as session:
        try:
            stmt = select(Question).where(
                and_(
                    Question.answer.is_(None),
                    Question.is_deleted == False
                )
            ).order_by(
                Question.created_at
            ).limit(limit)
            
            result = await session.execute(stmt)
            questions = result.scalars().all()
            
            logger.debug(f"Получено {len(questions)} неотвеченных вопросов")
            return list(questions)
            
        except SQLAlchemyError as e:
            logger.error(f"Ошибка БД при получении неотвеченных вопросов: {e}")
            return []
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении неотвеченных вопросов: {e}")
            return []


async def get_questions_stats() -> dict:
    """
    Возвращает статистику по вопросам.
    
    Returns:
        dict: Словарь со статистикой:
            - total: общее количество вопросов
            - answered: количество отвеченных вопросов  
            - unanswered: количество неотвеченных вопросов
            - favorites: количество избранных вопросов
            - deleted: количество удаленных вопросов
            
    Example:
        >>> stats = await get_questions_stats()
        >>> print(f"Всего вопросов: {stats['total']}")
    """
    async with async_session() as session:
        try:
            # Общее количество неудаленных вопросов
            total_result = await session.execute(
                select(Question.id).where(Question.is_deleted == False)
            )
            total = len(total_result.scalars().all())
            
            # Отвеченные вопросы
            answered_result = await session.execute(
                select(Question.id).where(
                    and_(
                        Question.answer.is_not(None),
                        Question.is_deleted == False
                    )
                )
            )
            answered = len(answered_result.scalars().all())
            
            # Неотвеченные вопросы
            unanswered = total - answered
            
            # Избранные вопросы
            favorites_result = await session.execute(
                select(Question.id).where(
                    and_(
                        Question.is_favorite == True,
                        Question.is_deleted == False
                    )
                )
            )
            favorites = len(favorites_result.scalars().all())
            
            # Удаленные вопросы
            deleted_result = await session.execute(
                select(Question.id).where(Question.is_deleted == True)
            )
            deleted = len(deleted_result.scalars().all())
            
            stats = {
                'total': total,
                'answered': answered,
                'unanswered': unanswered,
                'favorites': favorites,
                'deleted': deleted
            }
            
            logger.info(f"Статистика вопросов: {stats}")
            return stats
            
        except SQLAlchemyError as e:
            logger.error(f"Ошибка БД при получении статистики вопросов: {e}")
            return {
                'total': 0,
                'answered': 0,
                'unanswered': 0,
                'favorites': 0,
                'deleted': 0
            }
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении статистики вопросов: {e}")
            return {
                'total': 0,
                'answered': 0,
                'unanswered': 0,
                'favorites': 0,
                'deleted': 0
            }