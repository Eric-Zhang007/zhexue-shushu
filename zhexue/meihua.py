#!/usr/bin/env python3
"""
梅花易数起卦工具
Usage:
    python3 meihua.py <a> <b> <c>       # 数字起卦
    python3 meihua.py --time y m d h    # 时间起卦

数字起卦: a%8上卦, b%8下卦, c%6动爻 (余0=8坤, 余0=6上爻)
时间起卦: (y+m+d)%8上卦, (y+m+d+h)%8下卦, (y+m+d+h)%6动爻
"""

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from zhexue_core import (
    BA_GUA, BA_GUA_WX, XIAN_TIAN, SHU_TO_GUA, LIU_SHI_SI_GUA,
    get_gua_name, TIAN_GAN, DI_ZHI
)

# ========== 八卦爻画（从下到上：初→二→三） ==========
BA_GUA_YAO = {
    '乾': [1, 1, 1],
    '兑': [0, 1, 1],
    '离': [1, 0, 1],
    '震': [0, 0, 1],
    '巽': [1, 1, 0],
    '坎': [0, 1, 0],
    '艮': [1, 0, 0],
    '坤': [0, 0, 0],
}

YAO_TO_GUA = {tuple(v): k for k, v in BA_GUA_YAO.items()}

BA_GUA_CN = {
    '乾': '☰', '兑': '☱', '离': '☲', '震': '☳',
    '巽': '☴', '坎': '☵', '艮': '☶', '坤': '☷',
}

# 爻位名称（从下到上）
YAO_NAMES = ['初', '二', '三', '四', '五', '上']
YAO_SYMBOLS = {0: '⚋', 1: '⚊'}

# 五行生克关系
WUXING_SHENG = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
WUXING_KE = {'木': '土', '土': '水', '水': '火', '火': '金', '金': '木'}


# ========== 辅助函数 ==========

def num_to_gua(n):
    """数字 1-8 转八卦，余0→8坤"""
    n = int(n) % 8
    if n == 0:
        n = 8
    return SHU_TO_GUA[n]


def num_to_yao(n):
    """数字 0-5 转动爻位置，余0→6上爻"""
    n = int(n) % 6
    if n == 0:
        return 6  # 上爻
    return n


def get_6_yao(lower_gua, upper_gua):
    """将上下卦合并为6爻（从下到上）"""
    return BA_GUA_YAO[lower_gua] + BA_GUA_YAO[upper_gua]


def yao_6_to_gua(yao6):
    """6爻拆分为上下卦"""
    lower = YAO_TO_GUA.get(tuple(yao6[0:3]))
    upper = YAO_TO_GUA.get(tuple(yao6[3:6]))
    return lower, upper


def get_hu_gua(lower_gua, upper_gua):
    """计算互卦：二三四爻为下互，三四五爻为上互"""
    yao6 = get_6_yao(lower_gua, upper_gua)
    # 下互：二爻(1)、三爻(2)、四爻(3)
    xia_hu = YAO_TO_GUA.get(tuple(yao6[1:4]))
    # 上互：三爻(2)、四爻(3)、五爻(4)
    shang_hu = YAO_TO_GUA.get(tuple(yao6[2:5]))
    return xia_hu, shang_hu


def get_bian_gua(lower_gua, upper_gua, dong_yao):
    """计算变卦：翻转动爻所在的爻"""
    yao6 = get_6_yao(lower_gua, upper_gua)
    idx = dong_yao - 1  # 动爻位置（0-indexed）
    yao6[idx] = 1 - yao6[idx]  # 翻转（阳变阴，阴变阳）
    return yao_6_to_gua(yao6)


def get_ti_yong(lower_gua, upper_gua, dong_yao):
    """确定体卦和用卦
    动爻1-3 → 用在下卦, 体在上卦
    动爻4-6 → 用在上卦, 体在下卦
    """
    if 1 <= dong_yao <= 3:
        yong_gua = lower_gua
        ti_gua = upper_gua
    else:
        yong_gua = upper_gua
        ti_gua = lower_gua
    return ti_gua, yong_gua


def wuxing_rel(a_wx, b_wx):
    """五行关系"""
    if a_wx == b_wx:
        return 'tong'
    if WUXING_SHENG.get(a_wx) == b_wx:
        return 'wo_sheng'
    if WUXING_SHENG.get(b_wx) == a_wx:
        return 'sheng_wo'
    if WUXING_KE.get(a_wx) == b_wx:
        return 'wo_ke'
    if WUXING_KE.get(b_wx) == a_wx:
        return 'ke_wo'
    return 'unknown'


