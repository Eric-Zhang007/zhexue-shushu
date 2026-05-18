#!/usr/bin/env python3
"""紫微斗数 — 完整安星诀实现

CLI: python3 ziwei.py <year> <month> <day> <hour> <minute> <gender>
输出: JSON + 星盘文本

依赖: zhexue_core.py (同目录), lunarcalendar, ephem
"""
import sys, json
from datetime import datetime, date
from lunarcalendar import Lunar

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from zhexue_core import (
    TIAN_GAN, DI_ZHI, GAN_WUXING, ZHI_WUXING,
    GAN_YINYANG, ZHI_YINYANG,
    day_ganzhi_from_date, hour_zhi_index, hour_gan,
    month_gan, WU_HU_DUN, get_ju, get_nayin,
    NAYIN_TO_JU, NAYIN_WUXING,
    SHENG_XIAO, get_shi_shen,
)

# ========================================================================
# 农历转换 (使用 lunarcalendar)
# ========================================================================

_lunar_cache = {}

def solar_to_lunar(year, month, day):
    """公历→农历, 返回 (lunar_year, lunar_month, lunar_day, is_leap)"""
    key = (year, month, day)
    if key in _lunar_cache:
        return _lunar_cache[key]
    dt = date(year, month, day)
    l = Lunar.from_date(dt)
    result = (l.year, l.month, l.day, l.isleap)
    _lunar_cache[key] = result
    return result


# ========================================================================
# 安星诀 — 星曜定位
# ========================================================================

# 紫微星系 (6颗): 相对紫微偏移(顺时针+)
ZIWEI_OFFSETS = {
    '紫微':  0,
    '天机': -1,
    '太阳': -3,
    '武曲': -4,
    '天同': -5,
    '廉贞':  4,
}

# 天府星系 (8颗): 相对天府偏移(顺时针+)
TIANFU_OFFSETS = {
    '天府':  0,
    '太阴':  1,
    '贪狼':  2,
    '巨门':  3,
    '天相':  4,
    '天梁':  5,
    '七杀':  6,
    '破军':  8,
}

# 辅星
def zuofu_position(lunar_month):
    """左辅: 正月起辰(4), 顺数"""
    return (4 + lunar_month - 1) % 12

def youbi_position(lunar_month):
    """右弼: 正月起戌(10), 逆数"""
    return (10 - (lunar_month - 1) + 12) % 12

def wenchang_position(hour_zhi_idx):
    """文昌: 子时起戌(10), 逆数至生时"""
    return (10 - hour_zhi_idx + 12) % 12

def wenqu_position(hour_zhi_idx):
    """文曲: 子时起辰(4), 顺数至生时"""
    return (4 + hour_zhi_idx) % 12

TIANKUI_TABLE = {
    0: 1,   # 甲→丑
    1: 0,   # 乙→子
    2: 11,  # 丙→亥
    3: 9,   # 丁→酉
    4: 1,   # 戊→丑
    5: 0,   # 己→子
    6: 1,   # 庚→丑
    7: 6,   # 辛→午
    8: 3,   # 壬→卯
    9: 3,   # 癸→卯
}
TIANYUE_TABLE = {
    0: 7,   # 甲→未
    1: 8,   # 乙→申
    2: 9,   # 丙→酉
    3: 11,  # 丁→亥
    4: 7,   # 戊→未
    5: 8,   # 己→申
    6: 7,   # 庚→未
    7: 2,   # 辛→寅
    8: 5,   # 壬→巳
    9: 5,   # 癸→巳
}
LUCUN_TABLE = {
    0: 2,   # 甲→寅
    1: 3,   # 乙→卯
    2: 5,   # 丙→巳
    3: 6,   # 丁→午
    4: 5,   # 戊→巳
    5: 6,   # 己→午
    6: 8,   # 庚→申
    7: 9,   # 辛→酉
    8: 11,  # 壬→亥
    9: 0,   # 癸→子
}

def tianma_position(year_zhi_idx):
    """天马: 寅午戌→申, 申子辰→寅, 巳酉丑→亥, 亥卯未→巳"""
    triples = {
        (2,6,10): 8,   # 寅午戌→申
        (8,0,4): 2,    # 申子辰→寅
        (5,9,1): 11,   # 巳酉丑→亥
        (11,3,7): 5,   # 亥卯未→巳
    }
    for zhis, pos in triples.items():
        if year_zhi_idx in zhis:
            return pos
    return 8

def huoxing_position(year_zhi_idx, hour_zhi_idx):
    """火星: 年支三合定基宫, 逆数至生时"""
    base_map = {(2,6,10):1, (8,0,4):3, (5,9,1):6, (11,3,7):9}
    base = 1
    for zhis, b in base_map.items():
        if year_zhi_idx in zhis:
            base = b
            break
    return (base - hour_zhi_idx + 12) % 12

