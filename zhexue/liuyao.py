#!/usr/bin/env python3
"""
六爻排盘 — 纳甲筮法完整引擎
================================
起卦：铜钱摇卦 / 时间起卦 / 手动输入
装卦：纳甲（干支）、世应、六亲、六兽、动爻变卦
断卦：月建日辰、用神、旬空、生克冲合

用法：
  python3 liuyao.py coin                              # 铜钱起卦（当前时间）
  python3 liuyao.py coin -q "问事业"                   # 带问题
  python3 liuyao.py time 2026 7 28 8                   # 时间起卦
  python3 liuyao.py manual 0 1 0 1 0 1 2 0 1 2 1 0    # 手动输入（阳1阴0，动2=老阳, 动3=老阴）
  python3 liuyao.py manual-short 1 0 1 1 0 1           # 简写模式（仅本卦，自动判动爻）
"""

import sys, os
import json
import random
from datetime import datetime

# Import shared utilities from zhexue_core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zhexue_core import (
    TIAN_GAN, DI_ZHI,
    GAN_WUXING, ZHI_WUXING,
    day_ganzhi_from_date, hour_ganzhi,
    xunkong_ganzhi,
)
from jieqi_core import get_solar_month_idx

# ============================================================
# 1. 基础数据表
# ============================================================

# 八卦 → 索引 (标准先天八卦数: 乾1兑2离3震4巽5坎6艮7坤8)
# 用三爻二进制: 阳=1 阴=0, 自下而上
TRIGRAM_MAP = {
    # 三爻二进制: 阳=1 阴=0, 自下而上 (初, 二, 三)
    # 口诀: 兑上缺=(1,1,0), 巽下断=(0,1,1), 震仰盂=(1,0,0), 艮覆碗=(0,0,1)
    (1, 1, 1): ('乾', '☰', 1),
    (1, 1, 0): ('兑', '☱', 2),
    (1, 0, 1): ('离', '☲', 3),
    (1, 0, 0): ('震', '☳', 4),
    (0, 1, 1): ('巽', '☴', 5),
    (0, 1, 0): ('坎', '☵', 6),
    (0, 0, 1): ('艮', '☶', 7),
    (0, 0, 0): ('坤', '☷', 8),
}

# 八卦五行
TRIGRAM_WUXING = {
    '乾': '金', '兑': '金',
    '离': '火',
    '震': '木', '巽': '木',
    '坎': '水',
    '艮': '土', '坤': '土',
}

# 纳甲歌：八卦纳天干
TRIGRAM_NAGAN = {
    '乾': ('甲', '壬'),   # (内卦/下卦天干, 外卦/上卦天干)
    '坤': ('乙', '癸'),
    '震': ('庚', '庚'),
    '巽': ('辛', '辛'),
    '坎': ('戊', '戊'),
    '离': ('己', '己'),
    '艮': ('丙', '丙'),
    '兑': ('丁', '丁'),
}

# 浑天甲子定局 — 每卦六爻地支（初爻→上爻）
# 阳卦顺行阳支(子寅辰午申戌), 阴卦逆行阴支(丑亥酉未巳卯)
TRIGRAM_NAZHI = {
    # 乾(☰): 内卦起子，外卦起午
    '乾': {
        'inner': ['子', '寅', '辰'],    # 初、二、三爻
        'outer': ['午', '申', '戌'],    # 四、五、上爻
    },
    # 坎(☵): 内卦起寅，外卦起申
    '坎': {
        'inner': ['寅', '辰', '午'],
        'outer': ['申', '戌', '子'],
    },
    # 艮(☶): 内卦起辰，外卦起戌
    '艮': {
        'inner': ['辰', '午', '申'],
        'outer': ['戌', '子', '寅'],
    },
    # 震(☳): 内卦起子，外卦起午 (同乾)
    '震': {
        'inner': ['子', '寅', '辰'],
        'outer': ['午', '申', '戌'],
    },
    # 巽(☴): 内卦起丑，外卦起未 (阴支逆行)
    '巽': {
        'inner': ['丑', '亥', '酉'],
        'outer': ['未', '巳', '卯'],
    },
    # 离(☲): 内卦起卯，外卦起酉
    '离': {
        'inner': ['卯', '丑', '亥'],
        'outer': ['酉', '未', '巳'],
    },
    # 坤(☷): 内卦起未，外卦起丑
    '坤': {
        'inner': ['未', '巳', '卯'],
        'outer': ['丑', '亥', '酉'],
    },
    # 兑(☱): 内卦起巳，外卦起亥
    '兑': {
        'inner': ['巳', '卯', '丑'],
        'outer': ['亥', '酉', '未'],
    },
}

# ============================================================
# 2. 八宫六十四卦 — 完整列表
# ============================================================

