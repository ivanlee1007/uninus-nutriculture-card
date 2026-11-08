> 現行來源狀態（2026-11-08）：P1–P3、P4a／P4b／P4c與P5a首片已完成軟體來源交付。P5a交付基線：Backend `4a08e615bf1949ecbeea37fdba4696c5bf8d3062`（CI `42458123964`）、Card `3eaa78c55043598fd4bc666c8ef432b8870d6701`（CI `42458104719`）；獨立SPEC／品質、出版等價與遠端產物核驗已完成。 本提交新增P5b同槽pH／EC／液位歷史，功能、真Recorder整合與獨立SPEC／品質兩審已完成，B-01已關閉；出版與hosted CI以本提交的實際核驗結果為準，不冒用P5a基線CI。P5b唯一修補批次1/1已用，不重置舊額度。P5a joint-review修補1/1與具名read-side revocation修補1/1已用；P4c 4/4、P3 5/5結案不重置。完整P5十二組保留，部分已交付不等於全組完成；未實機／HACS／tag／release／部署。

# 測試與證據

## 最終結果

`docs/evidence/final-package-gate/` 是本次最後的完整 gate，直接載入根目錄交付 JS：

- Node **18.6.0**：語法檢查通過、**5 個單元探測通過，0 fail／skip／cancel**。
- Python **3.14.5** 的專案 venv、Playwright **1.56.0**、真正 Chromium **156.0.8078.4**：**16 個瀏覽器測試通過，無跳過**，最後一輪 browser runner 回報 9.899 秒。
- 三個 viewport 的卡片均展開全部參數：

  | viewport | 實測卡片寬度 | 最大橫向 overflow | 超出 viewport 的節點 |
  | ---: | ---: | ---: | ---: |
  | 320 | 304 | 0 | 0 |
  | 768 | 752 | 0 | 0 |
  | 1200 | 1184 | 0 | 0 |

  頁面左右各 8px fixture padding；不是把 304px 誤稱為 320px 卡片。幾何量測包含文件、卡片、tiles、十項參數、輸入及按鈕。另有 300 字元無斷行標題／原因碼的 overflow 回歸。
- Screenshot：`docs/evidence/final-package-gate/browser/card-{320,768,1200}.png`，皆明示模擬資料，非 live HA。
- Bundle：**16,322 bytes**；SHA-256：

  ```text
  e4b7d29962e10bbd9139a29923e2e4e35f21017714d04bb61474f5e40ea9ec25
  ```

  最終 manifest 中的 production／test／demo／package／CI 檔案與精確 snapshot 及目前工作檔均比對相符。未 stage／commit，因此不宣稱 Git blob／正式發行檔的 provenance。

## 重跑

只需 Python、Node 和測試用 Playwright；交付 JS 本身完全無依賴。一般環境：

```sh
python -m venv .venv
# 啟用虛擬環境後：
python -m pip install -r requirements-test.txt
python -m playwright install chromium
npm test
```

本機 Python 缺 pip，實際使用以下等效準備命令：

```sh
uv venv .venv
uv pip install --python .venv/Scripts/python.exe playwright==1.56.0
```

本次真正執行的最終 package 命令，由 Python subprocess 啟動 `npm.cmd` 避免 Git-Bash Node stdin/TTY wrapper 問題；等效 shell 表示：

```sh
CHROMIUM_EXECUTABLE='C:/Users/ivanl/AppData/Local/ms-playwright/chromium-1248/chrome-win64/chrome.exe' \
  npm test -- --evidence docs/evidence/final-package-gate
```

該目錄已存在，**勿覆寫歷史證據**。平常 `npm test` 自動建立新的 `test-results/gate/<uuid>/`；指定 `--evidence` 時使用新路徑。`CHROMIUM_EXECUTABLE` 僅用來選擇已安裝的瀏覽器，CI 不設定它而使用 Playwright 配對下載的 Chromium。`NODE` 可明確指定 native Node 執行檔。

也可直接執行：

```sh
.venv/Scripts/python.exe tests/check.py --evidence test-results/review-001
```

Linux venv 路徑為 `.venv/bin/python`。`tests/check.py` 依序執行 native Node `--version`／`--check`／prototype 單元探測與 Python browser suite，傳遞實際 child returncode，並核對註冊／執行 case 數。原始 stdout/stderr 不裁切，保存 child command、hash 與檔案快照。Windows timeout 使用 owned PID 的 `taskkill /T`，不終止其他程序。