def lingxing_position(year_zhi_idx, hour_zhi_idx):
    """铃星: 年支三合定基宫, 逆数至生时"""
    base_map = {(2,6,10):10, (8,0,4):6, (5,9,1):3, (11,3,7):0}
    base = 10
    for zhis, b in base_map.items():
        if year_zhi_idx in zhis:
            base = b
            break
    return (base - hour_zhi_idx + 12) % 12


# ========================================================================
# 四化 — 年干定
# ========================================================================
SIHUA_TABLE = {
    0: ('廉贞','破军','武曲','太阳'),  # 甲
    1: ('天机','天梁','紫微','太阴'),  # 乙
    2: ('天同','天机','文昌','廉贞'),  # 丙
    3: ('太阴','天同','天机','巨门'),  # 丁
    4: ('贪狼','太阴','右弼','天机'),  # 戊
    5: ('武曲','贪狼','天梁','文曲'),  # 己
    6: ('太阳','武曲','太阴','天同'),  # 庚
    7: ('巨门','太阳','文曲','文昌'),  # 辛
    8: ('天梁','紫微','左辅','武曲'),  # 壬
    9: ('破军','巨门','太阴','贪狼'),  # 癸
}

PALACE_NAMES = ['命宫','兄弟宫','夫妻宫','子女宫','财帛宫','疾厄宫',
                '迁移宫','交友宫','官禄宫','田宅宫','福德宫','父母宫']


def ziwei_star_position(lunar_day, ju):
    """紫微星定位. 返回地支索引(0=子...11=亥).
    诀: 生日/局=商余, 余0顺商, 余奇顺1, 余偶逆1
    """
    q = lunar_day // ju
    r = lunar_day % ju
    if r == 0:
        return (2 + q - 1) % 12
    else:
        base = (2 + q) % 12
        return (base + 1) % 12 if r % 2 == 1 else (base - 1) % 12


# ========================================================================
# 命盘
# ========================================================================

