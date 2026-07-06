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

**重跑測試、不重燒 image** —— 加 `--skip-flash`，跳過下載+燒入，直接對現在 adb 連著的裝置跑：

```bash
python autotest.py --skip-flash                     # 不燒，跑全部測項
python autotest.py --skip-flash --tests sensors     # 不燒，只跑感測器
python autotest.py --skip-flash --tests boot,serdes,sensors
run.bat --skip-flash --tests sensors                # Windows launcher（跑完停住顯示結果）
./run.sh --skip-flash --tests serdes                # Linux/WSL/macOS launcher
```
可反覆重跑、換 `--tests` 組合都不會重燒；多台裝置加 `--serial <序號>`。（想重跑功能測又不被
開機健檢 gating，就別選 `boot`，例如只 `--tests sensors`。）

**看測試過程的 log** —— 加 `-v` / `--verbose`，會把每個 `adb shell` 指令與其輸出即時印出來
（`[sh] <cmd>` 後接 `| <每行輸出>`、`-> rc=`），console 即時看得到、也一併寫進 `_ut_work/logs/`：

```bash
python autotest.py --skip-flash --tests sensors -v
run.bat --skip-flash --tests serdes --verbose
```

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
`--tests` / `-v`/`--verbose`（即時印指令與輸出）/
`--boot-timeout` / `--fastboot-wait` / `--flash-timeout`。

離開碼：全部 PASS → `0`，否則 `1`。

## 選測項（`--tests`）

不給或給 `all` 就跑全部；否則用**逗號**列出要跑的項目（key / 別名 / case-id 皆可），依註冊順序執行：

| key | 別名 | 測什麼 |
|-----|------|--------|
| `boot` | `boot_health` | 開機健檢（critical，失敗會 SKIP 其餘）|
| `serdes` | `lslink` / `Platform_SerDes.GZI3` | SerDes/LSLink 一測項：`cat /sys/bus/i2c/devices/9-0020/ping`==`ok`（需 root）→`switch golden`→`flashid main/sub`(LS 4MiB W25Q32JW)+`main-hs/sub-hs`(HS 16MiB W25Q128JW)→`switch feature`→`version main/sub`==`0x13` |
| `sensors` | `sensor` / `Platform_Sensor.GZI3` | 感測器一測項（需 root，SSC `see` 工具）：IMU whoami(accel=`lsm6dsv`)/streaming/selftest(accel+gyro，`test_type` HW×2 + `test_passed:1`)、Mag whoami(`bmm350`)/streaming/selftest、ALS whoami(`tsl2522`) + lux（**互動**：提示遮光/照光各讀一次，驗 `valid=1` 且暗 lux<亮 lux；無 tty 時退回自動判 `valid=1`+數值、跳過明暗比較） |
| `key` | `keypad` / `Platform_Keypad.GZI3` | POWER 鍵測試（**互動**）：提示後擷取 `getevent`，驗證有 KEY_POWER 按下(`0001 0074 00000001`)+放開(`...00000000`)。**需人在現場按鍵**；非互動環境（mail 觸發、無 tty）會自動 SKIP 不 FAIL |
| `camera` | `optical_camera` / `Optical_Camera.GZI3` | 相機模組（需 root+remount，**中途會 `adb reboot` 一次**）：套用 `enableNCSService=FALSE` override→stop camera-provider→`nativehaltest --gtest_filter=CameraModuleTest.TestNumberOfCamera`，驗 gtest `[≥1 PASSED] and [0 FAILED]` |

```bash
python autotest.py --tests serdes            # 只跑 SerDes/LSLink
python autotest.py --tests sensors           # 只跑感測器
python autotest.py --tests boot,serdes,sensors   # 開機健檢 + 兩組功能測
python autotest.py --skip-flash --tests sensors  # 不燒，只跑感測器測項
```

未知的 key 會直接報錯（列出可用清單），且在**燒入前**就驗證，不會白燒一輪。
`lslink_cli` 名稱與 ping 節點路徑在 `config.LSLINK_CLI` / `config.SERDES_PING_NODE`。

**從 mail 巨集選測項**：Outlook 按鈕觸發時會跳一個**勾選視窗**（預設名 `UserForm1`，列出 `boot` /
`serdes` / `sensors` / `key` 供打勾，**預設只勾 `boot`**、Run/Cancel），選擇經 `run_on_mail.py --tests` 一路傳到
`autotest.py`。視窗還有一個 **Test only（skip download+flash）** 勾選——勾了就帶
`run_on_mail.py --test-only`→轉成 `autotest.py --skip-flash --verbose`（**test only 會自動開 `-v`**，
只對現有 build 跑測試、不重燒，並即時顯示指令與輸出）。巨集需安裝兩塊：`mail_trigger/outlook_macro.vba`（標準 Module）＋
`mail_trigger/outlook_frmTests.vba`（Insert > UserForm、**沿用預設名 `UserForm1`（不用改名）**，按 F7 把
此檔貼進該表單的程式碼視窗；勾選框由程式碼動態建立，免拉控制項、免開「信任 VBA 專案物件模型」）。

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
  test_serdes.py       SerDes/LSLink 單測項（ping + flashid/switch/version）
  test_sensors.py      感測器單測項（IMU/Mag whoami+streaming+selftest、ALS）
  test_keys.py         POWER 鍵測項（互動；getevent 擷取按鍵事件）
  test_camera.py       相機測項（remount+reboot→override→nativehaltest gtest）
```

## 擴充

- **換燒入方式**（EDL / QFIL / python-fastboot）：在 `core/flasher.py` 加一個 `Flasher` 子類，實作 `flash(image_dir, device)`，在 `autotest.py` 換掉即可。
- **換下載方式**（HTTP / scp）：加一個 `Downloader` 子類，實作 `fetch() -> image_dir`。
- **加測試**：在 `tests/` 新增一檔，寫 `Test` 子類（`name`、`check(device)->(ok, detail)`；要擋後續就 `critical=True`），再加進 `autotest.py` 的 `build_tests()`。

## License

MIT — 見 [LICENSE](LICENSE)。
