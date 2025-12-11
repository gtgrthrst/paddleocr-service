#!/bin/bash
# ============================================
# PaddleOCR Web Service 安裝腳本
# 適用於 Proxmox VE Ubuntu CT 環境
# 支援從 GitHub 或本地安裝
# ============================================

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 輸出函數
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 檢查是否為 root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "請使用 root 權限執行此腳本 (sudo ./install.sh)"
    fi
}

# 設定變數
SERVICE_NAME="paddleocr"
SERVICE_USER="paddleocr"
INSTALL_DIR="/opt/paddleocr-service"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_PORT=${PORT:-8000}
PYTHON_VERSION="python3"

# GitHub 設定 (請修改為你的 GitHub 用戶名和倉庫名)
GITHUB_REPO="${GITHUB_REPO:-YOUR_USERNAME/paddleocr-service}"
GITHUB_BRANCH="${GITHUB_BRANCH:-main}"

# 顯示標題
show_banner() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║         PaddleOCR Web Service 安裝程式                   ║"
    echo "║         適用於 Proxmox VE Ubuntu CT                      ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
}

# 顯示使用說明
show_usage() {
    echo "用法: $0 [選項]"
    echo ""
    echo "選項:"
    echo "  --github          從 GitHub 克隆安裝"
    echo "  --repo REPO       指定 GitHub 倉庫 (預設: $GITHUB_REPO)"
    echo "  --branch BRANCH   指定分支 (預設: $GITHUB_BRANCH)"
    echo "  --port PORT       指定服務埠號 (預設: 8000)"
    echo "  -h, --help        顯示此說明"
    echo ""
    echo "範例:"
    echo "  sudo ./install.sh                              # 本地安裝"
    echo "  sudo ./install.sh --github                     # 從 GitHub 安裝"
    echo "  sudo ./install.sh --github --repo user/repo    # 指定倉庫"
    echo ""
}

# 安裝系統依賴
install_system_deps() {
    info "更新系統套件..."
    apt-get update -qq
    
    info "安裝系統依賴..."
    apt-get install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        poppler-utils \
        curl \
        wget \
        git
    
    success "系統依賴安裝完成"
}

# 創建服務用戶
create_service_user() {
    if id "$SERVICE_USER" &>/dev/null; then
        info "服務用戶 $SERVICE_USER 已存在"
    else
        info "創建服務用戶 $SERVICE_USER..."
        useradd -r -s /bin/false -m -d /var/lib/$SERVICE_USER $SERVICE_USER
        success "服務用戶創建完成"
    fi
}

# 安裝應用程式
install_application() {
    info "創建安裝目錄..."
    
    # 判斷安裝來源
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # 檢查是否從 GitHub 安裝
    if [ "$FROM_GITHUB" = "true" ] || [ ! -f "$SCRIPT_DIR/app.py" ]; then
        info "從 GitHub 克隆專案..."
        
        # 移除舊的安裝目錄
        if [ -d "$INSTALL_DIR" ]; then
            warning "移除舊的安裝目錄..."
            rm -rf $INSTALL_DIR
        fi
        
        git clone --depth 1 -b $GITHUB_BRANCH "https://github.com/$GITHUB_REPO.git" $INSTALL_DIR
        success "GitHub 克隆完成"
    else
        info "從本地目錄安裝..."
        mkdir -p $INSTALL_DIR
        
        # 複製檔案
        cp -r "$SCRIPT_DIR"/* $INSTALL_DIR/ 2>/dev/null || true
    fi
    
    # 確保目錄結構存在
    mkdir -p $INSTALL_DIR/templates
    mkdir -p $INSTALL_DIR/static
    mkdir -p $INSTALL_DIR/uploads
    mkdir -p $INSTALL_DIR/logs
    
    info "創建 Python 虛擬環境..."
    $PYTHON_VERSION -m venv $VENV_DIR
    
    info "升級 pip..."
    $VENV_DIR/bin/pip install --upgrade pip -q
    
    info "安裝 Python 依賴 (這可能需要幾分鐘)..."
    $VENV_DIR/bin/pip install -r $INSTALL_DIR/requirements.txt -q
    
    # 設定權限
    chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
    chmod 755 $INSTALL_DIR
    
    success "應用程式安裝完成"
}

# 創建 systemd 服務
create_systemd_service() {
    info "創建 systemd 服務..."
    
    cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=PaddleOCR Web Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python -m uvicorn app:app --host 0.0.0.0 --port $SERVICE_PORT
Restart=always
RestartSec=10
StandardOutput=append:$INSTALL_DIR/logs/service.log
StandardError=append:$INSTALL_DIR/logs/error.log

# 資源限制
LimitNOFILE=65536
MemoryMax=4G

# 安全設定
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    # 重新載入 systemd
    systemctl daemon-reload
    
    success "systemd 服務創建完成"
}

# 啟動服務
start_service() {
    info "啟動服務..."
    systemctl enable $SERVICE_NAME
    systemctl start $SERVICE_NAME
    
    # 等待服務啟動
    sleep 3
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        success "服務啟動成功"
    else
        warning "服務可能未正常啟動，請檢查日誌"
        journalctl -u $SERVICE_NAME --no-pager -n 20
    fi
}

# 顯示安裝資訊
show_info() {
    # 取得 IP
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║              安裝完成！                                  ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo -e "${GREEN}服務資訊:${NC}"
    echo "  • 服務名稱: $SERVICE_NAME"
    echo "  • 安裝目錄: $INSTALL_DIR"
    echo "  • 服務埠號: $SERVICE_PORT"
    echo ""
    echo -e "${GREEN}存取位址:${NC}"
    echo "  • 網頁介面: http://$LOCAL_IP:$SERVICE_PORT"
    echo "  • API 文檔: http://$LOCAL_IP:$SERVICE_PORT/api/docs"
    echo "  • 健康檢查: http://$LOCAL_IP:$SERVICE_PORT/api/health"
    echo ""
    echo -e "${GREEN}常用指令:${NC}"
    echo "  • 查看狀態: systemctl status $SERVICE_NAME"
    echo "  • 重啟服務: systemctl restart $SERVICE_NAME"
    echo "  • 停止服務: systemctl stop $SERVICE_NAME"
    echo "  • 查看日誌: journalctl -u $SERVICE_NAME -f"
    echo ""
    echo -e "${YELLOW}注意事項:${NC}"
    echo "  • 首次執行 OCR 時會下載模型檔案，可能需要等待"
    echo "  • 建議在防火牆開放 $SERVICE_PORT 埠"
    echo "  • 日誌位於 $INSTALL_DIR/logs/"
    echo ""
}

# 主程式
main() {
    # 解析參數
    FROM_GITHUB="false"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --github)
                FROM_GITHUB="true"
                shift
                ;;
            --repo)
                GITHUB_REPO="$2"
                shift 2
                ;;
            --branch)
                GITHUB_BRANCH="$2"
                shift 2
                ;;
            --port)
                SERVICE_PORT="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                warning "未知參數: $1"
                shift
                ;;
        esac
    done
    
    show_banner
    check_root
    
    info "開始安裝 PaddleOCR Web Service..."
    if [ "$FROM_GITHUB" = "true" ]; then
        info "安裝來源: GitHub ($GITHUB_REPO @ $GITHUB_BRANCH)"
    else
        info "安裝來源: 本地目錄"
    fi
    echo ""
    
    install_system_deps
    create_service_user
    install_application
    create_systemd_service
    start_service
    show_info
}

# 執行
main "$@"