def _build_64gua():
    """构建六十四卦完整映射表"""
    # 八宫: 乾兑离震巽坎艮坤
    palaces = []
    
    # 每宫的八卦配置
    palace_configs = [
        # (宫名, 纯卦上, 纯卦下, 一世到归魂的变化)
        # 一世=初爻变, 二世=初二变, 三世=初二+三爻变(即下卦全变)
        # 四世=下卦全变+四爻变, 五世=下卦全变+四五变, 游魂=下卦全变+四爻复原, 归魂=下卦复原
        ('乾', '☰', '☰', [
            ('一世', '☰', '☴'),   # 天风姤: 上乾下巽 (初爻变)
            ('二世', '☰', '☶'),   # 天山遁: 上乾下艮 (初二爻变)
            ('三世', '☰', '☷'),   # 天地否: 上乾下坤 (下卦全变)
            ('四世', '☴', '☷'),   # 风地观: 上巽下坤 (四爻变)
            ('五世', '☶', '☷'),   # 山地剥: 上艮下坤 (四五变)
            ('游魂', '☲', '☷'),   # 火地晋: 上离下坤 (四爻复)
            ('归魂', '☲', '☰'),   # 火天大有: 上离下乾 (下卦复)
        ]),
        ('兑', '☱', '☱', [
            ('一世', '☱', '☵'),   # 泽水困
            ('二世', '☱', '☷'),   # 泽地萃
            ('三世', '☱', '☶'),   # 泽山咸
            ('四世', '☵', '☶'),   # 水山蹇
            ('五世', '☷', '☶'),   # 地山谦
            ('游魂', '☳', '☶'),   # 雷山小过
            ('归魂', '☳', '☱'),   # 雷泽归妹
        ]),
        ('离', '☲', '☲', [
            ('一世', '☲', '☶'),   # 火山旅
            ('二世', '☲', '☴'),   # 火风鼎
            ('三世', '☲', '☵'),   # 火水未济
            ('四世', '☶', '☵'),   # 山水蒙
            ('五世', '☴', '☵'),   # 风水涣
            ('游魂', '☰', '☵'),   # 天水讼
            ('归魂', '☰', '☲'),   # 天火同人
        ]),
        ('震', '☳', '☳', [
            ('一世', '☳', '☷'),   # 雷地豫
            ('二世', '☳', '☵'),   # 雷水解
            ('三世', '☳', '☴'),   # 雷风恒
            ('四世', '☷', '☴'),   # 地风升
            ('五世', '☵', '☴'),   # 水风井
            ('游魂', '☱', '☴'),   # 泽风大过
            ('归魂', '☱', '☳'),   # 泽雷随
        ]),
        ('巽', '☴', '☴', [
            ('一世', '☴', '☰'),   # 风天小畜
            ('二世', '☴', '☲'),   # 风火家人
            ('三世', '☴', '☳'),   # 风雷益
            ('四世', '☰', '☳'),   # 天雷无妄
            ('五世', '☲', '☳'),   # 火雷噬嗑
            ('游魂', '☶', '☳'),   # 山雷颐
            ('归魂', '☶', '☴'),   # 山风蛊
        ]),
        ('坎', '☵', '☵', [
            ('一世', '☵', '☱'),   # 水泽节
            ('二世', '☵', '☳'),   # 水雷屯
            ('三世', '☵', '☲'),   # 水火既济
            ('四世', '☱', '☲'),   # 泽火革
            ('五世', '☳', '☲'),   # 雷火丰
            ('游魂', '☷', '☲'),   # 地火明夷
            ('归魂', '☷', '☵'),   # 地水师
        ]),
        ('艮', '☶', '☶', [
            ('一世', '☶', '☲'),   # 山火贲
            ('二世', '☶', '☰'),   # 山天大畜
            ('三世', '☶', '☱'),   # 山泽损
            ('四世', '☲', '☱'),   # 火泽睽
            ('五世', '☰', '☱'),   # 天泽履
            ('游魂', '☴', '☱'),   # 风泽中孚
            ('归魂', '☴', '☶'),   # 风山渐
        ]),
        ('坤', '☷', '☷', [
            ('一世', '☷', '☳'),   # 地雷复
            ('二世', '☷', '☱'),   # 地泽临
            ('三世', '☷', '☰'),   # 地天泰
            ('四世', '☳', '☰'),   # 雷天大壮
            ('五世', '☱', '☰'),   # 泽天夬
            ('游魂', '☵', '☰'),   # 水天需
            ('归魂', '☵', '☷'),   # 水地比
        ]),
    ]
    
    gua_names = {
        # 乾宫
        ('☰', '☰'): '乾为天', ('☰', '☴'): '天风姤', ('☰', '☶'): '天山遁',
        ('☰', '☷'): '天地否', ('☴', '☷'): '风地观', ('☶', '☷'): '山地剥',
        ('☲', '☷'): '火地晋', ('☲', '☰'): '火天大有',
        # 兑宫
        ('☱', '☱'): '兑为泽', ('☱', '☵'): '泽水困', ('☱', '☷'): '泽地萃',
        ('☱', '☶'): '泽山咸', ('☵', '☶'): '水山蹇', ('☷', '☶'): '地山谦',
        ('☳', '☶'): '雷山小过', ('☳', '☱'): '雷泽归妹',
        # 离宫
        ('☲', '☲'): '离为火', ('☲', '☶'): '火山旅', ('☲', '☴'): '火风鼎',
        ('☲', '☵'): '火水未济', ('☶', '☵'): '山水蒙', ('☴', '☵'): '风水涣',
        ('☰', '☵'): '天水讼', ('☰', '☲'): '天火同人',
        # 震宫
        ('☳', '☳'): '震为雷', ('☳', '☷'): '雷地豫', ('☳', '☵'): '雷水解',
        ('☳', '☴'): '雷风恒', ('☷', '☴'): '地风升', ('☵', '☴'): '水风井',
        ('☱', '☴'): '泽风大过', ('☱', '☳'): '泽雷随',
        # 巽宫
        ('☴', '☴'): '巽为风', ('☴', '☰'): '风天小畜', ('☴', '☲'): '风火家人',
        ('☴', '☳'): '风雷益', ('☰', '☳'): '天雷无妄', ('☲', '☳'): '火雷噬嗑',
        ('☶', '☳'): '山雷颐', ('☶', '☴'): '山风蛊',
        # 坎宫
        ('☵', '☵'): '坎为水', ('☵', '☱'): '水泽节', ('☵', '☳'): '水雷屯',
        ('☵', '☲'): '水火既济', ('☱', '☲'): '泽火革', ('☳', '☲'): '雷火丰',
        ('☷', '☲'): '地火明夷', ('☷', '☵'): '地水师',
        # 艮宫
        ('☶', '☶'): '艮为山', ('☶', '☲'): '山火贲', ('☶', '☰'): '山天大畜',
        ('☶', '☱'): '山泽损', ('☲', '☱'): '火泽睽', ('☰', '☱'): '天泽履',
        ('☴', '☱'): '风泽中孚', ('☴', '☶'): '风山渐',
        # 坤宫
        ('☷', '☷'): '坤为地', ('☷', '☳'): '地雷复', ('☷', '☱'): '地泽临',
        ('☷', '☰'): '地天泰', ('☳', '☰'): '雷天大壮', ('☱', '☰'): '泽天夬',
        ('☵', '☰'): '水天需', ('☵', '☷'): '水地比',
    }
    
    # 世应位置 (世爻位置)
    shi_yao_pos = {
        '本宫': 6, '一世': 1, '二世': 2, '三世': 3,
        '四世': 4, '五世': 5, '游魂': 4, '归魂': 3,
    }
    
    # 应爻 = (世爻 + 3) mod 6, 1-indexed
    def ying_yao(shi):
        y = shi + 3
        return y - 6 if y > 6 else y
    
    gua_db = {}  # key: (upper_trigram_char, lower_trigram_char)
    
    for palace, pure_upper, pure_lower, changes in palace_configs:
        wuxing = TRIGRAM_WUXING[palace]
        
        # 本宫卦 (纯卦, 六世)
        gua_db[(pure_upper, pure_lower)] = {
            'name': gua_names[(pure_upper, pure_lower)],
            'palace': palace,
            'palace_wuxing': wuxing,
            'shi_type': '本宫',
            'shi_yao': 6,
            'ying_yao': 3,
        }
        
        for shi_type, upper, lower in changes:
            gua_db[(upper, lower)] = {
                'name': gua_names[(upper, lower)],
                'palace': palace,
                'palace_wuxing': wuxing,
                'shi_type': shi_type,
                'shi_yao': shi_yao_pos[shi_type],
                'ying_yao': ying_yao(shi_yao_pos[shi_type]),
            }
    
    return gua_db

