# Telegram Match Reminder Bot

## Overview
A Telegram bot that parses match schedules from text messages and sends reminders 1 minute before each match starts. Built with Python using aiogram (async Telegram framework) and SQLite for data storage. All times are handled in Moscow timezone (Europe/Moscow).

## Features
- Parse match data from multi-line text messages with flexible date formats
- Store matches per chat (isolated match lists for different chats)
- Send automatic reminders 1 minute before match start time
- Commands:
  - `/start` - Show welcome message and instructions
  - `/today` - Display all upcoming matches for today
- Background scheduler that checks every 30 seconds for matches needing reminders
- Supports tab-separated and space-separated match data

## Project Structure
- `main.py` - Main bot entry point with command handlers and reminder scheduler
- `database.py` - SQLite database operations (create, read, update matches)
- `parser.py` - Text parsing logic to extract match datetime and titles
- `matches.db` - SQLite database file (auto-created on first run)

## Configuration
Required environment variable:
- `BOT_TOKEN` - Telegram bot token from @BotFather

## Database Schema
Table: `matches`
- `id` - Primary key
- `chat_id` - Telegram chat ID
- `match_datetime` - ISO format datetime string (Moscow timezone)
- `title` - Match name/description
- `reminded` - Boolean flag (0/1) indicating if reminder was sent
- `created_at` - Record creation timestamp

## Supported Date Formats
- DD.MM.YYYY HH:MM (primary format)
- DD.MM.YY HH:MM
- YYYY-MM-DD HH:MM
- DD/MM/YYYY HH:MM

## How It Works
1. User sends text with match schedule (one match per line)
2. Bot parses each line to extract datetime and match title
3. Matches are stored in database linked to the chat
4. Background scheduler runs every 30 seconds
5. When current time is 50-70 seconds before match time, reminder is sent
6. Match is marked as reminded to prevent duplicates

## Recent Changes
- 2025-11-15: Initial project creation with full bot functionality
