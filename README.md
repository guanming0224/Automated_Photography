# 自動拍照 GUI — 多相機自動化拍攝系統

## 專案介紹

基於 PySide6 + OpenCV 的多相機自動拍照應用，支援同時控制最多 5 台相機進行定時拍攝。
存檔影像直接取自相機原始 frame，畫質等同相機本身能力，不經 GUI 預覽路徑處理。

## 專案結構

```
auto_camera_gui/
├── main.py                  # 應用主入口
├── requirements.txt         # 依賴套件清單
├── CLAUDE.md               # AI 協作說明文件
├── README.md               # 本文件
├── core/
│   ├── camera.py           # 相機執行緒、非同步拍攝邏輯
│   └── config.py           # 所有常數集中管理
└── ui/
    ├── widgets.py           # 自訂元件（CameraCard、圓形進度等）
    └── main_window.py      # 主窗口、存檔執行緒
```

## 功能特性

- 自動偵測可用相機（最多 5 台）並以最高解析度串流
- 多相機同步拍攝，逾時保護（單台卡住不影響其他相機）
- 存檔使用相機原始畫質，不 resize、不裁切
- 右側預覽面板：2 欄 Grid，每張卡片含即時預覽 + 最後拍攝照片
- 圓形進度指示器：外圈顯示拍攝進度、內圈顯示倒數進度
- 暫停 / 繼續 / 結束拍攝控制
- 自訂存檔路徑與命名模板
- 控制面板與預覽面板皆可捲動，適合小螢幕

## 安裝與執行

### 1. 建立虛擬環境（建議）

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 執行應用

```powershell
python main.py
```

## 使用方法

1. **選擇相機**：勾選「相機選擇」區中要使用的相機
2. **設定存檔位置**：點擊「選擇資料夾」，或直接在路徑欄輸入
3. **自訂命名模板**：
   - `{camera}` → 相機索引（0、1、2…）
   - `{index:04d}` → 拍攝輪次，4 位補零（0001、0002…）
   - 副檔名決定格式，支援 `.jpg`、`.png`
4. **設定拍攝參數**：
   - 每台照片張數：總共拍幾輪
   - 間隔時間（秒）：每輪之間的等待時間，支援小數（如 0.5 s）
5. **開始拍攝**：點擊「開始拍攝」
6. **拍攝控制**：
   - 暫停：暫停倒數，再點一次繼續
   - 結束：立即終止流程，已拍的照片已存檔不受影響

## 打包成可執行檔

```powershell
# 單檔模式（方便分發）
pyinstaller --windowed --onefile --name "自動拍照GUI" main.py

# 資料夾模式（啟動速度較快）
pyinstaller --windowed --name "自動拍照GUI" main.py
```

產出在 `dist/` 資料夾。

## 模組說明

### core/config.py
所有常數集中於此，包含視窗尺寸、相機參數、UI 配色、拍攝預設值。
需要調整任何行為數值時，從這裡改。

### core/camera.py

| 類別 / 函式 | 說明 |
|---|---|
| `CameraThread` | 相機串流執行緒，以最高解析度串流；分別發出 `frame_ready`（GUI 預覽）與 `capture_ready`（存檔用原始 frame）兩個信號 |
| `open_camera()` | 優先用 `CAP_DSHOW` 開啟（Windows），失敗則 fallback |
| `find_available_cameras()` | 掃描 index 0–4，回傳可用相機清單 |

### ui/widgets.py

| 類別 | 說明 |
|---|---|
| `AspectRatioLabel` | 維持指定寬高比的 QLabel，用於相機預覽 |
| `CameraCard` | 單台相機卡片，含即時預覽、原始/最高解析度標籤、最後拍攝照片 |
| `CircularProgressWidget` | 雙環圓形進度，外圈=拍攝進度，內圈=倒數進度 |

### ui/main_window.py

| 類別 | 說明 |
|---|---|
| `AutoCameraGUI` | 主窗口，管理所有相機執行緒、拍攝狀態、UI 更新 |
| `SaveBatchThread` | 非同步存檔執行緒，避免 I/O 阻塞主執行緒 |

## 常見問題

**相機無法偵測**
- 確認相機已連接且未被其他程式佔用
- 重新啟動應用

**拍攝後找不到照片**
- 確認「存檔位置」路徑有效
- 檢查磁碟空間

**預覽畫面和存檔畫質不同**
- 屬於正常現象。預覽為了效能會縮放顯示，實際存檔直接取自相機原始 frame，畫質等同相機硬體能力。

## 技術棧

| 套件 | 用途 |
|---|---|
| Python 3.8+ | 執行環境 |
| PySide6 ≥ 6.0 | Qt6 GUI 框架 |
| OpenCV ≥ 4.5 | 相機控制、影像存檔 |
| PyInstaller ≥ 6.0 | 打包為可執行檔 |

## 更新日誌

### v1.1.0 (2026-05-21)
- 相機以最高解析度串流，存檔直接取原始 frame（無 resize/crop）
- 右側預覽改為 2 欄 Grid CameraCard（含即時預覽 + 最後拍攝照片）
- 控制面板與預覽面板加入 QScrollArea
- 相機最高解析度偵測移入 CameraThread，不阻塞主執行緒
- 修正關閉視窗時等待存檔執行緒完成
- 修正暫停狀態下不覆蓋狀態文字

### v1.0.0 (2026-04-19)
- 初始版本發佈
- 支援多相機同時拍攝
- 模組化代碼結構