GUA_DB = _build_64gua()

# ============================================================
# 3. 卦象解析
# ============================================================

def lines_to_trigrams(lines):
    """
    六爻 → 上下卦
    lines: list of 6 ints, 1=阳 0=阴, 从初爻(0)到上爻(5)
    返回: (upper_triple, lower_triple, upper_char, lower_char)
    """
    lower = tuple(lines[0:3])  # 初、二、三 → 下卦
    upper = tuple(lines[3:6])  # 四、五、上 → 上卦
    
    if lower not in TRIGRAM_MAP or upper not in TRIGRAM_MAP:
        raise ValueError(f"Invalid trigram: upper={upper}, lower={lower}")
    
    lower_name, lower_glyph, _ = TRIGRAM_MAP[lower]
    upper_name, upper_glyph, _ = TRIGRAM_MAP[upper]
    
    return upper_glyph, lower_glyph, upper_name, lower_name


def identify_gua(lines):
    """识别卦名和所属宫位"""
    upper_glyph, lower_glyph, upper_name, lower_name = lines_to_trigrams(lines)
    key = (upper_glyph, lower_glyph)
    
    if key in GUA_DB:
        info = GUA_DB[key].copy()
        info['upper_glyph'] = upper_glyph
        info['lower_glyph'] = lower_glyph
        info['upper_name'] = upper_name
        info['lower_name'] = lower_name
        return info
    
    # 不应发生
    raise ValueError(f"Unknown hexagram: upper={upper_glyph}, lower={lower_glyph}")


# ============================================================
# 4. 纳甲装卦
# ============================================================

