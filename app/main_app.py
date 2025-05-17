import logging
import json
import os
import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
from ai_answer_mdl import answer_question
from img_gen_mdl import generate_image
from img_recgn_mdl import recognize_image
from intent_analyzer_mdl import analyze_intent
from response_formatter_mdl import format_response
from database_mdl import Database
from io import BytesIO
from aiogram import F
import asyncio

# Настраиваем логи, чтобы видеть, что происходит
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Функция для чтения токена Telegram из JSON файла
def load_api_token():
    api_keys_path = os.path.join('api_keys', 'api_keys.json')
    try:
        with open(api_keys_path, 'r') as file:
            data = json.load(file)
            return data['telegram_api_token']
    except FileNotFoundError:
        logging.error("Не могу найти api_keys.json в папке api_keys")
        raise
    except KeyError:
        logging.error("В api_keys.json нет ключа telegram_api_token")
        raise
    except json.JSONDecodeError:
        logging.error("Не удалось разобрать JSON в api_keys.json")
        raise

# Создаём бота и базу данных
API_TOKEN = load_api_token()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())
db = Database()

# Делаем инлайн-клавиатуру с кнопками
def create_inline_keyboard(message_id: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Перегенерировать", callback_data=f"regenerate_{message_id}"),
            InlineKeyboardButton(text="Объяснить подробнее", callback_data=f"explain_{message_id}")
        ]
    ])
    return keyboard

# Реакция на команду /start
@dp.message(lambda message: message.text == "/start")
async def send_welcome(message: Message):
    user_name = message.from_user.first_name
    await message.reply(
        f"Привет, {user_name}! Я твой бот, умею отвечать на вопросы, генерить картинки и описывать изображения. Напиши /help, чтобы узнать, что я могу.")

# Показываем справку по командам
@dp.message(lambda message: message.text == "/help")
async def send_help(message: Message):
    help_text = """
    Команды:
    /start - Начать общение с ботом
    /help - Показать эту справку
    /history - Скачать историю твоих запросов в текстовом файле
    Просто пиши запрос, а я разберусь, что тебе нужно:
    - Задать вопрос
    - Сгенерировать картинку
    - Описать фотку (пришли изображение)
    """
    await message.reply(help_text, parse_mode='HTML')

