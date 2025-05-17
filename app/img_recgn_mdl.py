import asyncio
import base64
import logging
from openai import OpenAI
from io import BytesIO

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Читаем API ключ для OpenAI
def load_openai_api_key():
    import os
    import json
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

# Распознаём, что на картинке
async def recognize_image(image_data: bytes) -> tuple[str, bool]:
    # Проверяем, есть ли картинка
    if not image_data:
        return "Картинку не прислали.", False

    try:
        # Кодируем картинку в base64
        encoded_image = base64.b64encode(image_data).decode("utf-8")

        # Спрашиваем OpenAI, что на картинке
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://your-site-url",
                    "X-Title": "AI YALY TG BOT",
                },
                model="opengvlab/internvl3-14b:free",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Опиши подробно, что на этой картинке"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=10000
            )
        )

        # Получаем описание
        description = response.choices[0].message.content.strip()
        if description:
            return description, True
        else:
            return "Не смог разобрать, что на картинке.", False

    except Exception as e:
        logging.error(f"Ошибка при анализе картинки: {str(e)}")
        return f"Не получилось обработать картинку: {str(e)}", False