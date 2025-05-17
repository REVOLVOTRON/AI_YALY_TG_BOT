import sqlite3
import logging
from datetime import datetime

# Настраиваем логи, чтобы следить за базой
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class Database:
    def __init__(self, db_path: str = "user_queries.db"):
        # Создаём подключение к базе
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        # Создаём таблицу для запросов, если её нет
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_queries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        message_id INTEGER NOT NULL,
                        query TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                """)
                conn.commit()
                logging.info("Таблица user_queries готова к работе.")
        except sqlite3.Error as e:
            logging.error(f"Не смог настроить базу: {str(e)}")
            raise

    def save_query(self, user_id: int, chat_id: int, message_id: int, query: str):
        # Сохраняем запрос юзера в базу
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = datetime.utcnow().isoformat()
                cursor.execute("""
                    INSERT INTO user_queries (user_id, chat_id, message_id, query, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, chat_id, message_id, query, timestamp))
                conn.commit()
                logging.info(f"Сохранил запрос: user_id={user_id}, message_id={message_id}")
        except sqlite3.Error as e:
            logging.error(f"Не смог сохранить запрос: {str(e)}")
            raise

    def get_query(self, message_id: int, chat_id: int) -> str | None:
        # Ищем запрос по ID сообщения и чата
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT query FROM user_queries
                    WHERE message_id = ? AND chat_id = ?
                """, (message_id, chat_id))
                result = cursor.fetchone()
                if result:
                    logging.info(f"Нашёл запрос для message_id={message_id}, chat_id={chat_id}")
                    return result[0]
                else:
                    logging.warning(f"Запрос не нашёл для message_id={message_id}, chat_id={chat_id}")
                    return None
        except sqlite3.Error as e:
            logging.error(f"Ошибка при поиске запроса: {str(e)}")
            return None