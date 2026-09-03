"""Cong CHONG MUC BI BO LAI: mot muc duoc sua, muc khac noi nguoc lai ma khong ai thay.

⛔ VI SAO CO CONG NAY. Doc ngoai vong hai cua bai nay bi CHAN boi dung loi do. Muc Ket qua
duoc sua sau khi do them, muc Mo dau va Ket luan cung duoc sua, nhung muc De doa thi khong.
Ket qua: bai TU MAU THUAN o ba cho, va mau thuan lan ca vao abstract:

    muc De doa noi          | muc khac da noi
    ------------------------|----------------------------------
    payload la "uoc luong"  | suy ra tu RFC 4944
    so vong DTLS tu dac ta  | DO DUOC bang relay
    "khong co co khoi nao"  | co khoi lon nhat con 4x

Khong cong nao cu truoc do bat duoc. `check-no-typed-numbers` chi kiem chu SO. `check-sync`
chi kiem so trong PDF co khop JSON. Ca hai deu XANH trong khi bai tu mau thuan, vi mau thuan
nam o CHU chu khong o SO.

CACH KIEM. Khong the chung minh tu dong hai cau la mau thuan. Nhung co the bat hai dau hieu:

  1. CAP TU DOI LAP. Mot danh sach nho cac cap "A phu dinh B" (uoc luong / suy ra, trich dan /
     do duoc, khong co gi / co mot cai). Neu CA HAI ve cung xuat hien trong ban thao thi in ra
     ca hai cau de NGUOI doc quyet dinh. Day la canh bao, khong phai loi.

  2. MUC BI BO LAI. Neu mot tep .tex duoc sua gan day han han mot tep khac DANG KE, va ca hai
     cung dung chung macro so, thi tep cu co the da lac hau. In ra khoang cach thoi gian.

Ca hai deu la GOI Y cho nguoi doc lai, khong phai phan quyet. Mot cong khong the doc y; no chi
co the chi cho nguoi doc dung cho.
"""

import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# Cac cap doi lap thuong gay mau thuan khi mot muc duoc sua ma muc khac thi khong.
# Moi cap: (nhan, regex ve A, regex ve B).
PAIRS = [
    ("uoc luong  <->  suy ra co nguon",
     r"\b(is an estimate|rather than a measurement|estimated rather than)\b",
     r"\b(derives it|is derived|not an estimate|derived, not estimated)\b"),
    ("trich dan  <->  do duoc",
     r"\b(the source is the specification|taken from the specification|count is cited)\b",
     r"\b(we measure this|measured rather than cited|is measured on DTLS)\b"),
    ("khong co gi  <->  co mot cai",
     r"\bno (permitted )?block size (brings|recovers)\b",
     r"\b(tuning does help|the largest permitted block size brings|does recover)\b"),
    ("khong do  <->  da do",
     r"\baddressed only qualitatively\b",
     r"\bwe measure\b"),
]


def body(path):
    s = io.open(path, encoding="utf-8").read()
    if "\\begin{document}" in s:
        s = s.split("\\begin{document}", 1)[1]
    s = re.sub(r"^%.*$", "", s, flags=re.M)
    return re.sub(r"\s+", " ", s)


def sentence_around(text, m):
    a = text.rfind(".", 0, m.start()) + 1
    b = text.find(".", m.end())
    return text[a:(b + 1) if b > 0 else len(text)].strip()


def main():
    texs = [f for f in sorted(os.listdir(HERE))
            if f.endswith(".tex") and f not in ("cited-numbers.tex",)]
    if not texs:
        print("  (khong co tep .tex)"); return 0
    joined = {f: body(os.path.join(HERE, f)) for f in texs}
    allbody = " ".join(joined.values())

    warn = 0
    print("  1. cap tu doi lap cung xuat hien:")
    for label, ra, rb in PAIRS:
        ma = list(re.finditer(ra, allbody, re.I))
        mb = list(re.finditer(rb, allbody, re.I))
        if ma and mb:
            warn += 1
            print("     ⚠ %s" % label)
            for f, t in joined.items():
                for m in re.finditer(ra, t, re.I):
                    print("        [A] %s: ...%s..." % (f, sentence_around(t, m)[:120]))
                for m in re.finditer(rb, t, re.I):
                    print("        [B] %s: ...%s..." % (f, sentence_around(t, m)[:120]))
    if not warn:
        print("     ✅ khong thay cap doi lap nao cung xuat hien")

    print("  2. muc co the bi bo lai (theo thoi gian sua):")
    times = {f: os.path.getmtime(os.path.join(HERE, f)) for f in texs}
    newest = max(times.values())
    stale = [(f, (newest - t) / 3600.0) for f, t in times.items() if newest - t > 6 * 3600]
    for f, h in sorted(stale, key=lambda x: -x[1]):
        print("     ⚠ %-20s sua truoc muc moi nhat %.0f gio" % (f, h))
        warn += 1
    if not stale:
        print("     ✅ moi muc duoc sua trong cung mot dot")

    print()
    print("  => %s" % ("✅ khong co dau hieu bo lai"
                       if warn == 0 else
                       "⚠ %d dau hieu. DOC LAI cac muc duoc neu; day la canh bao, khong phai loi."
                       % warn))
    return 0            # canh bao, khong chan build


if __name__ == "__main__":
    sys.exit(main())
