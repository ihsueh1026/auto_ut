# auto_ut — SW6100 自動下載 / 燒入 / 測試框架

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/deps-stdlib%20only-brightgreen.svg)](#)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

給一個遠端 build 位置，自動 **下載 → 燒入 → 確認開機正常 → 接續跑測試 → 回報**（console + JSON）。
單機一台裝置、Python 3.10 純標準庫（無第三方相依）。Windows 用 `flash_all.bat`、Linux 用 `flash_all.sh`。

## 流程

```
UNC .zip ──下載/解壓──► image dir ──flash_all.bat──► 裝置重開
                                                        │
                                    boot_health(critical) ──► 其他測試 ──► 回報
```

1. **下載**：從 UNC 分享路徑複製 build `.zip`（同大小則沿用快取），解壓到 `_ut_work/images/<name>/`，用 `super.img` 定位 fastboot image 目錄。
2. **燒入**：`adb reboot bootloader` → 等 fastboot → 在 image 目錄執行燒錄腳本 → `fastboot reboot`。
   燒錄腳本**依 OS 自動選**：Windows = `flash_all.bat`（硬編 partition 清單）、Linux/macOS =
   `flash_all.sh`（廠商 XML 驅動版，讀 image 目錄的 `rawprogram0.xml`，需 `xmllint`；失敗即 `exit`）。
   失敗判定同時看 exit code 與輸出的 `FAILED`/`error:`/`flash failed`。
3. **開機健檢**（critical）：等 `sys.boot_completed==1`、確認 shell 有回應、掃 crash log。critical 若失敗，其餘測試標記 SKIP。
4. **回報**：console 摘要 + `_ut_work/results/result.json`（另存時間戳副本）。

## 用法

建議用 launcher 而非直接叫 python —— 它跑完會停住顯示結果（Windows 用 `run.bat` 的
`pause`，Linux/macOS/WSL 用 `run.sh`，互動終端會等你按 Enter），**視窗不會一結束就關**；
參數原樣傳入（例如 `run.bat --ask`、`./run.sh --skip-flash`）。
就算直接關視窗，結果仍存於 `_ut_work/results/result.json` 與 `_ut_work/logs/`。

```bash
run.bat                                     # Windows launcher（跑完停住顯示結果）
run.bat --ask
./run.sh                                    # Linux/macOS/WSL launcher（同上）
./run.sh --skip-flash
python autotest.py                          # 直接跑（視窗可能一結束就關）
python autotest.py --build \\host\path\CMBUILD     # 給目錄，自動挑最新 .zip
python autotest.py --build \\host\path\build.zip   # 給指定 .zip
python autotest.py --ask                    # 執行時互動輸入/貼上路徑
python autotest.py --local-dir D:\imgs\GZI3 # 已解壓好的 image 目錄
python autotest.py --skip-flash             # 不燒，只對現有裝置跑測試
python autotest.py --serial 1234abcd --force
```

**build 路徑**（`--build`）通常給**確切的 `.zip`**。每週 build 的資料夾名與檔名都會變，
所以每次更新 `config.BUILD_ZIP`（或用 `--build` / `--ask` 貼上）。若給的是**目錄**，只有在
該目錄剛好只有一支 `.zip` 時才會採用；有多支（build 目錄常含 target_files 等其他 zip）會
直接報錯要求指定確切 `.zip`，不會亂猜。`--ask` 可在執行時貼路徑（自動去除前後引號）。

主要參數：`--build` / `--ask` / `--local-dir` / `--work` / `--serial` /
`--skip-download`（沿用已下載的）/ `--skip-flash` / `--force` /
`--boot-timeout` / `--fastboot-wait` / `--flash-timeout`。

離開碼：全部 PASS → `0`，否則 `1`。

## 結構

```
autotest.py            主流程 / CLI
config.py              預設值（build 來源、逾時、工具路徑）
core/
  device.py            adb/fastboot 封裝 + 各種等待（皆 stdin=DEVNULL）
  downloader.py        Downloader ABC；UncZipDownloader / LocalDirDownloader
  flasher.py           Flasher ABC；FastbootBatFlasher（依 OS 跑 flash_all.bat / flash_all.sh）
  runner.py            依序執行測試 + critical gating
  reporter.py          console + result.json
tests/
  base.py              Test ABC + TestResult
  test_boot_health.py  開機健檢（critical）
```

## 擴充

- **換燒入方式**（EDL / QFIL / python-fastboot）：在 `core/flasher.py` 加一個 `Flasher` 子類，實作 `flash(image_dir, device)`，在 `autotest.py` 換掉即可。
- **換下載方式**（HTTP / scp）：加一個 `Downloader` 子類，實作 `fetch() -> image_dir`。
- **加測試**：在 `tests/` 新增一檔，寫 `Test` 子類（`name`、`check(device)->(ok, detail)`；要擋後續就 `critical=True`），再加進 `autotest.py` 的 `build_tests()`。

## License

MIT — 見 [LICENSE](LICENSE)。
