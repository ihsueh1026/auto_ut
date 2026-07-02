# mail_trigger — 選中 build 信、按鈕手動觸發 autotest（範例）

**目前為手動模式**：你選中（或開啟）一封「Build Successfully」信，按 Outlook 上的按鈕 →
從內文解析出這次的 build `.zip` UNC 路徑 → 呼叫 `autotest.py --build <路徑>`。
純標準庫、**不動現有框架**，不會在新信到達時自動燒機。

```
mail_trigger/
  parser.py         從主旨/內文抽 build .zip 路徑（處理軟換行、.zip.zip、截斷目錄路徑）
  run_on_mail.py    共用入口：抽路徑 + 啟動 autotest（--manual 跳過白名單/去重）
  outlook_macro.vba Outlook 按鈕巨集：對「選中的信」觸發（含確認框、視窗留著）
  test_msg.py       離線用 .msg 驗證（不需 Outlook、不需 pip）
```

## 資料流

```
選中信 → 按按鈕 → 確認框 ──► subject + body + EntryID ──► run_on_mail.py --manual
                                                            │ 抽路徑
                                                            ▼
                                          python autotest.py --build <path>
                                          （結果視窗用 cmd /k 留著）
```

邏輯集中在 `run_on_mail.py`（Python），觸發來源只負責「把信的 subject/body/id 交出來」，
所以**不開 Outlook 也能測**：

```bash
python parser.py                                   # 對照範例信自我測試（兩種解析都對）
echo "<body text>" | python run_on_mail.py --id X --subject "... Build Successfully" --dry-run
```

## 解析策略（parser.py）

1. **內文優先**（你選的方式）：抓內文**最後一個** `\\…\….zip`，去掉路徑中的軟換行，
   在第一個 `.zip` 截斷（信件會多寫成 `.zip.zip`）。
2. **主旨備援**：從主旨 token `GZI3.0068.PR1.2606291.F-000150` 重建
   → `<BASE>\GZI3.0068.PR1.2606291.F_000150\GZI3.0068.PR1.2606291.F.zip`
   （`-`→`_`；`BASE` 是 `parser.py` 裡的 `BUILD_BASE`，share 若搬家改這裡）。

> 針對你資料夾那封 `.msg` 實測過：內文 UTF-16LE、路徑被拆兩行、結尾 `.zip.zip`、
> 前面還有一條不含 `.zip` 的截斷目錄路徑——兩種策略都能還原出正確路徑。

## 在 Outlook 加按鈕（手動觸發）

1. Outlook → `Alt+F11` → 在左邊 Project 上按右鍵 → **插入(Insert) > 模組(Module)**。
   把 `outlook_macro.vba` 全部貼進那個**標準模組**（**不要**貼 `ThisOutlookSession`；
   放在 ThisOutlookSession 的巨集不會出現在按鈕清單）。
2. 改開頭兩個常數：`PY`（python.exe 路徑）、`RUN_ON_MAIL`（`run_on_mail.py` 路徑）。
3. 存檔、重開 Outlook（Trust Center 若提示，放行巨集）。
4. 把巨集掛成按鈕：`檔案 > 選項 > 快速存取工具列` → 上方下拉
   「**從下列位置選擇命令 = 巨集**」→ 選 `TriggerAutotestOnSelectedMail` → 加入 → 確定。
5. 用法：**在信件清單選中**那封 build 信（或雙擊開啟），按工具列上那顆按鈕 → 確認 → 開跑。

巨集作用在「當前開啟的信（Inspector）或清單第一封選中的信（Explorer）」，帶 `--manual`
呼叫 `run_on_mail.py`，結果用 `cmd /k` 開一個視窗顯示且**不會自動關閉**。

> 之後若要改回「新信自動觸發」，把巨集換成 `Application_NewMailEx` 事件、拿掉 `--manual`
> 即可（會啟用白名單 + 去重）。目前刻意不做自動。

## 去重與白名單（自動模式才用；手動 --manual 會略過）

- `run_on_mail.py` 的 `SUBJECT_MUST_CONTAIN`（主旨關鍵字）、`SENDER_ALLOW`（寄件者，空=不限）。
- 去重：已處理 msg-id 記在 `_ut_work/mail_seen.txt`，**啟動前**先標記，中途崩潰不會重觸發。
- **手動按鈕帶 `--manual`：跳過白名單與去重**（你既然刻意點選，就照做；仍要求成功解析出路徑）。
- 觸發前建議確認有 adb/fastboot 裝置在線。

## 離線解析 .msg（選用）

`.msg` 是 Outlook OLE 複合檔，純標準庫不易乾淨解析。要在**沒有 Outlook** 時直接讀 `.msg`
測試，可裝 `extract-msg`（`pip install extract-msg`）：

```python
import extract_msg
m = extract_msg.Message(r"...\Build Successfully.msg")
from run_on_mail import handle
handle(m.messageId or "test", m.subject, m.body, m.sender or "", dry_run=True)
```

線上觸發（VBA / IMAP / Graph）都能直接拿到 subject/body 文字，**不需要**解析 `.msg`。
