import asyncio
import logging
import pollinations

# Настраиваем логи, чтобы видеть, что к чему
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создаём модель для анализа текста
model = pollinations.Text()

# Проверяем, что хочет пользователь
async def analyze_intent(query: str) -> tuple[str, bool]:
    # Если запрос пустой, просим что-то написать
    if not query.strip():
        return "Напиши запрос, пожалуйста.", False

    try:
        # Формируем запрос для анализа
        prompt = f"""
        Посмотри на запрос и реши, что хочет пользователь.
        Верни только одно из: [image], [question], [image_description]
        [image] - хочет сгенерить картинку
        [question] - задаёт вопрос
        Запрос: {query}
        """
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model(prompt)
        )

        intent = response.strip()
        if intent in ["[image]", "[question]", "[image_description]"]:
            return intent, True
        else:
            return "Не понял, что ты хочешь. Попробуй переформулировать.", False

    except Exception as e:
        logging.error(f"Не смог разобрать намерение: {str(e)}")
        return f"Ошибка при обработке запроса: {str(e)}", False