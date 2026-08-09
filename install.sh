#!/usr/bin/env bash
# 玄学数术工具集 — 统一安装脚本
# 适用于: Claude Code / Codex / Hermes Agent / OpenCode / 任意终端
set -euo pipefail

REPO_URL="https://github.com/Eric-Zhang007/zhexue-shushu.git"
INSTALL_DIR="${INSTALL_DIR:-$HOME/zhexue-shushu}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  玄学数术工具集 — 统一安装${NC}"
echo -e "${CYAN}  八字 · 梅花 · 奇门 · 六壬 · 紫微${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 检查 Python
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo -e "${YELLOW}❌ 需要 Python 3.10+，请先安装。${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python: $($PYTHON --version)"

# 检查 pip
PIP=""
for cmd in pip3 pip; do
    if command -v "$cmd" &>/dev/null; then
        PIP="$cmd"
        break
    fi
done

if [ -z "$PIP" ]; then
    echo -e "${YELLOW}❌ 未找到 pip，请先安装 pip。${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Package manager: $PIP"

# 检查 git
if command -v git &>/dev/null; then
    echo -e "${GREEN}✓${NC} Git: $(git --version)"
    HAS_GIT=true
else
    echo -e "${YELLOW}⚠ Git 未安装，跳过 git clone。${NC}"
    HAS_GIT=false
fi

echo ""

# ========== 安装方式选择 ==========
echo "选择安装方式:"
echo "  1) pip 安装（推荐）— 一次命令，全局可用 bazi/chenggu/yongshen 命令"
echo "  2) 本地克隆 + pip 安装 — 可修改代码，适合二次开发"
echo "  3) 直接运行（不安装）— 仅 clone，每次 python3 zhexue/bazi.py 调用"
read -rp "请选择 [1/2/3] (默认: 1): " choice
choice="${choice:-1}"

case "$choice" in
    1)
        echo ""
        echo -e "${CYAN}→ 通过 pip 直接从 GitHub 安装...${NC}"
        $PIP install "$REPO_URL"
        echo ""
        echo -e "${GREEN}✓ 安装完成！${NC}"
        ;;
    2)
        echo ""
        echo -e "${CYAN}→ 克隆仓库到 $INSTALL_DIR ...${NC}"
        if [ "$HAS_GIT" = true ]; then
            git clone "$REPO_URL" "$INSTALL_DIR"
            cd "$INSTALL_DIR"
            $PIP install -e .
            echo ""
            echo -e "${GREEN}✓ 安装完成！${NC}"
            echo -e "源码目录: ${CYAN}$INSTALL_DIR${NC}"
        else
            echo -e "${YELLOW}请先安装 git，或选择方式 1。${NC}"
            exit 1
        fi
        ;;
    3)
        echo ""
        echo -e "${CYAN}→ 克隆仓库到 $INSTALL_DIR ...${NC}"
        if [ "$HAS_GIT" = true ]; then
            git clone "$REPO_URL" "$INSTALL_DIR"
            echo ""
            echo -e "${GREEN}✓ 克隆完成！${NC}"
            echo -e "源码目录: ${CYAN}$INSTALL_DIR${NC}"
            echo -e "运行示例: ${CYAN}python3 $INSTALL_DIR/zhexue/bazi.py 1986 3 15 12 0 male${NC}"
        else
            echo -e "${YELLOW}请先安装 git。${NC}"
            exit 1
        fi
        ;;
esac

# ========== 检查 Hermes Agent，可选安装为 skill ==========
if command -v hermes &>/dev/null; then
    echo ""
    echo -e "${CYAN}检测到 Hermes Agent。是否安装为 Hermes skill？[y/N]${NC} "
    read -rp "" install_skill
    if [ "$install_skill" = "y" ] || [ "$install_skill" = "Y" ]; then
        SKILL_DIR="${SKILL_DIR:-$HOME/.hermes/skills/zhexue-shushu}"
        mkdir -p "$SKILL_DIR"
        if [ -d "$INSTALL_DIR" ]; then
            cp -r "$INSTALL_DIR"/* "$SKILL_DIR/" 2>/dev/null || true
            echo -e "${GREEN}✓${NC} Skill 已安装到 $SKILL_DIR"
        else
            git clone "$REPO_URL" "$SKILL_DIR"
            echo -e "${GREEN}✓${NC} Skill 已安装到 $SKILL_DIR"
        fi
        echo -e "在 Hermes 中使用: ${CYAN}hermes skill load zhexue-shushu${NC}"
    fi
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}安装完成！使用方法：${NC}"
echo ""
echo "  # 八字排盘"
echo "  bazi 1986 3 15 12 0 male"
echo ""
echo "  # 用神分析"
echo "  yongshen 1986 3 15 12 0 male"
echo ""
echo "  # 称骨算命"
echo "  chenggu 丁亥 8 18 戌"
echo ""
echo "  # 交互查询"
echo "  bazi 1986 3 15 12 0 male --liunian 2035"
echo "  bazi 1986 3 15 12 0 male --liuyue 2026-08"
echo "  bazi 1986 3 15 12 0 male --liuri 2028-03-15"
echo ""
echo -e "${CYAN}========================================${NC}"
