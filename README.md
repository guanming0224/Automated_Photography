# 自動拍照GUI - 自動化相機系統

## 項目介紹
一款基於 PySide6 + OpenCV 的多相機自動拍照應用，支援同時控制最多5台相機進行定時拍攝。

## 項目結構

```
auto_camera_gui/
├── main.py                  # 應用主入口
├── requirements.txt         # 依賴套件清單
├── README.md               # 本文件
├── core/                   # 核心模組
│   ├── __init__.py
│   ├── camera.py          # 相機控制邏輯
│   └── config.py          # 應用配置常數
├── ui/                     # UI模組
│   ├── __init__.py
│   ├── widgets.py         # 自訂UI組件
│   └── main_window.py     # 主窗口類
└── icons/                  # 應用圖標資源
```

## 功能特性

- ✅ 自動尋找可用相機設備（最多5台）
- ✅ 多相機同時拍攝
- ✅ 自訂拍攝參數（數量、間隔時間）
- ✅ 自訂存檔路徑與文件命名
- ✅ 實時相機預覽
- ✅ 倒數計時器顯示
- ✅ 圓形進度指示器
- ✅ 暫停/繼續/結束拍攝功能
- ✅ 顯示每台相機的最後拍攝照片

## 安裝與運行

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 執行應用

```bash
python main.py
```

## 打包成可執行文件

### 使用 PyInstaller 打包

```bash
# 單文件模式（推薦用於分發）
pyinstaller --windowed --onefile --name "自動拍照GUI" main.py

# 或文件夾模式（啟動速度更快）
pyinstaller --windowed --name "自動拍照GUI" main.py
```

生成的可執行文件會在 `dist/` 資料夾內。

## 模塊說明

### core/camera.py
- `CameraThread`: 相機線程類，負責實時取框和信號發送
- `open_camera()`: 開啟相機的工具函數
- `find_available_cameras()`: 掃描可用相機的函數

### core/config.py
集中管理應用配置，包括：
- 窗口尺寸
- 相機參數
- UI 配色方案
- 默認設置值

### ui/widgets.py
- `AspectRatioLabel`: 保持 16:9 寬高比的標籤
- `CircularProgressWidget`: 圓形進度顯示組件

### ui/main_window.py
- `AutoCameraGUI`: 主窗口類，包含所有業務邏輯

## 使用方法

1. **選擇相機**: 在「相機選擇」區勾選要使用的相機
2. **設置存檔位置**: 點擊「選擇資料夾」確定照片保存位置
3. **自訂命名**: 編輯「命名模板」，可使用 `{camera}` 和 `{index:04d}` 變數
4. **拍攝設置**:
   - 每台照片張數：單次拍攝循環的照片數
   - 間隔時間：每張照片之間的時間間隔（秒）
5. **開始拍攝**: 點擊「開始拍攝」
6. **控制**:
   - 暫停拍攝：暫時停止，點擊「繼續拍攝」恢復
   - 結束拍攝：完全終止拍攝流程

## 常見問題

### 相機無法識別
- 確保相機已正確連接
- 檢查是否有其他應用佔用相機
- 嘗試重啟應用

### 拍攝效果不佳
- 調整相機角度和光線
- 確保相機有足夠的初始化時間
- 檢查相機是否支援 16:9 寬高比

## 維護與擴展

### 添加新功能
1. 如果涉及相機控制，修改 `core/camera.py`
2. 如果涉及配置，修改 `core/config.py`
3. 如果涉及 UI，修改 `ui/widgets.py` 或 `ui/main_window.py`
4. 在 `main.py` 保持簡潔

### 修改配色方案
編輯 `core/config.py` 中的顏色常數即可全局修改。

## 技術棧

- **Python 3.8+**
- **PySide6**: Qt for Python GUI 框架
- **OpenCV**: 相機與影像處理
- **PyInstaller**: 打包成可執行文件

## 許可證

Free to use

---

## 更新日誌

### v1.0.0 (2026-04-19)
- 初始版本發佈
- 支援多相機同時拍攝
- 模組化代碼結構
