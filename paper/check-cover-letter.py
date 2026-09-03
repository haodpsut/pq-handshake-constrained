"""Kiem MAT TIEN khop THAN BAI: cover letter khong duoc chua so nao bai khong co.

⚠ Da tung xay ra: mot cover letter khai doi khung trong khi abstract ngay duoi van neu lai
bon dong gop da rut. Cong chi doc than bai thi khong bao gio thay.
"""
import re, subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__)) or "."
def txt(f):
    p = os.path.join(HERE, f)
    if not os.path.exists(p):
        return None
    return re.sub(r"\s+", " ", subprocess.run(["pdftotext", p, "-"],
                                              capture_output=True, text=True).stdout)

cl, ms = txt("cover-letter.pdf"), txt("main.pdf")
if cl is None:
    print("  (chua co cover-letter.pdf)"); sys.exit(0)
if ms is None:
    print("  ⛔ chua co main.pdf de doi chieu"); sys.exit(1)

DATES = {"2024", "2025", "2026", "2027"}
n_cl = set(re.findall(r"(?<![\w.])\d{2,4}(?![\d.])", cl))
n_ms = set(re.findall(r"(?<![\w.])\d{2,4}(?![\d.])", ms))
orphan = sorted(n_cl - n_ms - DATES)
if orphan:
    print("  ⛔ so trong THU ma bai KHONG co: %s" % ", ".join(orphan))
    sys.exit(1)
print("  ✅ moi so trong thu deu xuat hien trong ban thao")
sys.exit(0)