def najia_setup(lines, day_gan_idx):
    """
    完整装卦
    lines: [初, 二, 三, 四, 五, 上], 每个值为:
            0=老阴(动爻×), 1=少阳, 2=老阳(动爻○), 3=少阴
    返回: 装卦结果 dict
    """
    # 标准化成 (is_yang, is_dong)
    # 0=老阴→阴动, 1=少阳→阳静, 2=老阳→阳动, 3=少阴→阴静
    normalized = []
    for v in lines:
        if v == 0:      # 老阴 ×
            normalized.append((0, True))
        elif v == 1:    # 少阳
            normalized.append((1, False))
        elif v == 2:    # 老阳 ○
            normalized.append((1, True))
        elif v == 3:    # 少阴
            normalized.append((0, False))
        else:
            raise ValueError(f"Invalid line value: {v}")
    
    yang_lines = [n[0] for n in normalized]  # 1=阳 0=阴
    dong_lines = [n[1] for n in normalized]  # True=动爻
    
    # 识别本卦
    gua_info = identify_gua(yang_lines)
    
    upper_glyph = gua_info['upper_glyph']
    lower_glyph = gua_info['lower_glyph']
    upper_name = gua_info['upper_name']
    lower_name = gua_info['lower_name']
    palace = gua_info['palace']
    palace_wuxing = gua_info['palace_wuxing']
    shi_yao = gua_info['shi_yao']
    ying_yao = gua_info['ying_yao']
    
    # 纳支: 下卦(初二三爻)用inner, 上卦(四五上爻)用outer
    lower_zhi = TRIGRAM_NAZHI[lower_name]['inner']  # [初, 二, 三]
    upper_zhi = TRIGRAM_NAZHI[upper_name]['outer']  # [四, 五, 上]
    all_zhi = lower_zhi + upper_zhi  # [初, 二, 三, 四, 五, 上]
    
    # 纳甲(天干): 下卦用inner_gan, 上卦用outer_gan
    inner_gan, outer_gan = TRIGRAM_NAGAN[lower_name]
    upper_inner_gan, upper_outer_gan = TRIGRAM_NAGAN[upper_name]
    
    lower_gan = inner_gan  # 下卦天干
    upper_gan = upper_outer_gan  # 上卦天干
    
    all_gan = [lower_gan] * 3 + [upper_gan] * 3
    
    # 完整干支
    all_ganzhi = [f"{all_gan[i]}{all_zhi[i]}" for i in range(6)]
    
    # 六亲 (基于宫五行 vs 爻地支五行)
    # 规则: 同我=兄弟, 生我=父母, 我生=子孙, 克我=官鬼, 我克=妻财
    # WUXING_SHENG[X]=X生什么, WUXING_KE[X]=X克什么
    def get_liuqin(zhi):
        zhi_wx = ZHI_WUXING[zhi]
        if zhi_wx == palace_wuxing:                        # 同我 → 兄弟
            return '兄弟'
        if WUXING_SHENG.get(zhi_wx) == palace_wuxing:       # 支生宫 → 生我 → 父母
            return '父母'
        if WUXING_SHENG.get(palace_wuxing) == zhi_wx:       # 宫生支 → 我生 → 子孙
            return '子孙'
        if WUXING_KE.get(zhi_wx) == palace_wuxing:          # 支克宫 → 克我 → 官鬼
            return '官鬼'
        if WUXING_KE.get(palace_wuxing) == zhi_wx:          # 宫克支 → 我克 → 妻财
            return '妻财'
        # fallback (should never reach here)
        return '兄弟'
    
    liuqin = [get_liuqin(all_zhi[i]) for i in range(6)]
    
    # 六兽 (基于日干)
    LIU_SHOU = ['青龙', '朱雀', '勾陈', '螣蛇', '白虎', '玄武']
    liushou_start = day_gan_idx % 6
    # 初爻起: 根据日干决定起始六兽
    # 甲乙起青龙, 丙丁起朱雀, 戊起勾陈, 己起螣蛇, 庚辛起白虎, 壬癸起玄武
    if day_gan_idx in (0, 1):    # 甲乙
        liushou_offset = 0
    elif day_gan_idx in (2, 3):  # 丙丁
        liushou_offset = 1
    elif day_gan_idx == 4:       # 戊
        liushou_offset = 2
    elif day_gan_idx == 5:       # 己
        liushou_offset = 3
    elif day_gan_idx in (6, 7):  # 庚辛
        liushou_offset = 4
    else:                         # 壬癸
        liushou_offset = 5
    
    liushou = [LIU_SHOU[(i + liushou_offset) % 6] for i in range(6)]
    
    # 变卦 (如果有动爻)
    bian_lines = yang_lines[:]
    for i in range(6):
        if dong_lines[i]:
            bian_lines[i] = 1 - bian_lines[i]  # 阴阳反转
    
    has_change = any(dong_lines)
    bian_gua = None
    if has_change:
        bian_gua = identify_gua(bian_lines)
        # 变爻的纳支
        b_upper_name = bian_gua['upper_name']
        b_lower_name = bian_gua['lower_name']
        b_lower_zhi = TRIGRAM_NAZHI[b_lower_name]['inner']
        b_upper_zhi = TRIGRAM_NAZHI[b_upper_name]['outer']
        b_all_zhi = b_lower_zhi + b_upper_zhi
        
        # 变卦纳甲
        b_inner_gan, b_outer_gan = TRIGRAM_NAGAN[b_lower_name]
        b_upper_inner, b_upper_outer = TRIGRAM_NAGAN[b_upper_name]
        b_all_gan = [b_inner_gan]*3 + [b_upper_outer]*3
        b_all_ganzhi = [f"{b_all_gan[i]}{b_all_zhi[i]}" for i in range(6)]
        
        # 变卦六亲
        b_liuqin = []
        b_palace_wx = bian_gua['palace_wuxing']
        for zhi in b_all_zhi:
            zhi_wx = ZHI_WUXING[zhi]
            if zhi_wx == b_palace_wx:
                b_liuqin.append('兄弟')
            elif WUXING_SHENG.get(zhi_wx) == b_palace_wx:
                b_liuqin.append('父母')
            elif WUXING_SHENG.get(b_palace_wx) == zhi_wx:
                b_liuqin.append('子孙')
            elif WUXING_KE.get(zhi_wx) == b_palace_wx:
                b_liuqin.append('官鬼')
            elif WUXING_KE.get(b_palace_wx) == zhi_wx:
                b_liuqin.append('妻财')
            else:
                b_liuqin.append('兄弟')
    else:
        b_all_zhi = all_zhi[:]
        b_all_ganzhi = all_ganzhi[:]
        b_liuqin = liuqin[:]
    
    # 组装结果
    yao_list = []
    for i in range(6):
        yao_pos = i + 1  # 1-based
        yao = {
            'position': yao_pos,
            'label': ['初', '二', '三', '四', '五', '上'][i],
            'yang': yang_lines[i],
            'is_dong': dong_lines[i],
            'gan': all_gan[i],
            'zhi': all_zhi[i],
            'ganzhi': all_ganzhi[i],
            'liuqin': liuqin[i],
            'liushou': liushou[i],
            'is_shi': yao_pos == shi_yao,
            'is_ying': yao_pos == ying_yao,
            'bian_ganzhi': b_all_ganzhi[i],
            'bian_liuqin': b_liuqin[i],
            'bian_yang': bian_lines[i],
        }
        yao_list.append(yao)
    
    result = {
        'gua': gua_info,
        'yao_list': yao_list,
        'has_change': has_change,
        'bian_gua': bian_gua,
        'dong_yao_positions': [i+1 for i in range(6) if dong_lines[i]],
        'shi_yao': shi_yao,
        'ying_yao': ying_yao,
        'palace': palace,
        'palace_wuxing': palace_wuxing,
    }
    
    return result


