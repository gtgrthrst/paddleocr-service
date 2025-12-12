#!/usr/bin/env python3
"""
PaddleOCR Web Service
=====================
基於 PaddleOCR 的 OCR 辨識服務，提供網頁介面與 REST API
適用於 Proxmox VE Ubuntu CT 環境部署
"""

import os
import uuid
import json
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 FastAPI
app = FastAPI(
    title="PaddleOCR 辨識服務",
    description="基於 PaddleOCR 的文字辨識 API 服務，支援圖片與 PDF 檔案",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 靜態文件與模板
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# 上傳目錄
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 允許的檔案類型
ALLOWED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
ALLOWED_PDF_EXTENSIONS = {'.pdf'}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_PDF_EXTENSIONS

# OCR 引擎 (延遲載入)
_ocr_engine = None
_structure_engine = None

def get_ocr_engine():
    """取得或初始化 OCR 引擎"""
    global _ocr_engine
    if _ocr_engine is None:
        logger.info("初始化 PaddleOCR 引擎...")
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        logger.info("PaddleOCR 引擎初始化完成")
    return _ocr_engine

def get_structure_engine():
    """取得或初始化 PP-StructureV3 引擎 (用於 PDF 解析)"""
    global _structure_engine
    if _structure_engine is None:
        logger.info("初始化 PP-StructureV3 引擎...")
        try:
            from paddleocr import PPStructureV3
            _structure_engine = PPStructureV3(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
            )
            logger.info("PP-StructureV3 引擎初始化完成")
        except ImportError:
            logger.warning("PP-StructureV3 不可用，PDF 將使用基本 OCR 處理")
            _structure_engine = False
    return _structure_engine

# ============== Pydantic Models ==============

class OCRResult(BaseModel):
    """OCR 辨識結果"""
    text: str
    confidence: float
    bbox: List[List[float]]

class OCRResponse(BaseModel):
    """OCR API 回應"""
    success: bool
    filename: str
    file_type: str
    results: List[OCRResult]
    full_text: str
    processing_time: float
    timestamp: str

class HealthResponse(BaseModel):
    """健康檢查回應"""
    status: str
    version: str
    ocr_ready: bool
    timestamp: str

class ErrorResponse(BaseModel):
    """錯誤回應"""
    success: bool = False
    error: str
    detail: Optional[str] = None

class TableResponse(BaseModel):
    """表格轉換回應"""
    success: bool
    csv_content: str
    markdown_table: str
    row_count: int
    col_count: int

# ============== Helper Functions ==============

def validate_file(filename: str) -> tuple[bool, str]:
    """驗證上傳的檔案"""
    if not filename:
        return False, "未提供檔案名稱"
    
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"不支援的檔案格式: {ext}。支援格式: {', '.join(ALLOWED_EXTENSIONS)}"
    
    return True, ext

def process_image_ocr(image_path: str) -> List[Dict[str, Any]]:
    """處理圖片 OCR"""
    ocr = get_ocr_engine()
    result = ocr.predict(input=image_path)
    
    ocr_results = []
    
    # PaddleOCR 3.x 返回格式處理
    for res in result:
        # 調試：記錄返回的屬性
        logger.info(f"OCR result type: {type(res)}, attributes: {dir(res)}")
        
        # 嘗試不同的屬性名稱 (PaddleOCR 3.x)
        texts = None
        scores = None
        boxes = None
        
        # 方式 1: rec_texts (PaddleOCR 3.x)
        if hasattr(res, 'rec_texts'):
            texts = res.rec_texts
            scores = getattr(res, 'rec_scores', [1.0] * len(texts))
            boxes = getattr(res, 'dt_polys', [[]] * len(texts))
        
        # 方式 2: 直接訪問 text 屬性
        elif hasattr(res, 'text'):
            texts = [res.text] if isinstance(res.text, str) else res.text
            scores = [getattr(res, 'score', 1.0)]
            boxes = [getattr(res, 'box', [])]
        
        # 方式 3: 字典格式
        elif isinstance(res, dict):
            if 'rec_texts' in res:
                texts = res['rec_texts']
                scores = res.get('rec_scores', [1.0] * len(texts))
                boxes = res.get('dt_polys', [[]] * len(texts))
            elif 'text' in res:
                texts = [res['text']]
                scores = [res.get('score', 1.0)]
                boxes = [res.get('box', [])]
        
        # 方式 4: 嘗試 json() 方法
        elif hasattr(res, 'json'):
            try:
                data = res.json()
                logger.info(f"OCR result json: {data}")
            except:
                pass
        
        # 方式 5: 嘗試 __dict__
        if texts is None and hasattr(res, '__dict__'):
            logger.info(f"OCR result __dict__: {res.__dict__}")
            d = res.__dict__
            if 'rec_texts' in d:
                texts = d['rec_texts']
                scores = d.get('rec_scores', [1.0] * len(texts))
                boxes = d.get('dt_polys', [[]] * len(texts))
        
        # 處理找到的結果
        if texts:
            for i, text in enumerate(texts):
                if text:  # 過濾空文字
                    score = scores[i] if i < len(scores) else 1.0
                    bbox = boxes[i] if i < len(boxes) else []
                    ocr_results.append({
                        'text': str(text),
                        'confidence': float(score) if score else 1.0,
                        'bbox': bbox.tolist() if hasattr(bbox, 'tolist') else (list(bbox) if bbox else [])
                    })
    
    logger.info(f"OCR 辨識完成，共 {len(ocr_results)} 個結果")
    return ocr_results

def process_pdf_ocr(pdf_path: str) -> List[Dict[str, Any]]:
    """處理 PDF OCR"""
    structure = get_structure_engine()
    
    if structure and structure is not False:
        # 使用 PP-StructureV3 處理 PDF
        result = structure.predict(input=pdf_path)
        ocr_results = []
        for res in result:
            if hasattr(res, 'text_contents'):
                for text in res.text_contents:
                    ocr_results.append({
                        'text': text,
                        'confidence': 1.0,
                        'bbox': []
                    })
        return ocr_results
    else:
        # 將 PDF 轉換為圖片後處理
        try:
            import pdf2image
            images = pdf2image.convert_from_path(pdf_path)
            all_results = []
            
            for i, img in enumerate(images):
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name)
                    page_results = process_image_ocr(tmp.name)
                    for r in page_results:
                        r['page'] = i + 1
                    all_results.extend(page_results)
                    os.unlink(tmp.name)
            
            return all_results
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="PDF 處理需要安裝 pdf2image 和 poppler-utils"
            )

