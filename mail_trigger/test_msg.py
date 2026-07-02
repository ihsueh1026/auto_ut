"""Offline test: parse a saved Outlook .msg and show what would be triggered.

No third-party libs needed - a .msg stores its text as UTF-16LE, so a crude
decode is enough to recover the body/subject for parsing. (Online triggers -
Outlook VBA / IMAP / Graph - hand you the text directly and don't need this.)

Usage:
    python test_msg.py                 # auto-find the *.msg in auto_ut/
    python test_msg.py "path\\to\\mail.msg"
    python test_msg.py mail.msg --go   # actually launch autotest (not dry-run)
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parser import extract_from_body, reconstruct_from_subject  # noqa: E402
from run_on_mail import handle  # noqa: E402


def main(argv):
    go = "--go" in argv
    args = [a for a in argv if a != "--go"]

    if args:
        msg = Path(args[0])
    else:
        cands = list((Path(__file__).resolve().parent.parent).glob("*.msg"))
        if not cands:
            print("no .msg given and none found in auto_ut/")
            return 1
        msg = cands[0]

    text = msg.read_bytes().decode("utf-16le", "ignore")
    print(f"msg      : {msg.name}")
    print(f"body ->  : {extract_from_body(text)}")
    print(f"subj ->  : {reconstruct_from_subject(text)}")

    # feed it through the real dispatcher (dry-run unless --go)
    print("-" * 40)
    return handle(msg_id=f"msgfile:{msg.name}", subject=text, body=text,
                  dry_run=not go, manual=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