# ============================================================
# 5. 起卦方法
# ============================================================

def coin_cast():
    """铜钱摇卦: 模拟三枚铜钱摇6次"""
    def one_cast():
        coins = [random.randint(0, 1) for _ in range(3)]
        heads = sum(coins)
        if heads == 0:   # 三反 → 老阳（阳动）
            return 2
        elif heads == 1:  # 两正一反 → 少阴
            return 3
        elif heads == 2:  # 一正两反 → 少阳
            return 1
        else:             # 三正 → 老阴（阴动）
            return 0
    
    lines = [one_cast() for _ in range(6)]
    return lines


def time_guaxiang(year, month, day, hour):
    """时间起卦: 年月日时 → 六爻"""
    # 梅花易数式时间起卦转为六爻用
    # 上卦 = (年+月+日) mod 8
    # 下卦 = (年+月+日+时) mod 8
    # 动爻 = (年+月+日+时) mod 6 + 1 (1-indexed)
    
    shang = (year + month + day) % 8
    xia = (year + month + day + hour) % 8
    dong_yao = ((year + month + day + hour) % 6)  # 0-indexed
    
    # 数字→八卦: 1乾2兑3离4震5巽6坎7艮8坤, 余数0→坤(8)
    # num_to_gua 键 0 已映射坤, 直接取; 不能查键8(不存在)
    num_to_gua = {1: '☰', 2: '☱', 3: '☲', 4: '☳', 5: '☴', 6: '☵', 7: '☶', 0: '☷'}

    shang_glyph = num_to_gua[shang]
    xia_glyph = num_to_gua[xia]
    
    # 从卦符反推三爻
    glyph_to_triple = {v: k for k, v in [(k[0], v[1]) for k, v in TRIGRAM_MAP.items()]}
    # Actually let me just build a simpler map
    trigram_glyph_to_lines = {}
    for triple, (name, glyph, num) in TRIGRAM_MAP.items():
        trigram_glyph_to_lines[glyph] = list(triple)
    
    shang_lines = trigram_glyph_to_lines[shang_glyph]
    xia_lines = trigram_glyph_to_lines[xia_glyph]
    
    # 六爻: 初(xia[0]), 二(xia[1]), 三(xia[2]), 四(shang[0]), 五(shang[1]), 上(shang[2])
    lines = xia_lines + shang_lines
    
    # 转换为六爻编码: 阳→1(少阳), 阴→3(少阴), 动爻位置变为老阳/老阴
    result = []
    for i in range(6):
        is_yang = lines[i]
        if i == dong_yao:
            result.append(2 if is_yang else 0)  # 老阳/老阴
        else:
            result.append(1 if is_yang else 3)  # 少阳/少阴
    
    return result


def manual_to_lines(values):
    """手动输入转六爻编码
    values: 简写模式 1=阳 0=阴 (6个值), 自动随机定动爻 (30%概率每爻)
           或完整模式 每个值: 0=老阴, 1=少阳, 2=老阳, 3=少阴 (6或12个值)
    """
    if len(values) == 6:
        # 简写模式, 自动定动爻
        result = []
        for v in values:
            if v == 1:
                result.append(2 if random.random() < 0.3 else 1)  # 30%概率为老阳
            else:
                result.append(0 if random.random() < 0.3 else 3)
        return result
    elif len(values) == 12:
        # 完整模式 (本卦6 + 动爻标识6)
        yang_vals = values[:6]
        dong_flags = values[6:]
        result = []
        for i in range(6):
            if dong_flags[i]:
                result.append(2 if yang_vals[i] else 0)
            else:
                result.append(1 if yang_vals[i] else 3)
        return result
    else:
        # 完整模式 直接给编码
        return values


# ============================================================
# 6. 月建日辰计算
# ============================================================

WUXING_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
WUXING_KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}

