"""Cong DONG BO BA CHIEU: JSON do duoc  <->  bang/macro sinh ra  <->  van xuoi da dich.

VI SAO CAN. Cong `check-no-typed-numbers.py` chi chan viec GO TAY so vao van. No khong tra
loi duoc cau hoi khac: **con so in ra trong PDF co dung bang so trong ket qua do duoc khong.**
Ba duong di lech nhau duoc ma khong cong nao thay:

  - macro sinh ra tu mot lan chay, PDF dich tu mot lan chay KHAC (quen build lai)
  - bang sinh dung, nhung van xuoi mo ta bang bang mot con so cu chep lai
  - JSON bi thay bang ban khac (da xay ra: hinh 4 tung ve MOT cai dat thay vi ba)

Cong nay lay JSON lam NGUON DUY NHAT, roi doi chieu xuoi:
  1. moi gia tri do duoc trong JSON  ->  co macro tuong ung, va macro dung gia tri do
  2. moi gia tri do  ->  xuat hien trong VAN BAN da dich cua main.pdf
  3. khong co gia tri MAU THUAN nao trong PDF (vd: ca 17/21 lan 16/21)

Chay: python3 paper/check-sync.py     (sau khi `bash figures/build.sh` va dich main.tex)
"""

import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
NUMBERS = os.path.join(ROOT, "figures", "out", "numbers.tex")
PDF = os.path.join(HERE, "main.pdf")


def load_json(name):
    p = os.path.join(RES, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def macros():
    if not os.path.exists(NUMBERS):
        return {}
    s = io.open(NUMBERS, encoding="utf-8").read()
    return dict(re.findall(r"\\newcommand\{\\(num[A-Za-z]+)\}\{([^}]*)\}", s))


def pdf_text():
    if not os.path.exists(PDF):
        return None
    r = subprocess.run(["pdftotext", PDF, "-"], capture_output=True, text=True)
    return re.sub(r"\s+", " ", r.stdout)


def main():
    m1, m3 = load_json("m1_coap_blockwise.json"), load_json("m3_fragment_threshold.json")
    mac = macros()
    txt = pdf_text()

    if not mac:
        print("  ⛔ THIEU numbers.tex. Chay `bash figures/build.sh` truoc."); return 2
    if m1 is None or m3 is None:
        print("  ⛔ THIEU JSON ket qua. Chay cac phep do truoc."); return 2

    # ── 1. JSON -> macro ─────────────────────────────────────────────────────
    # Tinh LAI tu JSON, khong doc lai gia tri macro roi so voi chinh no.
    want = {"numMOneMatch": str(m1["n_match"]),
            "numMOneTotal": str(m1["n_match"] + m1["n_mismatch"])}
    for impl in sorted({r["impl"] for r in m3["rows"]}):
        rs = [r for r in m3["rows"] if r["impl"] == impl]
        cap = impl.capitalize()
        want["num%sOk" % cap] = str(sum(1 for r in rs if r["handshake_ok"]))
        want["num%sTotal" % cap] = str(len(rs))

    bad = [(k, v, mac.get(k, "(THIEU)")) for k, v in want.items() if mac.get(k) != v]
    print("  1. JSON -> macro: kiem %d gia tri" % len(want))
    for k, exp, got in bad:
        print("     ⛔ \\%s = %s nhung JSON cho %s" % (k, got, exp))
    if not bad:
        print("     ✅ moi macro khop JSON")

    # ── 2. macro -> van xuoi da dich ─────────────────────────────────────────
    missing = []
    if txt is None:
        print("  2. macro -> PDF: (chua dich main.pdf, bo qua)")
    else:
        # Chi kiem cac gia tri THUC SU duoc dung trong ban thao.
        used = set()
        for f in os.listdir(HERE):
            if f.endswith(".tex"):
                used |= set(re.findall(r"\\(num[A-Za-z]+)",
                                       io.open(os.path.join(HERE, f), encoding="utf-8").read()))
        checked = 0
        for k in sorted(used):
            v = mac.get(k)
            if not v or not re.fullmatch(r"[\d.,/]+", v):
                continue                      # bo qua chuoi (vd ten thu vien)
            checked += 1
            if v not in txt:
                missing.append((k, v))
        print("  2. macro -> PDF: kiem %d gia tri co dung trong ban thao" % checked)
        for k, v in missing:
            print("     ⛔ \\%s = %s KHONG thay trong PDF (PDF cu? quen dich lai?)" % (k, v))
        if not missing and checked:
            print("     ✅ moi gia tri deu xuat hien trong ban da dich")
        if not checked:
            print("     ⚠ KIEM 0 GIA TRI. Cong nay dang khong kiem gi.")

    # ── 3. gia tri MAU THUAN trong PDF ───────────────────────────────────────
    # ⚠ Ban dau cong nay so gia tri cua TUNG cai dat voi MOI mau n/N trong PDF, nen no bao
    # dong gia 2 lan ngay lan chay dau: '9/21' la cua OpenSSL con '17/21' la cua GnuTLS, ca
    # hai deu dung cho. Chi coi la mau thuan khi ti so KHONG thuoc ve BAT KY cai dat nao.
    # Luat cua nha: siet cong thi phai DO ti le bao dong gia.
    contra = []
    if txt:
        legit = set()
        totals = set()
        for impl in sorted({r["impl"] for r in m3["rows"]}):
            rs = [r for r in m3["rows"] if r["impl"] == impl]
            ok, tot = sum(1 for r in rs if r["handshake_ok"]), len(rs)
            legit.add("%d/%d" % (ok, tot))
            totals.add(tot)
            # ti so "so o dat khung" cung hop le
            at = [r for r in rs if r["mtu"] == min(x["mtu"] for x in m3["rows"])]
            if at:
                legit.add("%d/%d" % (sum(1 for r in at if r["handshake_ok"]), len(at)))
                totals.add(len(at))
        for tot in totals:
            for other in range(tot + 1):
                cand = "%d/%d" % (other, tot)
                if cand in legit:
                    continue
                if re.search(r"(?<![\d/])%s(?![\d/])" % re.escape(cand), txt):
                    contra.append(("--", cand, " hoac ".join(sorted(legit))))
        print("  3. gia tri mau thuan trong PDF:")
        for impl, seen, exp in contra:
            print("     ⛔ thay '%s' khong thuoc cai dat nao (hop le: %s)" % (seen, exp))
        if not contra:
            print("     ✅ khong thay gia tri mau thuan")

    nbad = len(bad) + len(missing) + len(contra)
    print()
    print("  => %s" % ("✅ DONG BO" if nbad == 0 else "⛔ LECH %d cho" % nbad))
    return 1 if nbad else 0


if __name__ == "__main__":
    sys.exit(main())
