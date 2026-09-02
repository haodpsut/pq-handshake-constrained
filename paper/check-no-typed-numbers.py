"""Cong: ban thao KHONG duoc go tay con so nao chua giai trinh.

Luat cua nha: moi so headline phai co DUNG MOT CHO O. Vi pham dien hinh la mot con
so duoc chep vao van xuoi, roi chay lai thi nghiem thi hinh doi ma cau van khong.

Cong nay chay tren cac tep .tex cua ban thao. No:
  1. bo chu thich, bo macro \\numXxx, bo doi so cua \\ref/\\cite/\\texttt/...
  2. liet ke moi con so CON LAI trong van
  3. doi chieu voi danh sach MIEN TRU da giai trinh (ten chuan, ten phien ban)
  4. kiem moi macro \\numXxx dung trong bai co that su duoc sinh ra khong
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NUMBERS = os.path.join(os.path.dirname(HERE), "figures", "out", "numbers.tex")
# So TRICH tu bai khac co cho o rieng: chung khong den tu results/*.json nen khong
# the sinh ra duoc, nhung van phai co MOT cho o va phai ghi ro nguon.
CITED = os.path.join(HERE, "cited-numbers.tex")

# Mien tru: TEN chuan / phien ban / hang so cong bo. Them vao day phai kem LY DO.
ALLOWED = {
    "1.2": "DTLS 1.2, ten phien ban", "1.3": "DTLS 1.3, ten phien ban",
    "24.04": "Ubuntu 24.04, moi truong do",
    "256": "DTLS1_MIN_MTU, hang so cong bo trong ma nguon OpenSSL",
    "512": "ML-KEM-512", "768": "ML-KEM-768", "1024": "ML-KEM-1024",
    "44": "ML-DSA-44", "65": "ML-DSA-65", "87": "ML-DSA-87",
    "7959": "RFC 7959", "9147": "RFC 9147", "9528": "RFC 9528", "9668": "RFC 9668",
    "802.15": "IEEE 802.15.4", "4944": "RFC 4944", "9177": "RFC 9177",
    "6": "6LoWPAN, ten cong nghe",
    "5": "Claude Opus 5, ten cong cu trong muc khai dung AI",
}


def strip(s):
    s = re.sub(r"^%.*$", "", s, flags=re.M)
    s = re.sub(r"\\(num|cited)[A-Za-z]+", " ", s)
    s = re.sub(r"\\(ref|cite|label|texttt|emph|textbf|section|subsection|input)\{[^}]*\}", " ", s)
    return s


def main():
    # ⚠ Bo tep DINH NGHIA khoi danh sach quet. Chinh no la CHO O cua cac con so,
    # nen quet no thi moi dinh nghia deu bi doc thanh "go tay" -- cong tu to cao chinh
    # cho o ma no dang bao ve.
    texs = sorted(f for f in os.listdir(HERE)
                  if f.endswith(".tex") and f != os.path.basename(CITED))
    if not texs:
        print("  (chua co tep .tex nao trong paper/)"); return 0
    have = set()
    if os.path.exists(NUMBERS):
        have = set(re.findall(r"\\newcommand\{\\(num[A-Za-z]+)\}",
                              io.open(NUMBERS, encoding="utf-8").read()))
        if os.path.exists(CITED):
            have |= set(re.findall(r"\\newcommand\{\\(cited[A-Za-z]+)\}",
                                   io.open(CITED, encoding="utf-8").read()))
    else:
        print("  ⛔ THIEU figures/out/numbers.tex. Chay `bash figures/build.sh` truoc.")
        return 2

    bad_num, bad_macro, checked = [], [], 0
    for t in texs:
        s = io.open(os.path.join(HERE, t), encoding="utf-8").read()
        for n in set(re.findall(r"(?<![\w.])\d+(?:[.,]\d+)?", strip(s))):
            checked += 1
            if n not in ALLOWED:
                bad_num.append((t, n))
        for m in set(re.findall(r"\\((?:num|cited)[A-Za-z]+)", s)):
            if m not in have:
                bad_macro.append((t, m))

    print("  da kiem %d tep, %d con so trong van" % (len(texs), checked))
    if bad_macro:
        print("  ⛔ MACRO KHONG DUOC SINH RA:")
        for t, m in sorted(bad_macro):
            print("     %s: \\%s" % (t, m))
    if bad_num:
        print("  ⛔ SO GO TAY CHUA GIAI TRINH:")
        for t, n in sorted(bad_num):
            print("     %s: %s" % (t, n))
        print("     => hoac them macro trong make_figures.py, hoac them vao ALLOWED KEM LY DO")
    if not bad_num and not bad_macro:
        print("  ✅ 0 so go tay chua giai trinh, 0 macro thieu")
    return 1 if (bad_num or bad_macro) else 0


if __name__ == "__main__":
    sys.exit(main())
