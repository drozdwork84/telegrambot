import re
from datetime import datetime
from typing import List, Tuple, Optional
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

DATE_FORMATS = [
    r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})",
    r"(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})",
    r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})",
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})",
]

DATETIME_PARSERS = [
    "%d.%m.%Y %H:%M",
    "%d.%m.%y %H:%M",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M",
]


def parse_match_line(line: str) -> Optional[Tuple[datetime, str]]:
    """
    Parse a line of text to extract match datetime and title.
    Returns (datetime, title) or None if parsing failed.
    """
    line = line.strip()
    if not line:
        return None
    
    for pattern, fmt in zip(DATE_FORMATS, DATETIME_PARSERS):
        match = re.match(pattern, line)
        if match:
            try:
                date_str = match.group(1)
                time_str = match.group(2)
                datetime_str = f"{date_str} {time_str}"
                
                match_dt = datetime.strptime(datetime_str, fmt)
                match_dt = match_dt.replace(tzinfo=MOSCOW_TZ)
                
                remainder = line[match.end():].strip()
                
                if '\t' in remainder:
                    parts = remainder.split('\t')
                    parts = [p.strip() for p in parts if p.strip()]
                    
                    if len(parts) >= 3:
                        title = parts[2]
                    elif len(parts) >= 1:
                        title = parts[0]
                    else:
                        title = remainder
                else:
                    parts = remainder.split()
                    if len(parts) >= 3:
                        title = ' '.join(parts[2:])
                    elif len(parts) > 0:
                        title = remainder
                    else:
                        title = "Матч"
                
                return (match_dt, title)
            except ValueError:
                continue
    
    return None


def parse_matches(text: str) -> List[Tuple[datetime, str]]:
    """
    Parse multi-line text to extract all matches.
    Returns a list of (datetime, title) tuples.
    """
    lines = text.split('\n')
    matches = []
    
    for line in lines:
        result = parse_match_line(line)
        if result:
            matches.append(result)
    
    return matches
