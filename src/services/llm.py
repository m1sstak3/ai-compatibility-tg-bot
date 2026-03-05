import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from src.core.config import LLM_API_KEY, MODEL_NAME, MODEL_QUESTIONS, MODEL_FAKES

logger = logging.getLogger(__name__)

# OpenRouter Client
or_client = AsyncOpenAI(
    api_key=LLM_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

def clean_json_string(s: str) -> str:
    """Извлекает JSON из строки, убирая markdown и лишний текст."""
    try:
        if "```" in s:
            content = s.split("```")
            for chunk in content:
                if "{" in chunk or "[" in chunk:
                    s = chunk
                    if s.startswith("json"):
                        s = s[4:]
                    break

        start_obj = s.find('{')
        start_list = s.find('[')
        
        if start_obj == -1 and start_list == -1:
            return s.strip()
            
        if start_obj == -1: start = start_list
        elif start_list == -1: start = start_obj
        else: start = min(start_obj, start_list)
        
        end_obj = s.rfind('}')
        end_list = s.rfind(']')
        
        if end_obj == -1 and end_list == -1:
            return s.strip()
            
        if end_obj == -1: end = end_list
        elif end_list == -1: end = end_obj
        else: end = max(end_obj, end_list)
        
        if start != -1 and end != -1:
            return s[start:end+1]
    except Exception:
        pass
    return s.strip()

class LLMService:
    BRUTALITY_COEFFICIENT = 1.6
    
    # Решена архитектурная проблема: 
    # Semaphore(1) блокировал всех пользователей. Мы меняем его на (3),
    # чтобы позволить небольшую конкурентность, избегая жесткого 429 от OpenRouter.
    # В продакшене лучше использовать нормальный rate limiter.
    RATE_LIMIT = asyncio.Semaphore(3)

    @staticmethod
    async def _call_openrouter(prompt: str, model: str, system: str = "You are a helpful assistant. Return ONLY JSON.") -> Optional[Any]:
        """Вспомогательная функция для OpenRouter с гибким авто-повтором."""
        for attempt in range(3):
            need_sleep_429 = False
            async with LLMService.RATE_LIMIT:
                try:
                    response = await or_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        max_tokens=8192,
                        timeout=180
                    )
                    txt = response.choices[0].message.content
                    if not txt:
                        continue
                    
                    if "<title>Attention Required!" in txt or "cf-browser-verification" in txt:
                        logger.error("OpenRouter blocked by Cloudflare.")
                        return None

                    for tag in ["</think>", "</thought>"]:
                        if tag in txt:
                            txt = txt.split(tag)[-1]

                    try:
                        return json.loads(clean_json_string(txt))
                    except Exception as e:
                        logger.error(f"OpenRouter JSON Parse Error (Attempt {attempt}): {e}.")
                        continue
                        
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "402" in err_str:
                        logger.warning(f"⚠️ OpenRouter Rate Limit/Balance (429/402). Attempt {attempt}")
                        need_sleep_429 = True
                    else:
                        logger.error(f"OpenRouter Fail ({model}, attempt {attempt}): {str(e)[:100]}")
                        if attempt < 2: await asyncio.sleep(2**attempt)
                        continue
            
            if need_sleep_429:
                await asyncio.sleep(5)
        return None

    @staticmethod
    async def _call_utility_model(prompt: str, model: str, system: str = "You are a helpful assistant. Return ONLY JSON.") -> Optional[Any]:
        target_model = model or "arcee-ai/trinity-large-preview:free"
        return await LLMService._call_openrouter(prompt, target_model, system)

    @staticmethod
    async def generate_all_questions(p1_gender: str, p2_gender: str, is_distance: bool) -> Optional[List[Dict[str, str]]]:
        dist_mode = "LDR" if is_distance else "COHAB"
        prompt = f"""
        Сгенерируй ПАКЕТ из 10 раундов для игры «Тест на совместимость».
        Ведущая: ироничная, дерзкая, но корректная.
        
        ПРАВИЛА:
        1. Раунды 1-3: Стандартные (быт, досуг).
        2. Раунды 4-7: Острые (финансы, ревность, секс).
        3. Раунды 8-10: Глубокие (страхи, будущее, цели).
        4. Минимум 70% вопросов ДОЛЖНЫ быть открытыми (не да/нет).
        5. Каждый раунд: intro, q1 (для p1_gender), q2 (для p2_gender).
        
        ДАННЫЕ:
        - Игрок 1: {p1_gender}
        - Игрок 2: {p2_gender}
        - Статус: {dist_mode}
        
        ВЕРНИ СТРОГО JSON: {{"rounds": [{{"intro": "...", "q1": "...", "q2": "..."}}]}}
        Элементов в списке rounds: ровно 10.
        """
        data = await LLMService._call_openrouter(prompt, MODEL_QUESTIONS, "Maid Hostess Roleplay. All rounds batch. Only JSON.")
        
        if not data:
            return None
            
        if isinstance(data, list) and len(data) > 0:
            return data[:10]
            
        if isinstance(data, dict):
            if "rounds" in data:
                return data["rounds"]
            if "q1" in data:
                return [data] * 10
            for val in data.values():
                if isinstance(val, list) and len(val) >= 5:
                     return val[:10]
                
        logger.error("Failed to extract valid rounds from Qwen response.")
        return None

    @staticmethod
    async def generate_fake_options(real_answer: str, question: str, round_num: int) -> Dict[str, Any]:
        clean_ans = real_answer.lower().strip().rstrip('.!,')
        if clean_ans in ["да", "нет", "yes", "no", "конечно", "ни за что"]:
            opposite = "Нет" if clean_ans in ["да", "yes", "конечно"] else "Да"
            return {
                "fakes": [opposite],
                "subtext": "Ироничный комментарий к короткому ответу."
            }

        prompt = f"""
        Логика ИИ «Мастер психологической мимикрии» для генерации фейковых ответов

        **Роль модели:** Ты — «Мастер психологической мимикрии».  
        Твоя задача — генерировать фейковые ответы на вопрос: "{question}".
        Реальный ответ игрока: "{real_answer}".

        # 1. ЗАДАЧА №1 (МИМИКРИЯ):
        Фейковые ответы ДОЛЖНЫ быть МАКСИМАЛЬНО схожи по стилю с реальным ответом.
        - Идентичная длина (количество слов ±1-3).
        - Идентичная пунктуация и регистр.
        - Идентичный тон (сарказм, серьезность, небрежность).

        # 2. ЗАДАЧА №2 (РАЗЛИЧИЕ):
        При полной внешней схожести, фейки ДОЛЖНЫ обозначать АБСОЛЮТНО другой ответ по смыслу.
        Не делай синонимы. Делай кардинально иные варианты.

        # 3. ПРАВИЛА:
        1. Сгенерируй 3 фейка.
        2. Суть — КАРДИНАЛЬНО другая.
        3. Сохраняй уровень "странности" оригинала.

        ВЕРНИ ТОЛЬКО JSON: {{"fakes": ["...", "...", "..."], "subtext": "..."}}
        """
        data = await LLMService._call_utility_model(prompt, MODEL_FAKES, "Master of mimicry. Style matching. Only JSON.")
        return data if data else {"fakes": ["Это секрет", "Затрудняюсь ответить", "Спроси позже"], "subtext": "Игрок сохраняет интригу."}

    @staticmethod
    async def analyze_compatibility(history: list) -> Dict[str, Any]:
        prompt = f"Анализируй историю и дай вердикт: {json.dumps(history, ensure_ascii=False)}"
        data = await LLMService._call_utility_model(prompt, MODEL_NAME, "Profiler. Only JSON.")
        return data if data else {"score": 50, "verdict": "Сложно сказать."}
