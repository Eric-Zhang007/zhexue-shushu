#!/usr/bin/env python3
"""
大六壬排盘 (Da Liu Ren)

功能：
1. 月将确定：中气分界（雨水后亥,春分后戌,谷雨后酉,小满后申,夏至后未,大暑后午,处暑后巳,秋分后辰,霜降后卯,小雪后寅,冬至后丑,大寒后子）
2. 天地盘：月将加时
3. 四课：日干寄宫(甲寅乙辰丙巳丁未戊巳己未庚申辛酉壬亥癸丑)
4. 三传：贼克法(下贼上→上克下→伏吟)
5. 天将：贵人起法+昼夜贵+顺逆
6. 遁干：五鼠遁
7. 旬空驿马

CLI: python3 liuren.py <year> <month> <day> <hour> <minute>
输出：课式ASCII图+JSON
"""
import sys
import json
import math

sys.path.insert(0, '/home/zjc/.hermes/skills/zhexue-methods/scripts')
from zhexue_core import (
    TIAN_GAN, DI_ZHI, GAN_WUXING, ZHI_WUXING,
    WUXING_KE,
    day_ganzhi_from_date, hour_zhi_index, hour_gan,
    xunkong_ganzhi,
)

# ========== 1. 月将 ==========
# 中气（太阳过宫分界）近似日期 (月, 日)
ZHONG_QI = [
    (2, 19),   # 雨水
    (3, 21),   # 春分
    (4, 20),   # 谷雨
    (5, 21),   # 小满
    (6, 21),   # 夏至
    (7, 23),   # 大暑
    (8, 23),   # 处暑
    (9, 23),   # 秋分
    (10, 23),  # 霜降
    (11, 22),  # 小雪
    (12, 22),  # 冬至
    (1, 20),   # 大寒
]

# 月将地支索引: 雨水后亥,春分后戌,谷雨后酉,小满后申,夏至后未,大暑后午,
#                处暑后巳,秋分后辰,霜降后卯,小雪后寅,冬至后丑,大寒后子
YUE_JIANG_ZHI = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
YUE_JIANG_NAMES = ['亥', '戌', '酉', '申', '未', '午', '巳', '辰', '卯', '寅', '丑', '子']

def get_yuejiang(year, month, day):
    """根据中气确定月将地支索引"""
    for i in range(12):
        tm, td = ZHONG_QI[i]
        next_idx = (i + 1) % 12
        next_tm, next_td = ZHONG_QI[next_idx]

        # 大寒(1/20) -> 雨水(2/19) 跨年处理
        if i == 11:
            if month == 1 and day >= td:
                return YUE_JIANG_ZHI[i]
            if month == 2 and day < ZHONG_QI[0][1]:
                return YUE_JIANG_ZHI[i]
        else:
            # 当前月且已过中气日
            if month == tm and day >= td:
                return YUE_JIANG_ZHI[i]
            # 下个月但仍未到下个中气
            if month == next_tm and day < next_td:
                return YUE_JIANG_ZHI[i]
            # 月份在中气月份之间
            if tm < month < next_tm:
                return YUE_JIANG_ZHI[i]
            # 跨年：月份在大寒(1)和雨水(2)之间
            if i == 11 and month == 1 and day < td:
                # 属于上一年的大寒到雨水之间→上一个循环
                pass  # handled by the跨年 case above

    # 雨水前默认用最后一个(大寒后→子)
    if month == 2 and day < ZHONG_QI[0][1]:
        return YUE_JIANG_ZHI[11]  # 子
    if month == 1 and day < ZHONG_QI[11][1]:
        return YUE_JIANG_ZHI[11]  # 子
    return YUE_JIANG_ZHI[0]  # 默认雨水后→亥


# ========== 2. 天地盘 ==========
def make_tianpan(yuejiang, zhanshi):
    """天盘：月将加时。tianpan[d] = 天盘在地盘位置d上的地支索引"""
    return [(yuejiang - zhanshi + d) % 12 for d in range(12)]


