import asyncio
import logging
from openai import OpenAI
import os
import json

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Читаем API ключ для OpenAI
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
client = OpenAI(
    api_key=load_openai_api_key(),
    base_url="https://openrouter.ai/api/v1",
)

# Форматируем текст для Telegram
async def format_response(text: str) -> tuple[str, bool]:
    # Проверяем, есть ли текст
    if not text.strip():
        return "Пустой текст, нечего форматировать.", False

    try:
        # Просим OpenAI отформатировать текст в HTML для Telegram
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="nousresearch/deephermes-3-mistral-24b-preview:free",
                messages=[
                    {
                        "role": "system",
                        "content": """
                        Ты спец по форматированию. Переведи текст в HTML для Telegram.
                        - Если видишь код (например, начинается с 'import'), оберни в <pre><code>.
                        - Экранируй символы: '<' → '&lt;', '>' → '&gt;', '&' → '&amp;'.
                        - Для обычного текста добавляй <b>, <i> или другие теги, где нужно.
                        - Верни только готовый HTML для parse_mode='HTML'.
                        """
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.2,
                stream=False,
                max_completion_tokens=10000
            )
        )

        # Берём отформатированный текст
        formatted_text = response.choices[0].message.content.strip()
        return formatted_text, True

    except Exception as e:
        logging.error(f"Не смог отформатировать текст: {str(e)}")
        return f"Ошибка при форматировании: {str(e)}", False