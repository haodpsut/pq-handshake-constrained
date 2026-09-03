"""M5 — RANH GIOI GnuTLS: lap nhieu luot, va do CAC O CHUA THU.

⛔ VI SAO. Doc ngoai: "Fragment limits at 23 and 28 represent two single trials with cells
24-27 untested." Dung. Bai dang phat bieu mot ranh gioi tu HAI phep do don, va bo trong dung
khoang giua hai so do. Mot ranh gioi rut ra tu hai diem khong phai mot ranh gioi.

Tep nay:
  1. do DUNG cac o 24..27 ma truoc do khong ai cham toi
  2. lap N luot moi o, in TI LE THANH CONG chu khong in mot chu "xong/hong"
  3. bao cao o nao KHONG ON DINH (0 < ti le < 1), vi do moi la thong tin that

⚠ Van chay tren loopback, tuc TRE BANG 0. Doc ngoai neu dung diem nay va no van dung: loi do
bo dem gio thi loopback khong dai dien. Ket qua o day noi ve NGUONG, khong noi ve xac suat
tren link that.
"""
import io, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
CERTS = os.path.join(HERE, ".certs")
OUT = os.path.join(os.path.dirname(HERE), "results", "m5_boundary_repeats.json")
CERT, KEY = "c15360.pem", "k15360.pem"
REPEATS = int(os.environ.get("PQHS_REPEATS", "20"))
TIMEOUT = 30
PORT0 = 21100

# Chon MTU sao cho so manh roi dung vao 20..32, phu KIN khoang 24..27 con trong.
def mtu_for_frags(size, f):
    return max(1, -(-size // f))


def probe(crt, key, mtu, port):
    srv = subprocess.Popen(
        ["gnutls-serv", "--udp", "--port", str(port), "--mtu", str(mtu),
         "--nocookie", "--x509certfile", crt, "--x509keyfile", key],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    time.sleep(0.9)
    t0 = time.time()
    p = subprocess.Popen(["gnutls-cli", "--udp", "--port", str(port), "--mtu", str(mtu),
                          "--insecure", "127.0.0.1"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out = p.communicate(timeout=TIMEOUT)[0].decode("utf-8", "replace")
        timed_out = False
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(p.pid), 9)
        out = p.communicate(timeout=5)[0].decode("utf-8", "replace")
        timed_out = True
    dt = time.time() - t0
    srv.terminate()
    try:
        srv.wait(timeout=4)
    except subprocess.TimeoutExpired:
        srv.kill()
    return ("Handshake was completed" in out), timed_out, dt


def main():
    crt, key = os.path.join(CERTS, CERT), os.path.join(CERTS, KEY)
    if not os.path.exists(crt):
        print("  ⛔ thieu %s" % CERT); return 2
    size = os.path.getsize(crt)
    targets = list(range(20, 33))
    print("  GnuTLS · chung thu %d B · %d luot moi o · loopback\n" % (size, REPEATS))
    print("  %6s %6s %10s %9s %9s   %s" % ("manh", "MTU", "thanh cong", "TB giay", "het gio", ""))
    print("  " + "-" * 62)
    rows, port = [], PORT0
    for f in targets:
        mtu = mtu_for_frags(size, f)
        real_f = -(-size // mtu)
        ok = to = 0
        secs = []
        for _ in range(REPEATS):
            port += 1
            o, t, d = probe(crt, key, mtu, port)
            ok += 1 if o else 0
            to += 1 if t else 0
            secs.append(d)
        rate = ok / REPEATS
        tag = ""
        if 0 < rate < 1:
            tag = "⚠ KHONG ON DINH"
        rows.append({"target_frags": f, "mtu": mtu, "frags": real_f,
                     "repeats": REPEATS, "ok": ok, "timed_out": to,
                     "success_rate": rate, "mean_seconds": round(sum(secs)/len(secs), 2)})
        print("  %6d %6d %9d/%d %9.1f %9d   %s"
              % (real_f, mtu, ok, REPEATS, sum(secs)/len(secs), to, tag))

    print()
    unstable = [r for r in rows if 0 < r["success_rate"] < 1]
    allok = [r for r in rows if r["success_rate"] == 1]
    allbad = [r for r in rows if r["success_rate"] == 0]
    print("  o luon xong : %s" % ([r["frags"] for r in allok] or "khong"))
    print("  o luon hong : %s" % ([r["frags"] for r in allbad] or "khong"))
    print("  o KHONG ON DINH: %s" % ([("%d (%.0f%%)" % (r["frags"], 100*r["success_rate"]))
                                      for r in unstable] or "khong"))
    print()
    if allok and allbad:
        hi, lo = max(r["frags"] for r in allok), min(r["frags"] for r in allbad)
        if hi < lo and not unstable:
            print("  => ranh gioi SAC: luon xong toi %d manh, luon hong tu %d." % (hi, lo))
        else:
            print("  => ranh gioi KHONG sac. Co o khong on dinh, hoac hai vung chong lan.")
            print("     Bai phai noi la mot VUNG CHUYEN TIEP, khong phai mot nguong.")
    else:
        print("  => khong du hai phia de ket luan.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"impl": "gnutls 3.8.13", "cert": CERT, "cert_bytes": size,
                   "repeats": REPEATS, "note": "loopback, tre bang 0",
                   "rows": rows}, f, indent=2, ensure_ascii=False)
    print("\n  → %s" % os.path.basename(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