# ========== 3. 四课 ==========
# 日干寄宫: 甲寅乙辰丙巳丁未戊巳己未庚申辛酉壬亥癸丑
RI_GAN_JI_GONG = {
    0: 2,   # 甲→寅
    1: 4,   # 乙→辰
    2: 5,   # 丙→巳
    3: 7,   # 丁→未
    4: 5,   # 戊→巳
    5: 7,   # 己→未
    6: 8,   # 庚→申
    7: 9,   # 辛→酉
    8: 11,  # 壬→亥
    9: 1,   # 癸→丑
}

def get_si_ke(tianpan, ri_gan_idx, ri_zhi_idx):
    """
    四课：
    课1(干上): 天盘[日干寄宫]
    课2(干阴): 天盘[课1]
    课3(支上): 天盘[日支]
    课4(支阴): 天盘[课3]
    """
    jigong = RI_GAN_JI_GONG[ri_gan_idx]
    k1 = tianpan[jigong]  # 干上
    k2 = tianpan[k1]      # 干阴
    k3 = tianpan[ri_zhi_idx]  # 支上
    k4 = tianpan[k3]      # 支阴
    return [k1, k2, k3, k4]


# ========== 4. 三传 — 贼克法 ==========
def zhi_ke_zhi(a_idx, b_idx):
    """地支 a 是否克 地支 b？基于五行相克"""
    wx_a = ZHI_WUXING[DI_ZHI[a_idx]]
    wx_b = ZHI_WUXING[DI_ZHI[b_idx]]
    return WUXING_KE[wx_a] == wx_b

def get_san_chuan(tianpan, si_ke, ri_gan_idx, ri_zhi_idx):
    """
    贼克法求三传。
    四课对：(upper, lower)
    课1: (si_ke[0], 日干寄宫)
    课2: (si_ke[1], si_ke[0])
    课3: (si_ke[2], 日支)
    课4: (si_ke[3], si_ke[2])
    """
    jigong = RI_GAN_JI_GONG[ri_gan_idx]
    pairs = [
        (si_ke[0], jigong),       # 课1
        (si_ke[1], si_ke[0]),     # 课2
        (si_ke[2], ri_zhi_idx),   # 课3
        (si_ke[3], si_ke[2]),     # 课4
    ]

    # 检查伏吟：天盘==地盘（月将==占时）
    if tianpan == list(range(12)):
        return si_ke[0], si_ke[0], si_ke[0], 'fuyin'

    method = 'fuyin'

    # 第1优先：下贼上 (lower 克 upper)
    zei = []
    for i, (up, down) in enumerate(pairs):
        if zhi_ke_zhi(down, up):
            zei.append((i, up, down))

    if len(zei) == 1:
        chuchuan = zei[0][1]
        method = 'xiazeishang'
    elif len(zei) > 1:
        # 多下贼上：取与日干最亲近的（课1 > 课2 > 课3 > 课4）
        chuchuan = zei[0][1]
        method = 'xiazeishang_duo'
    else:
        # 第2优先：上克下 (upper 克 lower)
        ke = []
        for i, (up, down) in enumerate(pairs):
            if zhi_ke_zhi(up, down):
                ke.append((i, up, down))

        if len(ke) == 1:
            chuchuan = ke[0][1]
            method = 'shangkexia'
        elif len(ke) > 1:
            chuchuan = ke[0][1]
            method = 'shangkexia_duo'
        else:
            # 无克 — 伏吟
            chuchuan = si_ke[0]
            method = 'wuke'

    zhongchuan = tianpan[chuchuan]
    mochuan = tianpan[zhongchuan]
    return chuchuan, zhongchuan, mochuan, method


# ========== 5. 天将（贵人）==========
# 贵人起法：甲戊庚丑未, 乙己子申, 丙丁亥酉, 壬癸巳卯, 辛午寅
# 日干索引 -> (昼贵, 夜贵)
GUI_REN_TABLE = {
    0: (1, 7),   # 甲: 丑(1)昼, 未(7)夜
    1: (0, 8),   # 乙: 子(0)昼, 申(8)夜
    2: (11, 9),  # 丙: 亥(11)昼, 酉(9)夜
    3: (11, 9),  # 丁: 亥(11)昼, 酉(9)夜
    4: (1, 7),   # 戊: 丑(1)昼, 未(7)夜
    5: (0, 8),   # 己: 子(0)昼, 申(8)夜
    6: (1, 7),   # 庚: 丑(1)昼, 未(7)夜
    7: (6, 2),   # 辛: 午(6)昼, 寅(2)夜
    8: (5, 3),   # 壬: 巳(5)昼, 卯(3)夜
    9: (5, 3),   # 癸: 巳(5)昼, 卯(3)夜
}

