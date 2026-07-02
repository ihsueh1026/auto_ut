"""Extract the build .zip path from a 'Build Successfully' mail (example).

The weekly build mail (see the sample .msg in auto_ut/) carries the UNC path to
the build .zip in its body. Real-world quirks handled here, observed from the
sample mail:

  * body is UTF-16LE; the path is soft-wrapped across two lines
        \\...\GZI3.0068.PR1.2606291.F_        <- line break here
        000150\GZI3.0068.PR1.2606291.F.zip.zip
  * the path is written with a spurious trailing ".zip" -> ".zip.zip"
  * an earlier, TRUNCATED directory path (no .zip) also appears in the body,
    so we anchor on the LAST UNC path.

Two strategies, in order:
  1. extract_from_body(body)     - authoritative, parses the UNC path in the body
  2. reconstruct_from_subject()  - clean fallback, rebuilds from the subject token
                                   (assumes the share BASE below is stable)
"""
from __future__ import annotations
import re

# Stable share root; only used by the subject fallback. Adjust if it ever moves.
BUILD_BASE = r"\\sdrdfs1\AK7\GZI3\2_WeeklyFormal_Build\CMBUILD"


def extract_from_body(body: str) -> str | None:
    """Pull the last '\\\\...\\....zip' out of the mail body, de-wrapping any
    soft line break inside the path and trimming a doubled '.zip.zip'."""
    if not body:
        return None
    i = body.rfind("\\\\")          # last UNC path start (two backslashes)
    if i == -1:
        return None
    tail = re.sub(r"\s+", "", body[i:])            # join soft-wrapped path
    m = re.match(r"(\\\\[^\s]+?\.zip)", tail, re.IGNORECASE)   # stop at 1st .zip
    return m.group(1) if m else None


def reconstruct_from_subject(subject: str, base: str = BUILD_BASE) -> str | None:
    """Rebuild the path from the subject version token, e.g.
    '[GZI3.0068.PR1.2606291.F-000150] Build Successfully' ->
    <base>\\GZI3.0068.PR1.2606291.F_000150\\GZI3.0068.PR1.2606291.F.zip"""
    if not subject:
        return None
    m = re.search(r"(GZI3[\w.]*?\.[A-Za-z])-(\d{4,})", subject)  # ver '-' build#
    if not m:
        return None
    ver, num = m.group(1), m.group(2)
    folder = f"{ver}_{num}"
    return f"{base}\\{folder}\\{ver}.zip"


def extract_build_zip(subject: str = "", body: str = "") -> str | None:
    """Best effort: prefer the body, fall back to the subject."""
    return extract_from_body(body) or reconstruct_from_subject(subject)


# --- self-test against the observed sample -----------------------------------
if __name__ == "__main__":
    sample_subject = "[GZI3]-[vienna][CMBUILD][GZI3.0068.PR1.2606291.F-000150] Build Successfully"
    # body with the real soft-wrap + earlier truncated dir path + .zip.zip
    sample_body = "\n".join([
        "URL: http://10.113.8.92:8080/job/GZI3_FSW_Build/143/",
        r"\\sdrdfs1\AK7\GZI3\2_WeeklyFormal_Build\CMBUILD\GZI3.0068.PR1.2606291.F",
        "GZI3.0068.PR1.2606291.F_sys",
        "...commit list... Morpheus Chen Merge ...",
        r"\\sdrdfs1\AK7\GZI3\2_WeeklyFormal_Build\CMBUILD\GZI3.0068.PR1.2606291.F_",
        r"000150\GZI3.0068.PR1.2606291.F.zip.zip",
    ])
    want = (r"\\sdrdfs1\AK7\GZI3\2_WeeklyFormal_Build\CMBUILD"
            r"\GZI3.0068.PR1.2606291.F_000150\GZI3.0068.PR1.2606291.F.zip")
    from_body = extract_from_body(sample_body)
    from_subj = reconstruct_from_subject(sample_subject)
    print("body  ->", from_body)
    print("subj  ->", from_subj)
    assert from_body == want, from_body
    assert from_subj == want, from_subj
    print("OK: both strategies match")
