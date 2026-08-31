"""M3 — NGƯỠNG SỐ MẢNH: DTLS có bắt tay nổi ở cỡ hậu lượng tử trên MTU ràng buộc không?

⭐ ĐÂY LÀ PHÉP ĐO QUYẾT ĐỊNH CỦA CẢ HƯỚNG. Kết quả của nó đổi hẳn luận điểm bài báo.

BỐI CẢNH. M2 (trên macOS, GnuTLS 3.8.13) tìm ra một ranh giới sắc: bắt tay DTLS **xong ở 22
mảnh** và **hỏng ở 24 mảnh**. Ranh giới bám theo SỐ MẢNH chứ không theo tổng byte: giữ nguyên
chứng thư, chỉ đổi MTU, thì kết quả đổi. Ở cỡ hậu lượng tử trên MTU 802.15.4 (102 B), chứng
thư cần khoảng 52 đến 81 mảnh, tức vượt xa ngưỡng đó.

NẾU ĐÚNG thì bài không còn là "EDHOC thua DTLS" mà là "CẢ HAI giao thức đều hỏng, theo hai
kiểu khác nhau": EDHOC suy giảm êm nhưng thảm hại về số vòng, DTLS giữ số vòng nhưng cài đặt
GÃY HẲN.

⛔ NHƯNG MỘT CÀI ĐẶT KHÔNG CHỨNG MINH ĐƯỢC GÌ. Kiểm nội bộ chỉ chứng minh nhất quán. Tệp này
chạy CÙNG phép dò trên MỌI cài đặt tìm thấy được, để phân biệt:

    - Nhiều cài đặt cùng gãy ở CÙNG ngưỡng   -> vấn đề của GIAO THỨC hoặc của mô hình chung
    - Chỉ một cài đặt gãy                     -> lỗi riêng của cài đặt đó, KHÔNG viết thành
                                                 tuyên bố về giao thức
    - Ngưỡng khác nhau rõ rệt                 -> vấn đề THAM SỐ (bộ đệm, bộ đếm giờ), phải
                                                 nói đúng như vậy

BA GIẢ THUYẾT CẦN TÁCH, vì chúng cho BA KẾT LUẬN KHÁC NHAU:
    (a) giới hạn BỘ ĐỆM ráp mảnh      -> ngưỡng theo TỔNG BYTE, không theo số mảnh
    (b) HẾT GIỜ truyền lại            -> nới thời gian chờ thì ngưỡng dịch; và ca hỏng tốn
                                          THỜI GIAN LÂU hơn hẳn ca chạy
    (c) giới hạn SỐ MẢNH mỗi bản tin  -> ngưỡng theo SỐ MẢNH, không đổi khi nới giờ

M2 đã loại (a): cùng tổng byte, đổi MTU thì đổi kết quả. Tệp này đo THỜI GIAN tới lúc hỏng để
tách (b) khỏi (c).

CHẠY: python3 m3_fragment_threshold.py
Không cần GPU. Không cần cài PQC: chỉ cần chứng thư to dần, vì lập luận nằm ở KÍCH THƯỚC.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, ".certs")
OUT = os.path.join(os.path.dirname(HERE), "results", "m3_fragment_threshold.json")

# Chứng thư RSA nhiều cỡ. Cỡ lớn phủ vùng ML-DSA (pk+sig ~5,3 KB ở mức 65).
KEY_BITS = (2048, 8192, 15360)
# MTU quét. 102 = payload khung 802.15.4 sau MAC + AES-CCM*.
# Đổi được bằng biến môi trường để dò ranh giới mịn mà KHÔNG phải viết script rời.
# ⚠ Lý do có tuỳ chọn này: mỗi lần tôi tự chế một biến thể ad-hoc để dò nhanh, nó lại khác
# harness ở một chi tiết (stdin, thời gian chờ server) và cho kết quả MÂU THUẪN với harness.
# Đã xảy ra hai lần. Quy tắc: mọi phép dò phải chạy qua ĐÚNG hàm đã qua chứng dương tính.
MTUS = tuple(int(x) for x in os.environ["PQHS_MTUS"].split(",")) \
    if os.environ.get("PQHS_MTUS") else (102, 150, 200, 250, 300, 400, 600)
KEY_BITS = tuple(int(x) for x in os.environ["PQHS_KEYBITS"].split(",")) \
    if os.environ.get("PQHS_KEYBITS") else KEY_BITS
PORT_BASE = 16400
# Giới hạn cứng mỗi lần dò. Ca vượt giới hạn được ghi là TIMED_OUT, KHÔNG phải "hỏng".
PROBE_TIMEOUT = 25


# ⛔ BẢN TRƯỚC CỦA HÀM NÀY LÀM HỎNG CẢ PHÉP ĐO. Nó dùng shell=True với ĐƯỜNG ỐNG
# (`echo q | gnutls-cli ...`). Khi hết giờ, Python giết cái SHELL nhưng tiến trình CON vẫn
# sống và giữ ống, nên lệnh đọc treo vô hạn. Hệ quả: timeout 120 s mà đo ra 12.593 s, và
# nhiều ca bị ghi là "bắt tay hỏng" trong khi thật ra là HARNESS BỎ CUỘC.
#
# Đây là lần thứ tư trong cùng một đợt việc lẫn "công cụ hỏng" với "kết quả âm". Nên bản này
# PHÂN BIỆT HAI THỨ ĐÓ TRONG DỮ LIỆU RA: `ok` và `timed_out` là hai trường riêng.

def run_proc(argv, stdin_bytes=b"q\n", timeout=30):
    """Chạy một tiến trình, KHÔNG qua shell, KHÔNG đường ống.

    Trả về (stdout+stderr, đã_hết_giờ, số_giây). Khi hết giờ thì giết CẢ NHÓM tiến trình,
    nếu không thì tiến trình con sống sót và treo lần đọc kế tiếp.
    """
    t0 = time.time()
    p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out, _ = p.communicate(input=stdin_bytes, timeout=timeout)
        return out.decode("utf-8", "replace"), False, time.time() - t0
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:                                       # noqa: BLE001
            p.kill()
        try:
            out, _ = p.communicate(timeout=5)
        except Exception:                                       # noqa: BLE001
            out = b""
        return out.decode("utf-8", "replace"), True, time.time() - t0


def sh(cmd, timeout=120):
    """CHỈ dùng cho lệnh phụ trợ (sinh chứng thư, hỏi phiên bản), KHÔNG dùng để đo."""
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None


def make_cert(bits):
    os.makedirs(WORK, exist_ok=True)
    key = os.path.join(WORK, "k%d.pem" % bits)
    crt = os.path.join(WORK, "c%d.pem" % bits)
    if not os.path.exists(crt):
        sh("openssl req -x509 -newkey rsa:%d -keyout %s -out %s -days 2 -nodes "
           "-subj '/CN=t' 2>/dev/null" % (bits, key, crt), timeout=600)
    if not os.path.exists(crt):
        return None
    return key, crt, os.path.getsize(crt)


# ---------------------------------------------------------------- cài đặt

def probe_gnutls(crt, key, mtu, port):
    """Trả về (thành công, giây). Câu 'Handshake was completed' chỉ ca THÀNH CÔNG mới in."""
    srv = subprocess.Popen(
        ["gnutls-serv", "--udp", "--port", str(port), "--mtu", str(mtu), "--nocookie",
         "--x509certfile", crt, "--x509keyfile", key],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    time.sleep(1.2)
    out, timed_out, dt = run_proc(
        ["gnutls-cli", "--udp", "--port", str(port), "--mtu", str(mtu),
         "--insecure", "127.0.0.1"], timeout=PROBE_TIMEOUT)
    srv.terminate()
    try:
        srv.wait(timeout=5)
    except subprocess.TimeoutExpired:
        srv.kill()
    return ("Handshake was completed" in out), timed_out, dt


def probe_openssl(crt, key, mtu, port):
    """OpenSSL thật (KHÔNG phải LibreSSL của Apple). Bằng chứng thành công là dòng
    'Cipher    : <ten bo ma khong phai (NONE)>' -- phải kiểm CẢ giá trị, vì đầu ra của ca
    HỎNG cũng chứa chữ 'Cipher'."""
    srv = subprocess.Popen(
        ["openssl", "s_server", "-dtls1_2", "-mtu", str(mtu), "-accept", str(port),
         "-cert", crt, "-key", key, "-quiet"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    time.sleep(1.0)
    out, timed_out, dt = run_proc(
        ["openssl", "s_client", "-dtls1_2", "-mtu", str(mtu),
         "-connect", "127.0.0.1:%d" % port], timeout=PROBE_TIMEOUT)
    srv.terminate()
    try:
        srv.wait(timeout=5)
    except subprocess.TimeoutExpired:
        srv.kill()
    return openssl_handshake_ok(out), timed_out, dt


def openssl_handshake_ok(out):
    """⛔ BỘ DÒ CŨ CHO DƯƠNG TÍNH GIẢ TRÊN MỌI CA.

    Nó nhận bất kỳ đuôi nào sau `Cipher :` dài hơn 3 ký tự và không chứa "NONE". Nhưng một
    bắt tay HỎNG in `Cipher    : 0000` -- "0000" là mã bộ mã RỖNG, dài 4 ký tự, không chứa
    "NONE". Nên MỌI ca hỏng đều được đọc thành công. Đây là lần thứ NĂM trong cùng đợt việc
    mà bộ dò khớp hình thức thay vì bản chất, và là lần đầu cho DƯƠNG TÍNH giả.

    Bộ dò đúng phải đòi bằng chứng chỉ ca THÀNH CÔNG mới sinh ra được:
      - dòng "SSL handshake has read N bytes" với N > 0  (ca hỏng luôn đọc 0 byte), VÀ
      - tên bộ mã thật, không phải 0000 / (NONE).
    """
    read_bytes = 0
    m = re.search(r"handshake has read\s+(\d+)\s+bytes", out)
    if m:
        read_bytes = int(m.group(1))
    named = False
    for line in out.splitlines():
        m2 = re.match(r"\s*Cipher\s*:\s*(\S+)\s*$", line)
        if m2:
            v = m2.group(1)
            if v not in ("0000", "(NONE)", "NONE") and not v.strip("0") == "":
                named = True
    return read_bytes > 0 and named


IMPLS = []
if shutil.which("gnutls-serv"):
    v = sh("gnutls-serv --version 2>&1 | head -1")
    IMPLS.append(("gnutls", (v.stdout or "").strip() if v else "gnutls", probe_gnutls))
if shutil.which("openssl"):
    v = sh("openssl version")
    name = (v.stdout or "").strip() if v else "openssl"
    # LibreSSL của macOS đã được xác nhận không bắt tay nổi với chính nó. Vẫn chạy để GHI
    # NHẬN, nhưng phải gắn nhãn để không nhầm là bằng chứng về giao thức.
    IMPLS.append(("openssl", name, probe_openssl))


def main():
    if not IMPLS:
        print("  ⛔ khong tim thay cai dat DTLS nao"); return 1

    print("  Cài đặt tìm thấy:")
    for k, v, _ in IMPLS:
        flag = "  ⚠ LibreSSL, đã biết là không bắt tay nổi trên macOS" if "LibreSSL" in v else ""
        print("    %-8s %s%s" % (k, v, flag))
    print()

    # ══════════════════════════════════════════════════════════════════════════════════
    # CHỨNG DƯƠNG TÍNH BẮT BUỘC. Cài đặt nào không bắt tay nổi ở cấu hình DỄ NHẤT (chứng
    # thư nhỏ, MTU rộng) thì BỊ LOẠI, không được quét, vì mọi ô của nó sẽ vô nghĩa.
    #
    # Đây là sửa CẤU TRÚC sau NĂM lần cùng một lớp lỗi trong một đợt việc: bốn lần âm tính
    # giả, một lần dương tính giả. Bài học chung của cả năm: BỘ DÒ PHẢI ĐƯỢC THỬ TRÊN MỘT CA
    # ĐÃ BIẾT ĐÚNG, TRƯỚC KHI QUÉT. Nếu ca đó trượt thì dữ liệu không tồn tại, và im lặng bỏ
    # qua là cách sinh ra bảng đẹp mà rỗng.
    # ══════════════════════════════════════════════════════════════════════════════════
    made = make_cert(min(KEY_BITS))
    if made is None:
        print("  ⛔ khong sinh duoc chung thu de chay chung duong tinh"); return 1
    ck, cc, _ = made
    print("  ═══ CHỨNG DƯƠNG TÍNH (chứng thư nhỏ nhất, MTU 1400) ═══")
    usable = []
    port_ctl = PORT_BASE - 100
    for impl_key, impl_ver, probe in IMPLS:
        port_ctl += 1
        ok, timed_out, dt = probe(cc, ck, 1400, port_ctl)
        print("    %-8s %s  (%.2f s)"
              % (impl_key, "✅ bắt tay được ⇒ DÙNG ĐƯỢC"
                 if ok else "⛔ KHÔNG bắt tay nổi ⇒ LOẠI, mọi số của nó sẽ vô nghĩa", dt))
        if ok:
            usable.append((impl_key, impl_ver, probe))
    print()
    if not usable:
        print("  ⛔ KHÔNG cài đặt nào qua chứng dương tính. DỪNG, không sinh dữ liệu.")
        print("     Sửa môi trường trước. Quét tiếp chỉ tạo ra bảng rỗng trông như dữ liệu.")
        return 2
    IMPLS[:] = usable

    results = []
    port = PORT_BASE
    for key_bits in KEY_BITS:
        made = make_cert(key_bits)
        if made is None:
            print("  ⛔ khong sinh duoc chung thu %d" % key_bits); continue
        key, crt, csize = made
        print("  ══ chứng thư RSA-%d = %d byte ══" % (key_bits, csize))
        print("  %-9s %6s %7s %10s %9s" % ("cài đặt", "MTU", "~mảnh", "kết quả", "giây"))
        print("  " + "-" * 50)
        for impl_key, impl_ver, probe in IMPLS:
            for mtu in MTUS:
                port += 1
                frags = -(-csize // mtu)
                ok, timed_out, dt = probe(crt, key, mtu, port)
                results.append({"impl": impl_key, "impl_version": impl_ver,
                                "key_bits": key_bits, "cert_bytes": csize,
                                "mtu": mtu, "frags_est": frags,
                                "handshake_ok": ok, "timed_out": timed_out,
                                "seconds": round(dt, 2)})
                # BA trạng thái, không phải hai. "Hết giờ" KHÔNG được gộp vào "hỏng".
                label = "✅ xong" if ok else ("⏱ hết giờ" if timed_out else "⛔ hỏng")
                print("  %-9s %6d %7d %10s %9.2f" % (impl_key, mtu, frags, label, dt))
        print()

    # --- ranh giới nằm trên TRỤC NÀO: số mảnh hay MTU? ---
    # ⛔ Bản trước GIẢ ĐỊNH ranh giới là số mảnh và in "openssl xong tới 19 mảnh, hỏng từ 5
    # mảnh", một câu vô nghĩa vì hai khoảng CHỒNG LẤN. Ranh giới có thể nằm trên trục khác,
    # và việc đầu tiên phải làm là HỎI trục nào tách được dữ liệu, chứ không phải giả định.
    print("  ═══ RANH GIỚI NẰM TRÊN TRỤC NÀO? ═══")
    print("  Một trục 'tách được' khi mọi ca chạy nằm hẳn một bên mọi ca hỏng.")
    for impl_key, _, _ in IMPLS:
        rs = [r for r in results if r["impl"] == impl_key]
        if not rs:
            continue
        verdicts = []
        for axis, lo_is_ok in (("frags_est", True), ("mtu", False)):
            ok_v = [r[axis] for r in rs if r["handshake_ok"]]
            bad_v = [r[axis] for r in rs if not r["handshake_ok"]]
            if not ok_v or not bad_v:
                verdicts.append((axis, None, None))
                continue
            # tách được theo chiều nào?
            sep = (max(ok_v) < min(bad_v)) if lo_is_ok else (min(ok_v) > max(bad_v))
            bound = (max(ok_v), min(bad_v)) if lo_is_ok else (max(bad_v), min(ok_v))
            verdicts.append((axis, sep, bound))
        line = "  %-9s" % impl_key
        for axis, sep, bound in verdicts:
            name = "số mảnh" if axis == "frags_est" else "MTU"
            if sep is None:
                line += "  %s: (không đủ hai phía)" % name
            elif sep:
                line += "  %s: ✅ TÁCH ĐƯỢC, ranh giới %d|%d" % (name, bound[0], bound[1])
            else:
                line += "  %s: ⛔ chồng lấn" % name
        print(line)

    print()
    print("  ═══ NGƯỠNG THEO TỪNG CÀI ĐẶT (chỉ đúng nếu trục số mảnh TÁCH ĐƯỢC) ═══")
    thresholds = {}
    for impl_key, impl_ver, _ in IMPLS:
        rs = [r for r in results if r["impl"] == impl_key]
        ok_f = [r["frags_est"] for r in rs if r["handshake_ok"]]
        bad_f = [r["frags_est"] for r in rs if not r["handshake_ok"]]
        if not ok_f:
            print("  %-9s KHÔNG ca nào chạy ⇒ không dùng làm bằng chứng" % impl_key)
            thresholds[impl_key] = None
            continue
        hi_ok, lo_bad = max(ok_f), (min(bad_f) if bad_f else None)
        thresholds[impl_key] = {"max_ok_frags": hi_ok, "min_fail_frags": lo_bad}
        if lo_bad is None:
            print("  %-9s chạy được tới %d mảnh, KHÔNG ca nào hỏng" % (impl_key, hi_ok))
        else:
            print("  %-9s xong tới %d mảnh · hỏng từ %d mảnh" % (impl_key, hi_ok, lo_bad))

    # --- tách giả thuyết (b) hết giờ khỏi (c) giới hạn số mảnh ---
    # ⚠ Phép so thời gian này CHỈ có nghĩa khi ranh giới nằm trên trục SỐ MẢNH. Nếu ranh giới
    # nằm trên trục MTU (như OpenSSL) thì cả (b) lẫn (c) đều không phải giả thuyết đúng, và in
    # ra một trong hai là sai. Bản trước in "nghiêng về giới hạn số mảnh" cho một cài đặt mà
    # trục số mảnh CHỒNG LẤN. Cùng lớp lỗi với phần tổng kết ngưỡng: kết luận trên một trục
    # chưa kiểm là trục đúng.
    print()
    frag_separates = any(
        (lambda ok, bad: bool(ok) and bool(bad) and max(ok) < min(bad))(
            [r["frags_est"] for r in results if r["impl"] == k and r["handshake_ok"]],
            [r["frags_est"] for r in results if r["impl"] == k and not r["handshake_ok"]])
        for k, _, _ in IMPLS)
    if not frag_separates:
        print("  ═══ TÁCH GIẢ THUYẾT: BỎ QUA ═══")
        print("  Không cài đặt nào có ranh giới nằm trên trục SỐ MẢNH, nên câu hỏi 'hết giờ")
        print("  hay giới hạn số mảnh' không áp dụng. Xem lại phần trục ở trên.")
        print()
        _skip_hypothesis = True
    else:
        _skip_hypothesis = False
        print("  ═══ TÁCH GIẢ THUYẾT: hết giờ (b) hay giới hạn số mảnh (c)? ═══")
    fails = [r for r in results if not r["handshake_ok"] and r["seconds"] > 0]
    oks = [r for r in results if r["handshake_ok"]]
    if _skip_hypothesis:
        pass
    elif fails and oks:
        mf = sum(r["seconds"] for r in fails) / len(fails)
        mo = sum(r["seconds"] for r in oks) / len(oks)
        print("  thời gian trung bình: ca hỏng %.2f s · ca xong %.2f s (gấp %.1f lần)"
              % (mf, mo, mf / max(0.01, mo)))
        if mf > 3 * mo:
            print("  ⇒ ca hỏng tốn LÂU HƠN HẲN ⇒ nghiêng về (b) HẾT GIỜ truyền lại.")
            print("    Hệ quả cho bài: đây là vấn đề THAM SỐ THỜI GIAN, phải nói đúng vậy,")
            print("    và phải thử nới thời gian chờ trước khi kết luận bất cứ điều gì.")
        else:
            print("  ⇒ ca hỏng KHÔNG lâu hơn đáng kể ⇒ nghiêng về (c) GIỚI HẠN SỐ MẢNH.")
    else:
        print("  (không đủ dữ liệu hai phía để tách)")

    # --- phán quyết cho bài ---
    print()
    print("  ═══ PHÁN QUYẾT ═══")
    real = {k: v for k, v in thresholds.items() if v and v["min_fail_frags"] is not None}
    if len(real) >= 2:
        vals = [v["min_fail_frags"] for v in real.values()]
        if max(vals) <= 2 * min(vals):
            print("  ✅ NHIỀU cài đặt cùng gãy ở ngưỡng TƯƠNG ĐƯƠNG (%s mảnh)."
                  % ", ".join(str(v) for v in sorted(vals)))
            print("     ⇒ ĐƯỢC PHÉP viết như một giới hạn thực tiễn, kèm khai rõ cài đặt.")
        else:
            print("  ⚠ Các cài đặt gãy ở ngưỡng RẤT KHÁC nhau (%s)."
                  % ", ".join(str(v) for v in sorted(vals)))
            print("     ⇒ Đây là chuyện THAM SỐ CÀI ĐẶT, KHÔNG được viết thành tuyên bố về")
            print("        giao thức. Phải nêu từng cài đặt riêng.")
    elif len(real) == 1:
        print("  ⛔ CHỈ MỘT cài đặt gãy. KHÔNG đủ để viết thành tuyên bố về giao thức.")
        print("     Phải tìm thêm cài đặt thứ hai (wolfSSL, mbedTLS, tinydtls) trước khi tin.")
    else:
        print("  ⛔ KHÔNG cài đặt nào gãy trong dải đã quét ⇒ phát hiện của M2 KHÔNG tái lập")
        print("     được ở đây. Phải đọc lại M2 trước khi dùng bất cứ số nào của nó.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"implementations": [{"key": k, "version": v} for k, v, _ in IMPLS],
                   "thresholds": thresholds, "rows": results}, f, indent=2, ensure_ascii=False)
    print("\n  → %s" % os.path.relpath(OUT, os.path.dirname(HERE)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