# 12天将（顺行顺序）
TIAN_JIANG_SHUN = [
    '贵人', '螣蛇', '朱雀', '六合', '勾陈', '青龙',
    '天空', '白虎', '太常', '玄武', '太阴', '天后',
]

# 逆行顺序（起始也是贵人）
TIAN_JIANG_NI = [
    '贵人', '天后', '太阴', '玄武', '太常', '白虎',
    '天空', '青龙', '勾陈', '六合', '朱雀', '螣蛇',
]

def is_daytime(zhanshi_idx):
    """昼：卯(3)~申(8), 夜：酉(9)~寅(2)"""
    return 3 <= zhanshi_idx <= 8

def get_gui_ren(ri_gan_idx, zhanshi_idx):
    """获取贵人地支索引"""
    day = is_daytime(zhanshi_idx)
    if day:
        return GUI_REN_TABLE[ri_gan_idx][0]  # 昼贵
    else:
        return GUI_REN_TABLE[ri_gan_idx][1]  # 夜贵

def get_tianjiang(tianpan, ri_gan_idx, zhanshi_idx):
    """
    返回天盘12宫上各对应的天将。
    返回: dict {地盘索引: 天将名称}
    """
    gui_ren_zhi = get_gui_ren(ri_gan_idx, zhanshi_idx)

    # 贵人在地盘上的位置（贵人所在的天地盘位置）
    gui_ren_pos = gui_ren_zhi

    # 顺逆：贵人在亥子丑寅卯辰(11,0,1,2,3,4) → 顺
    #       贵人在巳午未申酉戌(5,6,7,8,9,10) → 逆
    if gui_ren_pos in [11, 0, 1, 2, 3, 4]:
        order = TIAN_JIANG_SHUN
        direction = 'shun'
    else:
        order = TIAN_JIANG_NI
        direction = 'ni'

    # 确定天将在12地盘位置上的分布
    # 从天盘上贵人所在的位置开始，按顺序分配12天将
    tianjiang = {}
    for offset in range(12):
        if direction == 'shun':
            idx = (gui_ren_pos + offset) % 12
        else:
            idx = (gui_ren_pos - offset) % 12
        tianjiang[idx] = order[offset]

    return tianjiang, direction, gui_ren_zhi


# ========== 6. 遁干 ==========
def get_dun_gan(ri_gan_idx, zhi_idx):
    """五鼠遁：根据地支索引获取遁干索引"""
    return hour_gan(ri_gan_idx, zhi_idx)


# ========== 7. 旬空 & 驿马 ==========
def get_yima(ri_zhi_idx):
    """驿马：寅午戌→申(8), 巳酉丑→亥(11), 申子辰→寅(2), 亥卯未→巳(5)"""
    YIMA_TABLE = {
        2: 8,    # 寅→申
        6: 8,    # 午→申
        10: 8,   # 戌→申
        5: 11,   # 巳→亥
        9: 11,   # 酉→亥
        1: 11,   # 丑→亥
        8: 2,    # 申→寅
        0: 2,    # 子→寅
        4: 2,    # 辰→寅
        11: 5,   # 亥→巳
        3: 5,    # 卯→巳
        7: 5,    # 未→巳
    }
    return YIMA_TABLE.get(ri_zhi_idx, 2)


# ========== 输出 ==========
def format_gz(gan_idx, zhi_idx):
    return f"{TIAN_GAN[gan_idx]}{DI_ZHI[zhi_idx]}"