def get_yuejian_richen(year, month, day, hour=0):
    """获取月建和日辰"""
    # 日干支
    ri_gan_idx, ri_zhi_idx = day_ganzhi_from_date(year, month, day)
    ri_gan = TIAN_GAN[ri_gan_idx]
    ri_zhi = DI_ZHI[ri_zhi_idx]
    
    # 月建 (节气月地支)
    solar_idx = get_solar_month_idx(year, month, day)
    # solar_idx: 0=丑月, 1=寅月, ..., 11=子月
    # 但我们需要统一: 寅=0 ... 丑=11 或保持原样
    # get_solar_month_idx returns: 寅=1 卯=2 ... 丑=0=12
    
    # 节气月 → 地支
    yue_zhi_map = {
        1: '寅', 2: '卯', 3: '辰', 4: '巳', 5: '午', 6: '未',
        7: '申', 8: '酉', 9: '戌', 10: '亥', 11: '子', 0: '丑',
    }
    yue_zhi = yue_zhi_map.get(solar_idx, '子')
    
    # 月干 (五虎遁: 甲己之年丙作首...)
    # yue_gan_map 索引以寅月为 0（如丙年: 庚寅、辛卯...乙未、丙申），
    # 而 solar_idx 以寅月为 1（0=丑月），故取 [solar_idx - 1]；丑月时 -1%12=11
    year_gan_idx = (year - 4) % 10
    yue_gan_map = {
        0: ['丙','丁','戊','己','庚','辛','壬','癸','甲','乙','丙','丁'],  # 甲年
        1: ['戊','己','庚','辛','壬','癸','甲','乙','丙','丁','戊','己'],  # 乙年
        2: ['庚','辛','壬','癸','甲','乙','丙','丁','戊','己','庚','辛'],  # 丙年
        3: ['壬','癸','甲','乙','丙','丁','戊','己','庚','辛','壬','癸'],  # 丁年
        4: ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸','甲','乙'],  # 戊年
    }
    yue_gan_map.update({
        5: ['丙','丁','戊','己','庚','辛','壬','癸','甲','乙','丙','丁'],  # 己年=甲年
        6: ['戊','己','庚','辛','壬','癸','甲','乙','丙','丁','戊','己'],  # 庚年=乙年
        7: ['庚','辛','壬','癸','甲','乙','丙','丁','戊','己','庚','辛'],  # 辛年=丙年
        8: ['壬','癸','甲','乙','丙','丁','戊','己','庚','辛','壬','癸'],  # 壬年=丁年
        9: ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸','甲','乙'],  # 癸年=戊年
    })

    yue_gan = yue_gan_map[year_gan_idx][solar_idx - 1]

    # 旬空 (按日柱所在旬: 甲子旬空戌亥 ... 甲寅旬空子丑)
    xunkong_zhi = [DI_ZHI[i] for i in xunkong_ganzhi(ri_gan_idx, ri_zhi_idx)]
    
    return {
        'year': year, 'month': month, 'day': day,
        'yue_gan': yue_gan,
        'yue_zhi': yue_zhi,
        'yue_ganzhi': f'{yue_gan}{yue_zhi}',
        'ri_gan': ri_gan,
        'ri_zhi': ri_zhi,
        'ri_ganzhi': f'{ri_gan}{ri_zhi}',
        'ri_gan_idx': ri_gan_idx,
        'ri_zhi_idx': ri_zhi_idx,
        'xunkong': xunkong_zhi,
        'solar_month_idx': solar_idx,
    }


# ============================================================
# 7. 用神判断
# ============================================================

YONGSHEN_MAP = {
    '事业': '官鬼',
    '工作': '官鬼',
    '功名': '官鬼',
    '考试': '父母',
    '文书': '父母',
    '学业': '父母',
    '感情': '妻财',  # 男测感情取妻财, 女测取官鬼
    '婚姻': '妻财',
    '财运': '妻财',
    '财富': '妻财',
    '健康': '子孙',  # 子孙为医药
    '疾病': '官鬼',  # 官鬼为病
    '子女': '子孙',
    '出行': '子孙',
    '诉讼': '官鬼',
    '父母': '父母',
    '兄弟': '兄弟',
    '朋友': '兄弟',
    '合作': '兄弟',
}

def determine_yongshen(question, gender='male'):
    """根据问题判断用神"""
    if not question:
        return None
    
    question_lower = question.lower()
    for keyword, yongshen in YONGSHEN_MAP.items():
        if keyword in question_lower or keyword in question:
            if keyword == '感情' and gender == 'female':
                return '官鬼'
            if keyword == '感情':
                return '妻财'
            return yongshen
    
    return None


# ============================================================
# 8. 解卦辅助
# ============================================================

def analyze_wangshuai(yao_list, yuejian, richen):
    """分析各爻旺衰"""
    yue_zhi = yuejian['yue_zhi']
    ri_zhi = richen['ri_zhi']
    
    def zhi_wangshuai(zhi):
        """判断地支在月建日辰下的旺衰"""
        # 月建: 同我为旺, 生我为相, 我生为休, 我克为囚, 克我为死
        zhi_wx = ZHI_WUXING[zhi]
        yue_wx = ZHI_WUXING[yue_zhi]
        
        if zhi_wx == yue_wx:
            yue_status = '旺'
        elif WUXING_SHENG.get(yue_wx) == zhi_wx:
            yue_status = '相'
        elif WUXING_SHENG.get(zhi_wx) == yue_wx:
            yue_status = '休'
        elif WUXING_KE.get(zhi_wx) == yue_wx:
            yue_status = '囚'
        elif WUXING_KE.get(yue_wx) == zhi_wx:
            yue_status = '死'
        else:
            yue_status = '平'
        
        # 日辰: 同我则旺
        ri_wx = ZHI_WUXING[ri_zhi]
        if zhi == ri_zhi:
            ri_status = '临日(旺)'
        elif zhi_wx == ri_wx:
            ri_status = '同气(旺)'
        elif zhi == DI_ZHI[(DI_ZHI.index(ri_zhi) + 6) % 12]:  # 六冲
            ri_status = '日冲(破)'
        elif zhi == DI_ZHI[(DI_ZHI.index(ri_zhi) + 1) % 12] or zhi == DI_ZHI[(DI_ZHI.index(ri_zhi) + 2) % 12]:
            # 简化的合判断
            ri_status = '平'
        else:
            ri_status = '平'
        
        # 旬空判定
        return {
            'yue_status': yue_status,
            'ri_status': ri_status,
        }
    
    for yao in yao_list:
        yao['wangshuai'] = zhi_wangshuai(yao['zhi'])


