"""Given a mail's subject+body, extract the build path and launch autotest.

This is the single entry point both a mail trigger (Outlook VBA / a poller)
can call. It:
  * filters by sender/subject (whitelist) so only real build mails fire,
  * extracts the build .zip path from the body (parser.py),
  * de-duplicates by message id (won't run twice for the same mail),
  * launches autotest.py --build <path>.

Usage (subject/body passed as text; id is any stable per-mail key):
    python run_on_mail.py --id <MSGID> --subject "<subj>" --body-file body.txt
    ... | python run_on_mail.py --id <MSGID> --subject "<subj>"      # body on stdin

Filtering knobs are the constants below - tweak to your build mail.
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parser import extract_build_zip  # noqa: E402

HERE = Path(__file__).resolve().parent
AUTOTEST = HERE.parent / "autotest.py"
SEEN_FILE = HERE.parent / "_ut_work" / "mail_seen.txt"

# --- whitelist: only fire for the real build mail ----------------------------
SUBJECT_MUST_CONTAIN = ["Build Successfully"]      # all must be present
SENDER_ALLOW = []                                  # e.g. ["buildbot@company.com"]; [] = any


def _seen(msg_id: str) -> bool:
    if not msg_id or not SEEN_FILE.exists():
        return False
    return msg_id in SEEN_FILE.read_text(encoding="utf-8").splitlines()


def _mark_seen(msg_id: str):
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(msg_id + "\n")


def handle(msg_id: str, subject: str, body: str, sender: str = "",
           dry_run=False, manual=False) -> int:
    # manual (button) triggers are deliberate: skip whitelist + de-dup.
    if not manual:
        if not all(s in subject for s in SUBJECT_MUST_CONTAIN):
            print(f"[skip] subject not a build mail: {subject!r}")
            return 2
        if SENDER_ALLOW and not any(a.lower() in sender.lower() for a in SENDER_ALLOW):
            print(f"[skip] sender not allowed: {sender!r}")
            return 2
        if _seen(msg_id):
            print(f"[skip] already processed id={msg_id}")
            return 3

    build = extract_build_zip(subject, body)
    if not build:
        print("[error] could not extract a build .zip path from subject/body")
        return 4
    print(f"[trigger] build = {build}")

    _mark_seen(msg_id)          # mark before running so a crash won't re-trigger
    if dry_run:
        print("[dry-run] would launch:", sys.executable, str(AUTOTEST), "--build", build)
        return 0

    # detached-friendly: run autotest and stream its output; its own logs/JSON persist
    p = subprocess.run([sys.executable, str(AUTOTEST), "--build", build])
    print(f"[done] autotest exit code = {p.returncode}")
    return p.returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description="Trigger autotest from a build mail.")
    ap.add_argument("--id", default="", help="stable per-mail id (Outlook EntryID / IMAP UID)")
    ap.add_argument("--subject", default="")
    ap.add_argument("--sender", default="")
    ap.add_argument("--body-file", help="file holding the mail body (else read stdin)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--manual", action="store_true",
                    help="deliberate button trigger: skip whitelist + de-dup")
    a = ap.parse_args(argv)

    if a.body_file:
        body = Path(a.body_file).read_text(encoding="utf-8", errors="replace")
    else:
        body = sys.stdin.read() if not sys.stdin.isatty() else ""
    return handle(a.id, a.subject, body, a.sender, a.dry_run, a.manual)


if __name__ == "__main__":
    sys.exit(main())
