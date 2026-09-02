"""M4 — SO VONG cua DTLS o co hau luong tu, DO DUOC chu khong trich RFC.

⛔ VI SAO CAN. Doc ngoai bat dung lo: bai so mot so luot EDHOC DO DUOC voi mot so vong DTLS
TRICH TU RFC 9147, trong khi chinh khao sat cua bai cho thay hai trong ba cai dat khong hoan
tat noi o co do. Nguyen van: "a measured EDHOC count against an unmeasured and possibly
unattainable DTLS count."

Tep nay do SO VONG that su cua DTLS, bang dung dai luong da dung cho CoAP: so lan luong DOI
CHIEU tren day. Chung thu dung CHUOI RSA-8192 vi mbedTLS khong nap noi khoa lon hon
(MBEDTLS_MPI_MAX_SIZE), nen phai lam bang tin to ra ma khong lam khoa to ra.
"""
import io
import json, os, re, socket, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
CERTS = os.path.join(HERE, ".certs")
MB = os.path.expanduser("~/mbedtls-src/programs/ssl")
MTU = 102
SRV, RLY = 20901, 20902


class Relay(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # ⚠ DTLS ban ca FLIGHT lien tiep, khac CoAP lock-step tung goi mot. Relay dung bo dem
        # mac dinh thi TRAN trong luc bung, mat goi, va bat tay hong -- dung phep do chu khong
        # dung giao thuc. Chinh la khac biet ma bai nay dang do.
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 << 20)
        self.s.bind(("127.0.0.1", RLY)); self.s.settimeout(0.05)
        self.srv = ("127.0.0.1", SRV); self.cli = None
        self.c2s = self.s2c = self.turns = 0; self.last = None; self.stop = False

    def run(self):
        while not self.stop:
            try: data, addr = self.s.recvfrom(65535)
            except socket.timeout: continue
            except OSError: break
            d = "s2c" if addr == self.srv else "c2s"
            if d == "c2s": self.cli = addr; self.c2s += 1; dst = self.srv
            else: self.s2c += 1; dst = self.cli
            if self.last is not None and d != self.last: self.turns += 1
            self.last = d
            if dst:
                try: self.s.sendto(data, dst)
                except OSError: pass


def run_case(crt, key):
    size = os.path.getsize(crt)
    srv = subprocess.Popen(
        [os.path.join(MB, "ssl_server2"), "dtls=1", "server_port=%d" % SRV,
         "mtu=%d" % MTU, "crt_file=%s" % crt, "key_file=%s" % key,
         "server_addr=127.0.0.1"], stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    time.sleep(1.3)
    r = Relay(); r.start()
    # ⚠ Bat stdout bang PIPE tra ve RONG du client co chay va datagram VAN di qua relay.
    # Ghi thang ra TEP thi bat duoc, dung nhu lan go loi thu cong da chay. Chon cach DA CHUNG
    # MINH LA CHAY, khong chon cach gon hon ma chua kiem.
    logf = "/tmp/m4_cli.log"
    with open(logf, "wb") as fh:
        p = subprocess.Popen(
            [os.path.join(MB, "ssl_client2"), "dtls=1", "server_port=%d" % RLY,
             "mtu=%d" % MTU, "server_addr=127.0.0.1", "auth_mode=none"],
            stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT,
            start_new_session=True)
        try:
            p.wait(timeout=90)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(p.pid), 9)
            p.wait(timeout=5)
    out = io.open(logf, encoding="utf-8", errors="replace").read()

    time.sleep(0.5); r.stop = True; r.join(timeout=2); r.s.close()
    srv.terminate()
    try: srv.wait(timeout=5)
    except subprocess.TimeoutExpired: srv.kill()
    # ⚠ Bo do ban dau doi dung chuoi "Ciphersuite is TLS-". Chay truc tiep thi khop, chay
    # qua relay thi KHONG, du bat tay VAN XONG (client in "Verifying peer X.509 ... ok" roi
    # ghi duoc du lieu). Lai la ca bo do bat sai chu khong phai giao thuc hong. Nen doi bang
    # chung sang thu chi ca THANH CONG moi sinh ra, va IN RA khi khong khop de con go.
    ok = bool(re.search(r"Ciphersuite is \S+", out)) or          bool(re.search(r"Verifying peer X\.509 certificate\.\.\. ok", out))
    if not ok:
        tail = " | ".join(x.strip() for x in out.strip().splitlines()[-3:])
        print("       (khong khop bo do; ba dong cuoi: %s)" % tail[:150])
    return {"cert": os.path.basename(crt), "cert_bytes": size,
            "frags_est": -(-size // MTU), "handshake_ok": ok,
            "datagrams": r.c2s + r.s2c, "turns": r.turns}


def main():
    cases = [("c8192.pem", "k8192.pem"), ("chain2.pem", "leaf.key"),
             ("chain3.pem", "leaf.key")]
    print("  mbedTLS DTLS 1.2 · MTU %d B · dem DATAGRAM va SO LAN DOI CHIEU\n" % MTU)
    print("  %-12s %7s %6s %10s %8s   %s" % ("chung thu", "byte", "manh",
                                             "datagram", "VONG", "bat tay"))
    print("  " + "-" * 62)
    rows = []
    for c, k in cases:
        cp, kp = os.path.join(CERTS, c), os.path.join(CERTS, k)
        if not (os.path.exists(cp) and os.path.exists(kp)):
            print("  %-12s (thieu tep)" % c); continue
        r = run_case(cp, kp); rows.append(r)
        print("  %-12s %7d %6d %10d %8d   %s"
              % (r["cert"], r["cert_bytes"], r["frags_est"], r["datagrams"],
                 r["turns"], "✅" if r["handshake_ok"] else "⛔"))
    ok = [r for r in rows if r["handshake_ok"]]
    print()
    if len(ok) >= 2:
        a, z = ok[0], ok[-1]
        print("  Tu %d len %d manh (x%.1f):" % (a["frags_est"], z["frags_est"],
                                                z["frags_est"] / a["frags_est"]))
        print("    datagram x%.2f · VONG x%.2f"
              % (z["datagrams"] / max(1, a["datagrams"]),
                 z["turns"] / max(1, a["turns"])))
        print("  => so vong DTLS o co hau luong tu gio la SO DO DUOC, khong con la so trich.")
    out = os.path.join(os.path.dirname(HERE), "results", "m4_dtls_pq_rounds.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"impl": "mbedtls 3.6.2", "dtls_version": "1.2", "mtu": MTU,
                   "counted": "UDP datagrams + direction changes via relay",
                   "rows": rows}, f, indent=2, ensure_ascii=False)
    print("\n  → %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
