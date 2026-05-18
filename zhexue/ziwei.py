#!/usr/bin/env python3
"""紫微斗数 — 文墨天机格式命盘输出

CLI: python3 ziwei.py <year> <month> <day> <hour> <minute> <gender>
输出: 文墨天机风格命盘文本

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
    MIAO_WANG_LI_XIAN, JU_NAMES,
    calc_ming_zhu, calc_shen_zhu, calc_dou_jun,
    star_hongluan, star_tianxi, star_tianyao, star_tianxing, star_yinsha,
    star_tianshang, star_tianshi, star_longde, star_tiande,
    star_jiesha, star_zhaisha,
    star_santai, star_bazuo, star_tianguan, star_tianfu,
    star_tiancai, star_tianshou, star_tianku, star_tianxu,
    star_tianchu, star_taifu, star_longchi, star_fengge,
    star_dijie, star_dikong,
    star_tianwu, star_tianyue, star_jieshen,
    star_xunkong, star_jiekong,
    star_posui, star_huagai, star_xianchi, star_guchen, star_guanxiu,
    star_feilian, star_enguang,
    star_fenggao,
    get_suiqian, get_jiangqian,
    ziwei_shier_changsheng,
    get_taisui_shalu,
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

# 星分类
MAIN_STARS = {'紫微','天机','太阳','武曲','天同','廉贞',
              '天府','太阴','贪狼','巨门','天相','天梁','七杀','破军'}
AUX_STARS = {'左辅','右弼','文昌','文曲','天魁','天钺',
             '禄存','擎羊','陀罗','火星','铃星','天马'}


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


def _get_star_brightness(star_name, zhi_idx):
    """获取星曜庙旺利陷等级, 返回中文名"""
    if star_name not in MIAO_WANG_LI_XIAN:
        return '-'
    pos_data = MIAO_WANG_LI_XIAN[star_name]
    if zhi_idx >= len(pos_data):
        return '-'
    val = pos_data[zhi_idx]
    if val == '-' or val is None:
        return '-'
    return val


# ========================================================================
# 命盘
# ========================================================================

class ZiweiChart:
    """紫微斗数命盘 — 文墨天机格式"""

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

        # 7. 布星 (主星 + 辅星 + 小星)
        self.stars = self._place_all_stars()

        # 8. 命主/身主/斗君
        self.ming_zhu = calc_ming_zhu(self.year_zhi)
        self.shen_zhu = calc_shen_zhu(self.year_zhi)
        self.dou_jun = calc_dou_jun(self.year_gan)

        # 9. 四化
        self.sihua = self._calc_sihua()

        # 10. 自化
        self.zihua = self._calc_zihua()

        # 11. 十二宫
        self.palaces = self._build_palaces()

        # 12. 大限
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
        """安放全部星曜 — 主星 + 辅星 + 小星"""
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

        # ---- 小星 ----
        minor_stars = self._calc_all_minor_stars()
        for zhi, names in minor_stars.items():
            stars.setdefault(zhi, []).extend(names)

        # 排序: 主星在前, 辅星在中, 小星在后
        for zhi in stars:
            stars[zhi].sort(key=_star_sort_key)

        return stars

    def _calc_all_minor_stars(self):
        """计算所有小星, 返回 {zhi: [star_names]}"""
        minor = {}
        
        # 月支索引 (正月=寅=2)
        month_zhi = (self.lunar_month + 1) % 12
        
        checks = [
            ('红鸾', star_hongluan(self.year_zhi)),
            ('天喜', star_tianxi(self.year_zhi)),
            ('天姚', star_tianyao(self.year_zhi)),
            ('天刑', star_tianxing(self.year_zhi)),
            ('阴煞', star_yinsha(self.year_zhi)),
            ('天伤', star_tianshang(self.ming_palace_zhi)),
            ('天使', star_tianshi(self.ming_palace_zhi)),
            ('龙德', star_longde(self.year_zhi)),
            ('天德', star_tiande(self.year_zhi)),
            ('劫煞', star_jiesha(self.year_zhi)),
            ('灾煞', star_zhaisha(self.year_zhi)),
            ('三台', star_santai(month_zhi)),
            ('八座', star_bazuo(month_zhi)),
            ('天官', star_tianguan(month_zhi)),
            ('天福', star_tianfu(month_zhi)),
            ('天巫', star_tianwu(month_zhi)),
            ('天月', star_tianyue(month_zhi)),
            ('解神', star_jieshen(month_zhi)),
            ('天厨', star_tianchu(self.hour_zhi)),
            ('台辅', star_taifu(self.hour_zhi)),
            ('龙池', star_longchi(self.hour_zhi)),
            ('凤阁', star_fengge(self.hour_zhi)),
            ('地劫', star_dijie(self.hour_zhi)),
            ('地空', star_dikong(self.hour_zhi)),
            ('封诰', star_fenggao(month_zhi)),
            ('天哭', star_tianku(month_zhi)),
            ('天虚', star_tianxu(month_zhi)),
            ('破碎', star_posui(self.year_zhi)),
            ('蜚廉', star_feilian(self.year_zhi)),
            ('天才', star_tiancai(self.ming_palace_zhi, self.year_zhi)),
            ('天寿', star_tianshou(self.shen_palace_zhi, self.year_zhi)),
            ('恩光', star_enguang(self.year_zhi)),
            ('华盖', star_huagai(self.year_zhi)),
            ('咸池', star_xianchi(self.year_zhi)),
            ('孤辰', star_guchen(self.year_zhi)),
            ('寡宿', star_guanxiu(self.year_zhi)),
        ]
        
        # 旬空/截空 返回 tuple
        xunk = star_xunkong(self.year_gan)
        if isinstance(xunk, tuple):
            for p in xunk:
                if p is not None:
                    minor.setdefault(p, []).append('旬空')
        jiek = star_jiekong(self.year_gan)
        if isinstance(jiek, tuple):
            for p in jiek:
                if p is not None:
                    minor.setdefault(p, []).append('截空')
        
        for name, pos in checks:
            if pos is None:
                continue
            if isinstance(pos, tuple):
                for p in pos:
                    if p is not None:
                        minor.setdefault(p, []).append(name)
            elif pos == pos:  # always True, but catches the case
                minor.setdefault(pos, []).append(name)
        
        return minor

    def _build_palaces(self):
        """构建十二宫(逆时针: 命→兄弟→夫妻→...)"""
        palaces = {}
        zhi = self.ming_palace_zhi
        for pi in range(12):
            # 神煞
            sui_qian = get_suiqian(self.year_zhi, zhi)
            jiang_qian = get_jiangqian(self.year_zhi, zhi)
            chang_sheng = ziwei_shier_changsheng(self.ming_palace_zhi, zhi)
            is_male = (self.gender == '男')
            gan_yang = GAN_YINYANG.get(TIAN_GAN[self.year_gan], 1)
            tai_sui = get_taisui_shalu(self.year_gan, zhi, is_male, gan_yang)

            # 小限
            xiao_xian_base = 1 + ((self.ming_palace_zhi - zhi) % 12)
            xiao_xian = [xiao_xian_base + 12 * n for n in range(6)]

            # 流年
            liu_nian_base = 1 + ((zhi - self.ming_palace_zhi) % 12)
            liu_nian = [liu_nian_base + 12 * n for n in range(6)]

            palaces[zhi] = {
                '宫名': PALACE_NAMES[pi],
                '地支': DI_ZHI[zhi],
                '天干': TIAN_GAN[self.palace_gans[zhi]],
                '干支': TIAN_GAN[self.palace_gans[zhi]] + DI_ZHI[zhi],
                '星曜': self.stars.get(zhi, []),
                '序号': pi,
                '神煞': {
                    '岁前星': sui_qian,
                    '将前星': jiang_qian,
                    '十二长生': chang_sheng,
                    '太岁煞禄': tai_sui,
                },
                '小限': xiao_xian,
                '流年': liu_nian,
            }
            zhi = (zhi - 1) % 12
        return palaces

    def _calc_sihua(self):
        s = SIHUA_TABLE[self.year_gan]
        return {'化禄': s[0], '化权': s[1], '化科': s[2], '化忌': s[3]}

    def _calc_zihua(self):
        """自化: 宫干飞四化落本宫(↓离心)或对宫(↑向心)"""
        zihua = {}  # {zhi_idx: {star_name: [tags]}}

        # First, mark 生年四化
        hua_labels = {'化禄': '生年禄', '化权': '生年权', '化科': '生年科', '化忌': '生年忌'}
        for hua_type, star in self.sihua.items():
            for zhi, star_list in self.stars.items():
                if star in star_list:
                    if zhi not in zihua:
                        zihua[zhi] = {}
                    if star not in zihua[zhi]:
                        zihua[zhi][star] = []
                    label = hua_labels[hua_type]
                    if label not in zihua[zhi][star]:
                        zihua[zhi][star].append(label)

        # Then, 宫干自化
        hua_types_short = ['禄', '权', '科', '忌']
        for zhi in range(12):
            gan = self.palace_gans[zhi]
            s = SIHUA_TABLE[gan]
            opposite_zhi = (zhi + 6) % 12

            for hua_type, star in zip(hua_types_short, s):
                # 离心(↓): star in this palace → self-transformation outwards
                if star in self.stars.get(zhi, []):
                    if zhi not in zihua:
                        zihua[zhi] = {}
                    if star not in zihua[zhi]:
                        zihua[zhi][star] = []
                    # Don't add if 生年 same type already exists
                    existing_tags = zihua[zhi][star]
                    has_shengnian = any('生年' in t for t in existing_tags)
                    if f'↓{hua_type}' not in existing_tags:
                        zihua[zhi][star].append(f'↓{hua_type}')
                # 向心(↑): star in opposite palace → flows into this palace
                elif star in self.stars.get(opposite_zhi, []):
                    if zhi not in zihua:
                        zihua[zhi] = {}
                    if star not in zihua[zhi]:
                        zihua[zhi][star] = []
                    if f'↑{hua_type}' not in zihua[zhi][star]:
                        zihua[zhi][star].append(f'↑{hua_type}')

        return zihua

    def _calc_grand_limits(self):
        """大限: 阳男阴女顺行, 阴男阳女逆行, 每宫10年, 起始岁=五行局数"""
        is_yang = GAN_YINYANG[TIAN_GAN[self.year_gan]] == 1
        is_male = (self.gender == '男')
        direction = 1 if (is_yang and is_male) or (not is_yang and not is_male) else -1

        limits = []
        zhi = self.ming_palace_zhi
        age = self.ju  # 起始岁 = 五行局数
        for i in range(12):
            palace_idx = (zhi - self.ming_palace_zhi + 12) % 12
            limits.append({
                '宫位': zhi,
                '名称': DI_ZHI[zhi],
                '宫名': PALACE_NAMES[palace_idx],
                '起始岁': age,
                '结束岁': age + 9,  # 每个大限10年
            })
            age += 10
            zhi = (zhi + direction) % 12
        return limits

    def _get_star_tags(self, star_name, zhi):
        """获取星曜的标签: [庙旺利陷] + [四化] + [自化]"""
        parts = []
        # 亮度
        brightness = _get_star_brightness(star_name, zhi)
        parts.append(brightness)

        # 四化/自化标签
        if zhi in self.zihua and star_name in self.zihua[zhi]:
            for tag in self.zihua[zhi][star_name]:
                parts.append(tag)

        return parts

    def _format_star_with_tags(self, star_name, zhi):
        """格式化星曜: 星名[亮度][四化标签]..."""
        tags = self._get_star_tags(star_name, zhi)
        if tags:
            return star_name + ''.join(f'[{t}]' for t in tags)
        return star_name

    def _get_palace_display_data(self, zhi):
        """获取单个宫的显示数据"""
        p = self.palaces.get(zhi, {})
        stars = p.get('星曜', [])
        
        main_stars = [s for s in stars if s in MAIN_STARS]
        aux_stars = [s for s in stars if s in AUX_STARS]
        minor_stars = [s for s in stars if s not in MAIN_STARS and s not in AUX_STARS]

        main_strs = [self._format_star_with_tags(s, zhi) for s in main_stars]
        aux_strs = [self._format_star_with_tags(s, zhi) for s in aux_stars]
        minor_strs = [self._format_star_with_tags(s, zhi) for s in minor_stars]

        return {
            '宫名': p.get('宫名', ''),
            '天干': p.get('天干', ''),
            '地支': p.get('地支', ''),
            '主星': ', '.join(main_strs) if main_strs else '',
            '辅星': ', '.join(aux_strs) if aux_strs else '',
            '小星': ', '.join(minor_strs) if minor_strs else '',
            '神煞': p.get('神煞', {}),
            '大限': self._get_grand_limit_for_palace(zhi),
            '小限': p.get('小限', []),
            '流年': p.get('流年', []),
            '序号': p.get('序号', 0),
        }

    def _get_grand_limit_for_palace(self, zhi):
        """获取某宫的大限信息"""
        for gl in self.grand_limits:
            if gl['宫位'] == zhi:
                return f"{gl['起始岁']}~{gl['结束岁']}虚岁"
        return ''

    def to_dict(self):
        """保留旧接口的字典输出"""
        sorted_palaces = []
        for zhi in range(12):
            if zhi in self.palaces:
                sorted_palaces.append(self.palaces[zhi])

        month_gan_idx = (WU_HU_DUN[self.year_gan] + self.lunar_month - 1) % 10
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
                '宫位': PALACE_NAMES[(self.ming_palace_zhi - self.shen_palace_zhi + 12) % 12],
            },
            '五行局': JU_NAMES[self.ju],
            '四化': self.sihua,
            '大限': self.grand_limits,
            '十二宫': sorted_palaces,
        }


# ========================================================================
# 辅助函数
# ========================================================================

def _star_sort_key(name):
    """排序键: 主星=0, 辅星=1, 小星=2"""
    if name in MAIN_STARS:
        return 0
    if name in AUX_STARS:
        return 1
    return 2


def _format_age_list(ages):
    """格式化岁数列表: 11,23,35,47,59虚岁"""
    return ','.join(str(a) for a in ages) + '虚岁'


def _make_tree_line(indent, label, value):
    """生成树形行: ├XXX : YYY"""
    prefix = '│' * indent if indent > 0 else ''
    branch = '├' if indent >= 0 else ''
    if indent == 0:
        return f'{prefix}{branch}{label}'
    return f'{prefix}{branch}{label} : {value}'


# ========================================================================
# 文墨天机格式渲染
# ========================================================================

def render_chart(chart):
    """渲染文墨天机风格命盘"""
    lines = []

    # ===== 基本信息 =====
    lines.append('├基本信息')

    # 性别
    lines.append(f'│ ├性别 : {chart.gender}')

    # 钟表时间
    lines.append(f'│ ├钟表时间 : {chart.solar_year}-{chart.solar_month:02d}-{chart.solar_day:02d} {chart.hour:02d}:{chart.minute:02d}')

    # 农历时间
    lunar_month_names = ['正','二','三','四','五','六','七','八','九','十','冬','腊']
    lunar_day_names = ['初一','初二','初三','初四','初五','初六','初七','初八','初九','初十',
                       '十一','十二','十三','十四','十五','十六','十七','十八','十九','二十',
                       '廿一','廿二','廿三','廿四','廿五','廿六','廿七','廿八','廿九','三十']
    lm_name = lunar_month_names[chart.lunar_month - 1]
    ld_name = lunar_day_names[chart.lunar_day - 1] if chart.lunar_day <= 30 else f'{chart.lunar_day}日'
    leap_str = '闰' if chart.lunar_is_leap else ''
    year_ganzhi = TIAN_GAN[chart.year_gan] + DI_ZHI[chart.year_zhi]
    
    # 时辰名
    hour_names = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
    hour_name = hour_names[chart.hour_zhi]
    
    lines.append(f'│ ├农历时间 : {year_ganzhi}年{leap_str}{lm_name}月{ld_name}{hour_name}时')

    # 节气四柱
    month_gan_idx = (WU_HU_DUN[chart.year_gan] + chart.lunar_month - 1) % 10
    month_zhi_idx = (chart.lunar_month + 1) % 12
    lines.append(f'│ ├节气四柱 : {TIAN_GAN[chart.year_gan]}{DI_ZHI[chart.year_zhi]} '
                 f'{TIAN_GAN[month_gan_idx]}{DI_ZHI[month_zhi_idx]} '
                 f'{TIAN_GAN[chart.day_gan]}{DI_ZHI[chart.day_zhi]} '
                 f'{TIAN_GAN[chart.hour_gan]}{DI_ZHI[chart.hour_zhi]}')

    # 五行局
    ju_name = JU_NAMES.get(chart.ju, f'{chart.ju}局')
    lines.append(f'│ ├五行局数 : {ju_name}')

    # 身主/命主/斗君/身宫
    shen_gong_name = PALACE_NAMES[(chart.ming_palace_zhi - chart.shen_palace_zhi + 12) % 12]
    dou_jun_zhi = DI_ZHI[chart.dou_jun]
    shen_zhi = DI_ZHI[chart.shen_palace_zhi]
    lines.append(f'│ └身主:{chart.shen_zhu}; 命主:{chart.ming_zhu}; 子年斗君:{dou_jun_zhi}; 身宫:{shen_zhi}')

    lines.append('│')

    # ===== 命盘十二宫 =====
    lines.append('├命盘十二宫')

    # 构建各宫显示数据 (按逆时针顺序)
    palace_displays = []
    zhi = chart.ming_palace_zhi
    for pi in range(12):
        pd = chart._get_palace_display_data(zhi)
        palace_displays.append(pd)
        zhi = (zhi - 1) % 12

    for idx, pd in enumerate(palace_displays):
        is_last_palace = (idx == len(palace_displays) - 1)
        palace_branch = '└' if is_last_palace else '├'

        # 宫头: ├命宫[辛亥] or └命宫[辛亥]
        lines.append(f'{palace_branch} {pd["宫名"]}[{pd["天干"]}{pd["地支"]}]')

        # 构建该宫的所有子行
        sub_lines = []
        has_aux = bool(pd['辅星'])
        has_minor = bool(pd['小星'])

        # 主星
        if pd['主星']:
            sub_lines.append(('主星', f'主星 : {pd["主星"]}'))
        else:
            sub_lines.append(('主星', f'主星 : 无'))

        # 辅星
        if has_aux:
            sub_lines.append(('辅星', f'辅星 : {pd["辅星"]}'))

        # 小星
        if has_minor:
            sub_lines.append(('小星', f'小星 : {pd["小星"]}'))

        # 神煞 (group header)
        sub_lines.append(('神煞_begin', '神煞'))

        shen = pd['神煞']
        sub_lines.append(('神煞_item', f'├岁前星 : {shen.get("岁前星", "")}'))
        sub_lines.append(('神煞_item', f'├将前星 : {shen.get("将前星", "")}'))
        sub_lines.append(('神煞_item', f'├十二长生 : {shen.get("十二长生", "")}'))
        sub_lines.append(('神煞_item', f'└太岁煞禄 : {shen.get("太岁煞禄", "")}'))

        sub_lines.append(('大限', f'大限 : {pd["大限"]}'))
        sub_lines.append(('小限', f'小限 : {_format_age_list(pd["小限"])}'))
        sub_lines.append(('流年', f'流年 : {_format_age_list(pd["流年"])}'))
        sub_lines.append(('限流叠宫', f'限流叠宫 : 无'))

        # 渲染子行
        for i, (key, text) in enumerate(sub_lines):
            is_last_sub = (i == len(sub_lines) - 1)
            if key == '神煞_begin':
                lines.append(f'│ ├{text}')
            elif key == '神煞_item':
                # 神煞项目: 用│ │前缀
                lines.append(f'│ │ {text}')
            else:
                sub_branch = '└' if is_last_sub else '├'
                lines.append(f'│ {sub_branch}{text}')

    return '\n'.join(lines)


# ========================================================================
# CLI
# ========================================================================

def main():
    if len(sys.argv) < 7:
        print("用法: python3 ziwei.py <year> <month> <day> <hour> <minute> <gender> [--longitude 经度]")
        print("  year/month/day: 公历日期")
        print("  hour/minute:    出生时间 (24小时制)")
        print("  gender:         男/女")
        print("  --longitude:    地理经度(东经正数)，用于真太阳时修正")
        sys.exit(1)

    year = int(sys.argv[1])
    month = int(sys.argv[2])
    day = int(sys.argv[3])
    hour = int(sys.argv[4])
    minute = int(sys.argv[5])
    gender = sys.argv[6]
    longitude = None

    # 解析可選参数
    for i, a in enumerate(sys.argv[7:], start=7):
        if a == '--longitude' and i + 1 < len(sys.argv):
            longitude = float(sys.argv[i + 1])

    # 真太阳时修正
    if longitude is not None:
        from zhexue_core import solar_time_correction
        corr_h, corr_m = solar_time_correction(longitude, year, month, day, hour, minute)
        print(f"# 真太阳时修正: {hour:02d}:{minute:02d} → {int(corr_h):02d}:{int(corr_m):02d} (经度{longitude})", file=sys.stderr)
        hour, minute = int(corr_h), int(corr_m)

    gender_map = {'M':'男','m':'男','male':'男','F':'女','f':'女','female':'女'}
    if gender in gender_map:
        gender = gender_map[gender]
    if gender not in ('男','女'):
        print("gender 必须为 男/女 或 male/female")
        sys.exit(1)

    chart = ZiweiChart(year, month, day, hour, minute, gender)
    # Also output JSON for machine consumption
    data = chart.to_dict()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print()
    print(render_chart(chart))


if __name__ == '__main__':
    main()