def build_ascii_diagram(tianpan, si_ke, san_chuan, ri_gan_idx, ri_zhi_idx,
                        yuejiang, zhanshi_idx, tianjiang_data, xunkong, yima,
                        method, jigong):
    """构建ASCII课式图"""
    chuchuan, zhongchuan, mochuan = san_chuan[:3]
    tianjiang_dict, direction, gui_ren_zhi = tianjiang_data
    gui_ren_name = DI_ZHI[gui_ren_zhi]

    k1, k2, k3, k4 = si_ke
    k1_g = get_dun_gan(ri_gan_idx, k1)
    k2_g = get_dun_gan(ri_gan_idx, k2)
    k3_g = get_dun_gan(ri_gan_idx, k3)
    k4_g = get_dun_gan(ri_gan_idx, k4)

    day_gan = TIAN_GAN[ri_gan_idx]
    day_zhi = DI_ZHI[ri_zhi_idx]
    yuejiang_name = DI_ZHI[yuejiang]
    zhanshi_name = DI_ZHI[zhanshi_idx]
    jigong_name = DI_ZHI[jigong]

    # 天盘文字（12宫）
    tp_lines = []
    for d in range(12):
        tp_branch = tianpan[d]
        tp_gan = get_dun_gan(ri_gan_idx, tp_branch)
        tp_gan_c = TIAN_GAN[tp_gan]
        tp_zhi_c = DI_ZHI[tp_branch]

        # 标注贵人位置
        gui_mark = ''
        if d == gui_ren_zhi:
            gui_mark = '●'

        # 标注四课和三传位置
        mark = ''
        roles = []
        if d == jigong:
            roles.append('干')
        if d == ri_zhi_idx:
            roles.append('支')
        if tp_branch == k1 or d == k1:
            pass  # 四课已有
        for idx, val in enumerate([k1, k2, k3, k4]):
            if tp_branch == val and d == jigong if idx==0 else False:
                pass

        tp_lines.append(f"  {DI_ZHI[d]}:{tp_gan_c}{tp_zhi_c}{gui_mark}")

    # 四课显示
    si_ke_str = (
        f"  课1(干上): {TIAN_GAN[k1_g]}{DI_ZHI[k1]}"
        f"  课2(干阴): {TIAN_GAN[k2_g]}{DI_ZHI[k2]}"
        f"\n  课3(支上): {TIAN_GAN[k3_g]}{DI_ZHI[k3]}"
        f"  课4(支阴): {TIAN_GAN[k4_g]}{DI_ZHI[k4]}"
    )

    # 三传显示
    cc_gan = get_dun_gan(ri_gan_idx, chuchuan)
    zc_gan = get_dun_gan(ri_gan_idx, zhongchuan)
    mc_gan = get_dun_gan(ri_gan_idx, mochuan)
    san_chuan_str = (
        f"  初传: {TIAN_GAN[cc_gan]}{DI_ZHI[chuchuan]}"
        f" → 中传: {TIAN_GAN[zc_gan]}{DI_ZHI[zhongchuan]}"
        f" → 末传: {TIAN_GAN[mc_gan]}{DI_ZHI[mochuan]}"
    )

    # 天将显示
    tianjiang_str = ''
    for d in range(12):
        tp_branch = tianpan[d]
        tp_gan = get_dun_gan(ri_gan_idx, tp_branch)
        tp_gan_c = TIAN_GAN[tp_gan]
        tp_zhi_c = DI_ZHI[tp_branch]
        tj = tianjiang_dict[d]
        tianjiang_str += f"\n  {DI_ZHI[d]}({tp_gan_c}{tp_zhi_c}): {tj}"

    # 旬空驿马
    xk_str = f"{DI_ZHI[xunkong[0]]}{DI_ZHI[xunkong[1]]}"

    # 方法
    method_names = {
        'xiazeishang': '下贼上',
        'xiazeishang_duo': '下贼上(多)',
        'shangkexia': '上克下',
        'shangkexia_duo': '上克下(多)',
        'fuyin': '伏吟',
        'wuke': '无克',
    }

    # 构建课式ASCII图 - 十二宫圆盘式
    diagram = f"""
╔══════════════════ 大六壬课式 ══════════════════╗
║                                                ║
║  日干: {day_gan}{day_zhi}  月将: {yuejiang_name}  占时: {zhanshi_name}    ║
║  日干寄宫: {jigong_name}  方法: {method_names.get(method, method)}        ║
║                                                ║
╠══════════════════ 天盘十二宫 ══════════════════╣
║                                                ║"""

    # 天盘十二宫表格
    diagram += "\n║  ┌─────┬─────┬─────┬─────┬─────┬─────┐  ║"
    tp_row1 = "║  │"
    for d in [11, 0, 1, 2, 3, 4]:  # 亥子丑寅卯辰
        tp_b = tianpan[d]
        tp_g = get_dun_gan(ri_gan_idx, tp_b)
        label = f"{TIAN_GAN[tp_g]}{DI_ZHI[tp_b]}"
        tp_row1 += f" {label:>4} │"
    diagram += f"\n{tp_row1}  ║"
    diagram += f"\n║  ├─────┼─────┼─────┼─────┼─────┼─────┤  ║"
    tp_row2 = "║  │"
    for d in [10, 9, 8, 7, 6, 5]:  # 戌酉申未午巳
        tp_b = tianpan[d]
        tp_g = get_dun_gan(ri_gan_idx, tp_b)
        label = f"{TIAN_GAN[tp_g]}{DI_ZHI[tp_b]}"
        tp_row2 += f" {label:>4} │"
    diagram += f"\n{tp_row2}  ║"
    diagram += "\n║  └─────┴─────┴─────┴─────┴─────┴─────┘  ║"

    diagram += f"""
║                                                ║
╠══════════════════ 四课 ════════════════════════╣
║                                                ║
║  ┌──────┬──────┬──────┬──────┐                 ║
║  │ {TIAN_GAN[k1_g]}{DI_ZHI[k1]:>3} │ {TIAN_GAN[k2_g]}{DI_ZHI[k2]:>3} │ {TIAN_GAN[k3_g]}{DI_ZHI[k3]:>3} │ {TIAN_GAN[k4_g]}{DI_ZHI[k4]:>3} │  上(天盘)    ║
║  ├──────┼──────┼──────┼──────┤                 ║
║  │ {day_gan}{DI_ZHI[jigong]:>3} │ {TIAN_GAN[k1_g]}{DI_ZHI[k1]:>3} │ {day_gan}{DI_ZHI[ri_zhi_idx]:>3} │ {TIAN_GAN[k3_g]}{DI_ZHI[k3]:>3} │  下(地盘)    ║
║  └──────┴──────┴──────┴──────┘                 ║
║  一课(干)  二课    三课(支)  四课               ║
║                                                ║
╠══════════════════ 三传 ════════════════════════╣
║                                                ║
║  {san_chuan_str:^48}  ║
║                                                ║
╠══════════════════ 天将(昼夜:{'昼' if is_daytime(zhanshi_idx) else '夜'} {direction}) ═════════╣
║  贵人: {gui_ren_name}({DI_ZHI[gui_ren_zhi]}){'●' if gui_ren_zhi == gui_ren_zhi else ''}                               ║
║                                                ║"""

    # 天将表格
    diagram += "\n║  ┌──────┬──────┬──────┬──────┬──────┬──────┐  ║"
    tj_row1 = "║  │"
    for d in [11, 0, 1, 2, 3, 4]:
        tj_row1 += f" {tianjiang_dict[d]:>5} │"
    diagram += f"\n{tj_row1}  ║"
    diagram += "\n║  ├──────┼──────┼──────┼──────┼──────┼──────┤  ║"
    tj_row2 = "║  │"
    for d in [5, 6, 7, 8, 9, 10]:  # 巳午未申酉戌
        tj_row2 += f" {tianjiang_dict[d]:>5} │"
    diagram += f"\n{tj_row2}  ║"
    diagram += "\n║  └──────┴──────┴──────┴──────┴──────┴──────┘  ║"

    diagram += f"""
║                                                ║
╠══════════════════ 神煞 ════════════════════════╣
║  旬空: {xk_str:>10}                             ║
║  驿马: {DI_ZHI[yima]:>10}                             ║
║                                                ║
╚════════════════════════════════════════════════╝"""
    return diagram


