import asyncio
import logging
import random
import uuid
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.fsm import GameStates
from src.services.llm import LLMService
from src.services.session_manager import game_sessions
from src.database.connection import get_user_data, save_user_gender, save_user_residency

logger = logging.getLogger(__name__)
router = Router()

async def start_background_generation(game_id: str, p1_gender: str, is_distance: bool):
    """Фоновая задача для Qwen, запускается максимально рано."""
    try:
        logger.info(f"🚀 [Генерация] Запуск Qwen для {game_id} (пол P1: {p1_gender})...")
        guessed_p2_gender = "Женщина" if p1_gender == "Мужчина" else "Мужчина"
        rounds = await LLMService.generate_all_questions(p1_gender, guessed_p2_gender, is_distance)
        
        game = game_sessions.get_game(game_id)
        if game:
            if rounds:
                game["rounds"] = rounds
                logger.info(f"✅ [Генерация] Вопросы для {game_id} готовы.")
            else:
                game["generation_failed"] = True
                logger.warning(f"❌ [Генерация] Не удалось получить вопросы для {game_id}.")
    except Exception as e:
        logger.error(f"Background generation error: {e}", exc_info=True)
        game = game_sessions.get_game(game_id)
        if game:
            game["generation_failed"] = True

def get_gender_kb():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="👨 Мужчина", callback_data="set_gender_m"))
    builder.row(types.InlineKeyboardButton(text="👩 Женщина", callback_data="set_gender_f"))
    return builder.as_markup()

@router.message(Command("start"))
@router.message(Command("abort"))
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    args = message.text.split(" ")
    if len(args) > 1 and args[1].startswith("join_"):
        game_id = args[1].replace("join_", "")
        await state.update_data(pending_game_id=game_id)
        
        user_data = await get_user_data(message.from_user.id)
        if user_data and user_data.get("gender"):
            await state.update_data(gender=user_data["gender"])
            return await handle_join_logic(message, state, bot, game_id)
            
        await state.set_state(GameStates.CHOOSING_GENDER)
        return await message.answer(
            "👿 <b>Добро пожаловать в игру!</b>\n\nПрежде чем войти, выбери свой пол:", 
            parse_mode="HTML", 
            reply_markup=get_gender_kb()
        )

    await state.clear()
    user_data = await get_user_data(message.from_user.id)
    if user_data and user_data.get("gender"):
        gender = user_data["gender"]
        is_dist_saved = user_data.get("is_distance")
        await state.update_data(gender=gender)
        
        game_id = str(uuid.uuid4())[:8]
        await state.update_data(game_id=game_id)
        
        if is_dist_saved:
            is_distance = True if is_dist_saved == "yes" else False
            await state.update_data(is_distance=is_distance)
            game_sessions.create_game(game_id, message.chat.id, gender, is_distance)
            
            asyncio.create_task(start_background_generation(game_id, gender, is_distance))
            await state.set_state(GameStates.WAITING_JOIN)
            await state.update_data(role="p1")
            me = await bot.get_me()
            link = f"https://t.me/{me.username}?start=join_{game_id}"
            
            builder = InlineKeyboardBuilder()
            share_text = f"Я рискнул пройти тест на совместимость с ИИ. Ты со мной? Заходи: {link}"
            builder.row(types.InlineKeyboardButton(text="🚀 Бросить вызов партнеру", switch_inline_query=share_text))
            
            return await message.answer(
                f"👿 <b>Комната готова!</b>\n\nКод: <code>{game_id}</code>\n\nМожешь отправить ссылку партнеру вручную или нажать кнопку ниже.\n\n<code>{link}</code>\n\n<i>P.S. ИИ-ведущий закончит подготовку вопросов, пока твой партнер заходит.</i>",
                parse_mode="HTML",
                reply_markup=builder.as_markup()
            )
            
        game_sessions.create_game(game_id, message.chat.id, gender, False)
        asyncio.create_task(start_background_generation(game_id, gender, False))
        
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🏠 Живем вместе", callback_data="set_dist_no"))
        builder.row(types.InlineKeyboardButton(text="✈️ На расстоянии", callback_data="set_dist_yes"))
        await state.set_state(GameStates.CHOOSING_DISTANCE)
        await message.answer("Добро пожаловать. Вы находитесь на расстоянии или живете вместе?", reply_markup=builder.as_markup())
    else:
        await state.set_state(GameStates.CHOOSING_GENDER)
        await message.answer("Добро пожаловать. Кто ты?", reply_markup=get_gender_kb())

