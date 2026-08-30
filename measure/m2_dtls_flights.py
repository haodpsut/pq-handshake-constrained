"""ĐO ĐỐI CHỨNG — DTLS có giữ SỐ VÒNG không đổi khi kích thước bắt tay phình không?

VÌ SAO PHẢI ĐO NỬA NÀY. `measure_blockwise.py` đã đo phía EDHOC-trên-CoAP và mô hình khớp
7/7. Nhưng luận điểm của bài là một SO SÁNH, và nửa DTLS mới chỉ đọc RFC chứ chưa đo. Luật
của nhà: baseline phải khớp tuyên bố. Đo một bên rồi suy bên kia là đúng cái lỗi đó.

TUYÊN BỐ CẦN THỬ: DTLS truyền THEO FLIGHT, nên khi kích thước bắt tay phình thì SỐ DATAGRAM
tăng nhưng SỐ VÒNG (số lần đổi chiều) GIỮ NGUYÊN. Còn CoAP block-wise thì mỗi khối một vòng,
nên số vòng nở tuyến tính. Nếu phép đo cho thấy số vòng của DTLS CŨNG nở thì luận điểm của
bài SAI, và phải biết điều đó trước khi viết chứ không phải sau khi nộp.

ĐẠI LƯỢNG ĐO, dùng CHUNG cho cả hai giao thức để so được:

    số vòng := số lần luồng ĐỔI CHIỀU trên dây (một chuỗi c2s liên tiếp tính là MỘT lượt).

Với CoAP block-wise mỗi khối tự nó là một lần đổi chiều nên đại lượng này trùng số khối, đúng
như đã đo. Với DTLS thì cả một flight nhiều datagram chỉ tính MỘT lần.

CÁCH PHÌNH KÍCH THƯỚC: chứng thư RSA to dần. Không cài ML-DSA, vì lập luận nằm ở KÍCH THƯỚC
chứ không ở phép toán. Cỡ lớn nhất chạm đúng vùng ML-DSA.

⛔ HAI HẠN CHẾ PHẢI KHAI TRONG BÀI, không được lờ:

 (1) LibreSSL 3.3.6 của macOS KHÔNG bắt tay nổi với chính nó ở đây (client ghi 2436 B rồi
     `CONNECT_CR_SRVR_HELLO: read timeout expired`). Đã chuyển sang **GnuTLS 3.8.13**.
 (2) GnuTLS 3.8.13 chỉ có tới **DTLS 1.2** (danh sách protocol không có DTLS 1.3). Khác biệt
     1.2 so với 1.3 là SỐ flight (2-RTT so với 1-RTT), KHÔNG phải bản chất theo-flight. Nên
     phép đo này chứng minh CƠ CHẾ; con số "DTLS 1.3 = 2 vòng" vẫn phải dẫn **RFC 9147**,
     không được dẫn phép đo này.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, ".certs")
MTU = 102                      # payload khung 802.15.4, GIỐNG measure_blockwise.py
SERVER_PORT = 15761
RELAY_PORT = 15762

KEY_BITS = (2048, 4096, 8192, 15360)


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def make_cert(bits):
    key = os.path.join(WORK, "k%d.pem" % bits)
    crt = os.path.join(WORK, "c%d.pem" % bits)
    if not os.path.exists(crt):
        sh("openssl req -x509 -newkey rsa:%d -keyout %s -out %s -days 2 -nodes "
           "-subj '/CN=t' 2>/dev/null" % (bits, key, crt))
    if not os.path.exists(crt):
        return None, None, 0
    return key, crt, os.path.getsize(crt)


class Relay(threading.Thread):
    """Relay UDP: đếm datagram VÀ đếm số lần ĐỔI CHIỀU. Đây là chỗ đo."""

    def __init__(self):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", RELAY_PORT))
        self.sock.settimeout(0.3)
        self.srv = ("127.0.0.1", SERVER_PORT)
        self.cli = None
        self.n_c2s = self.n_s2c = 0
        self.turns = 0
        self.last = None
        self.stop = False

    def run(self):
        while not self.stop:
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            d = "s2c" if addr == self.srv else "c2s"
            if d == "c2s":
                self.cli = addr
                self.n_c2s += 1
                dst = self.srv
            else:
                self.n_s2c += 1
                dst = self.cli
            if self.last is not None and d != self.last:
                self.turns += 1
            self.last = d
            if dst:
                try:
                    self.sock.sendto(data, dst)
                except OSError:
                    pass


def run_case(bits):
    key, crt, csize = make_cert(bits)
    if key is None:
        return None

    srv = subprocess.Popen(
        ["gnutls-serv", "--udp", "--port", str(SERVER_PORT), "--mtu", str(MTU),
         "--nocookie", "--x509certfile", crt, "--x509keyfile", key],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    time.sleep(1.2)

    relay = Relay()
    relay.start()

    try:
        cli = subprocess.run(
            ["gnutls-cli", "--udp", "--port", str(RELAY_PORT), "--mtu", str(MTU),
             "--insecure", "127.0.0.1"],
            input="q\n", capture_output=True, text=True, timeout=120)
        out = (cli.stdout or "") + (cli.stderr or "")
    except subprocess.TimeoutExpired:
        out = ""

    time.sleep(0.5)
    relay.stop = True
    relay.join(timeout=2)
    relay.sock.close()
    srv.terminate()
    try:
        srv.wait(timeout=5)
    except subprocess.TimeoutExpired:
        srv.kill()

    # Tiêu chí "bắt tay XONG" phải là bằng chứng chỉ ca THÀNH CÔNG mới sinh ra được.
    # ⛔ Trước đó tôi dùng grep "cipher", và đầu ra của ca HỎNG cũng chứa "Cipher is (NONE)",
    # nên nó báo xanh trên 4/4 ca hỏng. Ở đây dùng đúng câu GnuTLS chỉ in khi thành công.
    ok = "Handshake was completed" in out
    return {"bits": bits, "cert_bytes": csize, "handshake_completed": ok,
            "datagrams_c2s": relay.n_c2s, "datagrams_s2c": relay.n_s2c,
            "datagrams_total": relay.n_c2s + relay.n_s2c,
            "turns": relay.turns}


def main():
    if shutil.which("gnutls-serv") is None:
        print("  ⛔ khong co gnutls-serv"); return 1
    os.makedirs(WORK, exist_ok=True)
    ver = sh("gnutls-serv --version 2>&1 | head -1").stdout.strip()
    print("  %s · DTLS 1.2 · MTU ép về %d B (payload khung 802.15.4)\n" % (ver, MTU))
    print("  %9s %11s %11s %8s   %s"
          % ("khoá RSA", "chứng thư", "datagram", "VÒNG", "bắt tay"))
    print("  " + "-" * 62)

    rows = []
    for b in KEY_BITS:
        r = run_case(b)
        if r is None:
            print("  %9d %11s   ⛔ khong sinh duoc chung thu" % (b, "-"))
            continue
        rows.append(r)
        print("  %9d %11d %11d %8d   %s"
              % (b, r["cert_bytes"], r["datagrams_total"], r["turns"],
                 "✅ xong" if r["handshake_completed"] else "⛔ KHÔNG xong"))

    print()
    good = [r for r in rows if r["handshake_completed"] and r["datagrams_total"] > 0]
    verdict = None
    if len(good) >= 2:
        a, z = good[0], good[-1]
        gsize = z["cert_bytes"] / a["cert_bytes"]
        gdat = z["datagrams_total"] / max(1, a["datagrams_total"])
        gturn = z["turns"] / max(1, a["turns"])
        print("  Chứng thư %d B → %d B (×%.1f):" % (a["cert_bytes"], z["cert_bytes"], gsize))
        print("    số DATAGRAM  ×%.2f" % gdat)
        print("    số VÒNG      ×%.2f" % gturn)
        verdict = gturn < 1.5
        print()
        if verdict:
            print("  ✅ SỐ VÒNG KHÔNG NỞ theo kích thước, đúng tuyên bố theo-flight.")
            print("     Đối chiếu measure_blockwise.py: cùng đại lượng, phía CoAP nở tuyến")
            print("     tính (13 → 19 → 52 → 69). Khác biệt CƠ CHẾ giờ đã ĐO ở CẢ HAI phía.")
        else:
            print("  ⛔ SỐ VÒNG CŨNG NỞ. Tuyên bố trung tâm của bài SAI. Dừng, đọc lại.")
    else:
        print("  ⛔ CHƯA ĐỦ CA CHẠY ĐƯỢC (%d/%d). Không kết luận." % (len(good), len(rows)))

    out = os.path.join(os.path.dirname(HERE), "results", "m2_dtls_flights.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"implementation": ver, "dtls_version": "1.2",
                   "caveat": "GnuTLS 3.8.13 khong co DTLS 1.3; phep do nay chung minh CO CHE "
                             "theo flight. Con so 'DTLS 1.3 = 2 vong' phai dan RFC 9147.",
                   "mtu": MTU, "counted": "UDP datagrams + direction changes via relay",
                   "turns_constant": verdict, "rows": rows}, f, indent=2, ensure_ascii=False)
    print("\n  → %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
