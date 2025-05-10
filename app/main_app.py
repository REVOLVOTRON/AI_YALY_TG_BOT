import logging
import json
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
from ai_answer_mdl import answer_question
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Чтение API ключа из файла api_keys.json
def load_api_token():
    api_keys_path = os.path.join('api_keys', 'api_keys.json')
    try:
        with open(api_keys_path, 'r') as file:
            data = json.load(file)
            return data['telegram_api_token']
    except FileNotFoundError:
        logging.error("Файл api_keys.json не найден в директории api_keys")
        raise
    except KeyError:
        logging.error("Ключ 'telegram_api_token' не найден в api_keys.json")
        raise
    except json.JSONDecodeError:
        logging.error("Ошибка декодирования JSON в api_keys.json")
        raise

# Инициализация бота
API_TOKEN = load_api_token()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot=bot, storage=MemoryStorage())

# Обработчик команды /start
@dp.message(lambda message: message.text == "/start")
async def send_welcome(message: Message):
    user_name = message.from_user.first_name
    await message.reply(f"Привет, {user_name}! Я бот, который отвечает на вопросы. Напиши /help для списка команд.")

# Обработчик команды /help
@dp.message(lambda message: message.text == "/help")
async def send_help(message: Message):
    help_text = """
    <pre language="python">print('hello world')</pre>
    """
    await message.reply(help_text, parse_mode='HTML')

# Обработчик вопросов
@dp.message(lambda message: message.text.lower().startswith("ask"))
async def answer(message: Message):
    query = message.text[3:].strip()  # Убираем "Ask" из начала сообщения
    logging.info(f"Получен вопрос: {query}")
    result, success = await answer_question(query)
    logging.info(f"Ответ: {result}, Успех: {success}")
    try:
        await message.answer(result, parse_mode='HTML')
    except TelegramBadRequest as e:
        logging.error(f"Ошибка Telegram при отправке ответа: {str(e)}")
        await message.answer("Произошла ошибка при форматировании ответа. Попробуйте задать вопрос иначе.")

# Обработчик текстовых сообщений (эхо)
@dp.message()
async def echo(message: Message):
    if not message.text.startswith('/'):
        await message.answer(f"Ты сказал: {message.text}")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())