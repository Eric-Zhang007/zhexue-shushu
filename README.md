# 玄学数术工具集

八字(59神煞·节气·大运·流年·流月·流日·流时·用神称骨) + 梅花易数 + 奇门遁甲 + 大六壬 + 紫微斗数

纯 Python 实现，无外部依赖，零版权风险。可在任何 Python 3.10+ 环境中运行。

## 安装

### 方法一：pip 安装（一次命令，全局可用）

```bash
pip install git+https://github.com/Eric-Zhang007/zhexue-shushu.git

# 安装后即可直接使用（不需要加 python3 前缀）：
bazi 2007 9 28 20 8 male
chenggu 丁亥 8 18 戌
yongshen 2007 9 28 20 8 male
```

### 方法二：克隆 + 本地安装

```bash
git clone https://github.com/Eric-Zhang007/zhexue-shushu.git
cd zhexue-shushu
pip install -e .
```

### 方法三：直接运行（不安装）

```bash
git clone https://github.com/Eric-Zhang007/zhexue-shushu.git
cd zhexue-shushu

python3 zhexue/bazi.py 2007 9 28 20 8 male
python3 zhexue/chenggu.py 丁亥 8 18 戌
python3 zhexue/yongshen.py 2007 9 28 20 8 male
```

---

## 脚本总览

| 命令/文件 | 功能 |
|---------|------|
| `bazi` | 八字完整排盘 — 四柱、神煞59、流通、宫位、六亲、大运、流年、流月、流日、流时、用神 |
| `jieqi_core.py` | 节气引擎（被 bazi 内部调用） |
| `yongshen` | 用神分析 — 日主旺衰、用神、忌神 |
| `chenggu` | 袁天罡称骨算命 |
| `zhexue_core.py` | 核心数据+59神煞引擎 |
| `meihua.py` | 梅花易数 |
| `qimen.py` | 奇门遁甲（时家转盘·拆补法） |
| `liuren.py` | 大六壬（贼克法三传·天将） |
| `ziwei.py` | 紫微斗数（完整安星诀） |
| `run.py` | 统一入口 |

## 八字排盘 `bazi`

```bash
# 基础排盘
bazi 2007 9 28 20 8 male

# 交互查询
bazi 2007 9 28 20 8 male --liunian 2035     # 流年：干支+十神+神煞完整列表
bazi 2007 9 28 20 8 male --liuyue 2026-08   # 流月：节气+月柱+十神+神煞
bazi 2007 9 28 20 8 male --liuri 2028-03-15 # 流日：干支+十神+神煞
bazi 2007 9 28 20 8 male --liushi 2028-03-15# 流时：12时辰+十神
```

参数：`<年> <月> <日> <时> <分> <male|female> [流年开始年]`

输出包含：四柱表 / 神煞59 / 干支流通 / 宫位分析 / 六亲分析 / 日主旺衰 / 起运 / 大运12步120年 / 流年±5年 / 流月 / 用神 / 流日 / 流时

### 输出样例

```
四柱: 丁亥 己酉 乙丑 丙戌
起运: 6.83岁 逆排  日主: 乙木 死
用神: 木  忌神:金  身弱
称骨: 五两五钱 (年16+月15+日18+时6=55)
神煞: 23次命中 (年6+月6+日5+时6)
```

## 用神分析 `yongshen`

```bash
yongshen 2007 9 28 20 8 male

# 或直接传原生干支
yongshen --raw 丁 亥 己 酉 乙 丑 丙 戌
```

输出 JSON：
```json
{
  "yongshen": "木",
  "jishen": "金",
  "judgement": "身弱",
  "self_strength": 1.2072,
  "other_strength": 3.7928
}
```

## 称骨算命 `chenggu`

> ⚠ 必须用农历日期！不是公历。

```bash
chenggu 丁亥 8 18 戌
```

参数：`<年干支> <农历月> <农历日> <时辰>`

时辰支持：地支(戌)、24小时制(19-21)、地支索引(10)

---

## 神煞引擎（59种）

78条匹配规则。每条含起算来源、检视位置、性别条件。规则类型：

| 类型 | 含义 | 涵盖神煞 |
|-----|------|---------|
| 年干+日干双查地支 | 天乙/文昌/福星/太极/天厨/国印/金舆 | 7种 |
| 年支+日支双版查 | 驿马/华盖/桃花/将星/劫煞/亡神/灾煞 | 7种 |
| 月支起查天干+地支 | 天德/月德 | 2种 |
| 旬空 | 年柱空亡+日柱空亡 | 2种 |
| 特定日柱匹配 | 十灵日/六秀日/魁罡日/八专日/九丑日等 | 5种 |
| 纳音查 | 学堂/词馆/天罗地网 | 3种 |

```python
from zhexue.zhexue_core import shen_sha_all

r = shen_sha_all('丁','亥','己','酉','乙','丑','丙','戌')
# 返回 {'天乙贵人': ['年','月'], '文昌贵人': ['月'], ...}
```

神煞名称与含义详见 `references/shensha-references.txt`。

---

## 遍历查询

| 查询 | 命令 | 返回内容 |
|-----|------|---------|
| 流年 | `--liunian <年>` | 干支+十神+完整神煞列表 |
| 流月 | `--liuyue <年-月>` | 节气名+日期+月柱+十神+神煞 |
| 流日 | `--liuri <年-月-日>` | 干支+十神+神煞（含4位神煞） |
| 流时 | `--liushi <年-月-日>` | 12时辰+十神+神煞 |

---

## 跨框架使用

安装后，以下所有 AI 编码工具均可直接通过终端调用本工具：

| 框架 | 用法 |
|-----|------|
| **Claude Code** | 在任意项目中 `claude` 后可自然语言描述「算一下张三的生辰八字」，Claude 会自动调用 `bazi` 命令 |
| **Codex** | `codex` 环境下直接执行 `bazi 2007 9 28 20 8 male` |
| **Hermes Agent** | 如安装为 skill（`hermes skill install zhexue-shushu`），agent 自动获得完整上下文；否则直接 `python3 zhexue/bazi.py ...` |
| **OpenCode** | `opencode` 环境中直接运行 `bazi ...` |
| **任意 CLI** | 安装后 `bazi` / `chenggu` / `yongshen` 是全局命令，任何 terminal 都能用 |

核心思想：**pip install 就够了**。所有工具安装后成为系统级 CLI 命令，无需为每个框架做特殊配置。

---

## 数据

- `data/jieqi_data.txt` — 1800-2100 年 302 年节气数据（161KB），来自传统农历节气表
- `references/shensha-references.txt` — 59 条神煞完整解读（71KB）
- `references/shensha-mapping-table.md` — 59 种神煞 78 条规则的 JSON 映射

## 验证案例

```
2007-09-28 20:08 男

八字: 丁亥 己酉 乙丑 丙戌
起运: 6.83岁 逆排  日主: 乙木 死
用神: 木  忌神:金  身弱
称骨: 五两五钱 (年16+月15+日18+时6=55)
神煞: 23次命中 (年6+月6+日5+时6)
```

---

## 许可

MIT License