def generate_analysis(result, time_info, question=None, gender='male'):
    """生成基础分析"""
    lines = []
    lines.append("=" * 60)
    lines.append("六爻排盘 — 纳甲筮法")
    lines.append("=" * 60)
    
    gua = result['gua']
    
    # 时间信息
    lines.append(f"\n起卦时间: {time_info['year']}年{time_info['month']}月{time_info['day']}日")
    lines.append(f"月建: {time_info['yue_ganzhi']}  日辰: {time_info['ri_ganzhi']}")
    lines.append(f"旬空: {' '.join(time_info['xunkong'])}")
    
    if question:
        yongshen = determine_yongshen(question, gender)
        lines.append(f"所问: {question}")
        if yongshen:
            lines.append(f"用神: {yongshen}")
    
    # 本卦
    lines.append(f"\n{'─' * 40}")
    lines.append(f"【本卦】{gua['name']}  ({gua['palace']}宫, 属{gua['palace_wuxing']}, {gua['shi_type']}卦)")
    lines.append(f"{'─' * 40}")
    
    labels = ['上爻', '五爻', '四爻', '三爻', '二爻', '初爻']
    for i in range(5, -1, -1):
        yao = result['yao_list'][i]
        markers = []
        if yao['is_shi']:
            markers.append('世')
        if yao['is_ying']:
            markers.append('应')
        if yao['is_dong']:
            markers.append('动')
        
        marker_str = '(' + ' '.join(markers) + ')' if markers else ''
        
        yang_str = '━━━' if yao['yang'] else '━ ━'
        if yao['is_dong']:
            yang_str += ' ○' if yao['yang'] else ' ×'
        
        lines.append(f"  {yao['label']:3s} {yang_str:8s} {yao['liuqin']:4s} {yao['ganzhi']:4s} {yao['liushou']:4s} {marker_str}")
    
    # 变卦
    if result['has_change']:
        bian = result['bian_gua']
        lines.append(f"\n{'─' * 40}")
        lines.append(f"【变卦】{bian['name']}  ({bian['palace']}宫, 属{bian['palace_wuxing']})")
        lines.append(f"{'─' * 40}")
        
        for i in range(5, -1, -1):
            yao = result['yao_list'][i]
            if yao['is_dong']:
                byang = '━━━' if yao['bian_yang'] else '━ ━'
                lines.append(f"  {yao['label']:3s} {byang:8s} {yao['bian_liuqin']:4s} {yao['bian_ganzhi']:4s}  ←变")
            else:
                byang = '━━━' if yao['bian_yang'] else '━ ━'
                lines.append(f"  {yao['label']:3s} {byang:8s} {yao['bian_liuqin']:4s} {yao['bian_ganzhi']:4s}")
    
    # 旺衰分析
    lines.append(f"\n{'─' * 40}")
    lines.append("【旺衰分析】")
    lines.append(f"{'─' * 40}")
    for yao in result['yao_list']:
        if 'wangshuai' in yao:
            ws = yao['wangshuai']
            dong_str = '(动)' if yao['is_dong'] else ''
            shiying_str = '(世)' if yao['is_shi'] else ('(应)' if yao['is_ying'] else '')
            lines.append(f"  {yao['label']:3s} {yao['ganzhi']:4s} {yao['liuqin']:4s} 月{ws['yue_status']:3s} 日{ws['ri_status']} {dong_str}{shiying_str}")
    
    # 动爻分析
    if result['has_change']:
        lines.append(f"\n{'─' * 40}")
        lines.append("【动爻分析】")
        lines.append(f"{'─' * 40}")
        for i in result['dong_yao_positions']:
            yao = result['yao_list'][i - 1]
            lines.append(f"  {yao['label']}爻发动: {yao['liuqin']} {yao['ganzhi']}")
            lines.append(f"    本卦: {yao['ganzhi']} {yao['liuqin']} → 变卦: {yao['bian_ganzhi']} {yao['bian_liuqin']}")
            
            # 生克分析
            ben_zhi_wx = ZHI_WUXING[yao['zhi']]
            bian_zhi_wx = ZHI_WUXING[yao['bian_ganzhi'][1]]  # 变卦地支
            if WUXING_SHENG.get(ben_zhi_wx) == bian_zhi_wx:
                lines.append(f"    本生变(化泄): 自身力量泄于变化")
            elif WUXING_SHENG.get(bian_zhi_wx) == ben_zhi_wx:
                lines.append(f"    变生本(回头生): 变化加强自身")
            elif WUXING_KE.get(ben_zhi_wx) == bian_zhi_wx:
                lines.append(f"    本克变(化财): 自身克制变化")
            elif WUXING_KE.get(bian_zhi_wx) == ben_zhi_wx:
                lines.append(f"    变克本(回头克): ⚠ 变化克制自身, 不吉")
            elif ben_zhi_wx == bian_zhi_wx:
                lines.append(f"    比和: 自身与变化同气")
    
    # 世应用神
    lines.append(f"\n{'─' * 40}")
    lines.append("【世应关系】")
    lines.append(f"{'─' * 40}")
    shi_yao = result['yao_list'][result['shi_yao'] - 1]
    ying_yao = result['yao_list'][result['ying_yao'] - 1]
    lines.append(f"  世爻: {shi_yao['label']}  {shi_yao['liuqin']} {shi_yao['ganzhi']} {shi_yao['liushou']}")
    lines.append(f"  应爻: {ying_yao['label']}  {ying_yao['liuqin']} {ying_yao['ganzhi']} {ying_yao['liushou']}")
    
    # 世应生克
    shi_wx = ZHI_WUXING[shi_yao['zhi']]
    ying_wx = ZHI_WUXING[ying_yao['zhi']]
    if WUXING_KE.get(shi_wx) == ying_wx:
        lines.append(f"  世克应: 我方主导")
    elif WUXING_KE.get(ying_wx) == shi_wx:
        lines.append(f"  应克世: 对方制约我方")
    elif WUXING_SHENG.get(shi_wx) == ying_wx:
        lines.append(f"  世生应: 我方付出多")
    elif WUXING_SHENG.get(ying_wx) == shi_wx:
        lines.append(f"  应生世: 对方有益于我")
    elif shi_wx == ying_wx:
        lines.append(f"  比和: 双方对等")
    
    return '\n'.join(lines)


