# P4a Card checkpoint

已讀 frozen P4A_CONTRACT / IMPLEMENTATION_PLAN，僅 Card writer 工作。產品 shipped copy 為 root uninus-nutriculture-card.js；docs/evidence snapshots 全不變。schema/header 不升版。

最早可操作路徑：有效 S5 + callWS + 4 versioned services → 配方區 Load → New/name/10 parameters → Save（catalog only，response authority）。先寫真 Chromium UI 行為測試並保存 source/test bytes + command/raw child exit 至 sibling `_card-work`，再實作。

範圍為參數配方，不含硬體/流程/安全設定；完整 P4/P5 保留，無發布、安裝、網路、現場 HA、Git mutation。Backend peer 不讀其開發中檔案。

最終 checkpoint：Card candidate 已實作完整配方 UI。`npm test` 真通過 Node13、legacy browser38、新 browser11，零skip；raw/TAP/source/test bytes在 `../_card-work/14-npm-final`。JS SHA256 `b78b5057c02ada12ee5ee9c107b129275126d6e465a9d7f7e71ef6865cb0eb2a`。RED鏈及一筆harness timeout與失敗中間runs完整記於 HANDOFF；registered Core joint 留 parent，未發布。