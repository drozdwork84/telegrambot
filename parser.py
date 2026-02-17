import re
from datetime import datetime
from typing import List, Tuple, Optional
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

DATE_FORMATS = [
    r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2})[:\-](\d{2})",   # 16.11.2025 18:30 или 18-30
    r"(\d{2}\.\d{2}\.\d{2})\s+(\d{2})[:\-](\d{2})",
    r"(\d{4}-\d{2}-\d{2})\s+(\d{2})[:\-](\d{2})",
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2})[:\-](\d{2})",
]

DATETIME_PARSERS = [
    "%d.%m.%Y %H:%M",
    "%d.%m.%y %H:%M",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
]

# Новый шаблон только для времени, например "18:10 что-то", "20-09 Матч"
TIME_ONLY_REGEX = re.compile(r"^(\d{2})[:\-](\d{2})\s+[–-]?\s*(.+)$")

def parse_match_line(line: str, current_dt: Optional[datetime]=None) -> Optional[Tuple[datetime, str]]:
    """
    Parse a line of text to extract match datetime and title.
    Returns (datetime, title) or None if parsing failed.
    """
    line = line.strip()
    if not line:
        return None

    # Сначала пробуем полные форматы
    for pattern, fmt in zip(DATE_FORMATS, DATETIME_PARSERS):
        match = re.match(pattern, line)
        if match:
            try:
                date_str = match.group(1)
                hour = match.group(2)
                minute = match.group(3)
                datetime_str = f"{date_str} {hour}:{minute}"

                match_dt = datetime.strptime(datetime_str, fmt)
                match_dt = match_dt.replace(tzinfo=MOSCOW_TZ)

                remainder = line[match.end():].strip()
                title = remainder if remainder else "Матч"
                return (match_dt, title)
            except ValueError:
                continue

    # Если только время и событие (18:50 Матч, 17-05 Название)
    m = TIME_ONLY_REGEX.match(line)
    if m:
        hour, minute, title = m.groups()
        if not title:
            title = "Матч"
        # Принимаем за "сегодня" в заданном часовом поясе
        now = current_dt.astimezone(MOSCOW_TZ) if current_dt else datetime.now(MOSCOW_TZ)
        match_dt = now.replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        return (match_dt, title.strip())

    return None

def parse_matches(text: str, current_dt: Optional[datetime]=None) -> List[Tuple[datetime, str]]:
    """
    Parse multi-line text to extract all matches.
    Returns a list of (datetime, title) tuples.
    """
    lines = text.split('\n')
    matches = []

    for line in lines:
        result = parse_match_line(line, current_dt=current_dt)
        if result:
            matches.append(result)

    return matches
