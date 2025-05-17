import asyncio
from io import BytesIO
from PIL import Image as PILImage
import pollinations
import logging

# Настраиваем логи, чтобы следить за процессом
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создаём модель для работы с текстом
text_model = pollinations.Text()

# Переводим промпт на английский
async def translate_prompt(prompt: str) -> str:
    if not prompt.strip():
        return prompt

    try:
        translation_prompt = f"""
        Переведи этот текст на английский. Только перевод, без лишних слов:
        {prompt}
        """
        translated_text = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: text_model(translation_prompt)
        )
        translated_text = translated_text.strip()
        logging.info(f"Перевёл: '{prompt}' -> '{translated_text}'")
        return translated_text if translated_text else prompt
    except Exception as e:
        logging.error(f"Не смог перевести промпт: {str(e)}")
        return prompt

# Генерируем картинку по промпту
async def generate_image(prompt: str) -> tuple[bytes | str, bool]:
    if not prompt.strip():
        return "Напиши, какую картинку хочешь сгенерить.", False

    # Переводим промпт на английский
    translated_prompt = await translate_prompt(prompt)
    logging.info(f"Генерирую с промптом: {translated_prompt}")

    try:
        # Настраиваем модель для генерации картинок
        ai_image = pollinations.Image(
            model="flux",
            width=1024,
            height=1024,
            nologo=True,
            enhance=True,
        )

        # Генерируем картинку
        pil_image: PILImage = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: ai_image(translated_prompt)
        )

        if pil_image:
            # Сохраняем картинку в память
            image_bytes = BytesIO()
            pil_image.save(image_bytes, format=pil_image.format or "JPEG")
            return image_bytes.getvalue(), True
        else:
            return "Не получилось сгенерить картинку.", False

    except Exception as e:
        return f"Ошибка при генерации картинки: {str(e)}", False