以下為早期驗證歷史（非現行P4b／P4c交付狀態）：以下為早期驗證歷史（非現行P4b／P4c交付狀態）：Node 18.6.0 的 `node:test` 會輸出原生 **ExperimentalWarning**；原始記錄完整保留。這不是測試失敗，也沒有隱藏 warning。CI 定義使用 Node 22／Python 3.13 與 Chromium；**尚未執行遠端 CI，不能把本機 Node 18／Python 3.14 的結果稱為 CI 版本驗收**。

## TDD 原始鏈

每個 `tests/record_run.py <唯一標籤> [測試選擇]` 都在執行前保存當時 source/test 完整 bytes 與 SHA-256，之後保存真實結果。下列 RED 為 assertion 的功能失敗，不是 import/module-not-found：

| 證據目錄前綴 | RED 觀察 | GREEN |
| --- | --- | --- |
| 01-readings | 卡片沒有監測標題／安全說明／讀值 | 顯示來源讀值及安全文字；惡意 title 為文字 |
| 02-save | 尚無十項參數列 | 原生 metadata、明確單項儲存與正確 service payload |
| 03-tank | 切換 tank 後仍殘留 5.55 草稿 | 新 tank 使用自身值，舊草稿不送出 |
| 04-lifecycle-red-retry | 舊 flight 鎖住新 tank 的輸入 | 世代／operation fence 隔離完成結果 |
| 05-mapping | 舊草稿實際送至新 Number 映射 | 映射變更清除舊草稿，不送出 |
| 06-editor | picker 未登錄 | picker／GUI 編輯器／config helper 可用 |
| 07-flight | 相同設定／重新掛載時發出第二個同目標呼叫 | transport lock 保留至 Promise 完成 |
| 09-warning | 參數不可用只藏在收合區內 | 主卡片提示參數無法儲存 |

`08-supplementary-browser`、Node prototype 單元探測及後續額外 coverage 是已綠實作的補充驗證，**不冒稱新的 RED**。瀏覽器測試涵蓋十個實際 mapping、明確送出、雙擊、拒絕保留、Entity/config/disconnect／同目標未完成鎖、遙測中的節點焦點與 trusted keyboard 游標連續性、缺失/active/schema/Number/metadata、安全文字、未知狀態、原生編輯器事件與未知鍵、XSS 字串、離線 demo 無外網請求與響應式幾何。

最初 `04-lifecycle-red/` 發生測試 harness timeout：Playwright 將回傳函式的 assignment expression 視為可呼叫的 evaluation，等待尚未解決的 Promise。當時 runner 在 timeout 前未寫出 child log，**該次沒有完整原始 stdout，不能算 RED**；保留原始快照與說明，修正 evaluation 為無回傳的 block，並改用 file-backed child log／owned tree timeout 後，在 `04-lifecycle-red-retry/` 取得真正 behavioral RED，後續 GREEN 通過。

早期 screenshot gate 的 summary toggle 讓 768px fixture 保持收合；最終測試已明確將三個寬度全部 `open=true` 並重設模擬來源，早期證據不覆寫，不拿來宣稱全寬展開驗收。

## 範圍限制

- browser suite 使用模擬 `hass` transport；離線 HTML demo 的寫入只改記憶體。沒有替代／偽造 HA backend 原生回應作為整合成功證據。
- 未連線真實 HA、未檢查其 service 權限／狀態一致性／真實後端、未操作任何硬體。
- 真正 HA 的 dashboard Add Card 宿主流程、HACS 安裝、私有 GitHub 存取、正式 CI、發布與部署均待授權後另行驗收。
- 沒有新增任意 backend custom service。群組原子參數儲存明確延期 P3。

## P4c現行portable驗收

Card canonical gate執行unit14及DOM38＋16＋21＋16＝91；P4c既有16 cases正式註冊，沒有wrapper或重複計數。Backend永久suite為553／82；完整gate是R4歷史來源驗收，本出版prep只重跑Card canonical及portable真join，不冒稱再次執行553。

Backend與Card使用明確sibling checkout；`python -B tools/p4c_native_join.py --output <owned-output>` 後執行 `python -B tools/p4c_native_verify.py --output <owned-output>`。可用`--card-repo`指定Card；`P4C_CARD_PYTHON`指定browser SDK，預設當前Python。Chromium可由Playwright安裝或`CHROMIUM_EXECUTABLE`明確指定。只用loopback假硬體；不讀現場auth。CI pins保持Ubuntu24.04／Backend Python3.14／Card Python3.13／Node22，本機Node18.6非hosted驗收。
