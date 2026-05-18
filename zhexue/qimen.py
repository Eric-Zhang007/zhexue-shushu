#!/usr/bin/env python3
"""
奇门遁甲排盘 — Qimen Dunjia Compass
基于 zhexue_core.py 核心库

CLI: python3 qimen.py <year> <month> <day> <hour> <minute>
输出：九宫ASCII图 + JSON

规则要点：
  节气定局 → 三元确定 → 地盘(阳顺阴逆, 中五独立) →
  旬首→值符/值使 → 天盘九星(中五禽寄坤) →
  八门 → 八神(阳顺阴逆) → 马星·空亡

注意：中五寄坤仅天盘天禽星，地盘不寄坤
"""

import sys
import json
import math
from datetime import datetime, timedelta

sys.path.insert(0, '/home/zjc/.hermes/skills/zhexue-methods/scripts')
from zhexue_core import *

# ========== 辅助函数 ==========

# 正确的旬空表 (核心库有偏移bug，此处覆盖)
XUN_KONG_CORRECT = {0: (10, 11), 1: (8, 9), 2: (6, 7), 3: (4, 5), 4: (2, 3), 5: (0, 1)}
# 甲子旬→戌亥, 甲戌→申酉, 甲申→午未, 甲午→辰巳, 甲辰→寅卯, 甲寅→子丑

def correct_xunkong(gan_idx, zhi_idx):
    """正确的旬空计算"""
    gap = (zhi_idx - gan_idx) % 12
    xun = {0:0, 10:1, 8:2, 6:3, 4:4, 2:5}.get(gap, 0)
    return list(XUN_KONG_CORRECT[xun])

# ========== 二十四节气定局 ==========
# 阳遁: 冬至→夏至  阴遁: 夏至→冬至
SOLAR_TERMS = [
    ('冬至', 12, 22,  1, 1),
    ('小寒',  1,  6,  1, 2),
    ('大寒',  1, 20,  1, 3),
    ('立春',  2,  4,  1, 8),
    ('雨水',  2, 19,  1, 9),
    ('惊蛰',  3,  6,  1, 1),
    ('春分',  3, 21,  1, 3),
    ('清明',  4,  5,  1, 4),
    ('谷雨',  4, 20,  1, 5),
    ('立夏',  5,  5,  1, 4),
    ('小满',  5, 21,  1, 5),
    ('芒种',  6,  6,  1, 6),
    ('夏至',  6, 21, -1, 9),
    ('小暑',  7,  7, -1, 8),
    ('大暑',  7, 23, -1, 7),
    ('立秋',  8,  7, -1, 2),
    ('处暑',  8, 23, -1, 1),
    ('白露',  9,  7, -1, 9),
    ('秋分',  9, 23, -1, 7),
    ('寒露', 10,  8, -1, 6),
    ('霜降', 10, 23, -1, 5),
    ('立冬', 11,  7, -1, 6),
    ('小雪', 11, 22, -1, 5),
    ('大雪', 12,  7, -1, 4),
]

# 洛书九宫 → 地支映射
# 子1, 丑艮8, 寅艮8, 卯震3, 辰巽4, 巳巽4
# 午离9, 未坤2, 申坤2, 酉兑7, 戌乾6, 亥乾6
ZHI_TO_PALACE = [1, 8, 8, 3, 4, 4, 9, 2, 2, 7, 6, 6]

# 八神顺序
SHEN_ORDER = ['值符', '螣蛇', '太阴', '六合', '白虎', '玄武', '九地', '九天']

# 马星规则：时支定
# 申子辰→寅, 寅午戌→申, 巳酉丑→亥, 亥卯未→巳
MAXING_MAP = {
    0: 2,    # 申子辰→寅
    4: 2,
    8: 2,
    2: 8,    # 寅午戌→申
    6: 8,
    10: 8,
    5: 11,   # 巳酉丑→亥
    9: 11,
    1: 11,
    3: 5,    # 亥卯未→巳
    7: 5,
    11: 5,
}

# 洛书顺序 (顺排)
LUOSHU_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9]
# 逆排
LUOSHU_REVERSE = [1, 9, 8, 7, 6, 5, 4, 3, 2]

# 九宫名称
PALACE_NAMES = {1: '坎一', 2: '坤二', 3: '震三', 4: '巽四',
                5: '中五', 6: '乾六', 7: '兑七', 8: '艮八', 9: '离九'}