@router.callback_query(F.data.startswith("set_gender_"))
async def handle_gender(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    gender = "Мужчина" if callback.data.endswith("m") else "Женщина"
    await state.update_data(gender=gender)
    await save_user_gender(callback.from_user.id, gender, callback.from_user.username)
    
    data = await state.get_data()
    pending_game_id = data.get("pending_game_id")
    
    if pending_game_id:
        return await handle_join_logic(callback.message, state, bot, pending_game_id)
        
    game_id = str(uuid.uuid4())[:8]
    await state.update_data(game_id=game_id)
    game_sessions.create_game(game_id, callback.message.chat.id, gender, False)
    
    asyncio.create_task(start_background_generation(game_id, gender, False))
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏠 Живем вместе", callback_data="set_dist_no"))
    builder.row(types.InlineKeyboardButton(text="✈️ На расстоянии", callback_data="set_dist_yes"))
    
    await callback.message.edit_text("Вы находитесь на расстоянии или живете вместе?", reply_markup=builder.as_markup())
    await state.set_state(GameStates.CHOOSING_DISTANCE)

@router.callback_query(F.data.startswith("set_dist_"))
async def handle_distance(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    is_dist_str = "yes" if callback.data.endswith("yes") else "no"
    is_distance = True if is_dist_str == "yes" else False
    
    data = await state.get_data()
    await state.update_data(is_distance=is_distance)
    await save_user_residency(callback.from_user.id, is_dist_str)
    
    game_id = data.get("game_id")
    game = game_sessions.get_game(game_id) if game_id else None
    
    if game:
        old_dist = game.get("is_distance")
        game["is_distance"] = is_distance
        if is_distance != old_dist and not game.get("rounds"):
             logger.info(f"🔄 Смена дистанции для {game_id}. Перезапуск генерации...")
             asyncio.create_task(start_background_generation(game_id, game["p1_gender"], is_distance))
    
    await callback.message.edit_text("⏳ ИИ-ведущий изучает ваше грязное белье... Подождите.")
    await create_game_logic(callback.message, state, bot)

async def create_game_logic(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    game_id = data.get("game_id")
    
    await state.set_state(GameStates.WAITING_JOIN)
    
    if not game_id:
        game_id = str(uuid.uuid4())[:8]
        await state.update_data(game_id=game_id)
        gender = data.get("gender", "Мужчина")
        is_dist = data.get("is_distance", False)
        game_sessions.create_game(game_id, message.chat.id, gender, is_dist)
        asyncio.create_task(start_background_generation(game_id, gender, is_dist))

    await state.update_data(role="p1")
    
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=join_{game_id}"
    
    builder = InlineKeyboardBuilder()
    share_text = f"Я рискнул пройти тест на совместимость с ИИ. Ты со мной? Заходи: {link}"
    builder.row(types.InlineKeyboardButton(text="🚀 Бросить вызов партнеру", switch_inline_query=share_text))
    
    await bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=f"👿 <b>Комната готова!</b>\n\nКод: <code>{game_id}</code>\n\nМожешь отправить ссылку партнеру вручную или нажать кнопку ниже.\n\n<code>{link}</code>\n\n<i>P.S. ИИ-ведущий закончит подготовку вопросов, пока твой партнер заходит.</i>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

async def trigger_next_round(bot: Bot, storage, game_id: str):
    game = game_sessions.get_game(game_id)
    if not game: return
    game["current_round"] += 1
    round_num = game["current_round"]
    
    if round_num > 10: 
        return asyncio.create_task(start_guessing_phase(bot, storage, game_id))

    try:
        for attempt in range(180):
            if game.get("generation_failed"):
                if not game.get("error_notified"):
                    game["error_notified"] = True
                    for uid in [game["p1"], game["p2"]]:
                        await bot.send_message(uid, "❌ <b>Ошибка генерации:</b> ИИ отказался сотрудничать. Игра прервана, попробуйте /start заново.", parse_mode="HTML")
                return
            
            if game.get("rounds") and len(game["rounds"]) >= 10:
                break
            
            if round_num == 1 and attempt > 0 and attempt % 15 == 0:
                for uid in [game["p1"], game["p2"]]:
                    await bot.send_message(uid, "⏳ <i>Ведущая всё еще листает ваше дело... Почти готово.</i>", parse_mode="HTML")
            
            await asyncio.sleep(1)
            
        if not game.get("rounds") or len(game["rounds"]) < round_num:
            for uid in [game["p1"], game["p2"]]:
                await bot.send_message(uid, "⏱ <b>Тайм-аут:</b> ИИ слишком долго думает. Попробуйте начать новую игру позднее.")
            return

        ai_data = game["rounds"][round_num-1]
        
        intro = ai_data.get("intro", "Продолжаем наш допрос...")
        # Hardcoded filename removed from logic, handled gracefully
        welcome_photo_path = "assets/welcome.png"
        
        for uid in [game["p1"], game["p2"]]:
            if round_num == 1:
                try:
                    welcome_photo = types.FSInputFile(welcome_photo_path)
                    await bot.send_photo(
                        uid, 
                        photo=welcome_photo, 
                        caption=f"🎙 <b>ВЕДУЩАЯ:</b>\n<i>«{intro}»</i>", 
                        parse_mode="HTML"
                    )
                except Exception:
                    # Fallback if image doesn't exist
                    await bot.send_message(uid, f"🎙 <b>ВЕДУЩАЯ:</b>\n<i>«{intro}»</i>", parse_mode="HTML")
            else:
                await bot.send_message(uid, f"🎙 <b>ВЕДУЩАЯ:</b>\n<i>«{intro}»</i>", parse_mode="HTML")
            
            q_idx = 1 if uid == game["p1"] else 2
            question = ai_data.get(f"q{q_idx}", "Как твои дела?")
            
            key = StorageKey(bot_id=bot.id, chat_id=uid, user_id=uid)
            u_state = FSMContext(storage=storage, key=key)
            await u_state.set_state(GameStates.WAITING_ANSWERS)
            await bot.send_message(uid, f"❓ <b>РАУНД {round_num}:</b>\n\n{question}", parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"ERROR in trigger_next_round: {e}")

@router.message(GameStates.WAITING_ANSWERS)
async def handle_text_answer(message: types.Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    game_id = user_data.get("game_id")
    game = game_sessions.get_game(game_id)
    if not game: return
    
    round_num = game["current_round"]
    if round_num not in game["answers"]: game["answers"][round_num] = {}

    game["answers"][round_num][message.from_user.id] = {"real": message.text}
    await message.answer("✅ Ответ принят. Ждем партнера...")
    
    if len(game["answers"][round_num]) == 2:
        if game.get("last_triggered_round") == round_num:
            return
        game["last_triggered_round"] = round_num
        
        async def fetch_and_save_fakes(uid):
            ans_data = game["answers"][round_num][uid]
            q_idx = 1 if uid == game["p1"] else 2
            q_text = game["rounds"][round_num-1].get(f"q{q_idx}")
            analysis = await LLMService.generate_fake_options(ans_data["real"], q_text, round_num)
            ans_data["fakes"] = analysis.get("fakes", ["Option 1", "Option 2", "Option 3"])
            ans_data["subtext"] = analysis.get("subtext", "")
            
        await asyncio.gather(
            fetch_and_save_fakes(game["p1"]),
            fetch_and_save_fakes(game["p2"])
        )
        
        asyncio.create_task(trigger_next_round(bot, state.storage, game_id))

async def start_guessing_phase(bot: Bot, storage, game_id: str):
    game = game_sessions.get_game(game_id)
    if not game: return
    
    for uid in [game["p1"], game["p2"]]:
        await bot.send_message(uid, "🏁 <b>Все вопросы заданы!</b>\nТеперь самое интересное: угадай, где ответ твоего партнера. Поехали!", parse_mode="HTML")
        await ask_guess_question(bot, storage, game_id, uid, 1)

async def ask_guess_question(bot: Bot, storage, game_id: str, user_id: int, r_num: int):
    game = game_sessions.get_game(game_id)
    partner_id = game["p2"] if user_id == game["p1"] else game["p1"]
    
    partner_q_idx = 1 if partner_id == game["p1"] else 2
    partner_question = game["rounds"][r_num-1].get(f"q{partner_q_idx}")
    partner_ans_data = game["answers"][r_num][partner_id]
    
    options = partner_ans_data.get("fakes", ["-", "-", "-"]) + [partner_ans_data["real"]]
    random.shuffle(options)
    
    builder = InlineKeyboardBuilder()
    for opt in options:
        is_correct = "1" if opt == partner_ans_data["real"] else "0"
        builder.row(types.InlineKeyboardButton(text=opt, callback_data=f"guess_{game_id}_{r_num}_{is_correct}"))
    
    key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    u_state = FSMContext(storage=storage, key=key)
    await u_state.set_state(GameStates.GUESSING)
    
    await bot.send_message(user_id, f"🧐 <b>ВОПРОС ПАРТНЕРА ({r_num}/10):</b>\n<i>{partner_question}</i>\n\n<b>Что он(а) ответил(а)?</b>", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("guess_"))
async def handle_guess(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    _, game_id, r_num, is_correct = callback.data.split("_")
    r_num = int(r_num)
    game = game_sessions.get_game(game_id)
    if not game: return
    
    uid = callback.from_user.id
    if is_correct == "1":
        game["results"][uid] = game.get("results", {}).get(uid, 0) + 1
        await callback.message.edit_text("✅ <b>Верно!</b> Ты чувствуешь партнера.", parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ <b>Мимо!</b> ИИ перехитрил тебя.", parse_mode="HTML")
    
    if r_num < 10:
        await ask_guess_question(bot, state.storage, game_id, uid, r_num + 1)
    else:
        await callback.message.answer("🙌 Ты закончил угадывать! Ждем партнера для финального вердикта.")
        game["finished_guessing"].add(uid)
        
        if len(game["finished_guessing"]) == 2:
            await finish_game(bot, state.storage, game_id)

async def handle_join_logic(message: types.Message, state: FSMContext, bot: Bot, game_id: str):
    game = game_sessions.get_game(game_id)
    if not game: 
        return await message.answer("❌ Комната не найдена. Возможно, бот был перезагружен.")
    
    data = await state.get_data()
    game["p2"] = message.chat.id
    game["p2_gender"] = data.get("gender", "Женщина")
    await state.update_data(game_id=game_id, role="p2")
    
    if isinstance(message, types.CallbackQuery):
        await message.message.answer("😈 Ты в игре! ИИ-ведущий подбирает самые неудобные вопросы...")
    else:
        await message.answer("😈 Ты в игре! ИИ-ведущий подбирает самые неудобные вопросы...")
    
    await bot.send_message(game["p1"], "👤 Партнер зашел! ИИ-ведущий заряжает вопросы... ⏳")
    
    asyncio.create_task(trigger_next_round(bot, state.storage, game_id))

async def finish_game(bot: Bot, storage, game_id: str):
    game = game_sessions.get_game(game_id)
    if not game: return
    
    history_to_analyze = []
    for r_idx, r_data in enumerate(game.get("rounds", [])):
        round_num = r_idx + 1
        p1_ans = game["answers"].get(round_num, {}).get(game["p1"], {}).get("real", "Нет ответа")
        p2_ans = game["answers"].get(round_num, {}).get(game["p2"], {}).get("real", "Нет ответа")
        history_to_analyze.append({
            "round": round_num,
            "topic": r_data.get("topic"),
            "q1": r_data.get("q1"),
            "ans1": p1_ans,
            "q2": r_data.get("q2"),
            "ans2": p2_ans
        })

    for uid in [game["p1"], game["p2"]]:
        await bot.send_message(uid, "📋 <b>ИИ-ведущий анализирует вашу совместимость...</b>\nЭто займет около 10-15 секунд.", parse_mode="HTML")

    try:
        report = await LLMService.analyze_compatibility(history_to_analyze)
        score = report.get("score", 50)
        verdict = report.get("verdict", "Вы — загадка.")
        red_flag = report.get("red_flag", "Особых рисков не обнаружено.")
        
        final_msg = (
            f"📊 <b>ИТОГОВЫЙ ОТЧЕТ:</b>\n\n"
            f"🔥 <b>Совместимость: {score}%</b>\n\n"
            f"🎭 <b>Вердикт:</b> {verdict}\n\n"
            f"🚩 <b>Red Flag:</b> {red_flag}\n\n"
            f"<i>Игра окончена. Теперь живите с этим.</i>"
        )
        
        for uid in [game["p1"], game["p2"]]:
            await bot.send_message(uid, final_msg, parse_mode="HTML")
            key = StorageKey(bot_id=bot.id, chat_id=uid, user_id=uid)
            u_state = FSMContext(storage=storage, key=key)
            await u_state.clear()
            
    except Exception as e:
        logger.error(f"Finish Game Error: {e}")
        for uid in [game["p1"], game["p2"]]:
            await bot.send_message(uid, "❌ Ошибка при генерации финального отчета. Но мы то знаем, что вы подходите друг другу!")
    
    # Clean up memory
    game_sessions.delete_game(game_id)
