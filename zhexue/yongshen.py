#!/usr/bin/env python3
"""
用神算法 — 移植自问真八字App（YongShenTool.java）
根据日干五行 + 四柱藏干权重 + 月令系数 → 判旺衰 → 定用神忌神
"""
import sys, json

# ========== 五行映射（与 BZTool.t() 一致）==========
GAN_WUXING = {
    '甲':'木','乙':'木','丙':'火','丁':'火','戊':'土',
    '己':'土','庚':'金','辛':'金','壬':'水','癸':'水'
}
ZHI_WUXING = {
    '子':'水','丑':'土','寅':'木','卯':'木','辰':'土',
    '巳':'火','午':'火','未':'土','申':'金','酉':'金',
    '戌':'土','亥':'水'
}
TIAN_GAN = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
DI_ZHI   = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']

def wuxing_of(gan_or_zhi):
    """BZTool.t() 等效：返回天干/地支对应的五行"""
    if gan_or_zhi in GAN_WUXING:
        return GAN_WUXING[gan_or_zhi]
    if gan_or_zhi in ZHI_WUXING:
        return ZHI_WUXING[gan_or_zhi]
    return ''

def sheng_wo(wuxing):
    """BZTool.k() 等效：返回生该五行的五行（印星）"""
    table = {'木':'水','火':'木','土':'火','金':'土','水':'金'}
    return table.get(wuxing, '')

# ========== 地支藏干及权重（与 YongShenTool.a() 一致）==========
ZHI_CANG_GAN_WEIGHT = {
    '子': {'癸': 100},
    '丑': {'己': 60, '癸': 30, '辛': 10},
    '寅': {'甲': 60, '丙': 30, '戊': 10},
    '卯': {'乙': 100},
    '辰': {'戊': 60, '乙': 30, '癸': 10},
    '巳': {'丙': 60, '戊': 30, '庚': 10},
    '午': {'丁': 70, '己': 30},
    '未': {'己': 60, '丁': 30, '乙': 10},
    '申': {'庚': 60, '壬': 30, '戊': 10},
    '酉': {'辛': 100},
    '戌': {'戊': 60, '辛': 30, '丁': 10},
    '亥': {'壬': 70, '甲': 30},
}

# ========== 月令系数（与 YongShenTool.c() 一致）==========
MONTH_COEFF = {
    '寅': {'木':1.571, '火':1.548, '土':0.924, '金':0.716, '水':0.862},
    '卯': {'木':2.000, '火':1.414, '土':0.500, '金':0.707, '水':1.000},
    '辰': {'木':1.166, '火':1.074, '土':1.421, '金':1.161, '水':0.800},
    '巳': {'木':0.862, '火':1.571, '土':1.548, '金':0.924, '水':0.716},
    '午': {'木':0.912, '火':1.700, '土':1.590, '金':0.774, '水':0.645},
    '未': {'木':0.924, '火':1.341, '土':1.674, '金':1.069, '水':0.612},
    '申': {'木':0.795, '火':0.674, '土':1.012, '金':1.641, '水':1.498},
    '酉': {'木':0.500, '火':0.707, '土':1.000, '金':2.000, '水':1.414},
    '戌': {'木':0.674, '火':1.012, '土':1.641, '金':1.498, '水':0.795},
    '亥': {'木':1.590, '火':0.774, '土':0.645, '金':0.912, '水':1.700},
    '子': {'木':1.414, '火':0.500, '土':0.707, '金':1.000, '水':2.000},
    '丑': {'木':0.898, '火':0.821, '土':1.512, '金':1.348, '水':1.041},
}

WUXING_LIST = ['木','火','土','金','水']