# Отправляем историю запросов в txt файле
@dp.message(lambda message: message.text == "/history")
async def send_history(message: Message):
    user_id = message.from_user.id
    try:
        # Тянем все запросы пользователя из базы
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT query, timestamp FROM user_queries
                WHERE user_id = ?
                ORDER BY timestamp ASC
            """, (user_id,))
            queries = cursor.fetchall()

        if not queries:
            await message.reply("Ты пока ничего не спрашивал.")
            return

        # Собираем текст для файла
        history_text = f"История запросов пользователя {message.from_user.username or message.from_user.first_name}:\n\n"
        for query, timestamp in queries:
            history_text += f"[{timestamp}] {query}\n"

        # Пишем текст в файл в памяти
        history_bytes = history_text.encode('utf-8')
        history_file = BufferedInputFile(history_bytes, filename=f"history_{user_id}.txt")

        # Отправляем файл юзеру
        await message.reply_document(history_file)
        logging.info(f"Отправил историю запросов юзеру: user_id={user_id}")

    except sqlite3.Error as e:
        logging.error(f"Проблема с базой при получении истории: {str(e)}")
        await message.reply("Не получилось достать историю запросов.")
    except Exception as e:
        logging.error(f"Ошибка при отправке истории: {str(e)}")
        await message.reply("Что-то пошло не так при отправке файла.")

# Обрабатываем текстовые сообщения
@dp.message(lambda message: message.text and not message.text.startswith("/"))
async def handle_text(message: Message):
    query = message.text.strip()
    logging.info(f"Получил текст: {query}")

    # Проверяем, что хочет пользователь
    intent, success = await analyze_intent(query)
    logging.info(f"Намерение: {intent}, получилось: {success}")

    if not success:
        formatted_intent, format_success = await format_response(intent)
        await message.answer(formatted_intent if format_success else intent,
                             parse_mode='HTML' if format_success else None)
        return

    if intent == "[question]":
        result, success = await answer_question(query)
        logging.info(f"Ответ: {result}, получилось: {success}")
        if success:
            formatted_result, format_success = await format_response(result)
            try:
                # Отправляем ответ и запоминаем ID сообщения
                sent_message = await message.answer(
                    formatted_result if format_success else result,
                    parse_mode='HTML' if format_success else None,
                    reply_markup=create_inline_keyboard(message.message_id)
                )
                # Сохраняем запрос в базу
                db.save_query(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    message_id=message.message_id,
                    query=query
                )
            except TelegramBadRequest as e:
                logging.error(f"Ошибка Telegram при отправке: {str(e)}")
                await message.answer("Не удалось красиво оформить ответ. Попробуй спросить по-другому.")
        else:
            await message.answer(result)
    elif intent == "[image]":
        prompt = query  # Берём запрос как промпт для генерации
        logging.info(f"Хочет сгенерить картинку: {prompt}")
        result, success = await generate_image(prompt)
        logging.info(f"Результат генерации: {result}, получилось: {success}")
        if success:
            try:
                await message.answer_photo(
                    photo=BufferedInputFile(result, filename="image.jpg"),
                    caption=prompt
                )
            except TelegramBadRequest as e:
                logging.error(f"Ошибка Telegram при отправке картинки: {str(e)}")
                await message.answer("Не получилось отправить картинку. Попробуй ещё раз.")
        else:
            await message.answer(result)
    elif intent == "[image_description]":
        formatted_result, format_success = await format_response("Пришли картинку, и я её опишу.")
        await message.answer(formatted_result if format_success else "Пришли картинку, и я её опишу.",
                             parse_mode='HTML' if format_success else None)

# Старый способ обработки вопросов (для совместимости)
@dp.message(lambda message: message.text and message.text.lower().startswith("ask"))
async def answer(message: Message):
    query = message.text[3:].strip()  # Убираем "Ask" из начала
    logging.info(f"Получил вопрос: {query}")
    result, success = await answer_question(query)
    logging.info(f"Ответ: {result}, получилось: {success}")
    if success:
        formatted_result, format_success = await format_response(result)
        try:
            # Отправляем ответ и запоминаем ID
            sent_message = await message.answer(
                formatted_result if format_success else result,
                parse_mode='HTML' if format_success else None,
                reply_markup=create_inline_keyboard(message.message_id)
            )
            # Пишем запрос в базу
            db.save_query(
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                message_id=message.message_id,
                query=query
            )
        except TelegramBadRequest as e:
            logging.error(f"Ошибка Telegram при отправке: {str(e)}")
            await message.answer("Не смог красиво оформить ответ. Попробуй спросить иначе.")
        else:
            await message.answer(result)

# Старый способ генерации картинок (для совместимости)
@dp.message(lambda message: message.text and message.text.lower().startswith("generate"))
async def generate(message: Message):
    prompt = message.text[8:].strip()  # Убираем "Generate"
    logging.info(f"Запрос на картинку: {prompt}")
    result, success = await generate_image(prompt)
    logging.info(f"Результат: {result}, получилось: {success}")
    if success:
        try:
            await message.answer_photo(
                photo=BufferedInputFile(result, filename="image.jpg"),
                caption=prompt
            )
        except TelegramBadRequest as e:
            logging.error(f"Ошибка Telegram при отправке картинки: {str(e)}")
            await message.answer("Не получилось отправить картинку. Попробуй ещё раз.")
        else:
            await message.answer(result)

# Обрабатываем присланные фотки
@dp.message(F.photo)
async def handle_image(message: Message):
    try:
        # Берём фотку в лучшем качестве
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        image_data = await bot.download_file(file_info.file_path)

        logging.info("Получил фотку для анализа")
        description, success = await recognize_image(image_data.read())

        if success:
            formatted_description, format_success = await format_response(description)
            await message.answer(formatted_description if format_success else description,
                                 parse_mode='HTML' if format_success else None)
        else:
            await message.answer(description)

    except Exception as e:
        logging.error(f"Ошибка при анализе фотки: {str(e)}")
        await message.answer("Не смог обработать изображение.")

# Обрабатываем кнопку "Перегенерировать"
@dp.callback_query(lambda c: c.data.startswith("regenerate_"))
async def handle_regenerate(callback: CallbackQuery):
    message_id = int(callback.data.split("_")[1])
    query = db.get_query(message_id=message_id, chat_id=callback.message.chat.id)

    if not query:
        await callback.message.answer("Не нашёл исходный запрос. Задай вопрос заново.")
        await callback.answer()
        return

    try:
        # Пробуем заново сгенерить ответ
        result, success = await answer_question(query)
        logging.info(f"Новый ответ: {result}, получилось: {success}")
        if success:
            formatted_result, format_success = await format_response(result)
            try:
                # Меняем текст сообщения
                await callback.message.edit_text(
                    formatted_result if format_success else result,
                    parse_mode='HTML' if format_success else None,
                    reply_markup=create_inline_keyboard(message_id)
                )
            except TelegramBadRequest as e:
                logging.error(f"Ошибка Telegram при редактировании: {str(e)}")
                await callback.message.answer("Не получилось обновить ответ. Попробуй ещё раз.")
        else:
            await callback.message.edit_text(result, reply_markup=create_inline_keyboard(message_id))
    except Exception as e:
        logging.error(f"Ошибка при перегенерации: {str(e)}")
        await callback.message.answer(f"Ошибка при перегенерации: {str(e)}")

    await callback.answer()

# Обрабатываем кнопку "Объяснить подробнее"
@dp.callback_query(lambda c: c.data.startswith("explain_"))
async def handle_explain(callback: CallbackQuery):
    message_id = int(callback.data.split("_")[1])
    query = db.get_query(message_id=message_id, chat_id=callback.message.chat.id)

    if not query:
        await callback.message.answer("Не нашёл исходный запрос. Задай вопрос заново.")
        await callback.answer()
        return

    try:
        # Просим подробное объяснение
        explain_query = f"Объясните тему или вопрос подробно: {query}"
        result, success = await answer_question(explain_query)
        logging.info(f"Объяснение: {result}, получилось: {success}")
        if success:
            formatted_result, format_success = await format_response(result)
            try:
                # Отправляем новое сообщение
                await callback.message.answer(
                    formatted_result if format_success else result,
                    parse_mode='HTML' if format_success else None
                )
            except TelegramBadRequest as e:
                logging.error(f"Ошибка Telegram при отправке объяснения: {str(e)}")
                await callback.message.answer("Не получилось отправить объяснение. Попробуй ещё раз.")
        else:
            await callback.message.answer(result)
    except Exception as e:
        logging.error(f"Ошибка при объяснении: {str(e)}")
        await callback.message.answer(f"Ошибка при объяснении: {str(e)}")

    await callback.answer()

# Запускаем бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())