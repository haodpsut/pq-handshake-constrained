"""Cong SO HAI NGUON KET QUA VOI NHAU khi chung do CUNG mot dai luong.

⛔ VI SAO CO CONG NAY. Ranh gioi GnuTLS duoc do HAI lan: m3 (mot luot moi o) va m5 (13 o x 20
luot). Van xuoi duoc cap nhat sang so cua m5 (22|23). Bang III thi van in so cua m3 (23|28), vi
bo sinh bang doc m3. Bai sap in HAI ranh gioi khac nhau cho cung mot thu viện.

Khong cong nao cu bat duoc:
  check-no-typed-numbers  -> XANH, ca hai so deu sinh tu JSON, khong go tay
  check-sync              -> XANH, moi so trong PDF deu khop MOT tep JSON nao do
  check-cross-section     -> XANH, mau thuan nam o SO chu khong o cap tu doi lap

Ca ba cong deu hoi "so nay tu dau ra?" va ca hai so deu tra loi duoc. KHONG cong nao hoi
"hai cau tra loi co GIONG NHAU khong?".

⇒ LUAT: khi mot dai luong duoc do o NHIEU HON MOT tep ket qua, phai khai o day. Cong doi chieu
   va bat build neu lech. Do lai cung mot thu ma ra so khac thi do la PHAT HIEN, khong phai
   phien toai: hoac phep do cu sai, hoac dieu kien da doi va phai noi ra.
"""

import io
import json
import os
import sys

# ⛔ THU MUC KET QUA PHAI LA THAM SO, khong duoc suy tu vi tri cua chinh tep nay. Ban dong goi
# dau tien tra `<cho-dat-script>/../results`, nen chay o kho khac thi no kiem 0 don vi va bao
# "thieu nguon, bo qua" cho MOI dai luong. Cai chot "0 don vi khong phai la sach" da bat duoc,
# nhung dung de phai nho den no.
RES = os.environ.get("PAPER_RESULTS") or (
    sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "results"))


def load(name):
    p = os.path.join(RES, name)
    if not os.path.exists(p):
        return None
    return json.load(io.open(p, encoding="utf-8"))


def _span(cert_bytes, mtu):
    """DON VI SO SANH: ti so KHONG lam tron. Lam tron bang ceil() gop 22,40 va 22,95 thanh
    cung so nguyen 23 va do CHINH LA cho ranh gioi di qua, nen so nguyen khong dung de doi
    chieu duoc. Xem m6_boundary_mechanism.py."""
    return cert_bytes / float(mtu)


def gnutls_span_m3(m3):
    rows = [r for r in m3["rows"] if r["impl"] == "gnutls"]
    ok = [_span(r["cert_bytes"], r["mtu"]) for r in rows if r["handshake_ok"]]
    bad = [_span(r["cert_bytes"], r["mtu"]) for r in rows if not r["handshake_ok"]]
    return (round(max(ok), 2) if ok else None, round(min(bad), 2) if bad else None)


def gnutls_span_m5(m5):
    ok = [_span(m5["cert_bytes"], r["mtu"]) for r in m5["rows"] if r["success_rate"] == 1]
    bad = [_span(m5["cert_bytes"], r["mtu"]) for r in m5["rows"] if r["success_rate"] == 0]
    return (round(max(ok), 2) if ok else None, round(min(bad), 2) if bad else None)


def gnutls_span_m6(m6):
    g = m6["grid"]
    ok = [_span(c["cert_bytes"], c["mtu"]) for c in g if c["success_rate"] == 1.0]
    bad = [_span(c["cert_bytes"], c["mtu"]) for c in g if c["success_rate"] == 0.0]
    return (round(max(ok), 2) if ok else None, round(min(bad), 2) if bad else None)


def consistent(a, b):
    """Hai nguon KHONG can cho cung so. Chung phai khong CHONG NHAU: khoang (xong cao nhat,
    hong thap nhat) cua ben nay phai khong bi ben kia bac bo."""
    (aok, abad), (bok, bbad) = a, b
    if None in (aok, abad, bok, bbad):
        return True
    return aok < bbad and bok < abad


# Moi muc: (nhan, ham lay so tu nguon A, ham lay so tu nguon B, nguon nao la TRONG TAI)
CLAIMS = [
    ("ranh gioi GnuTLS: m3 voi m5", "m3_fragment_threshold.json", gnutls_span_m3,
     "m5_boundary_repeats.json", gnutls_span_m5, "m6 (luoi tach nhieu) la trong tai"),
    ("ranh gioi GnuTLS: m3 voi m6", "m3_fragment_threshold.json", gnutls_span_m3,
     "m6_boundary_mechanism.json", gnutls_span_m6, "m6 la trong tai"),
    ("ranh gioi GnuTLS: m5 voi m6", "m5_boundary_repeats.json", gnutls_span_m5,
     "m6_boundary_mechanism.json", gnutls_span_m6, "m6 la trong tai"),
]


def main():
    print("  thu muc ket qua: %s" % RES)
    fail = 0
    checked = 0
    for label, fa, ga, fb, gb, arbiter in CLAIMS:
        a, b = load(fa), load(fb)
        if a is None or b is None:
            print("  ⏭ %-42s thieu nguon, bo qua" % label)
            continue
        va, vb = ga(a), gb(b)
        checked += 1
        if consistent(va, vb):
            print("  ✅ %-30s khong chong nhau: %s · %s" % (label, va, vb))
        else:
            fail += 1
            print("  ⛔ %s" % label)
            print("     %-34s xong<=%s · hong>=%s" % (fa, va[0], va[1]))
            print("     %-34s xong<=%s · hong>=%s" % (fb, vb[0], vb[1]))
            print("     => %s. Moi hien vat PHAI dung so cua no." % arbiter)

    print()
    if checked == 0:
        print("  ⚠ KHONG doi chieu duoc dai luong nao (0 don vi). Day KHONG phai la sach.")
        return 1
    print("  => %s (%d dai luong do o hai nguon)"
          % ("✅ hai nguon noi cung mot chuyen" if fail == 0
             else "⛔ %d dai luong LECH giua hai nguon" % fail, checked))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
