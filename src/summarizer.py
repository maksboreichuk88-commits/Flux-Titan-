"""
Модуль суммаризации через Google Gemini API.
Преобразует новости в формат "Business Insights".
"""

import asyncio
import logging
from typing import Optional, Dict, Any

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, GenerationConfig
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger("NewsBot.Summarizer")


class GeminiSummarizer:
    """
    Суммаризация статей через Google Gemini API.
    Генерирует профессиональный контент для Telegram-канала.
    """

    SYSTEM_INSTRUCTION = """Ты — редактор новостного Telegram-канала о технологиях и бизнесе.
Твоя задача — превращать новости в краткие, информативные и привлекательные посты.

ПРАВИЛА:
• Пиши на РУССКОМ языке
• Используй только Telegram HTML: <b>жирный</b>, <i>курсив</i>, <a href="url">ссылка</a>
• НЕ используй Markdown (**, ##, ```)
• Будь лаконичен, но информативен
• Добавляй эмодзи уместно
• Фокусируйся на главном: что случилось и почему это важно"""

    SUMMARIZE_PROMPT = """Преобразуй эту новость в пост для Telegram-канала.

**СТРУКТУРА ПОСТА:**
1. {source_icon} <b>Яркий заголовок</b> (не более 10 слов)
2. Пустая строка
3. Суть новости (2-3 предложения, 50-80 слов)
4. Почему это важно (1-2 предложения)
5. Пустая строка
6. 2-3 релевантных хэштега (#AI #Tech #Бизнес)
7. 🔗 <a href="{link}">Читать полностью</a>

**СТИЛЬ:**
• Деловой, но живой
• Конкретные цифры и факты
• Без воды и клише

---
**ИСТОЧНИК:** {source}
**ЗАГОЛОВОК:** {title}
**АВТОР:** {author}
**КОНТЕНТ:** {content}
---

Напиши пост (только HTML, без пояснений):"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Инициализация Gemini клиента.
        
        Args:
            api_key: API ключ Google AI
            model: название модели Gemini
        """
        self.api_key = api_key
        self.model_name = model
        self._model = None
        self._configure()

    def _configure(self) -> None:
        """Конфигурация Gemini API."""
        try:
            genai.configure(api_key=self.api_key)
            
            # Настройки безопасности (разрешаем новостной контент)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
            
            # Параметры генерации
            generation_config = GenerationConfig(
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                max_output_tokens=1024,
            )
            
            self._model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                safety_settings=safety_settings,
                system_instruction=self.SYSTEM_INSTRUCTION,
            )
            
            logger.info(f"Gemini модель инициализирована: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации Gemini: {e}")
            raise

    def _generate_sync(self, prompt: str) -> Optional[str]:
        """
        Синхронная генерация (для запуска в thread pool).
        
        Args:
            prompt: подготовленный промпт
            
        Returns:
            Сгенерированный текст или None
        """
        try:
            response = self._model.generate_content(prompt)
            
            # Проверяем, не заблокирован ли ответ
            if not response.parts:
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    logger.warning(f"Gemini заблокировал ответ: {response.prompt_feedback.block_reason}")
                return None
            
            return response.text
            
        except google_exceptions.InvalidArgument as e:
            logger.error(f"Gemini: неверный аргумент - {e}")
        except google_exceptions.ResourceExhausted as e:
            logger.error(f"Gemini: превышен лимит - {e}")
        except google_exceptions.GoogleAPIError as e:
            logger.error(f"Gemini API ошибка: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка Gemini: {e}")
        
        return None

    async def summarize(self, article: Dict[str, Any]) -> Optional[str]:
        """
        Асинхронная суммаризация статьи.
        
        Args:
            article: словарь с данными статьи
            
        Returns:
            Готовый пост для Telegram или None
        """
        try:
            prompt = self.SUMMARIZE_PROMPT.format(
                source=article.get("source", "Unknown"),
                source_icon=article.get("source_icon", "📰"),
                title=article.get("title", ""),
                author=article.get("author", "Редакция"),
                content=article.get("content", article.get("summary", ""))[:1500],
                link=article.get("link", ""),
            )
            
            # Запускаем синхронный Gemini в thread pool
            result = await asyncio.to_thread(self._generate_sync, prompt)
            
            if result:
                # Очищаем возможные markdown-артефакты
                result = self._clean_response(result)
                return result.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка суммаризации: {e}")
            return None

    @staticmethod
    def _clean_response(text: str) -> str:
        """Очистка ответа от markdown-артефактов."""
        import re
        
        # Удаляем блоки кода, если есть
        text = re.sub(r'^```html?\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()