def get_jixiong(ti_wx, yong_wx):
    """根据体用生克判断吉凶"""
    rel = wuxing_rel(ti_wx, yong_wx)
    if rel == 'wo_ke':
        return '大吉', '体克用'
    if rel == 'sheng_wo':
        return '吉', '用生体'
    if rel == 'tong':
        return '小吉', '比和'
    if rel == 'wo_sheng':
        return '凶', '体生用'
    if rel == 'ke_wo':
        return '大凶', '用克体'
    return '未知', '未知'


def format_yao_line(yao, name):
    """格式化单行爻"""
    sym = YAO_SYMBOLS[yao]
    label = '阳' if yao == 1 else '阴'
    return f"    {sym} {name}爻（{label}）"


def print_hexagram(title, lower_gua, upper_gua, highlight_yao=None):
    """打印一个六爻卦的详细信息"""
    gua_name = get_gua_name(lower_gua, upper_gua)
    yao6 = get_6_yao(lower_gua, upper_gua)

    print(f"\n{'=' * 40}")
    print(f"【{title}】{gua_name}")
    print(f"  {BA_GUA_CN[upper_gua]} 上卦：{upper_gua}（{BA_GUA_WX[upper_gua]}）")
    print(f"  {BA_GUA_CN[lower_gua]} 下卦：{lower_gua}（{BA_GUA_WX[lower_gua]}）")
    print()

    # 从最上面开始打印
    for i in range(5, -1, -1):
        yao = yao6[i]
        name = YAO_NAMES[i]
        marker = ' ← 动爻' if highlight_yao and (i + 1) == highlight_yao else ''
        sym = YAO_SYMBOLS[yao]
        label = '阳' if yao == 1 else '阴'
        print(f"    {sym} {name}爻（{label}）{marker}")

    return gua_name


def print_gua_symbol_bar(lower_gua, upper_gua, label):
    """打印紧凑的卦符条"""
    yao6 = get_6_yao(lower_gua, upper_gua)
    syms = ''.join(YAO_SYMBOLS[y] for y in yao6)
    print(f"  {syms}  {get_gua_name(lower_gua, upper_gua)}（{lower_gua}{BA_GUA_CN[lower_gua]}下·{upper_gua}{BA_GUA_CN[upper_gua]}上）— {label}")


def meihua_shuqifa(a, b, c):
    """数字起卦"""
    shang_gua = num_to_gua(a)
    xia_gua = num_to_gua(b)
    dong_yao = num_to_yao(c)

    print(f"\n{'★' * 20}")
    print(f"  梅 花 易 数 — 数 字 起 卦")
    print(f"{'★' * 20}")
    print(f"\n输入数字：a={a}, b={b}, c={c}")
    print(f"  上卦 = {a} % 8 = {a % 8} → {shang_gua}")
    print(f"  下卦 = {b} % 8 = {b % 8} → {xia_gua}")
    print(f"  动爻 = {c} % 6 = {c % 6} → 第{dong_yao}爻")

    compute_all(xia_gua, shang_gua, dong_yao)


def meihua_timefa(year, month, day, hour):
    """时间起卦"""
    # 计算上卦：(年 + 月 + 日) % 8
    shang_sum = year + month + day
    shang_gua = num_to_gua(shang_sum)

    # 计算下卦：(年 + 月 + 日 + 时) % 8
    xia_sum = year + month + day + hour
    xia_gua = num_to_gua(xia_sum)

    # 计算动爻：(年 + 月 + 日 + 时) % 6
    dong_yao = num_to_yao(xia_sum)

    print(f"\n{'★' * 20}")
    print(f"  梅 花 易 数 — 时 间 起 卦")
    print(f"{'★' * 20}")
    print(f"\n时间：{year}年 {month}月 {day}日 {hour}时")
    print(f"  上卦 = ({year}+{month}+{day}) % 8 = {shang_sum} % 8 = {shang_sum % 8} → {shang_gua}")
    print(f"  下卦 = ({year}+{month}+{day}+{hour}) % 8 = {xia_sum} % 8 = {xia_sum % 8} → {xia_gua}")
    print(f"  动爻 = ({year}+{month}+{day}+{hour}) % 6 = {xia_sum} % 6 = {xia_sum % 6} → 第{dong_yao}爻")

    compute_all(xia_gua, shang_gua, dong_yao)