# ============================================================
# 9. 主函数
# ============================================================

def run_liuyao(method='coin', params=None, question=None, gender='male', year=None, month=None, day=None, hour=None):
    """
    运行六爻排盘
    
    method: 'coin', 'time', 'manual'
    params: 对于manual, 六爻值列表
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    if day is None:
        day = now.day
    if hour is None:
        hour = now.hour
    
    # 起卦
    if method == 'coin':
        lines = coin_cast()
    elif method == 'time':
        lines = time_guaxiang(year, month, day, hour)
    elif method == 'manual':
        if params is None:
            raise ValueError("Manual method requires params")
        lines = manual_to_lines(params)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # 日辰信息
    time_info = get_yuejian_richen(year, month, day, hour)
    
    # 装卦
    result = najia_setup(lines, time_info['ri_gan_idx'])
    
    # 旺衰分析
    analyze_wangshuai(result['yao_list'], 
                       {'yue_zhi': time_info['yue_zhi']},
                       {'ri_zhi': time_info['ri_zhi']})
    
    # 用神
    yongshen = determine_yongshen(question, gender) if question else None
    
    # 生成分析文本
    analysis = generate_analysis(result, time_info, question, gender)
    
    # JSON输出
    json_output = {
        'method': method,
        'time': {
            'year': year, 'month': month, 'day': day, 'hour': hour,
            'yue_ganzhi': time_info['yue_ganzhi'],
            'ri_ganzhi': time_info['ri_ganzhi'],
            'xunkong': time_info['xunkong'],
        },
        'question': question,
        'yongshen': yongshen,
        'ben_gua': {
            'name': result['gua']['name'],
            'palace': result['gua']['palace'],
            'palace_wuxing': result['gua']['palace_wuxing'],
            'shi_type': result['gua']['shi_type'],
            'shi_yao': result['shi_yao'],
            'ying_yao': result['ying_yao'],
        },
        'yao': [],
        'has_change': result['has_change'],
        'dong_yao_positions': result['dong_yao_positions'],
    }
    
    for yao in result['yao_list']:
        jy = {
            'position': yao['position'],
            'label': yao['label'],
            'yang': yao['yang'],
            'is_dong': yao['is_dong'],
            'ganzhi': yao['ganzhi'],
            'liuqin': yao['liuqin'],
            'liushou': yao['liushou'],
            'is_shi': yao['is_shi'],
            'is_ying': yao['is_ying'],
            'wangshuai': yao.get('wangshuai', {}),
        }
        if result['has_change']:
            jy['bian_ganzhi'] = yao['bian_ganzhi']
            jy['bian_liuqin'] = yao['bian_liuqin']
            jy['bian_yang'] = yao['bian_yang']
        json_output['yao'].append(jy)
    
    if result['has_change']:
        json_output['bian_gua'] = {
            'name': result['bian_gua']['name'],
            'palace': result['bian_gua']['palace'],
            'palace_wuxing': result['bian_gua']['palace_wuxing'],
        }
    
    print(analysis)
    print("\n" + "=" * 60)
    print("\n[JSON OUTPUT]")
    print(json.dumps(json_output, ensure_ascii=False, indent=2))
    
    return json_output


# ============================================================
# 10. CLI入口
# ============================================================

def main():
    args = sys.argv[1:]
    
    if len(args) == 0:
        # 默认铜钱起卦
        run_liuyao(method='coin')
        sys.exit(0)
    
    method = args[0]
    question = None
    remaining = list(args[1:])
    
    # 解析 -q 参数
    if '-q' in remaining:
        qi = remaining.index('-q')
        if qi + 1 < len(remaining):
            question = remaining[qi + 1]
            remaining = remaining[:qi] + remaining[qi+2:]
    
    if '--question' in remaining:
        qi = remaining.index('--question')
        if qi + 1 < len(remaining):
            question = remaining[qi + 1]
            remaining = remaining[:qi] + remaining[qi+2:]
    
    try:
        if method == 'coin':
            run_liuyao(method='coin', question=question)
        
        elif method == 'time':
            y, m, d = int(remaining[0]), int(remaining[1]), int(remaining[2])
            h = int(remaining[3]) if len(remaining) > 3 else 12
            run_liuyao(method='time', question=question, year=y, month=m, day=d, hour=h)
        
        elif method == 'manual' or method == 'manual-short':
            values = [int(v) for v in remaining]
            run_liuyao(method='manual', params=values, question=question)
        
        elif method == 'test':
            # 测试: 铜钱起卦
            random.seed(42)  # 固定种子用于测试
            run_liuyao(method='coin', question='问事业')
        
        else:
            print(f"Unknown method: {method}")
            print("Usage: python3 liuyao.py [coin|time|manual|manual-short] [params...] [-q question]")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