# 地支→地支序号 (for 空亡 output)
DI_ZHI_IDX = {z: i for i, z in enumerate(DI_ZHI)}


# ==================== 辅助函数 ====================

def find_solar_term(year, month, day):
    """查找当前节气，返回 (名称, 方向, 上元局数, 距节气首日日数)"""
    dt = datetime(year, month, day)
    # 生成节气日期列表 (考虑跨年)
    terms = []
    for name, m, d, direction, base in SOLAR_TERMS:
        y = year
        if m == 12 and month == 1:
            y = year - 1  # 冬至在去年12月
        elif m == 1 and month == 12:
            y = year + 1  # 小寒在明年1月
        terms.append((name, direction, base, datetime(y, m, d)))

    # 按时间排序
    terms.sort(key=lambda t: t[3])

    # 找到当前所在的节气区间
    for i, (name, direction, base, td) in enumerate(terms):
        next_td = terms[(i + 1) % len(terms)][3]
        if i == len(terms) - 1:
            # 最后一个节气，检查是否在其区间
            if td <= dt:
                days_diff = (dt - td).days
                return name, direction, base, days_diff
        elif td <= dt < next_td:
            days_diff = (dt - td).days
            return name, direction, base, days_diff

    # 兜底：找最近的节气
    closest = min(terms, key=lambda t: abs((dt - t[3]).days))
    days_diff = (dt - closest[3]).days
    return closest[0], closest[1], closest[2], max(0, days_diff)


