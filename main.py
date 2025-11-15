import asyncio
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

from database import init_db, add_match, get_today_matches, get_matches_for_reminders, mark_as_reminded
from parser import parse_matches

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command"""
    await message.answer(
        "Привет! Я бот для напоминаний о матчах.\n\n"
        "Просто отправьте мне текст с расписанием матчей, и я буду напоминать вам за 1 минуту до начала каждого матча.\n\n"
        "Формат даты/времени: DD.MM.YYYY HH:MM\n"
        "Например:\n"
        "16.11.2025 08:55\tДинамо — Спартак\n\n"
        "Команды:\n"
        "/start - показать это сообщение\n"
        "/today - показать матчи на сегодня"
    )


@dp.message(Command("today"))
async def cmd_today(message: types.Message):
    """Handle /today command - show today's upcoming matches"""
    chat_id = message.chat.id
    matches = await get_today_matches(chat_id)
    
    if not matches:
        await message.answer("На сегодня будущих матчей нет")
        return
    
    response_lines = []
    for match in matches:
        match_dt = datetime.fromisoformat(match["match_datetime"])
        time_str = match_dt.strftime("%H:%M")
        response_lines.append(f"{time_str} — {match['title']}")
    
    response = "\n".join(response_lines)
    await message.answer(f"Матчи на сегодня:\n\n{response}")


@dp.message(F.text)
async def handle_text(message: types.Message):
    """Handle text messages - parse matches and add to database"""
    if not message.text:
        return
    
    if message.text.startswith('/'):
        return
    
    chat_id = message.chat.id
    text = message.text
    
    matches = parse_matches(text)
    
    if not matches:
        await message.answer("Не удалось распознать ни одного матча. Проверьте формат даты/времени (DD.MM.YYYY HH:MM)")
        return
    
    for match_dt, title in matches:
        await add_match(chat_id, match_dt, title)
    
    count = len(matches)
    await message.answer(f"Добавлено матчей: {count}")


async def reminder_scheduler():
    """Background task that checks for matches and sends reminders"""
    logger.info("Reminder scheduler started")
    
    while True:
        try:
            await asyncio.sleep(30)
            
            now = datetime.now(MOSCOW_TZ)
            matches = await get_matches_for_reminders()
            
            for match in matches:
                match_dt = datetime.fromisoformat(match["match_datetime"])
                
                time_diff = match_dt - now
                
                if timedelta(seconds=50) <= time_diff <= timedelta(seconds=70):
                    time_str = match_dt.strftime("%H:%M")
                    message_text = f"Через минуту матч в {time_str} — {match['title']}"
                    
                    try:
                        await bot.send_message(chat_id=match["chat_id"], text=message_text)
                        await mark_as_reminded(match["id"])
                        logger.info(f"Sent reminder for match {match['id']}: {match['title']}")
                    except Exception as e:
                        logger.error(f"Failed to send reminder for match {match['id']}: {e}")
        
        except Exception as e:
            logger.error(f"Error in reminder scheduler: {e}")
            await asyncio.sleep(30)


async def main():
    """Main entry point"""
    logger.info("Initializing database...")
    await init_db()
    
    logger.info("Starting reminder scheduler...")
    scheduler_task = asyncio.create_task(reminder_scheduler())
    
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
