#!/usr/bin/env python3
"""
八字排盘 增强版 — 匹配问真八字APP全部信息
输出：四柱完整信息（主星·天干·地支·藏干·星运·自坐·空亡·纳音·神煞）+大运+流年+流月
"""
import sys, os, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zhexue_core import (
    TIAN_GAN, DI_ZHI, GAN_WUXING, GAN_YINYANG, ZHI_WUXING,
    day_ganzhi_from_date, hour_zhi_index, hour_ganzhi,
    get_shi_shen, ZHI_CANG_GAN, xunkong_ganzhi,
    JIE_TERMS, JIE_ZHI, WU_HU_DUN,
    get_nayin,
    shier_changsheng,
    flow_month, flow_hour,
    liutong_ganzhi,
    gongwei_fenxi,
    liuqin_fenxi,
)
from jieqi_core import get_solar_month_idx, calc_dayun_start_age

def pillar_info(year, month, day, hour, minute, gender, liunian_year=None):
    """输出完整排盘"""
    # 基本计算
    y_gan, y_zhi = year_ganzhi(year, month, day)
    m_idx = get_solar_month_idx_correct(year, month, day)
    m_gan, m_zhi = month_gan_correct(y_gan, m_idx)
    d_gan, d_zhi = day_ganzhi_from_date(year, month, day)
    hz = hour_zhi_index(hour, minute)
    h_gan, h_zhi = hour_ganzhi(d_gan, hz)

    pillars = {}
    pillar_data = [
        ('nian', y_gan, y_zhi, '年柱'),
        ('yue', m_gan, m_zhi, '月柱'),
        ('ri', d_gan, d_zhi, '日柱'),
        ('shi', h_gan, h_zhi, '时柱'),
    ]
    
    for key, gan, zhi, name in pillar_data:
        gan_c = TIAN_GAN[gan]
        zhi_c = DI_ZHI[zhi]
        cang = ZHI_CANG_GAN[zhi]
        cang_shishen = [(TIAN_GAN[c], c, get_shi_shen(d_gan, c)) for c in cang]
        
        # 十二长生 - 星运=日干对各柱地支, 自坐=本柱天干对本柱地支
        xingyun = shier_changsheng(d_gan, zhi)  # 星运都用日干
        zizuo = shier_changsheng(gan, zhi)  # 自坐用本柱天干
        
        kong = xunkong_ganzhi(gan, zhi)
        nayin = get_nayin(gan, zhi)
        
        # 主星
        if key == 'ri':
            zhuxing = '元男' if gender == 'male' else '元女'
        else:
            zhuxing = get_shi_shen(d_gan, gan)
        
        pillars[key] = {
            'name': name,
            'zhuxing': zhuxing,
            'gan': gan_c,
            'gan_idx': gan,
            'zhi': zhi_c,
            'zhi_idx': zhi,
            'cang_gan': cang_shishen,
            'xingyun': xingyun,
            'zizuo': zizuo if zizuo else xingyun,
            'kongwang': f"{DI_ZHI[kong[0]]}{DI_ZHI[kong[1]]}",
            'nayin': nayin,
        }

    # 日主信息
    day_master = {
        'gan': TIAN_GAN[d_gan],
        'wu_xing': GAN_WUXING[TIAN_GAN[d_gan]],
        'qiang_ruo': get_rizhu_qiangruo(d_gan, m_zhi),
    }
    
    # 干支流通分析
    gan_zhi_tuple_dict = {
        'nian': (y_gan, y_zhi),
        'yue': (m_gan, m_zhi),
        'ri': (d_gan, d_zhi),
        'shi': (h_gan, h_zhi),
    }
    liutong = liutong_ganzhi(gan_zhi_tuple_dict)
    
    # 宫位分析
    gender_cn = '男' if gender == 'male' else '女'
    gongwei = gongwei_fenxi(y_gan, y_zhi, m_gan, m_zhi, d_gan, d_zhi, h_gan, h_zhi, gender_cn)
    
    # 六亲分析
    liuqin = liuqin_fenxi(d_gan, y_gan, y_zhi, m_gan, m_zhi, d_gan, d_zhi, h_gan, h_zhi, gender_cn)
    
    # 大运
    yin_gender = GAN_YINYANG[TIAN_GAN[y_gan]]  # 0=阴,1=阳
    is_male = (gender == 'male')
    shun_pai = (yin_gender == 1 and is_male) or (yin_gender == 0 and not is_male)
    start_age = calc_start_age(year, month, day, hour, minute, shun_pai)
    
    dayun_list = []
    dayun_steps = 12  # 120年，覆盖全生命周期
    if shun_pai:
        for step in range(1, dayun_steps + 1):
            dg = (m_gan + step) % 10
            dz = (m_zhi + step) % 12
            age_low = int(start_age) + (step - 1) * 10
            age_high = age_low + 9
            gan_c, zhi_c = TIAN_GAN[dg], DI_ZHI[dz]
            dayun_list.append({
                'ganzhi': f"{gan_c}{zhi_c}",
                'age_range': f"{age_low}~{age_high}岁",
                'shi_shen_gan': get_shi_shen(d_gan, dg),
                'shi_shen_zhi': get_shi_shen(d_gan, ZHI_CANG_GAN[dz][0]),
            })
    else:
        for step in range(1, dayun_steps + 1):
            dg = (m_gan - step) % 10
            dz = (m_zhi - step) % 12
            age_low = int(start_age) + (step - 1) * 10
            age_high = age_low + 9
            gan_c, zhi_c = TIAN_GAN[dg], DI_ZHI[dz]
            dayun_list.append({
                'ganzhi': f"{gan_c}{zhi_c}",
                'age_range': f"{age_low}~{age_high}岁",
                'shi_shen_gan': get_shi_shen(d_gan, dg),
                'shi_shen_zhi': get_shi_shen(d_gan, ZHI_CANG_GAN[dz][0]),
            })
    
    # 流年
    if liunian_year is None:
        liunian_year = datetime.now().year
    ly = liunian_year
    lg, lz = (ly - 4) % 10, (ly - 4) % 12
    liunian_list = []
    for offset in range(-5, 16):
        yy = ly + offset
        yg, yz = (yy - 4) % 10, (yy - 4) % 12
        gz = f"{TIAN_GAN[yg]}{DI_ZHI[yz]}"
        # 流年神煞
        try:
            from zhexue_core import shen_sha_all
            ln_ss = shen_sha_all(TIAN_GAN[yg], DI_ZHI[yz],
                                TIAN_GAN[m_gan], DI_ZHI[m_zhi],
                                TIAN_GAN[d_gan], DI_ZHI[d_zhi],
                                TIAN_GAN[h_gan], DI_ZHI[h_zhi])
            ln_ss_list = list(ln_ss.keys())[:5]
        except Exception:
            ln_ss_list = []
        liunian_list.append({
            'year': yy,
            'ganzhi': gz,
            'shi_shen_gan': get_shi_shen(d_gan, yg),
            'shi_shen_zhi': get_shi_shen(d_gan, ZHI_CANG_GAN[yz][0]),
            'shen_sha': ln_ss_list,
        })
    
    # 流月 (当前年)
    flow_months = flow_month(ly, month, day)
    
    # 小运 (简单版: 年干定)
    xiaoyun_gan, xiaoyun_zhi = (ly - 4) % 10, (ly - 4) % 12
    for one in ['nian','yue','ri','shi']:
        pillars[one]['xiao_yun'] = {  # 匹配APP里的"小运"和"司令"
            'gan': TIAN_GAN[(ly - 4) % 10],
            'zhi': DI_ZHI[(ly - 4) % 12],
        }
    
    # 起运信息
    qiyun_year = year + int(start_age)
    qiyun_month = month + int((start_age % 1) * 12)  # 简化
    
    result = {
        'input': {'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute, 'gender': '男' if gender=='male' else '女'},
        'bazi': pillars,
        'day_master': day_master,
        'qiyun': {
            'start_age': round(start_age, 2),
            'start_year': qiyun_year,
            'direction': '顺排' if shun_pai else '逆排',
        },
        'dai_yun_ganzhi': f"{TIAN_GAN[m_gan]}{DI_ZHI[m_zhi]}",
        'dayun': dayun_list,
        'liunian': liunian_list,
        'liuyue': flow_months,
        'liutong': liutong,
        'gongwei': gongwei,
        'liuqin': liuqin,
    }

    # 用神
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from yongshen import calc_yongshen
        pillars_list = [TIAN_GAN[y_gan], DI_ZHI[y_zhi], TIAN_GAN[m_gan], DI_ZHI[m_zhi],
                        TIAN_GAN[d_gan], DI_ZHI[d_zhi], TIAN_GAN[h_gan], DI_ZHI[h_zhi]]
        ys = calc_yongshen(pillars_list)
        result['yongshen'] = ys
    except Exception:
        pass

    # 称骨 - 需要农历参数，先不自动加

    # 流日
    try:
        from zhexue_core import compute_liuri
        start = f"{year:04d}-{month:02d}-{day:02d}"
        result['liuri'] = compute_liuri(start, days=10)
    except Exception:
        pass

    # 流时
    try:
        from zhexue_core import compute_liushi
        result['liushi'] = compute_liushi(TIAN_GAN[d_gan])
    except Exception:
        pass

    # 神煞完整版59种
    try:
        from zhexue_core import shen_sha_all
        result['shen_sha'] = shen_sha_all(
            TIAN_GAN[y_gan], DI_ZHI[y_zhi],
            TIAN_GAN[m_gan], DI_ZHI[m_zhi],
            TIAN_GAN[d_gan], DI_ZHI[d_zhi],
            TIAN_GAN[h_gan], DI_ZHI[h_zhi])
    except Exception:
        pass

    return result

# ===== 辅助函数 =====
def year_ganzhi(year, month, day):
    if month < 2 or (month == 2 and day < 4):
        y = year - 1
    else:
        y = year
    return (y - 4) % 10, (y - 4) % 12

def get_solar_month_idx_correct(year, month, day):
    """Use JieQiCore's precise 节气 data for solar month determination."""
    return get_solar_month_idx(year, month, day)

def month_gan_correct(year_gan, solar_idx):
    """solar_idx 0=小寒(丑月),1=立春(寅月),...11=大雪(子月)"""
    start = WU_HU_DUN[year_gan]  # 寅月(索引1)的天干
    gan = (start + solar_idx - 1) % 10  # 从寅月偏移
    zhi = JIE_ZHI[solar_idx]  # 直接从JIE_ZHI取地支
    return gan, zhi

# 日主强弱
WANG_XIANG_TABLE = {
    # (日干五行, 月支五行) → '旺','相','休','囚','死'
    '木': {'寅':'旺','卯':'旺','巳':'休','午':'休','辰':'囚','戌':'囚','丑':'囚','未':'囚',
           '申':'死','酉':'死','亥':'相','子':'相'},
    '火': {'寅':'相','卯':'相','巳':'旺','午':'旺','辰':'休','戌':'休','丑':'休','未':'休',
           '申':'死','酉':'死','亥':'囚','子':'囚'},
    '土': {'寅':'死','卯':'死','巳':'相','午':'相','辰':'旺','戌':'旺','丑':'旺','未':'旺',
           '申':'休','酉':'休','亥':'囚','子':'囚'},
    '金': {'寅':'囚','卯':'囚','巳':'死','午':'死','辰':'相','戌':'相','丑':'相','未':'相',
           '申':'旺','酉':'旺','亥':'休','子':'休'},
    '水': {'寅':'休','卯':'休','巳':'囚','午':'囚','辰':'死','戌':'死','丑':'死','未':'死',
           '申':'相','酉':'相','亥':'旺','子':'旺'},
}

def get_rizhu_qiangruo(d_gan, m_zhi):
    wx = GAN_WUXING[TIAN_GAN[d_gan]]
    mz_c = DI_ZHI[m_zhi]
    return WANG_XIANG_TABLE.get(wx, {}).get(mz_c, '平')

# 起运岁数 (简化版)
def calc_start_age(year, month, day, hour, minute, shun_pai):
    """精确起运岁数：基于距下一个/上一个节气天数 ÷ 3"""
    return calc_dayun_start_age(year, month, day, hour, minute, shun_pai)

def format_output(result):
    """格式化输出匹配问真八字风格"""
    lines = []
    lines.append("=" * 72)
    lines.append(f"  八字排盘 | {result['input']['year']}年{result['input']['month']}月{result['input']['day']}日 {result['input']['hour']}:{result['input']['minute']:02d} {result['input']['gender']}")
    lines.append("=" * 72)
    lines.append("")
    
    # 四柱表头
    b = result['bazi']
    header = f"{'|':8s}{b['nian']['name']:^14s}{b['yue']['name']:^14s}{b['ri']['name']:^14s}{b['shi']['name']:^14s}"
    lines.append(header)
    lines.append("-" * 72)
    
    rows = ['主星','天干','地支','藏干','星运','自坐','空亡','纳音']
    for row in rows:
        parts = [f"{row:4s}"]
        for k in ['nian','yue','ri','shi']:
            p = b[k]
            if row == '主星': parts.append(f"{p['zhuxing']:^14s}")
            elif row == '天干': parts.append(f"{p['gan']:^14s}")
            elif row == '地支': parts.append(f"{p['zhi']:^14s}")
            elif row == '藏干': 
                cg = ' '.join([f"{c[0]}({c[2]})" for c in p['cang_gan']])
                parts.append(f"{cg:^14s}")
            elif row == '星运': parts.append(f"{p['xingyun']:^14s}")
            elif row == '自坐': parts.append(f"{p['zizuo']:^14s}")
            elif row == '空亡': parts.append(f"{p['kongwang']:^14s}")
            elif row == '纳音': parts.append(f"{p['nayin']:^14s}")
        lines.append('|'.join(parts))

    lines.append("")
    lines.append("-" * 72)
    lines.append("【干支流通】")
    lt = result.get('liutong', {})
    # 天干生克
    if lt.get('tian_gan_sheng_ke'):
        lines.append("  天干生克:")
        for item in lt['tian_gan_sheng_ke']:
            lines.append(f"    {item[0]:12s} {item[1]}")
    # 天干五合
    if lt.get('tian_gan_chong_he'):
        lines.append("  天干五合:")
        for item in lt['tian_gan_chong_he']:
            lines.append(f"    {item[0]:12s} {item[1]}")
    # 地支六合/三合
    if lt.get('di_zhi_he'):
        lines.append("  地支合:")
        for item in lt['di_zhi_he']:
            lines.append(f"    {item[0]:12s} {item[1]}")
    # 地支六冲
    if lt.get('di_zhi_chong'):
        lines.append("  地支冲:")
        for item in lt['di_zhi_chong']:
            lines.append(f"    {item}")
    # 地支三刑
    if lt.get('di_zhi_xing'):
        lines.append("  地支刑:")
        for item in lt['di_zhi_xing']:
            lines.append(f"    {item}")
    # 地支六害
    if lt.get('di_zhi_hai'):
        lines.append("  地支害:")
        for item in lt['di_zhi_hai']:
            lines.append(f"    {item}")
    # 盖头截脚
    if lt.get('gan_zhi_guanxi'):
        lines.append("  坐支关系:")
        for item in lt['gan_zhi_guanxi']:
            lines.append(f"    {item[0]:16s} {item[1]:10s} [{item[2]}]")
    if lt.get('流通分析'):
        lines.append(f"  流通: {lt['流通分析']}")
    
    lines.append("")
    lines.append("-" * 72)
    lines.append("【宫位分析】")
    gw = result.get('gongwei', {})
    for k in ['nian','yue','ri','shi']:
        if k in gw:
            g = gw[k]
            lines.append(f"  {k+'柱':4s}{g['gongwei']:12s} {g['nianling']:10s}")
            for lq in g.get('liuqin', []):
                lines.append(f"        {lq}")
    
    lines.append("")
    lines.append("-" * 72)
    lines.append("【六亲分析】")
    lq = result.get('liuqin', {})
    for key, label in [('father','父亲'),('mother','母亲'),('spouse','配偶')]:
        if key in lq:
            item = lq[key]
            lines.append(f"  {label}: 天干{item['gan']} ({item['shi_shen']}) 位于{item['zhuwei']}")
    if lq.get('children'):
        lines.append("  子女:")
        for c in lq['children']:
            lines.append(f"    {c.get('person','?')}: {c.get('gan','?')}({c.get('shi_shen','?')}) 位于{c.get('zhuwei','?')}")
    if lq.get('siblings'):
        lines.append("  兄弟姐妹:")
        for s in lq['siblings']:
            lines.append(f"    {s.get('person','?')}: {s.get('gan','?')}({s.get('shi_shen','?')}) 位于{s.get('zhuwei','?')}")
    
    lines.append("")
    lines.append("-" * 72)
    lines.append(f"【日主】{result['day_master']['gan']}({result['day_master']['wu_xing']}) {result['day_master']['qiang_ruo']}")
    lines.append(f"【起运】{result['qiyun']['start_age']}岁  {result['qiyun']['direction']}")
    lines.append("")
    
    # 大运
    lines.append("【大运】")
    for row_idx in range(0, len(result['dayun']), 4):
        row = result['dayun'][row_idx:row_idx+4]
        lines.append("  " + "".join(f"{dy['age_range']:^14s}" for dy in row))
        lines.append("  " + "".join(f"{dy['ganzhi']:^14s}" for dy in row))
    
    # 流年
    lines.append("")
    lines.append("【流年】")
    for liu in result['liunian']:
        mark = "→" if liu['year'] == datetime.now().year else "  "
        ss_str = ' '.join(liu.get('shen_sha', [])[:3])
        lines.append(f"  {mark} {liu['year']} {liu['ganzhi']}  {liu['shi_shen_gan']}/{liu['shi_shen_zhi']}  [{ss_str}]")
    
    # 流月
    lines.append("")
    lines.append("【流月】")
    for lm in result['liuyue']:
        lines.append(f"  {lm['jieqi']:4s} {lm['month']}/{lm['day']:<2d}   {lm['ganzhi']:4s}  {lm['shi_shen']}")

    # 用神
    if 'yongshen' in result:
        ys = result['yongshen']
        lines.append("")
        lines.append("-" * 72)
        lines.append(f"【用神】{ys.get('yongshen','?')}  忌神:{ys.get('jishen','?')}  {ys.get('judgement','?')}")

    # 称骨
    if 'chenggu' in result:
        cg = result['chenggu']
        lines.append(f"【称骨】{cg['weight_text']}  {cg['interpretation']['man']}")

    # 流日
    if 'liuri' in result:
        lines.append("")
        lines.append("-" * 72)
        lines.append("【流日】")
        for lr in result['liuri'][:7]:
            lines.append(f"  {lr['date']}  {lr['ganzhi']}")

    # 流时
    if 'liushi' in result:
        lines.append("")
        lines.append("-" * 72)
        lines.append("【流时】")
        for ls in result['liushi'][:6]:
            lines.append(f"  {ls['time_label']} {ls['gan']}{ls['zhi']}")

    # 神煞完整版
    if 'shen_sha' in result:
        lines.append("")
        lines.append("-" * 72)
        lines.append("【神煞】")
        ss_data = result['shen_sha']
        # 新格式: {神煞名: [柱列表]}
        if ss_data and isinstance(next(iter(ss_data.values())), list):
            pillar_map = {'年':[], '月':[], '日':[], '时':[]}
            for shen_name, pillars_list in ss_data.items():
                for p in pillars_list:
                    if p in pillar_map:
                        pillar_map[p].append(shen_name)
            for p_name in ['年','月','日','时']:
                if pillar_map[p_name]:
                    lines.append(f"  {p_name}柱: {' '.join(pillar_map[p_name][:10])}")

    return '\n'.join(lines)

def main():
    # 交互查询参数
    query_liunian = None
    query_liuyue = None
    query_liuri = None
    query_liushi = None
    liunian_year = None
    longitude = None
    no_solar_eot = False
    
    args = sys.argv[1:]
    
    # Parse query flags
    skip_next = False
    clean_args = []
    for i, a in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if a == '--liunian':
            query_liunian = int(args[i+1])
            skip_next = True
            continue
        if a == '--liuyue':
            query_liuyue = args[i+1]
            skip_next = True
            continue
        if a == '--liuri':
            query_liuri = args[i+1]
            skip_next = True
            continue
        if a == '--liushi':
            query_liushi = args[i+1]
            skip_next = True
            continue
        if a == '--longitude':
            longitude = float(args[i+1])
            skip_next = True
            continue
        if a == '--no-solar-eot':
            no_solar_eot = True
            continue
        clean_args.append(a)
    
    base_args = clean_args
    year, month, day = int(base_args[0]), int(base_args[1]), int(base_args[2])
    hour, minute = int(base_args[3]), int(base_args[4])
    gender = base_args[5] if len(base_args) > 5 else 'male'
    if len(base_args) > 6:
        liunian_year = int(base_args[6])
    
    # 真太阳时修正
    if longitude is not None:
        from zhexue_core import solar_time_correction
        corr_h, corr_m = solar_time_correction(longitude, year, month, day, hour, minute)
        print(f"# 真太阳时修正: {hour:02d}:{minute:02d} → {int(corr_h):02d}:{int(corr_m):02d} (经度{longitude})")
        hour, minute = int(corr_h), int(corr_m)
    
    gender_map = {'male':'男','female':'女','男':'男','女':'女'}
    result = pillar_info(year, month, day, hour, minute, 'male' if gender in ('male','男') else 'female', liunian_year)
    
    # 交互查询
    if query_liunian:
        from zhexue_core import day_ganzhi_from_date, get_shi_shen, ZHI_CANG_GAN, shen_sha_all
        yg, yz = (query_liunian - 4) % 10, (query_liunian - 4) % 12
        d_gan, d_zhi = day_ganzhi_from_date(year, month, day)
        gz = f"{TIAN_GAN[yg]}{DI_ZHI[yz]}"
        ss = shen_sha_all(TIAN_GAN[yg], DI_ZHI[yz], result['bazi']['yue']['gan'], result['bazi']['yue']['zhi'],
                          result['bazi']['ri']['gan'], result['bazi']['ri']['zhi'],
                          result['bazi']['shi']['gan'], result['bazi']['shi']['zhi'])
        q_result = {
            'query_type': 'liunian',
            'year': query_liunian,
            'ganzhi': gz,
            'shi_shen_gan': get_shi_shen(d_gan, yg),
            'shi_shen_zhi': get_shi_shen(d_gan, ZHI_CANG_GAN[yz][0]),
            'shen_sha': list(ss.keys()),
        }
        print(json.dumps(q_result, ensure_ascii=False, indent=2))
        sys.exit(0)

    if query_liuyue:
        parts = query_liuyue.split('-')
        ly, lm = int(parts[0]), int(parts[1])
        from jieqi_core import get_jieqi
        entry = get_jieqi(ly, lm)
        if entry:
            from zhexue_core import day_ganzhi_from_date, get_shi_shen, shen_sha_all
            from bazi import year_ganzhi, month_gan_correct, get_solar_month_idx_correct
            yg, yz = year_ganzhi(ly, lm, int(entry[1]))
            m_idx = get_solar_month_idx_correct(ly, lm, int(entry[1]))
            mg, mz = month_gan_correct(yg, m_idx)
            d_gan, d_zhi = day_ganzhi_from_date(ly, lm, int(entry[1]))
            ss = shen_sha_all(TIAN_GAN[yg], DI_ZHI[yz], TIAN_GAN[mg], DI_ZHI[mz], result['bazi']['ri']['gan'], result['bazi']['ri']['zhi'],
                              result['bazi']['shi']['gan'], result['bazi']['shi']['zhi'])
            q_result = {
                'query_type': 'liuyue',
                'year': ly, 'month': lm,
                'jieqi': entry[0],
                'date': f"{entry[1]}日 {entry[2]}",
                'yue_ganzhi': f"{TIAN_GAN[mg]}{DI_ZHI[mz]}",
                'shi_shen': get_shi_shen(result['bazi']['ri']['gan_idx'], mg),
                'shen_sha': list(ss.keys()),
            }
            print(json.dumps(q_result, ensure_ascii=False, indent=2))
            sys.exit(0)
    
    if query_liuri:
        from zhexue_core import compute_liuri, get_shi_shen, shen_sha_all
        lr = compute_liuri(query_liuri, days=1)
        if lr:
            d = lr[0]
            dg, dz = d['gan'], d['zhi']
            dg_idx = TIAN_GAN.index(dg) if dg in TIAN_GAN else 0
            dz_idx = DI_ZHI.index(dz) if dz in DI_ZHI else 0
            from zhexue_core import ZHI_CANG_GAN
            ss = shen_sha_all(result['bazi']['nian']['gan'], result['bazi']['nian']['zhi'],
                              result['bazi']['yue']['gan'], result['bazi']['yue']['zhi'],
                              dg, dz,
                              result['bazi']['shi']['gan'], result['bazi']['shi']['zhi'])
            d['shi_shen'] = get_shi_shen(result['bazi']['ri']['gan_idx'], dg_idx)
            d['shen_sha'] = list(ss.keys())
        print(json.dumps({'query_type':'liuri','result':lr[0] if lr else None}, ensure_ascii=False, indent=2))
        sys.exit(0)
    
    if query_liushi:
        from zhexue_core import compute_liushi, get_shi_shen
        from zhexue_core import shen_sha_all
        ls = compute_liushi(result['bazi']['ri']['gan'])
        for l in ls:
            l['shi_shen'] = get_shi_shen(result['bazi']['ri']['gan_idx'], l['gan_idx'])
            # Simplified 神煞 per hour: just show 时柱 based
        print(json.dumps({'query_type':'liushi','result':ls}, ensure_ascii=False, indent=2))
        sys.exit(0)
    
    # JSON输出
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()
    # 可读文本
    print(format_output(result))

if __name__ == '__main__':
    main()