def calc_yongshen(pillar_ganzhi_list):
    """
    计算用神忌神

    Args:
        pillar_ganzhi_list: 8元素列表 [年干, 年支, 月干, 月支, 日干, 日支, 时干, 时支]
                           例如 ['甲','子','丙','寅','戊','辰','庚','申']

    Returns:
        dict: {self_ratios, other_ratios, counts, self_strength, other_strength,
               yongshen, jishen, judgement}
    """
    if len(pillar_ganzhi_list) != 8:
        raise ValueError(f"需要8个元素(四柱天干地支)，得到{len(pillar_ganzhi_list)}个")

    # Step 1: 计算原始五行权重 (hashMap3) 和 出现次数 (hashMap4)
    raw_weight = {wx: 0 for wx in WUXING_LIST}   # hashMap3
    count = {wx: 0 for wx in WUXING_LIST}          # hashMap4

    for i in range(8):
        gz = pillar_ganzhi_list[i]
        wx = wuxing_of(gz)
        if i % 2 == 0:  # 天干 (even index)
            raw_weight[wx] += 100
            count[wx] += 1
        else:            # 地支 (odd index) — 查藏干
            cang_dict = ZHI_CANG_GAN_WEIGHT.get(gz, {})
            for gan, weight in cang_dict.items():
                cang_wx = wuxing_of(gan)
                raw_weight[cang_wx] += weight
                count[cang_wx] += 1

    # Step 2: 月令系数调整
    month_zhi = pillar_ganzhi_list[3]  # 月支
    coeffs = MONTH_COEFF.get(month_zhi, {wx:1.0 for wx in WUXING_LIST})

    adjusted = {}
    for wx in WUXING_LIST:
        adjusted[wx] = raw_weight[wx] * coeffs.get(wx, 1.0)

    # Step 3: 计算平均值
    total = sum(adjusted.values())
    avg = total / 5.0

    # Step 4: 分组 — 自党(日干五行+生日干=比劫印) vs 异党(食伤财官)
    ri_gan_wx = wuxing_of(pillar_ganzhi_list[4])  # 日干五行
    sheng_wo_wx = sheng_wo(ri_gan_wx)               # 生日干的五行（印）

    self_ratios = {}   # 自党 (hashMap)
    other_ratios = {}  # 异党 (hashMap2)
    self_total = 0.0
    other_total = 0.0
    self_weakest_val = 99999.0
    other_weakest_val = 99999.0
    self_weakest_wx = ''
    other_weakest_wx = ''

    for wx in WUXING_LIST:
        ratio = adjusted[wx] / avg if avg > 0 else 0
        if wx == ri_gan_wx or wx == sheng_wo_wx:
            # 自党：日干五行 + 生我(印)
            self_ratios[wx] = round(ratio, 4)
            self_total += adjusted[wx]
            if adjusted[wx] < self_weakest_val:
                self_weakest_val = adjusted[wx]
                self_weakest_wx = wx
        else:
            # 异党：其他
            other_ratios[wx] = round(ratio, 4)
            other_total += adjusted[wx]
            if adjusted[wx] < other_weakest_val:
                other_weakest_val = adjusted[wx]
                other_weakest_wx = wx

    self_strength = round(self_total / avg, 4) if avg > 0 else 0
    other_strength = round(other_total / avg, 4) if avg > 0 else 0

    # Step 5: 旺衰判断与用神忌神
    # 身旺 = 自党强度 > 异党强度
    is_strong = self_strength > other_strength

    if is_strong:
        # 身旺 — 用神取异党中最弱者（最缺的异党五行）
        yongshen = other_weakest_wx
        # 忌神取自党中最弱者（最缺的自党五行，补之反旺？）
        # 传统：身旺忌生扶，故自党中越弱越需抑
        jishen = self_weakest_wx
        judgement = '身旺'
    else:
        # 身弱 — 用神取自党中最弱者（最缺的自党五行，补身）
        yongshen = self_weakest_wx
        # 忌神取异党中最强者
        other_strongest_val = 0
        other_strongest_wx = ''
        for wx, ratio in other_ratios.items():
            if adjusted.get(wx, 0) > other_strongest_val:
                other_strongest_val = adjusted.get(wx, 0)
                other_strongest_wx = wx
        jishen = other_strongest_wx
        judgement = '身弱'

    return {
        'ri_gan_wuxing': ri_gan_wx,
        'month_zhi': month_zhi,
        'raw_weight': raw_weight,
        'adjusted_weight': {k: round(v, 2) for k, v in adjusted.items()},
        'self_ratios': self_ratios,
        'other_ratios': other_ratios,
        'counts': count,
        'self_strength': self_strength,
        'other_strength': other_strength,
        'self_weakest': self_weakest_wx,
        'other_weakest': other_weakest_wx,
        'yongshen': yongshen,
        'jishen': jishen,
        'judgement': judgement,
    }


