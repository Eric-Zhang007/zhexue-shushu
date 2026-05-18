#!/usr/bin/env python3
"""
JieQiCore - Python port of 问真八字 App's 节气/起运 calculation engine.
Extracted via decompilation of dex_main.dex.
"""
import re
from datetime import datetime, timedelta

# Load the full 节气 data string (1800-2100)
_DATA_RAW = open('/tmp/jieqi_data.txt', 'r', encoding='utf-8').read()

# Parse into: year -> { month_index -> [节气名, 日(string), 时间(string)] }
# month_index: 1=寅月(立春), 2=卯月(惊蛰), ..., 12=丑月(小寒)
JIE_NAMES = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
             "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]
ZHONG_NAMES = ["雨水", "春分", "谷雨", "小满", "夏至", "大暑",
               "处暑", "秋分", "霜降", "小雪", "冬至", "大寒"]

_jieqi_a = {}  # year -> {month -> [name, day_str, time_str]}


def _parse_data():
    global _jieqi_a
    if _jieqi_a:
        return
    blocks = _DATA_RAW.split('@')
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        parts = block.split('|')
        if len(parts) < 3:
            continue
        year = int(parts[0])
        month_map = {}
        # Find each of the 12 节 in this year's data
        for name in JIE_NAMES:
            for j in range(1, len(parts) - 1, 2):
                if parts[j] == name:
                    date_str = parts[j + 1]  # "02-04 01:55:34"
                    month_str, rest = date_str.split('-', 1)
                    day_str, time_str = rest.split(' ')
                    cal_month = int(month_str)
                    month_map[cal_month] = [name, day_str, time_str]
                    break
        _jieqi_a[year] = month_map


def time_to_minutes(t):
    """Convert 'HH:mm:ss' to minutes since midnight."""
    h, m, s = t.split(':')
    return int(h) * 60 + int(m) + (int(s) / 60)


def minutes_to_time(minutes):
    """Convert minutes back to 'HH:mm:ss'."""
    total_sec = int(minutes * 60)
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_jieqi(year, month):
    """Get [节气名, 日, 时间] for a given year and month (1=寅月)."""
    _parse_data()
    if year in _jieqi_a and month in _jieqi_a[year]:
        return _jieqi_a[year][month]
    return None


def b(year, month, day):
    """Check if given day matches the 节气 day for this year/month.
    Returns [节气名, 日, 时间] if match, else None.
    """
    entry = get_jieqi(year, month)
    if entry and int(entry[1]) == day:
        return entry
    return None


def g(date_str):
    """Adjust date backward to the previous 节气 boundary.
    Input: "YYYY年MM月DD日 HH:mm:ss"
    Returns: "YYYY年M月D日 HH:mm:ss" (adjusted to 节气 date)
    """
    _parse_data()
    # Parse input
    m = re.match(r'(\d+)年(\d+)月(\d+)日 (\d+:\d+:\d+)', date_str)
    if not m:
        return ""
    year = int(m.group(1))
    month = int(m.group(2))
    day = int(m.group(3))
    time_str = m.group(4)

    current_minutes = time_to_minutes(time_str) + (day - 1) * 1440

    # Get current month's 节气
    entry = get_jieqi(year, month)
    if entry is None:
        return ""

    jieqi_day = int(entry[1])
    jieqi_minutes = time_to_minutes(entry[2]) + (jieqi_day - 1) * 1440

    if current_minutes >= jieqi_minutes:
        # We're past the 节气, this month is correct
        return f"{year}年{month}月{jieqi_day}日 {entry[2]}"

    # Before the 节气, go to previous month
    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year = year - 1

    prev_entry = get_jieqi(prev_year, prev_month)
    if prev_entry is None:
        return ""
    return f"{prev_year}年{prev_month}月{prev_entry[1]}日 {prev_entry[2]}"


def e(date_str):
    """Adjust date FORWARD to the next 节气 boundary.
    Input: "YYYY年MM月DD日 HH:mm:ss"
    """
    _parse_data()
    m = re.match(r'(\d+)年(\d+)月(\d+)日 (\d+:\d+:\d+)', date_str)
    if not m:
        return ""
    year = int(m.group(1))
    month = int(m.group(2))
    day = int(m.group(3))
    time_str = m.group(4)

    current_minutes = time_to_minutes(time_str) + (day - 1) * 1440

    entry = get_jieqi(year, month)
    if entry is None:
        return ""

    jieqi_day = int(entry[1])
    jieqi_minutes = time_to_minutes(entry[2]) + (jieqi_day - 1) * 1440

    if current_minutes <= jieqi_minutes:
        return f"{year}年{month}月{jieqi_day}日 {entry[2]}"

    # Past the 节气, go to next month
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year = year + 1

    next_entry = get_jieqi(next_year, next_month)
    if next_entry is None:
        return ""
    return f"{next_year}年{next_month}月{next_entry[1]}日 {next_entry[2]}"


def f(date_str):
    """Like g() but returns 'YYYY-MM-DD HH:mm:ss|节气名' format."""
    result = g(date_str)
    if not result:
        return ""
    m = re.match(r'(\d+)年(\d+)月(\d+)日 (\d+:\d+:\d+)', result)
    if not m:
        return ""
    entry = get_jieqi(int(m.group(1)), int(m.group(2)))
    name = entry[0] if entry else ""
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} {m.group(4)}|{name}"