# ========== 主函数 ==========
def liuren_pai_pan(year, month, day, hour, minute=0):
    """大六壬排盘主函数，返回结构化数据"""

    # 日干支
    ri_gan_idx, ri_zhi_idx = day_ganzhi_from_date(year, month, day)

    # 占时
    zhanshi_idx = hour_zhi_index(hour, minute)

    # 月将
    yuejiang = get_yuejiang(year, month, day)

    # 天地盘
    tianpan = make_tianpan(yuejiang, zhanshi_idx)

    # 四课
    si_ke = get_si_ke(tianpan, ri_gan_idx, ri_zhi_idx)

    # 三传
    chuchuan, zhongchuan, mochuan, method = get_san_chuan(
        tianpan, si_ke, ri_gan_idx, ri_zhi_idx
    )

    # 天将
    tianjiang_data = get_tianjiang(tianpan, ri_gan_idx, zhanshi_idx)

    # 旬空
    xunkong = xunkong_ganzhi(ri_gan_idx, ri_zhi_idx)

    # 驿马
    yima = get_yima(ri_zhi_idx)

    # 遁干
    jigong = RI_GAN_JI_GONG[ri_gan_idx]
    k1, k2, k3, k4 = si_ke
    dun_gan = {
        'jigong': get_dun_gan(ri_gan_idx, jigong),
        'rizhi': get_dun_gan(ri_gan_idx, ri_zhi_idx),
        'si_ke': [
            {'zhi': k1, 'gan': get_dun_gan(ri_gan_idx, k1)},
            {'zhi': k2, 'gan': get_dun_gan(ri_gan_idx, k2)},
            {'zhi': k3, 'gan': get_dun_gan(ri_gan_idx, k3)},
            {'zhi': k4, 'gan': get_dun_gan(ri_gan_idx, k4)},
        ],
        'san_chuan': [
            {'zhi': chuchuan, 'gan': get_dun_gan(ri_gan_idx, chuchuan)},
            {'zhi': zhongchuan, 'gan': get_dun_gan(ri_gan_idx, zhongchuan)},
            {'zhi': mochuan, 'gan': get_dun_gan(ri_gan_idx, mochuan)},
        ],
    }

    tianjiang_dict, direction, gui_ren_zhi = tianjiang_data
    tianjiang_list = []
    for d in range(12):
        tp = tianpan[d]
        tianjiang_list.append({
            'di_pan': d,
            'tian_pan': tp,
            'tian_jiang': tianjiang_dict[d],
        })

    result = {
        'title': '大六壬课式',
        'input': {
            'year': year,
            'month': month,
            'day': day,
            'hour': hour,
            'minute': minute,
            'ri_gan': ri_gan_idx,
            'ri_zhi': ri_zhi_idx,
            'ri_gan_str': TIAN_GAN[ri_gan_idx],
            'ri_zhi_str': DI_ZHI[ri_zhi_idx],
            'ri_ganzhi': format_gz(ri_gan_idx, ri_zhi_idx),
            'zhanshi': zhanshi_idx,
            'zhanshi_str': DI_ZHI[zhanshi_idx],
        },
        'yuejiang': {
            'index': yuejiang,
            'name': DI_ZHI[yuejiang],
        },
        'tianpan': [{
            'di_zhi': d,
            'di_zhi_str': DI_ZHI[d],
            'tian_pan': tianpan[d],
            'tian_pan_str': DI_ZHI[tianpan[d]],
        } for d in range(12)],
        'si_ke': [
            {'lesson': 1, 'name': '干上', 'zhi': k1, 'zhi_str': DI_ZHI[k1],
             'gan': get_dun_gan(ri_gan_idx, k1), 'gan_str': TIAN_GAN[get_dun_gan(ri_gan_idx, k1)]},
            {'lesson': 2, 'name': '干阴', 'zhi': k2, 'zhi_str': DI_ZHI[k2],
             'gan': get_dun_gan(ri_gan_idx, k2), 'gan_str': TIAN_GAN[get_dun_gan(ri_gan_idx, k2)]},
            {'lesson': 3, 'name': '支上', 'zhi': k3, 'zhi_str': DI_ZHI[k3],
             'gan': get_dun_gan(ri_gan_idx, k3), 'gan_str': TIAN_GAN[get_dun_gan(ri_gan_idx, k3)]},
            {'lesson': 4, 'name': '支阴', 'zhi': k4, 'zhi_str': DI_ZHI[k4],
             'gan': get_dun_gan(ri_gan_idx, k4), 'gan_str': TIAN_GAN[get_dun_gan(ri_gan_idx, k4)]},
        ],
        'san_chuan': {
            'method': method,
            'chuchuan': {
                'zhi': chuchuan, 'zhi_str': DI_ZHI[chuchuan],
                'gan': get_dun_gan(ri_gan_idx, chuchuan),
                'gan_str': TIAN_GAN[get_dun_gan(ri_gan_idx, chuchuan)],
                'ganzhi': format_gz(get_dun_gan(ri_gan_idx, chuchuan), chuchuan),
            },
            'zhongchuan': {
                'zhi': zhongchuan, 'zhi_str': DI_ZHI[zhongchuan],
                'gan': get_dun_gan(ri_gan_idx, zhongchuan),
                'gan_str': TIAN_GAN[get_dun_gan(ri_gan_idx, zhongchuan)],
                'ganzhi': format_gz(get_dun_gan(ri_gan_idx, zhongchuan), zhongchuan),
            },
            'mochuan': {
                'zhi': mochuan, 'zhi_str': DI_ZHI[mochuan],
                'gan': get_dun_gan(ri_gan_idx, mochuan),
                'gan_str': TIAN_GAN[get_dun_gan(ri_gan_idx, mochuan)],
                'ganzhi': format_gz(get_dun_gan(ri_gan_idx, mochuan), mochuan),
            },
        },
        'tianjiang': {
            'gui_ren_zhi': gui_ren_zhi,
            'gui_ren_str': DI_ZHI[gui_ren_zhi],
            'direction': direction,
            'day_night': '昼' if is_daytime(zhanshi_idx) else '夜',
            'positions': tianjiang_list,
        },
        'xunkong': [xunkong[0], xunkong[1]],
        'xunkong_str': f"{DI_ZHI[xunkong[0]]}{DI_ZHI[xunkong[1]]}",
        'yima': yima,
        'yima_str': DI_ZHI[yima],
        'jigong': jigong,
        'jigong_str': DI_ZHI[jigong],
    }

    return result