# ========== CLI 入口 ==========
if __name__ == '__main__':
    if len(sys.argv) < 6:
        print("用法: yongshen.py <year> <month> <day> <hour> <male/female> [minute]")
        print("示例: yongshen.py 1990 5 15 12 male")
        print("      yongshen.py 2000 1 1 8 female 30")
        print("")
        print("旧用法(直接给干支): yongshen.py --raw <年干> <年支> <月干> <月支> <日干> <日支> <时干> <时支>")
        sys.exit(1)

    if sys.argv[1] == '--raw':
        # 旧格式兼容: 直接给8个干支
        pillars = sys.argv[2:10]
        if len(pillars) != 8:
            print("错误: --raw 模式需要8个参数(年干 年支 月干 月支 日干 日支 时干 时支)")
            sys.exit(1)
        result = calc_yongshen(pillars)
        result['bazi'] = ''.join(pillars[:2]) + ' ' + ''.join(pillars[2:4]) + ' ' + ''.join(pillars[4:6]) + ' ' + ''.join(pillars[6:8])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 新格式: 年 月 日 时 分 性别 (与 bazi.py 一致)
    args = sys.argv[1:]
    longitude = None
    clean = []
    skip = False
    for i, a in enumerate(args):
        if skip:
            skip = False
            continue
        if a == '--longitude':
            longitude = float(args[i+1]) if i+1 < len(args) else None
            skip = True
            continue
        clean.append(a)
    
    year, month, day = int(clean[0]), int(clean[1]), int(clean[2])
    hour = int(clean[3])
    minute = int(clean[4])
    gender = clean[5]

    # 真太阳时修正
    if longitude is not None:
        from zhexue_core import solar_time_correction
        corr_h, corr_m = solar_time_correction(longitude, year, month, day, hour, minute)
        hour, minute = int(corr_h), int(corr_m)

    gender_map = {'male':'男','female':'女','男':'男','女':'女'}
    gender_cn = gender_map.get(gender, '男')
    gender_bazi = 'male' if gender in ('male','男') else 'female'

    # 调用 bazi.py 的 pillar_info 计算八字
    sys.path.insert(0, '/home/zjc/.hermes/skills/zhexue-methods/scripts')
    from bazi import pillar_info
    bazi_result = pillar_info(year, month, day, hour, minute, gender_bazi)

    # 提取四柱天干地支
    b = bazi_result['bazi']
    pillars = [
        b['nian']['gan'], b['nian']['zhi'],  # 年柱
        b['yue']['gan'], b['yue']['zhi'],    # 月柱
        b['ri']['gan'], b['ri']['zhi'],      # 日柱
        b['shi']['gan'], b['shi']['zhi'],    # 时柱
    ]

    result = calc_yongshen(pillars)
    result['bazi'] = f"{b['nian']['gan']}{b['nian']['zhi']} {b['yue']['gan']}{b['yue']['zhi']} {b['ri']['gan']}{b['ri']['zhi']} {b['shi']['gan']}{b['shi']['zhi']}"
    result['input'] = {'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute, 'gender': gender_cn}

    print(json.dumps(result, ensure_ascii=False, indent=2))