def h(date_str1, date_str2):
    """Compare two dates against the 节气 table.
    Returns the 节气 name range, e.g. "立春-惊蛰"
    """
    _parse_data()
    # Parse both dates
    for ds in [date_str1, date_str2]:
        m = re.match(r'(\d+)年(\d+)月(\d+)日', ds)
        if not m:
            return ""
        year = int(m.group(1))
        month = int(m.group(2))
        day = int(m.group(3))

        # Find which 节气 period this date falls in
        entry = get_jieqi(year, month)
        if entry is None:
            continue
        jieqi_day = int(entry[1])

        if day >= jieqi_day:
            return entry[0]  # Current 节气 name

        # Before the 节气, previous period
        prev_month = month - 1
        prev_year = year
        if prev_month < 1:
            prev_month = 12
            prev_year = year - 1
        prev_entry = get_jieqi(prev_year, prev_month)
        if prev_entry:
            return prev_entry[0]

    return ""


def get_solar_month_idx(year, month, day):
    """Determine the solar month index (0=丑月/小寒, 1=寅月/立春, ...)
    based on the 节气 data. Returns 0-11.
    """
    _parse_data()
    date_str = f"{year}年{month:02d}月{day:02d}日 12:00:00"
    result = g(date_str)
    if not result:
        return _simple_solar_month_idx(year, month, day)

    m = re.match(r'(\d+)年(\d+)月', result)
    if not m:
        return _simple_solar_month_idx(year, month, day)

    adjusted_month = int(m.group(2))
    # Calendar month → solar index: 1→0(丑), 2→1(寅), 3→2(卯), ..., 12→11(子)
    return adjusted_month - 1


def _simple_solar_month_idx(year, month, day):
    """Fallback: simple JIE_TERMS lookup."""
    from zhexue_core import JIE_TERMS
    for i in range(12):
        tm, td = JIE_TERMS[i]
        next_idx = (i + 1) % 12
        next_tm, next_td = JIE_TERMS[next_idx]
        if i == 11:
            if (month == 12 and day >= td) or (month == 1 and day < JIE_TERMS[0][1]):
                return i
        else:
            if (month == tm and day >= td) or (month == next_tm and day < next_td):
                return i
            if month > tm and month < next_tm:
                return i
    return 0


def calc_dayun_start_age(year, month, day, hour, minute, shun_pai):
    """Calculate accurate 起运 age based on distance to next/prev 节气.
    Formula: days_to_jieqi / 3 = start_age_years
    """
    _parse_data()
    date_str = f"{year}年{month:02d}月{day:02d}日 {hour:02d}:{minute:02d}:00"

    # Get adjusted date to find which 节气 period we're in
    adjusted = g(date_str)
    if not adjusted:
        return 6.0  # Fallback

    m = re.match(r'(\d+)年(\d+)月(\d+)日 (\d+:\d+:\d+)', adjusted)
    if not m:
        return 6.0

    adj_year = int(m.group(1))
    adj_month = int(m.group(2))
    adj_day = int(m.group(3))
    adj_time = m.group(4)

    # The 节气 date of our period
    try:
        birth = datetime(year, month, day, hour, minute)
        jieqi_dt = datetime(adj_year, adj_month, adj_day,
                            int(adj_time.split(':')[0]),
                            int(adj_time.split(':')[1]))
    except ValueError:
        return 6.0

    if shun_pai:
        # 阳男阴女 顺排: distance to NEXT 节气
        # Get next month's 节气
        next_month = adj_month + 1
        next_year = adj_year
        if next_month > 12:
            next_month = 1
            next_year = adj_year + 1
        next_entry = get_jieqi(next_year, next_month)
        if next_entry is None:
            return 6.0
        next_jieqi = datetime(next_year, next_month, int(next_entry[1]),
                              int(next_entry[2].split(':')[0]),
                              int(next_entry[2].split(':')[1]))
        days_diff = abs((next_jieqi - birth).total_seconds()) / 86400
    else:
        # 阴男阳女 逆排: distance to PREVIOUS/PREV-PREV 节气
        # Actually: distance from birth to the current period's 节气
        days_diff = abs((birth - jieqi_dt).total_seconds()) / 86400

    # Formula: 3 days = 1 year, so days_diff / 3 = start_age
    # App does: days_diff * 4 / 365 for more precision? Let me check
    # Actually the standard formula: 1 day = 4 months, 3 days = 1 year
    start_age = days_diff / 3.0
    return round(start_age, 2)


if __name__ == '__main__':
    # Test
    _parse_data()
    print(f"Data loaded: {len(_jieqi_a)} years ({min(_jieqi_a.keys())}-{max(_jieqi_a.keys())})")
    print(f"2026 month 5 (午月): {get_jieqi(2026, 5)}")
    print(f"g('2026年05月18日 12:00:00') = {g('2026年05月18日 12:00:00')}")
    print(f"e('2026年05月18日 12:00:00') = {e('2026年05月18日 12:00:00')}")
    print(f"get_solar_month_idx(2026, 5, 18) = {get_solar_month_idx(2026, 5, 18)}")
    print(f"get_solar_month_idx(2026, 5, 5) = {get_solar_month_idx(2026, 5, 5)}")
    print(f"get_solar_month_idx(2026, 2, 3) = {get_solar_month_idx(2026, 2, 3)}")
    print(f"get_solar_month_idx(2026, 2, 4) = {get_solar_month_idx(2026, 2, 4)}")
