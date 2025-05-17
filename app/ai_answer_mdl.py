import openai
import asyncio
import json
import os
import logging

# Настраиваем логирование, чтобы видеть, что происходит
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Читаем API ключ для OpenAI из JSON файла
def load_openai_api_key():
    api_keys_path = os.path.join('api_keys', 'api_keys.json')
    try:
        with open(api_keys_path, 'r') as file:
            data = json.load(file)
            return data['openai_api_key']
    except FileNotFoundError:
        logging.error("Не нашёл api_keys.json в папке api_keys")
        raise
    except KeyError:
        logging.error("В api_keys.json нет ключа openai_api_key")
        raise
    except json.JSONDecodeError:
        logging.error("Не смог разобрать JSON в api_keys.json")
        raise

# Создаём клиент для OpenAI
client = openai.OpenAI(
    api_key=load_openai_api_key(),
    base_url="https://openrouter.ai/api/v1",
)

# Функция для обработки вопросов через OpenAI
async def answer_question(query: str) -> tuple[str, bool]:
    # Проверяем, есть ли вообще вопрос
    if not query:
        return "Напиши вопрос после 'Ask', пожалуйста.", False

    try:
        # Отправляем запрос к OpenAI
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="nousresearch/deephermes-3-mistral-24b-preview:free",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        Ты умный помощник. Отвечай кратко и по делу.
                        Не добавляй HTML или Markdown, только чистый текст.
                        """
                    },
                    {"role": "user", "content": query},
                ],
                temperature=0.4,
                stream=False,
                max_completion_tokens=10000
            )
        )

        # Берём ответ
        answer = response.choices[0].message.content.strip()
        return answer, True

    except Exception as e:
        return f"Что-то пошло не так с вопросом: {str(e)}", False