# ============== API Routes ==============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首頁 - 網頁介面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """API 健康檢查"""
    ocr_ready = False
    try:
        get_ocr_engine()
        ocr_ready = True
    except Exception:
        pass
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        ocr_ready=ocr_ready,
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/ocr", response_model=OCRResponse)
async def ocr_recognize(
    file: UploadFile = File(..., description="上傳圖片或 PDF 檔案"),
    output_format: str = Form(default="json", description="輸出格式: json, text, markdown")
):
    """
    OCR 文字辨識 API
    
    支援格式:
    - 圖片: PNG, JPG, JPEG, BMP, GIF, WebP, TIFF
    - 文件: PDF
    
    回傳辨識結果，包含文字內容、信心度與座標位置
    """
    start_time = datetime.now()
    
    # 驗證檔案
    valid, result = validate_file(file.filename)
    if not valid:
        raise HTTPException(status_code=400, detail=result)
    
    file_ext = result
    
    # 儲存上傳的檔案
    file_id = str(uuid.uuid4())
    temp_path = UPLOAD_DIR / f"{file_id}{file_ext}"
    
    try:
        # 寫入檔案
        content = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"處理檔案: {file.filename} ({file_ext})")
        
        # 執行 OCR
        if file_ext in ALLOWED_PDF_EXTENSIONS:
            ocr_results = process_pdf_ocr(str(temp_path))
            file_type = "pdf"
        else:
            ocr_results = process_image_ocr(str(temp_path))
            file_type = "image"
        
        # 組合完整文字
        full_text = '\n'.join([r['text'] for r in ocr_results])
        
        # 計算處理時間
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 建立回應
        results = [
            OCRResult(
                text=r['text'],
                confidence=r['confidence'],
                bbox=r.get('bbox', [])
            ) for r in ocr_results
        ]
        
        return OCRResponse(
            success=True,
            filename=file.filename,
            file_type=file_type,
            results=results,
            full_text=full_text,
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"OCR 處理錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR 處理失敗: {str(e)}")
    
    finally:
        # 清理暫存檔案
        if temp_path.exists():
            temp_path.unlink()