class ZiweiChart:
    """紫微斗数命盘"""

    def __init__(self, year, month, day, hour, minute, gender):
        self.solar_year = year
        self.solar_month = month
        self.solar_day = day
        self.hour = hour
        self.minute = minute
        self.gender = gender  # '男'/'女'

        # 1. 公历→农历
        ly, lm, ld, is_leap = solar_to_lunar(year, month, day)
        self.lunar_year = ly
        self.lunar_month = lm
        self.lunar_day = ld
        self.lunar_is_leap = is_leap

        # 2. 日干支 + 时干支
        self.day_gan, self.day_zhi = day_ganzhi_from_date(year, month, day)
        self.hour_zhi = hour_zhi_index(hour, minute)
        self.hour_gan = hour_gan(self.day_gan, self.hour_zhi)

        # 3. 年干支(农历年)
        self.year_gan = (self.lunar_year - 4) % 10
        self.year_zhi = (self.lunar_year - 4) % 12

        # 4. 命宫/身宫
        self.ming_palace_zhi = self._calc_ming_palace()
        self.shen_palace_zhi = self._calc_shen_palace()

        # 5. 十二宫天干 (五虎遁)
        self.palace_gans = self._calc_palace_gans()

        # 6. 命宫干支 → 纳音 → 五行局
        ming_gan = self.palace_gans[self.ming_palace_zhi]
        self.ming_ganzhi = (ming_gan, self.ming_palace_zhi)
        self.ju = get_ju(ming_gan, self.ming_palace_zhi)

        # 7. 布星
        self.stars = self._place_all_stars()

        # 8. 十二宫
        self.palaces = self._build_palaces()

        # 9. 四化
        self.sihua = self._calc_sihua()

        # 10. 大限
        self.grand_limits = self._calc_grand_limits()

    def _calc_ming_palace(self):
        """命宫: 寅上正月逆数, 生月支上子时顺数"""
        return (2 - (self.lunar_month - 1) + self.hour_zhi) % 12

    def _calc_shen_palace(self):
        """身宫: 寅上正月顺数, 生月支上子时顺数"""
        return (2 + (self.lunar_month - 1) + self.hour_zhi) % 12

    def _calc_palace_gans(self):
        """五虎遁: 寅月起年干月干, 轮十二宫"""
        start = WU_HU_DUN[self.year_gan]
        gans = {}
        for zhi_idx in range(12):
            gans[zhi_idx] = (start + (zhi_idx - 2 + 12) % 12) % 10
        return gans

    def _place_all_stars(self):
        """安放全部星曜"""
        stars = {}

        ziwei_pos = ziwei_star_position(self.lunar_day, self.ju)

        # ---- 紫微星系 ----
        for name, off in ZIWEI_OFFSETS.items():
            stars.setdefault((ziwei_pos + off) % 12, []).append(name)

        # ---- 天府星系 ----
        tianfu_pos = (6 - ziwei_pos) % 12
        for name, off in TIANFU_OFFSETS.items():
            stars.setdefault((tianfu_pos + off) % 12, []).append(name)

        # ---- 辅星 ----
        stars.setdefault(zuofu_position(self.lunar_month), []).append('左辅')
        stars.setdefault(youbi_position(self.lunar_month), []).append('右弼')
        stars.setdefault(wenchang_position(self.hour_zhi), []).append('文昌')
        stars.setdefault(wenqu_position(self.hour_zhi), []).append('文曲')
        stars.setdefault(TIANKUI_TABLE[self.year_gan], []).append('天魁')
        stars.setdefault(TIANYUE_TABLE[self.year_gan], []).append('天钺')

        lc_pos = LUCUN_TABLE[self.year_gan]
        stars.setdefault(lc_pos, []).append('禄存')
        stars.setdefault((lc_pos + 1) % 12, []).append('擎羊')
        stars.setdefault((lc_pos - 1) % 12, []).append('陀罗')
        stars.setdefault(tianma_position(self.year_zhi), []).append('天马')

        hx_pos = huoxing_position(self.year_zhi, self.hour_zhi)
        stars.setdefault(hx_pos, []).append('火星')
        lx_pos = lingxing_position(self.year_zhi, self.hour_zhi)
        stars.setdefault(lx_pos, []).append('铃星')

        # 排序: 主星在前, 辅星在后
        for zhi in stars:
            stars[zhi].sort(key=lambda n: 0 if n in ZIWEI_OFFSETS or n in TIANFU_OFFSETS else 1)

        return stars

    def _build_palaces(self):
        """构建十二宫(逆时针: 命→兄弟→夫妻→...)"""
        palaces = {}
        zhi = self.ming_palace_zhi
        for pi in range(12):
            palaces[zhi] = {
                '宫名': PALACE_NAMES[pi],
                '地支': DI_ZHI[zhi],
                '天干': TIAN_GAN[self.palace_gans[zhi]],
                '干支': TIAN_GAN[self.palace_gans[zhi]] + DI_ZHI[zhi],
                '星曜': self.stars.get(zhi, []),
                '序号': pi,
            }
            zhi = (zhi - 1) % 12
        return palaces

    def _calc_sihua(self):
        s = SIHUA_TABLE[self.year_gan]
        return {'化禄': s[0], '化权': s[1], '化科': s[2], '化忌': s[3]}

    def _calc_grand_limits(self):
        """大限: 阳男阴女顺行, 阴男阳女逆行, 每宫局数年"""
        is_yang = GAN_YINYANG[TIAN_GAN[self.year_gan]] == 1
        is_male = (self.gender == '男')
        direction = 1 if (is_yang and is_male) or (not is_yang and not is_male) else -1

        limits = []
        zhi = self.ming_palace_zhi
        age = 1
        for i in range(12):
            palace_idx = (zhi - self.ming_palace_zhi + 12) % 12
            limits.append({
                '宫位': zhi,
                '名称': DI_ZHI[zhi],
                '宫名': PALACE_NAMES[palace_idx],
                '起始岁': age,
                '结束岁': age + self.ju - 1,
            })
            age += self.ju
            zhi = (zhi + direction) % 12
        return limits

    def to_dict(self):
        sorted_palaces = []
        for zhi in range(12):
            if zhi in self.palaces:
                sorted_palaces.append(self.palaces[zhi])

        # 月柱: 五虎遁起寅月
        month_gan_idx = (WU_HU_DUN[self.year_gan] + self.lunar_month - 1) % 10
        month_zhi_idx = (self.lunar_month + 1) % 12  # 寅=2, 正月(lm=1)→寅(2→2+1=3? 不对)

        # 修正: 正月为寅(2), 二月为卯(3), ...
        # lunar_month=1 → zhi_idx=2
        month_zhi_idx = (self.lunar_month + 1) % 12

        return {
            '输入': {
                '公历': f"{self.solar_year}-{self.solar_month:02d}-{self.solar_day:02d} "
                        f"{self.hour:02d}:{self.minute:02d}",
                '性别': self.gender,
            },
            '农历': {
                '年': self.lunar_year,
                '月': self.lunar_month,
                '日': self.lunar_day,
                '闰月': self.lunar_is_leap,
            },
            '四柱': {
                '年柱': TIAN_GAN[self.year_gan] + DI_ZHI[self.year_zhi],
                '月柱': TIAN_GAN[month_gan_idx] + DI_ZHI[month_zhi_idx],
                '日柱': TIAN_GAN[self.day_gan] + DI_ZHI[self.day_zhi],
                '时柱': TIAN_GAN[self.hour_gan] + DI_ZHI[self.hour_zhi],
            },
            '命宫': {
                '地支': DI_ZHI[self.ming_palace_zhi],
                '干支': TIAN_GAN[self.ming_ganzhi[0]] + DI_ZHI[self.ming_ganzhi[1]],
            },
            '身宫': {
                '地支': DI_ZHI[self.shen_palace_zhi],
                '宫位': PALACE_NAMES[(self.shen_palace_zhi - self.ming_palace_zhi + 12) % 12],
            },
            '五行局': self.ju,
            '四化': self.sihua,
            '大限': self.grand_limits,
            '十二宫': sorted_palaces,
        }


