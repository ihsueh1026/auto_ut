"""Keypad (physical button) test - mirrors the Platform_Keypad list.

  Platform_Keypad.GZI3.001  button POWER test
    adb root; adb shell getevent; then press and release POWER.
    Expect the POWER key event on press (value 1) and release (value 0):
      /dev/input/event0: 0001 0074 00000001   (down)
      /dev/input/event0: 0001 0074 00000000   (up)

This is inherently INTERACTIVE - a human must press the button - so it prompts
you and captures getevent for a short window. In a non-interactive run (e.g. the
mail-triggered flow, no tty) it skips itself rather than failing.
"""
from __future__ import annotations
import re
import sys

import config
from tests.base import Test, SkipTest


class KeyTest(Test):
    name = "Platform_Keypad.GZI3"
    critical = False

    def __init__(self, code=None, capture_s=None):
        self.code = code or config.KEY_POWER_CODE       # POWER = 0074
        self.capture_s = capture_s or config.KEY_CAPTURE_S

    def check(self, device):
        if not sys.stdin.isatty():
            raise SkipTest("interactive test: needs a terminal (someone must press POWER)")

        device.root()          # spec: adb root first (getevent may need it)

        w = self.capture_s
        print(f"\n>>> [key] 準備測 POWER 鍵：接下來 {w} 秒內請【按一下並放開 POWER】。")
        try:
            input(">>> [key] 按 Enter 開始擷取…")
        except EOFError:
            raise SkipTest("no interactive stdin")
        print(f">>> [key] 擷取中… 現在請按 POWER 鍵（{w} 秒）")

        out = device.capture_shell("getevent", w)

        # type EV_KEY (0001), code KEY_POWER (0074), value 1 down / 0 up.
        t, c = config.KEY_EV_TYPE, self.code
        down = re.search(rf'{t}\s+{c}\s+0*1\b', out, re.I) is not None
        up = re.search(rf'{t}\s+{c}\s+0+\b', out, re.I) is not None
        # symbolic getevent (-l) fallback, in case a wrapper aliases it
        if not (down and up) and "KEY_POWER" in out.upper():
            up = up or "UP" in out.upper()
            down = down or "DOWN" in out.upper()

        seen = [ln.strip() for ln in out.splitlines()
                if re.search(rf'{t}\s+{c}\s', ln, re.I) or "KEY_POWER" in ln.upper()]
        note = f"down={'y' if down else 'n'} up={'y' if up else 'n'}"
        if seen:
            note += " | " + " ; ".join(seen[:4])

        if down and up:
            return True, f"POWER key press+release detected ({note})"
        if not out.strip():
            return False, f"no getevent output captured - did you press within {w}s? ({note})"
        return False, f"POWER key event incomplete ({note})"
