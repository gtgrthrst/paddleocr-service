# PaddleOCR Web Service

基於 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) 的 OCR 辨識服務，提供網頁介面與 REST API。

專為 **Proxmox VE Ubuntu CT** 環境設計。

## ✨ 功能特色

- 🖼️ **圖片辨識**: 支援 PNG, JPG, JPEG, BMP, GIF, WebP, TIFF 格式
- 📑 **PDF 辨識**: 支援多頁 PDF 文件
- 🌐 **網頁介面**: 現代化拖放上傳介面
- 🔌 **REST API**: 完整的 API 文檔與串接範例
- 📦 **批次處理**: 支援多檔案批次辨識
- 🚀 **高效能**: 基於 PaddleOCR 引擎

## 📋 系統需求

- Ubuntu 20.04 / 22.04 LTS (CT 環境)
- Python 3.8+
- 建議記憶體: 2GB 以上
- 建議儲存空間: 5GB 以上 (含模型)

## 🚀 快速安裝

### 方法一: 一鍵安裝 (推薦)

```bash
# 使用 curl
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/paddleocr-service/main/quick-install.sh | sudo bash

# 或使用 wget
wget -qO- https://raw.githubusercontent.com/YOUR_USERNAME/paddleocr-service/main/quick-install.sh | sudo bash
```

### 方法二: 從 GitHub 克隆安裝

```bash
# 1. 克隆倉庫
git clone https://github.com/YOUR_USERNAME/paddleocr-service.git
cd paddleocr-service

# 2. 執行安裝腳本
sudo chmod +x install.sh
sudo ./install.sh
```

### 方法三: 指定倉庫安裝

```bash
# 下載安裝腳本
curl -O https://raw.githubusercontent.com/YOUR_USERNAME/paddleocr-service/main/install.sh
chmod +x install.sh

# 從 GitHub 安裝 (可指定倉庫和分支)
sudo ./install.sh --github --repo YOUR_USERNAME/paddleocr-service --branch main
```

### 方法四: 手動安裝

```bash
# 1. 安裝系統依賴
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 \
    libxrender1 poppler-utils git

# 2. 克隆專案
git clone https://github.com/YOUR_USERNAME/paddleocr-service.git
cd paddleocr-service

# 3. 創建虛擬環境
python3 -m venv venv
source venv/bin/activate

# 4. 安裝 Python 依賴
pip install -r requirements.txt

# 5. 啟動服務
python app.py --host 0.0.0.0 --port 8000
```

## 🔧 安裝腳本參數

```bash
sudo ./install.sh [選項]

選項:
  --github          從 GitHub 克隆安裝
  --repo REPO       指定 GitHub 倉庫 (預設: YOUR_USERNAME/paddleocr-service)
  --branch BRANCH   指定分支 (預設: main)
  --port PORT       指定服務埠號 (預設: 8000)
  -h, --help        顯示說明
```

## 📡 API 使用

### 健康檢查

```bash
curl http://YOUR_HOST:8000/api/health
```

### OCR 辨識

```bash
# 上傳圖片進行辨識
curl -X POST "http://YOUR_HOST:8000/api/ocr" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_image.png"
```

### 批次辨識

```bash
curl -X POST "http://YOUR_HOST:8000/api/ocr/batch" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@image1.png" \
  -F "files=@image2.jpg"
```

### Python 範例

```python
import requests

# 單檔辨識
url = "http://YOUR_HOST:8000/api/ocr"
files = {"file": open("image.png", "rb")}
response = requests.post(url, files=files)
result = response.json()

print("辨識結果:")
print(result["full_text"])
print(f"處理時間: {result['processing_time']:.2f}s")
```

### JavaScript 範例

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://YOUR_HOST:8000/api/ocr', {
    method: 'POST',
    body: formData
});

const result = await response.json();
console.log(result.full_text);
```

## 📖 API 回應格式

```json
{
  "success": true,
  "filename": "example.png",
  "file_type": "image",
  "results": [
    {
      "text": "辨識出的文字",
      "confidence": 0.98,
      "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    }
  ],
  "full_text": "完整辨識文字\n第二行文字",
  "processing_time": 1.23,
  "timestamp": "2025-01-01T12:00:00"
}
```

## 🛠️ 服務管理

```bash
# 查看服務狀態
sudo systemctl status paddleocr

# 啟動服務
sudo systemctl start paddleocr

# 停止服務
sudo systemctl stop paddleocr

# 重啟服務
sudo systemctl restart paddleocr

# 查看即時日誌
sudo journalctl -u paddleocr -f

# 設定開機自動啟動
sudo systemctl enable paddleocr
```

## ⚙️ 設定說明

### 修改服務埠號

編輯 systemd 服務檔案:

```bash
sudo nano /etc/systemd/system/paddleocr.service
```

修改 `--port` 參數後重新載入:

```bash
sudo systemctl daemon-reload
sudo systemctl restart paddleocr
```

### 環境變數

| 變數名稱 | 說明 | 預設值 |
|---------|------|--------|
| PORT | 服務埠號 | 8000 |

## 📁 目錄結構

```
/opt/paddleocr-service/
├── app.py              # 主程式
├── requirements.txt    # Python 依賴
├── templates/          
│   └── index.html      # 網頁介面
├── static/             # 靜態檔案
├── uploads/            # 暫存上傳檔案
├── logs/               # 日誌目錄
└── venv/               # Python 虛擬環境
```

## 🔧 疑難排解

### 問題: 服務無法啟動

```bash
# 檢查日誌
sudo journalctl -u paddleocr -n 50

# 手動測試
cd /opt/paddleocr-service
source venv/bin/activate
python app.py
```

### 問題: 記憶體不足

PaddleOCR 首次載入模型時需要較多記憶體。建議:

1. 增加 CT 記憶體配置至 2GB 以上
2. 或設定 swap:
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### 問題: PDF 處理失敗

確保已安裝 poppler-utils:

```bash
sudo apt install poppler-utils
```

## 📜 授權

本服務基於 Apache 2.0 授權的 PaddleOCR 建構。

## 🔗 相關連結

- [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR 文檔](https://paddlepaddle.github.io/PaddleOCR/)
- [FastAPI 文檔](https://fastapi.tiangolo.com/)

---

## 📤 上傳到 GitHub

如果你想將此專案上傳到自己的 GitHub:

### 1. 創建 GitHub 倉庫

在 GitHub 網站上創建新的倉庫，例如 `paddleocr-service`

### 2. 初始化並推送

```bash
cd paddleocr-service

# 初始化 Git
git init
git add .
git commit -m "Initial commit: PaddleOCR Web Service"

# 添加遠端倉庫 (替換 YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/paddleocr-service.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

### 3. 更新安裝腳本中的倉庫位址

上傳後，記得修改以下檔案中的 `YOUR_USERNAME`:

- `install.sh` - 第 35 行的 `GITHUB_REPO`
- `quick-install.sh` - 第 20 行的 `GITHUB_REPO`
- `README.md` - 所有安裝指令中的位址

### 4. 在其他機器安裝

上傳完成後，就可以在任何 Ubuntu CT 中使用一鍵安裝:

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/paddleocr-service/main/quick-install.sh | sudo bash
```