# ========================================================================
# 星盘文本
# ========================================================================

def _stars_abbrev(stars, max_n=4):
    if not stars:
        return "空"
    s = " ".join(stars[:max_n])
    if len(stars) > max_n:
        s += "…"
    return s

def render_chart(chart):
    d = chart.to_dict()
    lines = []
    lines.append("=" * 66)
    lines.append("  紫 微 斗 数 命 盘")
    lines.append(f"  公历: {d['输入']['公历']}")
    ly_info = f"{d['农历']['年']}年"
    if d['农历']['闰月']:
        ly_info += f"闰{d['农历']['月']}月"
    else:
        ly_info += f"{d['农历']['月']}月"
    ly_info += f"{d['农历']['日']}日"
    lines.append(f"  农历: {ly_info}")
    lines.append(f"  性别: {d['输入']['性别']}")
    lines.append(f"  四柱: {d['四柱']['年柱']} {d['四柱']['月柱']} {d['四柱']['日柱']} {d['四柱']['时柱']}")
    lines.append(f"  命宫: {d['命宫']['干支']}  身宫: {d['身宫']['地支']}({d['身宫']['宫位']})")
    lines.append(f"  五行局: {d['五行局']}局")
    lines.append(f"  四化: 禄({d['四化']['化禄']}) 权({d['四化']['化权']}) 科({d['四化']['化科']}) 忌({d['四化']['化忌']})")
    lines.append("=" * 66)

    # 星盘4列布局
    layout = [[5,6,7,8],[4,-1,-1,9],[3,2,1,0]]
    center_info = f" {d['命宫']['干支']} 局{d['五行局']} "

    for row in layout:
        r0, r1, r2, sep = "", "", "", ""
        for col_idx, zhi in enumerate(row):
            sep += "├──────────"
            if zhi == -1:
                if col_idx == 1:
                    r0 += f"│{center_info:^10}"
                else:
                    r0 += "│          "
                r1 += "│          "
                r2 += "│          "
            else:
                p = chart.palaces.get(zhi, {})
                r0 += f"│{DI_ZHI[zhi]:^10}"
                r1 += f"│{p.get('宫名',''):^10}"
                r2 += f"│{_stars_abbrev(p.get('星曜',[])):^10}"
        sep += "┤"
        lines.append(f"{r0}│")
        lines.append(f"{r1}│")
        lines.append(f"{r2}│")
        lines.append(sep)

    lines.append("─" * 66)
    lines.append("  大限:")
    for gl in d['大限']:
        lines.append(f"    {gl['名称']}({gl['宫名']}): {gl['起始岁']}~{gl['结束岁']}岁")

    lines.append("─" * 66)
    lines.append("  各宫星曜总览:")
    for zhi in range(12):
        p = chart.palaces.get(zhi, {})
        ss = p.get('星曜', [])
        if ss:
            lines.append(f"    {DI_ZHI[zhi]}({p['宫名']}): {' '.join(ss)}")
        else:
            lines.append(f"    {DI_ZHI[zhi]}({p['宫名']}): 无主星")
    lines.append("=" * 66)
    return "\n".join(lines)


# ========================================================================
# CLI
# ========================================================================

def main():
    if len(sys.argv) < 7:
        print("用法: python3 ziwei.py <year> <month> <day> <hour> <minute> <gender>")
        print("  year/month/day: 公历日期")
        print("  hour/minute:    出生时间 (24小时制)")
        print("  gender:         男/女")
        sys.exit(1)

    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    hour = int(sys.argv[4])
    minute = int(sys.argv[5])
    gender = sys.argv[6]

    gender_map = {'M':'男','m':'男','male':'男','F':'女','f':'女','female':'女'}
    if gender in gender_map:
        gender = gender_map[gender]
    if gender not in ('男','女'):
        print("gender 必须为 男/女 或 male/female")
        sys.exit(1)

    chart = ZiweiChart(year, month, day, hour, minute, gender)
    data = chart.to_dict()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print()
    print(render_chart(chart))


if __name__ == '__main__':
    main()