def main():
    if len(sys.argv) < 5:
        print("用法: python3 liuren.py <year> <month> <day> <hour> <minute>")
        sys.exit(1)

    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    hour = int(sys.argv[4])
    minute = int(sys.argv[5]) if len(sys.argv) > 5 else 0

    result = liuren_pai_pan(year, month, day, hour, minute)

    # ASCII图输出
    tianpan = make_tianpan(
        get_yuejiang(year, month, day),
        hour_zhi_index(hour, minute)
    )
    ri_gan_idx, ri_zhi_idx = day_ganzhi_from_date(year, month, day)
    zhanshi_idx = hour_zhi_index(hour, minute)
    yuejiang = get_yuejiang(year, month, day)
    si_ke = get_si_ke(tianpan, ri_gan_idx, ri_zhi_idx)
    san_chuan = get_san_chuan(tianpan, si_ke, ri_gan_idx, ri_zhi_idx)
    tianjiang_data = get_tianjiang(tianpan, ri_gan_idx, zhanshi_idx)
    xunkong = xunkong_ganzhi(ri_gan_idx, ri_zhi_idx)
    yima = get_yima(ri_zhi_idx)
    jigong = RI_GAN_JI_GONG[ri_gan_idx]

    diagram = build_ascii_diagram(
        tianpan, si_ke, san_chuan, ri_gan_idx, ri_zhi_idx,
        yuejiang, zhanshi_idx, tianjiang_data, xunkong, yima,
        san_chuan[3] if len(san_chuan) > 3 else 'fuyin', jigong
    )
    print(diagram)

    # JSON输出
    print("\n--- JSON ---")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
