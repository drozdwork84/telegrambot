import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

from database import init_db, add_match, get_today_matches, get_matches_for_reminders, mark_as_reminded, get_next_match, delete_match, update_match_time, get_all_upcoming_matches
from parser import parse_matches, parse_match_line

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# Regex patterns for natural language commands
RE_LIST = re.compile(r"^список$", re.IGNORECASE)
RE_DELETE = re.compile(r"^удали\s+(\d+)$", re.IGNORECASE)
RE_EDIT = re.compile(r"^перенеси\s+(\d+)\s+на\s+(.+)$", re.IGNORECASE)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN ="8526120174:AAG-XU3dm3Z5vQg7N6FIUEy1Oca2vm73Fg8"
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


HELP_TEXT = (
    "Привет! Я бот для напоминаний о матчах.\n\n"
    "Просто отправьте мне текст с расписанием матчей, и я буду напоминать вам за 1 минуту до начала каждого матча.\n\n"
    "Формат даты/времени: DD.MM.YYYY HH:MM\n"
    "Например:\n"
    "16.11.2025 08:55\tДинамо — Спартак\n\n"
    "Команды:\n"
    "/start - показать это сообщение\n"
    "/help - список доступных команд\n"
    "/today - матчи на сегодня\n"
    "/list - все будущие матчи\n"
    "/next - ближайший матч\n"
    "/delete ID - удалить матч\n"
    "/edit ID Время - изменить время (например: /edit 5 18:30)"
)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command"""
    await message.answer(HELP_TEXT)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command"""
    await message.answer(HELP_TEXT)


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
        response_lines.append(f"ID: {match['id']} | {time_str} — {match['title']}")
    
    response = "\n".join(response_lines)
    await message.answer(f"Матчи на сегодня:\n\n{response}")


@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    """Show all future matches"""
    chat_id = message.chat.id
    matches = await get_all_upcoming_matches(chat_id)
    
    if not matches:
        await message.answer("Будущих матчей нет")
        return
    
    response_lines = []
    for match in matches:
        match_dt = datetime.fromisoformat(match["match_datetime"])
        time_str = match_dt.strftime("%d.%m.%Y %H:%M")
        response_lines.append(f"ID: {match['id']} | {time_str} — {match['title']}")
    
    response = "\n".join(response_lines)
    await message.answer(f"Все будущие матчи:\n\n{response}")


@dp.message(Command("delete"))
async def cmd_delete(message: types.Message):
    """Delete a match by ID"""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажите ID матча: /delete <ID>")
        return
    
    try:
        match_id = int(args[1])
        deleted = await delete_match(match_id, message.chat.id)
        if deleted:
            await message.answer(f"Матч ID {match_id} удален")
        else:
            await message.answer(f"Матч с ID {match_id} не найден")
    except ValueError:
        await message.answer("ID должен быть числом")


@dp.message(Command("edit"))
async def cmd_edit(message: types.Message):
    """Edit match time by ID"""
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Использование: /edit <ID> <Новое время>\nНапример: /edit 5 18:30 или /edit 5 16.11.2025 18:30")
        return
    
    try:
        match_id = int(args[1])
        time_text = args[2]
        
        # Try to parse new time/datetime
        parsed = parse_match_line(time_text, current_dt=datetime.now(MOSCOW_TZ))
        if not parsed:
            await message.answer("Не удалось распознать время. Используйте форматы: HH:MM или DD.MM.YYYY HH:MM")
            return
        
        new_dt, _ = parsed
        updated = await update_match_time(match_id, message.chat.id, new_dt)
        
        if updated:
            await message.answer(f"Время матча ID {match_id} изменено на {new_dt.strftime('%d.%m.%Y %H:%M')}")
        else:
            await message.answer(f"Матч с ID {match_id} не найден")
            
    except ValueError:
        await message.answer("ID должен быть числом")


@dp.message(Command("next"))
async def cmd_next(message: types.Message):
    """Show the next upcoming match"""
    chat_id = message.chat.id
    match = await get_next_match(chat_id)
    if not match:
        await message.answer("Нет ближайших будущих матчей.")
    else:
        match_dt = datetime.fromisoformat(match["match_datetime"])
        time_str = match_dt.strftime("%d.%m.%Y %H:%M")
        await message.answer(f"Ближайший матч (ID: {match['id']}):\n{time_str} — {match['title']}")


async def handle_natural_language(message: types.Message) -> bool:
    """Check if message matches natural language commands and execute them"""
    text = message.text.strip()
    
    # Check for "список"
    if RE_LIST.match(text):
        await cmd_list(message)
        return True
        
    # Check for "удали ID"
    match_delete = RE_DELETE.match(text)
    if match_delete:
        match_id = match_delete.group(1)
        # Rewrite message text to simulate command
        message.text = f"/delete {match_id}"
        await cmd_delete(message)
        return True
        
    # Check for "перенеси ID на TIME"
    match_edit = RE_EDIT.match(text)
    if match_edit:
        match_id = match_edit.group(1)
        new_time = match_edit.group(2)
        # Rewrite message text to simulate command
        message.text = f"/edit {match_id} {new_time}"
        await cmd_edit(message)
        return True
        
    return False


@dp.message(F.text)
async def handle_text(message: types.Message):
    """Handle text messages - parse matches and add to database"""
    if not message.text:
        return
    
    # Try to handle as natural language command first
    if await handle_natural_language(message):
        return
    
    if message.text.startswith('/'):
        return
    
    chat_id = message.chat.id
    text = message.text
    
    matches = parse_matches(text, current_dt=datetime.now(MOSCOW_TZ))
    
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
            now = datetime.now(MOSCOW_TZ)
            matches = await get_matches_for_reminders()
            
            for match in matches:
                match_dt = datetime.fromisoformat(match["match_datetime"])
                
                time_diff = match_dt - now
                total_seconds = time_diff.total_seconds()
                
                if 45 <= total_seconds <= 75:
                    time_str = match_dt.strftime("%H:%M")
                    message_text = f"{time_str} {match['title']}"
                    
                    try:
                        await bot.send_message(chat_id=match["chat_id"], text=message_text)
                        await mark_as_reminded(match["id"])
                        logger.info(f"Sent reminder for match {match['id']}: {match['title']}")
                    except Exception as e:
                        logger.error(f"Failed to send reminder for match {match['id']}: {e}")
            
            await asyncio.sleep(15)
        
        except Exception as e:
            logger.error(f"Error in reminder scheduler: {e}")
            await asyncio.sleep(15)


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



