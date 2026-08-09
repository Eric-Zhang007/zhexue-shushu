# Direct zhexue_core API Usage Patterns

When bazi.py output is insufficient (e.g., comparing multiple people, custom analysis),
use zhexue_core functions directly. This doc covers patterns discovered in practice.

## Core Data Structures

```python
TIAN_GAN = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']  # indices 0-9
DI_ZHI  = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']  # indices 0-11

# Index maps for easy lookup:
TG = {g: i for i, g in enumerate(TIAN_GAN)}
DZ = {z: i for i, z in enumerate(DI_ZHI)}
```

## ZHI_CANG_GAN (藏干) — Integer Keys

**WARNING**: ZHI_CANG_GAN uses integer indices (0-11), NOT Chinese character keys!
Values are lists of TIAN_GAN integer indices.

```python
ZHI_CANG_GAN = {
    0: [9],          # 子藏癸
    1: [5, 9, 7],    # 丑藏己癸辛
    2: [0, 2, 4],    # 寅藏甲丙戊
    3: [1],          # 卯藏乙
    4: [4, 1, 9],    # 辰藏戊乙癸
    5: [2, 4, 6],    # 巳藏丙戊庚
    6: [3, 5],       # 午藏丁己
    7: [5, 3, 1],    # 未藏己丁乙
    8: [6, 8, 4],    # 申藏庚壬戊
    9: [7],          # 酉藏辛
    10: [4, 7, 3],   # 戌藏戊辛丁
    11: [8, 0],      # 亥藏壬甲
}

# Usage:
cangs = ZHI_CANG_GAN[DZ['酉']]  # → [7]
gan_names = [TIAN_GAN[gi] for gi in cangs]  # → ['辛']
```

## get_shi_shen(day_gan_idx, other_gan_idx)

**Both arguments are INTEGER indices**, not Chinese characters!

```python
# WRONG: get_shi_shen('乙', '辛')
# RIGHT:
get_shi_shen(TG['乙'], TG['辛'])  # → '七杀'
get_shi_shen(TG['乙'], TG['庚'])  # → '正官'
```

## Key Functions

### 日柱
```python
day_r = day_ganzhi_from_date(2008, 5, 16)  # → (gan_index, zhi_index) tuple
ri_gan_idx, ri_zhi_idx = day_r
ri_gan, ri_zhi = TIAN_GAN[ri_gan_idx], DI_ZHI[ri_zhi_idx]
```

### 时柱
```python
hour_r = hour_gan(ri_gan_idx, hour)  # hour = 0-23, returns hour_zhi_index (int)
# 时干需要自己用五鼠遁推算
hour_z_idx = hour_r
```

### 真太阳时修正
```python
h, m = solar_time_correction(longitude, year, month, day, hour, minute)
# longitude: 东经正数 (e.g. 北京116.4, 北京116.4)
# 返回 (float_hour, float_minute)
# 修正量 = 经度差×4分/度 + EoT方程
```

## Comparison Pattern (Two People)

```python
def analyze_person(name, nian_g, nian_z, yue_g, yue_z, ri_g, ri_z, shi_g, shi_z):
    """分析并打印一个人的八字关键信息"""
    ri = TG[ri_g]
    print(f"{name}: {nian_g}{nian_z} {yue_g}{yue_z} {ri_g}{ri_z} {shi_g}{shi_z}")
    print(f"  日主: {ri_g}({TIAN_GAN[ri]['wuxing']})")
    
    # 月令格局
    yue_cangs = ZHI_CANG_GAN[DZ[yue_z]]
    yue_zhuqi = TIAN_GAN[yue_cangs[0]]
    geju = get_shi_shen(ri, TG[yue_zhuqi])
    print(f"  格局: {geju}格")
    
    # 杀/官分布
    for pos, z in [('年',nian_z),('月',yue_z),('日',ri_z),('时',shi_z)]:
        for gi in ZHI_CANG_GAN[DZ[z]]:
            ss = get_shi_shen(ri, gi)
            if ss in ['七杀','正官']:
                print(f"    {pos}藏{TIAN_GAN[gi]}={ss}")
```

## Health Analysis Pattern

For 健康/发烧 analysis from bazi:
1. Check day master (日主) strength — 身弱 more vulnerable
2. Current year's 干支 and its 十神 vs 日主
3. Current day's 流日 干支— triple fire years (丙午年+丙午日+午月) = acute health triggers
4. 地支合化 (e.g. 午未合火) that removes root support
5. 神煞: 血刃/灾煞/羊刃 appearing in 流日 = acute issue signal

Reference: 中医五行对应 — 火=热/炎症/发烧, 金=肺/呼吸系统, 水=肾/免疫力基础

## Academic/PhD Planning Pattern

1. Map academic milestones to 流年 (e.g. 2028戊申, 2029己酉 for PhD apps)
2. Check 流年地支藏干 for 印星 (水) — even hidden water is a lifeline
3. 大运走势: 身弱七杀格的关键转折在 水运(印星)到来
4. Priority: 化杀生身(水/印运) > 帮身抗杀(木/比劫年) > 食伤制杀(火年=辛苦出活)
5. Key: 食伤旺年=研究成果爆发期, 印星年=录取/贵人运