@app.post("/api/ocr/batch")
async def ocr_batch(
    files: List[UploadFile] = File(..., description="批次上傳多個檔案")
):
    """
    批次 OCR 辨識 API
    
    同時處理多個檔案，回傳所有結果
    """
    results = []
    
    for file in files:
        try:
            result = await ocr_recognize(file=file)
            results.append({
                "filename": file.filename,
                "success": True,
                "data": result.dict()
            })
        except HTTPException as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": e.detail
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
    
    return {
        "success": True,
        "total": len(files),
        "processed": len([r for r in results if r["success"]]),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/ocr/table")
async def ocr_to_table(
    file: UploadFile = File(..., description="上傳圖片或 PDF 檔案"),
):
    """
    OCR 辨識並轉換為表格格式
    
    自動偵測表格結構，回傳 CSV 和 Markdown 表格格式
    """
    start_time = datetime.now()
    
    # 驗證檔案
    valid, result = validate_file(file.filename)
    if not valid:
        raise HTTPException(status_code=400, detail=result)
    
    file_ext = result
    file_id = str(uuid.uuid4())
    temp_path = UPLOAD_DIR / f"{file_id}{file_ext}"
    
    try:
        content = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(content)
        
        # 執行 OCR
        if file_ext in ALLOWED_PDF_EXTENSIONS:
            ocr_results = process_pdf_ocr(str(temp_path))
        else:
            ocr_results = process_image_ocr(str(temp_path))
        
        # 轉換為表格
        csv_content, markdown_table, rows, cols = convert_to_table(ocr_results)
        
        return TableResponse(
            success=True,
            csv_content=csv_content,
            markdown_table=markdown_table,
            row_count=rows,
            col_count=cols
        )
        
    except Exception as e:
        logger.error(f"表格轉換錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"表格轉換失敗: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()

@app.post("/api/convert/table")
async def convert_text_to_table(
    text: str = Form(..., description="OCR 辨識的文字內容"),
    delimiter: str = Form(default="auto", description="分隔符: auto, tab, space, comma")
):
    """
    將 OCR 文字轉換為表格格式
    
    可指定分隔符或自動偵測
    """
    try:
        # 建立假的 OCR 結果
        lines = text.strip().split('\n')
        ocr_results = [{'text': line, 'confidence': 1.0, 'bbox': []} for line in lines if line.strip()]
        
        csv_content, markdown_table, rows, cols = convert_to_table(ocr_results, delimiter)
        
        return TableResponse(
            success=True,
            csv_content=csv_content,
            markdown_table=markdown_table,
            row_count=rows,
            col_count=cols
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"轉換失敗: {str(e)}")

def convert_to_table(ocr_results: List[Dict], delimiter: str = "auto") -> tuple:
    """將 OCR 結果轉換為表格"""
    import csv
    import io
    import re
    
    if not ocr_results:
        return "", "", 0, 0
    
    # 收集所有文字行
    lines = [r['text'] for r in ocr_results if r.get('text')]
    
    if not lines:
        return "", "", 0, 0
    
    # 自動偵測分隔符
    if delimiter == "auto":
        # 統計各種分隔符出現次數
        tab_count = sum(line.count('\t') for line in lines)
        comma_count = sum(line.count(',') for line in lines)
        space_count = sum(len(re.findall(r'\s{2,}', line)) for line in lines)
        
        if tab_count > len(lines) * 0.5:
            delimiter = '\t'
        elif comma_count > len(lines) * 0.5:
            delimiter = ','
        elif space_count > len(lines) * 0.3:
            delimiter = 'space'
        else:
            # 嘗試用多空格分割
            delimiter = 'space'
    
    # 解析表格
    table_data = []
    max_cols = 0
    
    for line in lines:
        if delimiter == 'space':
            # 用2個以上空格分割
            cells = re.split(r'\s{2,}', line.strip())
        elif delimiter == 'tab':
            cells = line.split('\t')
        elif delimiter == 'comma':
            cells = line.split(',')
        else:
            cells = line.split(delimiter)
        
        cells = [c.strip() for c in cells if c.strip()]
        if cells:
            table_data.append(cells)
            max_cols = max(max_cols, len(cells))
    
    if not table_data:
        return "", "", 0, 0
    
    # 補齊列數
    for row in table_data:
        while len(row) < max_cols:
            row.append("")
    
    # 生成 CSV
    csv_output = io.StringIO()
    writer = csv.writer(csv_output)
    writer.writerows(table_data)
    csv_content = csv_output.getvalue()
    
    # 生成 Markdown 表格
    md_lines = []
    if table_data:
        # 表頭
        md_lines.append("| " + " | ".join(table_data[0]) + " |")
        md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        # 資料行
        for row in table_data[1:]:
            md_lines.append("| " + " | ".join(row) + " |")
    
    markdown_table = "\n".join(md_lines)
    
    return csv_content, markdown_table, len(table_data), max_cols

@app.get("/api/formats")
async def get_supported_formats():
    """取得支援的檔案格式"""
    return {
        "image_formats": list(ALLOWED_IMAGE_EXTENSIONS),
        "document_formats": list(ALLOWED_PDF_EXTENSIONS),
        "all_formats": list(ALLOWED_EXTENSIONS)
    }

# ============== Error Handlers ==============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未預期的錯誤: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "內部伺服器錯誤",
            "detail": str(exc)
        }
    )

# ============== Main ==============

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PaddleOCR Web Service")
    parser.add_argument("--host", default="0.0.0.0", help="綁定的主機位址")
    parser.add_argument("--port", type=int, default=8000, help="服務埠號")
    parser.add_argument("--reload", action="store_true", help="開發模式 (自動重載)")
    
    args = parser.parse_args()
    
    logger.info(f"啟動 PaddleOCR 服務於 http://{args.host}:{args.port}")
    
    uvicorn.run(
        "app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
