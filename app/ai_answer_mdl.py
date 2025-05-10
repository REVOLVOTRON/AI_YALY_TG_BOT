import openai
import asyncio
import json
import os
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Чтение OpenAI API ключа из файла api_keys.json
def load_openai_api_key():
    api_keys_path = os.path.join('api_keys', 'api_keys.json')
    try:
        with open(api_keys_path, 'r') as file:
            data = json.load(file)
            return data['openai_api_key']
    except FileNotFoundError:
        logging.error("Файл api_keys.json не найден в директории api_keys")
        raise
    except KeyError:
        logging.error("Ключ 'openai_api_key' не найден в api_keys.json")
        raise
    except json.JSONDecodeError:
        logging.error("Ошибка декодирования JSON в api_keys.json")
        raise

# Инициализация OpenAI клиента
client = openai.OpenAI(
    api_key=load_openai_api_key(),
    base_url="https://api.intelligence.io.solutions/api/v1/",
)

async def answer_question(query: str) -> tuple[str, bool]:
    """
    Обрабатывает вопрос через OpenAI API, затем форматирует ответ через второе обращение.
    Возвращает кортеж: (отформатированный ответ или сообщение об ошибке, успех ли).
    """
    if not query:
        return "Пожалуйста, задайте вопрос после 'Ask'.", False

    try:
        # Первое обращение: Запрос к OpenAI API для получения ответа
        response = client.chat.completions.create(
            model="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[
                {"role": "system", "content": """
                Вы — полезный ассистент. Отвечайте на вопросы пользователей кратко и точно.
                Не используйте форматирование (HTML или Markdown), возвращайте чистый текст.
                """},
                {"role": "user", "content": query},
            ],
            temperature=0.4,
            stream=False,
            max_completion_tokens=10000
        )

        # Получаем ответ из первого запроса
        answer = response.choices[0].message.content.strip()

        # Второе обращение: Форматирование ответа для Telegram
        format_response = client.chat.completions.create(
            model="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
            messages=[
                {"role": "system", "content": """
                Вы — ассистент по форматированию. Преобразуйте предоставленный текст в Telegram-совместимый HTML.
                - Если текст содержит код (например, начинается с 'import' или содержит синтаксис программирования), оберните его в <pre><code>.
                - Экранируйте специальные символы: '<' → '<', '>' → '>', '&' → '&'.
                - Для обычного текста используйте <b>, <i> или другие HTML-теги при необходимости.
                - Верните только отформатированный текст, готовый для отправки через Telegram с parse_mode='HTML'.
                """},
                {"role": "user", "content": answer},
            ],
            temperature=0.2,
            stream=False,
            max_completion_tokens=10000
        )

        # Получаем отформатированный ответ
        formatted_answer = format_response.choices[0].message.content.strip()

        return formatted_answer, True

    except Exception as e:
        return f"Ошибка при обработке вопроса: {str(e)}", False