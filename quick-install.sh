#!/bin/bash
# ============================================
# PaddleOCR Web Service 一鍵安裝腳本
# 從 GitHub 下載並安裝
# 
# 使用方式:
# curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/paddleocr-service/main/quick-install.sh | sudo bash
# 或
# wget -qO- https://raw.githubusercontent.com/YOUR_USERNAME/paddleocr-service/main/quick-install.sh | sudo bash
# ============================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 設定變數 (請修改為你的 GitHub 倉庫)
GITHUB_REPO="${GITHUB_REPO:-YOUR_USERNAME/paddleocr-service}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"
INSTALL_DIR="/opt/paddleocr-service"
TEMP_DIR="/tmp/paddleocr-install-$$"

# 檢查 root
if [ "$EUID" -ne 0 ]; then
    error "請使用 root 權限執行 (sudo)"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       PaddleOCR Web Service 一鍵安裝                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 安裝 git
info "檢查並安裝必要工具..."
apt-get update -qq
apt-get install -y -qq git curl

# 克隆倉庫
info "從 GitHub 下載專案..."
mkdir -p $TEMP_DIR
cd $TEMP_DIR
git clone --depth 1 -b $GITHUB_BRANCH "https://github.com/$GITHUB_REPO.git" .

# 執行安裝腳本
info "執行安裝腳本..."
chmod +x install.sh
./install.sh

# 清理
cd /
rm -rf $TEMP_DIR

success "安裝完成!"