def get_yuan(days_since_term):
    """三元确定：(节气天数差)//5%3 → 0上元, 1中元, 2下元"""
    return (days_since_term // 5) % 3


def get_game_number(base_ju, yuan, direction):
    """局数：每个节气固定，三元不影响局数"""
    return base_ju


def get_direction_name(direction):
    """阳遁/阴遁"""
    return '阳遁' if direction == 1 else '阴遁'


def build_earth_plate(ju, direction):
    """地盘排布：阳顺阴逆
    returns: dict {palace: gan_idx}
    戊己庚辛壬癸丁丙乙 对应 TIAN_GAN 索引: 4,5,6,7,8,9,3,2,1
    """
    # 九干顺序: 戊(4),己(5),庚(6),辛(7),壬(8),癸(9),丁(3),丙(2),乙(1)
    stem_order = [4, 5, 6, 7, 8, 9, 3, 2, 1]

    plate = {}
    if direction == 1:  # 阳顺
        for i, stem_idx in enumerate(stem_order):
            palace = (ju + i - 1) % 9 + 1
            plate[palace] = stem_idx
    else:  # 阴逆
        for i, stem_idx in enumerate(stem_order):
            palace = (ju - i - 1) % 9 + 1
            plate[palace] = stem_idx

    return plate


def get_xun_first(gan_idx, zhi_idx):
    """获取旬首的干支索引"""
    xun = get_xun(gan_idx, zhi_idx)
    xun_zhi = {0: 0, 1: 10, 2: 8, 3: 6, 4: 4, 5: 2}[xun]
    return 0, xun_zhi  # 甲(0), 地支


def get_shigan_palace(hour_gan_idx, earth_plate):
    """时干宫：时干对应的地盘天干所在宫位
    甲→戊(0→4), 乙→己(1→5), 丙→庚(2→6), 丁→辛(3→7),
    戊→壬(4→8), 己→癸(5→9), 庚→丁(6→2), 辛→丙(7→3),
    壬→乙(8→1), 癸→戊(9→4)
    """
    HOUR_TO_DI = {0: 4, 1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 2, 7: 3, 8: 1, 9: 4}
    di_gan = HOUR_TO_DI.get(hour_gan_idx, 4)
    # 找这个天干在地盘哪个宫
    for palace, gan in earth_plate.items():
        if gan == di_gan:
            return palace
    return 1  # fallback


def build_heaven_stars(zhifu_star_idx, shigan_palace, direction):
    """天盘九星排布
    值符星从原宫转到时干宫，其余星顺/逆转
    天禽星天盘寄坤2宫

    规则：8星（除天禽外）顺/逆排入8宫（跳过中五），
    天禽星固定寄坤2宫。
    """
    # 九星: 天蓬1,天芮2,天冲3,天辅4,天禽5,天心6,天柱7,天任8,天英9
    all_stars = ['天蓬', '天芮', '天冲', '天辅', '天禽', '天心', '天柱', '天任', '天英']

    # 值符星在星序中的位置 (0-based)
    zhifu_pos = zhifu_star_idx - 1

    # 8星序列（除天禽外），从值符星开始循环
    eight_stars = [s for s in (all_stars[zhifu_pos:] + all_stars[:zhifu_pos]) if s != '天禽']

    # 8宫序列（跳过中五）
    palace_8 = [1, 2, 3, 4, 6, 7, 8, 9]

    if direction == 1:  # 阳顺
        palace_seq = palace_8
    else:  # 阴逆
        palace_seq = list(reversed(palace_8))

    # 时干宫在8宫序列中的位置
    if shigan_palace == 5:
        start = 0  # 时干在中五则从第一个开始
    else:
        start = palace_seq.index(shigan_palace)

    # 8星排入8宫
    heaven = {}
    for i, star in enumerate(eight_stars):
        pos = (start + i) % 8
        palace = palace_seq[pos]
        heaven[palace] = star

    # 天禽星寄坤2
    heaven[2] = '天禽'

    return heaven


def build_doors(zhishi_door_idx, shigan_palace, xun_first_zhi, hour_zhi, direction, earth_plate):
    """八门排布
    值使门步数=(时支-旬首支)%12
    值使门从原宫移动步数后，其余门顺/逆排
    """
    # 八门按洛书宫位: 1休, 8生, 3伤, 4杜, 9景, 2死, 7惊, 6开
    door_order = ['休门', '死门', '伤门', '杜门', '开门', '惊门', '景门', '生门']
    door_by_palace = {1: '休门', 2: '死门', 3: '伤门', 4: '杜门',
                      6: '开门', 7: '惊门', 8: '生门', 9: '景门'}

    # 值使门原宫位
    zhishi_original_palace = zhishi_door_idx

    # 步数
    steps = (hour_zhi - xun_first_zhi) % 12
    steps = steps % 8  # 最多8步

    # 值使门新宫位：在八门宫序中移动steps步
    # 八门宫序 (洛书顺序，跳过5宫): [1, 2, 3, 4, 6, 7, 8, 9]
    door_palace_order = [1, 2, 3, 4, 6, 7, 8, 9]
    door_palace_rev = [1, 9, 8, 7, 6, 4, 3, 2]

    if direction == 1:  # 阳顺
        palace_seq = door_palace_order
    else:  # 阴逆
        palace_seq = door_palace_order  # Eight doors always go forward in洛书order... 
        # Actually, for 阴遁, the doors also go逆? Let me re-check.
        # In Qimen, 八门 always follow the 值使门's movement direction.
        # The 值使门 moves forward in the 地支 order, and the remaining doors follow.
        # Actually, the standard is: 八门顺排 (always), regardless of 阴遁/阳遁.
        # The direction only affects 九星 and 八神.
        
        # Actually, let me reconsider. Traditionally, 八门 are always顺排 in洛书 order,
        # regardless of 阴遁/阳遁. The 值使门 moves steps, and the rest of the 八门
        # follow in 洛书顺序 (1→2→3→4→5(skip)→6→7→8→9).
        pass

    # Standard approach: 八门 always顺排 in洛书 order (skipping 5)
    # The 值使门 is placed at: original_pos + steps (in 八门 palace order)
    # Then other doors follow in order
    
    zhishi_idx_in_order = door_palace_order.index(zhishi_original_palace)
    zhishi_new_idx = (zhishi_idx_in_order + steps) % 8
    zhishi_new_palace = door_palace_order[zhishi_new_idx]

    # Now arrange all 8 doors
    door_list = ['休门', '死门', '伤门', '杜门', '开门', '惊门', '景门', '生门']
    # 值使门在door_list中的位置
    zhishi_door_name = door_by_palace[zhishi_door_idx]
    zhishi_in_door_list = door_list.index(zhishi_door_name)

    # 从值使门开始的循环门序
    cyclic_doors = door_list[zhishi_in_door_list:] + door_list[:zhishi_in_door_list]

    # 从值使门新宫位开始，按洛书宫序顺排 (always顺排 for 八门)
    start_pos = door_palace_order.index(zhishi_new_palace)

    doors = {}
    for i, d in enumerate(cyclic_doors):
        pos = (start_pos + i) % 8
        palace = door_palace_order[pos]
        doors[palace] = d

    return doors


def build_shen(shigan_palace, direction):
    """八神排布：阳顺阴逆
    值符在时干宫，其余按八神顺序排入八宫（跳过中五）
    """
    # 八神顺序: 值符, 螣蛇, 太阴, 六合, 白虎, 玄武, 九地, 九天
    shen_order = SHEN_ORDER

    # 八宫顺序 (跳过5)
    palace_8 = [1, 2, 3, 4, 6, 7, 8, 9]

    if direction == 1:  # 阳顺
        palace_seq = palace_8
    else:  # 阴逆
        palace_seq = list(reversed(palace_8))

    # 找到时干宫在palace_seq中的位置
    if shigan_palace == 5:
        # 时干在中五，寄坤2
        start = palace_seq.index(2)
    else:
        start = palace_seq.index(shigan_palace)

    shen = {}
    for i, s in enumerate(shen_order):
        pos = (start + i) % 8
        palace = palace_seq[pos]
        shen[palace] = s

    return shen


def get_maxing_palace(zhi_idx):
    """马星：时支定，返回地支索引"""
    return MAXING_MAP.get(zhi_idx, 2)


def zhi_to_palace(zhi_idx):
    """地支转九宫"""
    return ZHI_TO_PALACE[zhi_idx % 12]


def get_kong_xun(kong_zhi_indices):
    """返回空亡的地支名称列表"""
    return [DI_ZHI[i] for i in kong_zhi_indices]


# ==================== 绘图 ====================

def draw_qimen_table(earth, heaven_stars, doors, shen, shigan_palace,
                     kong_xun, maxing_palace_zhi, ju, direction, term_name,
                     year, month, day, hour, minute,
                     day_gan, day_zhi, hour_gan, hour_zhi,
                     gz_hour_str, xun_name, zhifu_star, zhishi_door):
    """绘制九宫ASCII图"""
    gn = PALACE_NAMES
    di_zhi_list = DI_ZHI
    tian_gan_list = TIAN_GAN

    direction_name = get_direction_name(direction)
    direction_label = {1: '顺', -1: '逆'}[direction]

    # 格式化宫位布局 (洛书九宫)
    layout = [
        [4, 9, 2],
        [3, 5, 7],
        [8, 1, 6]
    ]

    lines = []
    lines.append('=' * 68)
    title = f'奇门遁甲 | {year}年{month}月{day}日 {hour}:{minute:02d}'
    lines.append(f'   {title}')
    lines.append(f'   {term_name} · {direction_name}{ju}局')
    lines.append(f'   {tian_gan_list[day_gan]}{di_zhi_list[day_zhi]}日  {gz_hour_str}')
    lines.append(f'   {xun_name}旬  值符: {zhifu_star}  值使: {zhishi_door}')
    lines.append('=' * 68)

    for row_idx, row in enumerate(layout):
        # 上边框
        if row_idx == 0:
            lines.append('  ┌────────────┬────────────┬────────────┐')
        else:
            lines.append('  ├────────────┼────────────┼────────────┤')

        # 宫名行
        labels = [f'{gn[n]:4s}' for n in row]
        parts = []
        for n in row:
            info = ''
            if n == shigan_palace:
                info = '★时干'
            if n != 5:
                pass  # don't add info in label line for simplicity
        lines.append('  │' + '│'.join(f' {l:8s} ' for l in labels) + '│')

        # 八神行
        parts = []
        for n in row:
            if n == 5:
                parts.append('    中宫    ')
            else:
                s = shen.get(n, '')
                s_str = f'  {s:4s}  '
                parts.append(s_str)
        lines.append('  │' + '│'.join(parts) + '│')

        # 九星行
        parts = []
        for n in row:
            if n == 5:
                # 天禽星寄坤2，中五无星
                parts.append('  (寄坤)  ')
            else:
                star = heaven_stars.get(n, '')
                if star == '天禽':
                    parts.append(f' {star:4s}★ ')
                else:
                    parts.append(f'  {star:4s}  ')
        lines.append('  │' + '│'.join(parts) + '│')

        # 八门行
        parts = []
        for n in row:
            if n == 5:
                parts.append('           ')
            else:
                d = doors.get(n, '')
                parts.append(f'  {d:4s}  ')
        lines.append('  │' + '│'.join(parts) + '│')

        # 地盘天干行（带标记）
        parts = []
        for n in row:
            if n == 5:
                di = earth.get(n, '')
                gan_name = tian_gan_list[di] if di != '' else ''
                parts.append(f'  {gan_name:4s}(中) ')
            else:
                di = earth.get(n, '')
                gan_name = tian_gan_list[di] if di != '' else ''
                # 标记
                marks = []
                if n == shigan_palace:
                    marks.append('时干')
                # 空亡
                kong_zhi_names = get_kong_xun(kong_xun)
                # 检查该宫的地支是否有空亡
                # 空亡是地支，需要检查该宫对应的地支
                # 九宫对应地支: 1子, 2未申, 3卯, 4辰巳, 6戌亥, 7酉, 8丑寅, 9午
                palace_to_zhi = {
                    1: [0], 2: [7, 8], 3: [3], 4: [4, 5],
                    6: [10, 11], 7: [9], 8: [1, 2], 9: [6]
                }
                for pz in palace_to_zhi.get(n, []):
                    if di_zhi_list[pz] in kong_zhi_names:
                        marks.append('空')
                        break

                mark_str = '·'.join(marks) if marks else ''
                if mark_str:
                    s = f'{gan_name:5s}({mark_str})'
                else:
                    s = f'  {gan_name:5s}  '
                parts.append(s)
        lines.append('  │' + '│'.join(parts) + '│')

    # 底边框
    lines.append('  └────────────┴────────────┴────────────┘')

    # 附加信息
    lines.append('')
    lines.append(f'  马星: {di_zhi_list[maxing_palace_zhi]}')
    kong_str = '、'.join(get_kong_xun(kong_xun))
    lines.append(f'  空亡: {kong_str}')

    return '\n'.join(lines)


# ==================== 主函数 ====================

def calculate_qimen(year, month, day, hour, minute):
    """完整奇门遁甲排盘计算
    returns dict with all data
    """
    result = {}

    # ---------- 基本信息 ----------
    result['datetime'] = f'{year}-{month:02d}-{day:02d} {hour}:{minute:02d}'

    # 日干支
    day_gan, day_zhi = day_ganzhi_from_date(year, month, day)
    result['day_gan'] = day_gan
    result['day_zhi'] = day_zhi
    result['day_ganzhi'] = f'{TIAN_GAN[day_gan]}{DI_ZHI[day_zhi]}'

    # 时干支
    hour_zhi = hour_zhi_index(hour, minute)
    hour_gan_idx = hour_gan(day_gan, hour_zhi)
    result['hour_gan'] = hour_gan_idx
    result['hour_zhi'] = hour_zhi
    result['hour_ganzhi'] = f'{TIAN_GAN[hour_gan_idx]}{DI_ZHI[hour_zhi]}'

    # ---------- 节气定局 ----------
    term_name, direction, base_ju, days_since_term = find_solar_term(year, month, day)
    result['solar_term'] = term_name
    result['direction'] = direction
    result['base_ju'] = base_ju
    result['days_since_term'] = days_since_term

    # 三元确定
    yuan = get_yuan(days_since_term)
    yuan_names = ['上元', '中元', '下元']
    result['yuan'] = yuan
    result['yuan_name'] = yuan_names[yuan]

    # 局数
    ju = get_game_number(base_ju, yuan, direction)
    result['ju'] = ju

    # ---------- 地盘 ----------
    earth_plate = build_earth_plate(ju, direction)
    result['earth_plate'] = {str(k): v for k, v in earth_plate.items()}

    # ---------- 旬首 → 值符星/值使门 ----------
    xun = get_xun(hour_gan_idx, hour_zhi)
    xun_first_gan, xun_first_zhi = get_xun_first(hour_gan_idx, hour_zhi)
    result['xun'] = xun
    result['xun_name'] = f'甲{DI_ZHI[xun_first_zhi]}'
    result['xun_first_gan'] = xun_first_gan
    result['xun_first_zhi'] = xun_first_zhi

    # 旬首地支对应的九宫
    xun_first_palace = zhi_to_palace(xun_first_zhi)
    result['xun_first_palace'] = xun_first_palace

    # 值符星 = 旬首宫对应的九星 (九星在九宫中的原始位置)
    star_names_by_palace = {1: '天蓬', 2: '天芮', 3: '天冲', 4: '天辅',
                            5: '天禽', 6: '天心', 7: '天柱', 8: '天任', 9: '天英'}
    zhifu_star = star_names_by_palace[xun_first_palace]
    result['zhifu_star'] = zhifu_star
    result['zhifu_star_idx'] = xun_first_palace  # 值符星在宫位中的索引

    # 值使门 = 旬首宫对应的八门
    door_names_by_palace = {1: '休门', 8: '生门', 3: '伤门', 4: '杜门',
                            9: '景门', 2: '死门', 7: '惊门', 6: '开门'}
    zhishi_door = door_names_by_palace[xun_first_palace]
    result['zhishi_door'] = zhishi_door
    result['zhishi_door_idx'] = xun_first_palace

    # ---------- 时干宫 ----------
    shigan_palace = get_shigan_palace(hour_gan_idx, earth_plate)
    result['shigan_palace'] = shigan_palace

    # ---------- 天盘九星 ----------
    heaven_stars = build_heaven_stars(xun_first_palace, shigan_palace, direction)
    # 确保结果中有 天禽寄坤的信息
    result['heaven_stars'] = heaven_stars

    # ---------- 八门 ----------
    doors = build_doors(xun_first_palace, shigan_palace, xun_first_zhi, hour_zhi, direction, earth_plate)
    result['doors'] = doors

    # ---------- 八神 ----------
    shen = build_shen(shigan_palace, direction)
    result['shen'] = shen

    # ---------- 马星 ----------
    maxing_zhi = get_maxing_palace(hour_zhi)
    maxing_palace = zhi_to_palace(maxing_zhi)
    result['maxing_zhi'] = maxing_zhi
    result['maxing_zhi_name'] = DI_ZHI[maxing_zhi]
    result['maxing_palace'] = maxing_palace

    # ---------- 空亡 ----------
    kong_xun_indices = correct_xunkong(hour_gan_idx, hour_zhi)
    result['kong_xun_zhi'] = kong_xun_indices
    result['kong_xun_names'] = [DI_ZHI[i] for i in kong_xun_indices]

    # ---------- 生成ASCII图 ----------
    gz_hour = f'{TIAN_GAN[hour_gan_idx]}{DI_ZHI[hour_zhi]}时'
    xun_name = f'甲{DI_ZHI[xun_first_zhi]}'

    ascii_chart = draw_qimen_table(
        earth_plate, heaven_stars, doors, shen,
        shigan_palace, kong_xun_indices, maxing_zhi,
        ju, direction, term_name,
        year, month, day, hour, minute,
        day_gan, day_zhi, hour_gan_idx, hour_zhi,
        gz_hour, xun_name, zhifu_star, zhishi_door
    )
    result['ascii_chart'] = ascii_chart

    return result


def result_to_json(result):
    """将结果转为JSON可序列化格式"""
    json_result = {
        'datetime': result['datetime'],
        'solar_term': result['solar_term'],
        'direction': get_direction_name(result['direction']),
        'ju': result['ju'],
        'yuan': result['yuan_name'],
        'day_ganzhi': result['day_ganzhi'],
        'hour_ganzhi': result['hour_ganzhi'],
        'xun': result['xun_name'],
        'zhifu_star': result['zhifu_star'],
        'zhishi_door': result['zhishi_door'],
        'shigan_palace': result['shigan_palace'],
        'earth_plate': {},
        'heaven_stars': {},
        'doors': {},
        'shen': {},
        'maxing': result['maxing_zhi_name'],
        'kong_xun': result['kong_xun_names'],
    }

    for p in range(1, 10):
        p_str = str(p)
        # 地盘存的是str key
        if p_str in result['earth_plate']:
            json_result['earth_plate'][p_str] = TIAN_GAN[result['earth_plate'][p_str]]

    for p in range(1, 10):
        p_str = str(p)
        if p in result['heaven_stars']:
            json_result['heaven_stars'][p_str] = result['heaven_stars'][p]

    for p in range(1, 10):
        p_str = str(p)
        if p in result['doors']:
            json_result['doors'][p_str] = result['doors'][p]

    for p in range(1, 10):
        p_str = str(p)
        if p in result['shen']:
            json_result['shen'][p_str] = result['shen'][p]

    return json_result


def main():
    if len(sys.argv) < 5:
        print('用法: python3 qimen.py <year> <month> <day> <hour> <minute>')
        print('示例: python3 qimen.py 2026 5 17 7 57')
        sys.exit(1)

    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    hour = int(sys.argv[4])
    minute = int(sys.argv[5]) if len(sys.argv) > 5 else 0

    try:
        result = calculate_qimen(year, month, day, hour, minute)
    except Exception as e:
        print(f'错误: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ASCII图输出
    print(result['ascii_chart'])

    # JSON输出
    if '--json' in sys.argv or '-j' in sys.argv:
        json_out = result_to_json(result)
        print()
        print(json.dumps(json_out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