def compute_all(xia_gua, shang_gua, dong_yao):
    """核心计算并输出所有结果"""

    # === 本卦 ===
    ben_gua_name = print_hexagram('本卦', xia_gua, shang_gua, highlight_yao=dong_yao)

    # === 体用生克 ===
    ti_gua, yong_gua = get_ti_yong(xia_gua, shang_gua, dong_yao)
    ti_wx = BA_GUA_WX[ti_gua]
    yong_wx = BA_GUA_WX[yong_gua]
    jixiong_str, guanxi_str = get_jixiong(ti_wx, yong_wx)

    print(f"\n{'─' * 40}")
    print(f"【体用生克】")
    print(f"  动爻在第{dong_yao}爻 → {'用在下卦' if 1 <= dong_yao <= 3 else '用在上卦'}")
    print(f"  体卦：{ti_gua}{BA_GUA_CN[ti_gua]}（{ti_wx}）")
    print(f"  用卦：{yong_gua}{BA_GUA_CN[yong_gua]}（{yong_wx}）")
    print(f"  体用关系：{ti_gua}{ti_wx} {'克' if guanxi_str=='体克用' else '生' if guanxi_str=='体生用' else '被' if '用' in guanxi_str else '与'} {yong_gua}{yong_wx} → {guanxi_str}")
    print(f"  ★ 吉凶：{jixiong_str} ★")

    # === 变卦 ===
    bian_xia, bian_shang = get_bian_gua(xia_gua, shang_gua, dong_yao)
    bian_gua_name = print_hexagram('变卦（之卦）', bian_xia, bian_shang)

    # === 互卦 ===
    hu_xia, hu_shang = get_hu_gua(xia_gua, shang_gua)
    hu_gua_name = print_hexagram('互卦', hu_xia, hu_shang)

    # === 综合总结 ===
    print(f"\n{'═' * 40}")
    print(f"【占断总结】")
    print(f"  本卦：{ben_gua_name}")
    print(f"  变卦：{bian_gua_name}")
    print(f"  互卦：{hu_gua_name}")
    print(f"  体用：{ti_gua}（{ti_wx}）{'克' if guanxi_str=='体克用' else '生' if guanxi_str=='体生用' else '被' if '用' in guanxi_str and '体' in guanxi_str else '与'} {yong_gua}（{yong_wx}）→ {guanxi_str}")
    print(f"  吉凶：{jixiong_str}")
    print(f"{'═' * 40}")

    # 摘要
    print(f"\n摘要：本卦{ben_gua_name}→体{ti_gua}用{yong_gua}→{guanxi_str}（{jixiong_str}）")


def print_usage():
    print("""梅花易数起卦工具

用法：
  python3 meihua.py <a> <b> <c>               数字起卦
  python3 meihua.py --time <y> <m> <d> <h>    时间起卦

数字起卦说明：
  a % 8 = 上卦（余0=8坤）
  b % 8 = 下卦（余0=8坤）
  c % 6 = 动爻（余0=6上爻）

时间起卦说明：
  上卦 = (年 + 月 + 日) % 8
  下卦 = (年 + 月 + 日 + 时) % 8
  动爻 = (年 + 月 + 日 + 时) % 6

示例：
  python3 meihua.py 3 8 6
  python3 meihua.py --time 2026 5 17 10
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    if sys.argv[1] == '--time':
        if len(sys.argv) != 6:
            print("错误：时间起卦需要4个参数：--time <year> <month> <day> <hour>")
            print_usage()
            sys.exit(1)
        try:
            args = [int(x) for x in sys.argv[2:6]]
        except ValueError:
            print("错误：参数必须为整数")
            sys.exit(1)
        meihua_timefa(*args)
    elif sys.argv[1] in ('-h', '--help'):
        print_usage()
    else:
        if len(sys.argv) != 4:
            print("错误：数字起卦需要3个参数：<a> <b> <c>")
            print_usage()
            sys.exit(1)
        try:
            args = [int(x) for x in sys.argv[1:4]]
        except ValueError:
            print("错误：参数必须为整数")
            sys.exit(1)
        meihua_shuqifa(*args)


if __name__ == '__main__':
    main()
