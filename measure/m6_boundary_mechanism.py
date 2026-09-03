"""M6 — CAI GI THAT SU CHAN GnuTLS: so manh, MTU, hay chinh dong ho cua bo do?

⛔ VI SAO CO TEP NAY. Sau khi m5 chay xong, doi chieu hai nguon ket qua thi lo ra BA van de,
va ca ba deu nam duoi moi cong dang xanh.

  1. HAI NGUON NOI NGUOC NHAU. m3 do o (chung thu 5600 B, MTU 250) => 23 manh, XONG trong 8,6 s.
     m5 do o (chung thu 5600 B, MTU 244) => 23 manh, HONG 20/20. Cung chung thu, cung so manh,
     MTU lech 6 byte, ket qua lat han. Khong the ca hai cung dung.

  2. THUOC DO LA UOC LUONG, KHONG PHAI PHEP DEM. Ca hai tep tinh so manh bang cong thuc
     `ceil(cert_bytes / mtu)`. Do la kich thuoc CHUNG THU chia cho MTU, bo qua header ban ghi
     DTLS, header handshake, va viec mot flight con cho nhieu thong diep khac. So manh THAT
     tren day luon lon hon. Gan nguong, hai o cung duoc dan nhan "23" co the that su la 26 va
     27. ⇒ Mau thuan o muc 1 co the la do CAI THUOC, khong phai do phep do.

  3. MOI O HONG CUA m5 DUNG DUNG 30,0 GIAY = tran dong ho. Khong o nao tu bo cuoc som hon.
     Trong khi do ban thao dang viet: "the client still abandons the handshake on its own
     retransmission schedule, well inside that allowance". Du lieu noi nguoc: chinh BO DO giet,
     khong phai client bo cuoc. Day la dung cai "impatient harness" ma bai tuyen bo da loai tru.

TEP NAY DO BA THU, va moi thu deu de BAC BO duoc:

  A. TACH NHIEU. Quet luoi (chung thu x MTU) sao cho CUNG so manh uoc luong xuat hien o NHIEU
     MTU khac nhau, va cung MTU xuat hien o nhieu so manh khac nhau. Neu so manh la bien dieu
     khien thi ket qua phai khong doi theo MTU khi giu so manh; va nguoc lai.

  B. DEM MANH THAT bang relay UDP dem tung datagram, thay vi uoc luong tu kich thuoc tep. Day
     la cung ky thuat da dung o m1 va m4. Ranh gioi sau do phat bieu bang DON VI DO DUOC.

  C. NOI RONG DONG HO tu 30 s len LONG_TIMEOUT tren cac o hong. Neu o hong van hong va tien
     trinh TU THOAT truoc han, thi that su la client bo cuoc va cau trong bai dung. Neu no
     chay den het han moi bi giet, thi cau do SAI va phai xoa.

⚠ CHUNG DUONG TINH CHO CHINH PHEP DO. Relay them mot chang, va no co the tu lam hong bat tay.
   Nen moi o deu chay HAI lan: truc tiep va qua relay. Neu hai ben cho phan quyet khac nhau thi
   in ra va KHONG dung so cua relay de ket luan. Mot dung cu do chua duoc chung minh la trong
   suot thi khong dung de bac bo cai gi.

⚠ VAN TREN LOOPBACK, tre bang 0. Ket luan chi noi ve NGUONG, khong noi ve link that.
"""

import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
CERTS = os.path.join(HERE, ".certs")
OUT = os.path.join(os.path.dirname(HERE), "results", "m6_boundary_mechanism.json")

REPEATS = int(os.environ.get("PQHS_M6_REPEATS", "5"))
LONG_REPEATS = int(os.environ.get("PQHS_M6_LONG_REPEATS", "3"))
TIMEOUT = 30            # giong m5, de so sanh duoc truc tiep
LONG_TIMEOUT = 240      # 8 lan, de tra loi cau hoi C
WORKERS = int(os.environ.get("PQHS_M6_WORKERS", "10"))
PORT0 = 22000

# (nhan, tep chung thu, tep khoa). Nhieu co chung thu de TACH so manh khoi MTU.
CERT_SET = [
    ("c2048", "c2048.pem", "k2048.pem"),
    ("c8192", "c8192.pem", "k8192.pem"),
    ("c15360", "c15360.pem", "k15360.pem"),
]
MTUS = [102, 150, 200, 234, 244, 250, 267, 300, 400, 600]

CRT_OF = {a: b for a, b, _ in CERT_SET}
KEY_OF = {a: c for a, _, c in CERT_SET}


def est_frags(size, mtu):
    """Cong thuc CU, giu nguyen de doi chieu voi m3/m5. Day la UOC LUONG, khong phai phep dem."""
    return -(-size // mtu)


class Relay(threading.Thread):
    """Dem datagram theo tung chieu va dem so lan DOI CHIEU. Giong m4."""

    def __init__(self, listen_port, srv_port):
        super().__init__(daemon=True)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bo dem lon: DTLS ban ca flight lien tiep, bo dem mac dinh se TRAN va lam hong bat tay,
        # tuc dung phep do chu khong dung giao thuc.
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 << 20)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 << 20)
        self.s.bind(("127.0.0.1", listen_port))
        self.s.settimeout(0.05)
        self.srv = ("127.0.0.1", srv_port)
        self.cli = None
        self.c2s = self.s2c = self.turns = 0
        self.last = None
        self.stop = False

    def run(self):
        while not self.stop:
            try:
                data, addr = self.s.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            d = "s2c" if addr == self.srv else "c2s"
            if d == "c2s":
                self.cli = addr
                self.c2s += 1
                dst = self.srv
            else:
                self.s2c += 1
                dst = self.cli
            if self.last is not None and d != self.last:
                self.turns += 1
            self.last = d
            if dst:
                try:
                    self.s.sendto(data, dst)
                except OSError:
                    pass

    def close(self):
        self.stop = True
        try:
            self.s.close()
        except OSError:
            pass


def one_run(crt, key, mtu, srv_port, timeout, relay_port=None):
    """Mot lan bat tay. Tra ve dict. relay_port=None nghia la noi TRUC TIEP, khong qua relay."""
    srv = subprocess.Popen(
        ["gnutls-serv", "--udp", "--port", str(srv_port), "--mtu", str(mtu),
         "--nocookie", "--x509certfile", crt, "--x509keyfile", key],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL)
    time.sleep(0.9)
    r = None
    if relay_port is not None:
        r = Relay(relay_port, srv_port)
        r.start()
    connect_port = relay_port if relay_port is not None else srv_port
    t0 = time.time()
    p = subprocess.Popen(
        ["gnutls-cli", "--udp", "--port", str(connect_port), "--mtu", str(mtu),
         "--insecure", "127.0.0.1"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out = p.communicate(timeout=timeout)[0].decode("utf-8", "replace")
        killed = False
    except subprocess.TimeoutExpired:
        # ⛔ Phai giet CA NHOM tien trinh. Giet moi tien trinh cha thi con giu ong va lenh doc
        # treo vo han: mot timeout 120 s tung ghi lai 12.593 s vi dung loi nay.
        os.killpg(os.getpgid(p.pid), 9)
        out = p.communicate(timeout=5)[0].decode("utf-8", "replace")
        killed = True
    dt = time.time() - t0
    srv.terminate()
    try:
        srv.wait(timeout=4)
    except subprocess.TimeoutExpired:
        srv.kill()
    rec = {"ok": "Handshake was completed" in out,
           # ⭐ PHAN BIET HAI KIEU KHONG XONG, va day la ca cau hoi C:
           #   killed=True  -> BO DO giet khi het gio. KHONG ket luan duoc gi ve client.
           #   killed=False -> client TU THOAT truoc han. Day moi la "client bo cuoc".
           "killed_by_harness": killed,
           "self_exited": (not killed),
           "seconds": round(dt, 2),
           "allowance": timeout}
    if r is not None:
        time.sleep(0.25)          # cho not datagram cuoi di qua truoc khi dong
        rec.update({"dg_c2s": r.c2s, "dg_s2c": r.s2c,
                    "dg_total": r.c2s + r.s2c, "turns": r.turns})
        r.close()
    return rec


def cell_job(job):
    """Mot o cua luoi: (idx, nhan, tep crt, tep key, kich thuoc, mtu, so luot, allowance, co relay)."""
    idx, label, crt, key, size, mtu, reps, allowance, use_relay = job
    base = PORT0 + idx * 60
    runs = []
    for i in range(reps):
        srv_port = base + 2 * i
        rly_port = (base + 2 * i + 1) if use_relay else None
        try:
            runs.append(one_run(os.path.join(CERTS, crt), os.path.join(CERTS, key),
                                mtu, srv_port, allowance, rly_port))
        except Exception as e:                      # noqa: BLE001
            runs.append({"ok": False, "error": repr(e), "seconds": None,
                         "killed_by_harness": None, "self_exited": None,
                         "allowance": allowance})
    ok = sum(1 for r in runs if r["ok"])
    errs = sum(1 for r in runs if r.get("error"))
    dgs = [r["dg_total"] for r in runs if r.get("dg_total")]
    turns = [r["turns"] for r in runs if r.get("turns")]
    return {"cert": label, "cert_bytes": size, "mtu": mtu,
            "est_frags": est_frags(size, mtu),
            "relay": use_relay, "allowance": allowance,
            "repeats": reps, "ok": ok, "success_rate": ok / float(reps),
            # ⛔ o co loi KHONG duoc tinh la "hong". Lan chay dau tien cua tep nay co 150 lan
            # FileNotFoundError (gnutls khong o PATH) va van in "✅ so manh khong cho hai ket
            # cuc": mot phan quyet tren 0 don vi do duoc. Xem memory feedback-kiem-0-don-vi.
            "errors": errs, "valid": reps - errs,
            "killed_by_harness": sum(1 for r in runs if r["killed_by_harness"]),
            "self_exited_before_deadline": sum(
                1 for r in runs if r["self_exited"] and not r["ok"]),
            "mean_seconds": round(sum(r["seconds"] for r in runs if r["seconds"]) /
                                  max(1, len([r for r in runs if r["seconds"]])), 2),
            # ⭐ DON VI DO DUOC, thay cho uoc luong ceil(cert/mtu)
            "dg_total_median": sorted(dgs)[len(dgs) // 2] if dgs else None,
            "turns_median": sorted(turns)[len(turns) // 2] if turns else None,
            "runs": runs}


def sizes():
    out = {}
    for label, crt, key in CERT_SET:
        p = os.path.join(CERTS, crt)
        if not os.path.exists(p):
            print("  ⛔ thieu %s" % crt)
            return None
        out[label] = os.path.getsize(p)
    return out


def main():
    S = sizes()
    if S is None:
        return 2
    print("  chung thu: %s" % ", ".join("%s=%dB" % (k, v) for k, v in S.items()))
    print("  %d luot moi o · dong ho %d s · %d tien trinh song song\n"
          % (REPEATS, TIMEOUT, WORKERS))

    # ---- A + B: luoi tach nhieu, do QUA RELAY de dem datagram ----
    jobs, idx = [], 0
    for label, crt, key in CERT_SET:
        for mtu in MTUS:
            jobs.append((idx, label, crt, key, S[label], mtu, REPEATS, TIMEOUT, True))
            idx += 1
    print("  [A+B] luoi %d o qua relay ..." % len(jobs))
    with Pool(WORKERS) as pool:
        grid = pool.map(cell_job, jobs)

    print("  %-8s %5s %6s %7s %7s %8s %7s" %
          ("chung", "MTU", "~manh", "dg do", "doi chieu", "xong", "TB giay"))
    print("  " + "-" * 60)
    for g in sorted(grid, key=lambda x: (x["cert_bytes"], -x["mtu"])):
        print("  %-8s %5d %6d %7s %9s %6d/%d %7.1f"
              % (g["cert"], g["mtu"], g["est_frags"], g["dg_total_median"],
                 g["turns_median"], g["ok"], g["repeats"], g["mean_seconds"]))

    # ---- CHUNG DUONG TINH: relay co lam doi phan quyet khong ----
    ctrl_jobs, cidx = [], 100
    for g in grid:
        if g["success_rate"] in (0.0, 1.0):
            ctrl_jobs.append((cidx, g["cert"], CRT_OF[g["cert"]], KEY_OF[g["cert"]],
                              g["cert_bytes"], g["mtu"], 2, TIMEOUT, False))
            cidx += 1
    print("\n  [chung duong tinh] %d o chay lai KHONG qua relay ..." % len(ctrl_jobs))
    with Pool(WORKERS) as pool:
        ctrl = pool.map(cell_job, ctrl_jobs)
    bykey = {(c["cert"], c["mtu"]): c for c in ctrl}
    disagree = []
    for g in grid:
        c = bykey.get((g["cert"], g["mtu"]))
        if c is None:
            continue
        if (g["success_rate"] > 0.5) != (c["success_rate"] > 0.5):
            disagree.append((g["cert"], g["mtu"], g["success_rate"], c["success_rate"]))
    if disagree:
        print("  ⛔ RELAY LAM DOI PHAN QUYET o %d o. KHONG dung so relay de ket luan:"
              % len(disagree))
        for cert, mtu, a, b in disagree:
            print("     %s MTU %d: qua relay %.2f · truc tiep %.2f" % (cert, mtu, a, b))
    else:
        print("  ✅ relay trong suot: %d o cho cung phan quyet" % len(ctrl))

    # ---- C: noi rong dong ho tren cac o hong ----
    bad = [g for g in grid if g["success_rate"] == 0.0]
    long_jobs, lidx = [], 200
    for g in bad:
        long_jobs.append((lidx, g["cert"], CRT_OF[g["cert"]], KEY_OF[g["cert"]],
                          g["cert_bytes"], g["mtu"], LONG_REPEATS, LONG_TIMEOUT, False))
        lidx += 1
    print("\n  [C] %d o hong chay lai voi dong ho %d s (khong relay) ..."
          % (len(long_jobs), LONG_TIMEOUT))
    longarm = []
    if long_jobs:
        with Pool(WORKERS) as pool:
            longarm = pool.map(cell_job, long_jobs)
        print("  %-8s %5s %6s %8s %10s %12s %8s"
              % ("chung", "MTU", "~manh", "xong", "bi giet", "tu thoat", "TB giay"))
        print("  " + "-" * 62)
        for g in sorted(longarm, key=lambda x: (x["cert_bytes"], -x["mtu"])):
            print("  %-8s %5d %6d %6d/%d %8d/%d %10d/%d %8.1f"
                  % (g["cert"], g["mtu"], g["est_frags"], g["ok"], g["repeats"],
                     g["killed_by_harness"], g["repeats"],
                     g["self_exited_before_deadline"], g["repeats"], g["mean_seconds"]))

    # ---- CHAN: khong phan quyet tren o loi ----
    allcells = grid + ctrl + longarm
    bad_err = [c for c in allcells if c["errors"]]
    if bad_err:
        tot_err = sum(c["errors"] for c in bad_err)
        print("\n  ⛔ DUNG LAI. %d lan chay bi LOI o %d o (vd: %s)."
              % (tot_err, len(bad_err),
                 next((r["error"] for c in bad_err for r in c["runs"]
                       if r.get("error")), "?")))
        print("     O loi KHONG phai o hong. Khong in ket luan nao tren du lieu nay.")
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(
            {"aborted": "co o loi, khong ket luan", "grid": grid,
             "control_direct": ctrl, "long_allowance": longarm},
            indent=1, ensure_ascii=False))
        return 3

    # ---- PHAN QUYET ----
    print("\n  ══ KET LUAN ══")
    print("  (%d o · %d lan chay hop le · 0 loi)"
          % (len(allcells), sum(c["valid"] for c in allcells)))

    # A: so manh co du doan duoc ket qua khong?
    print("\n  A. cung SO MANH uoc luong o nhieu MTU khac nhau:")
    byfrag = {}
    for g in grid:
        byfrag.setdefault(g["est_frags"], []).append(g)
    split = {f: v for f, v in byfrag.items()
             if len(v) > 1 and len(set(x["success_rate"] > 0.5 for x in v)) > 1}
    if split:
        print("     ⛔ SO MANH KHONG du doan duoc ket qua. %d gia tri so manh cho ca hai"
              " ket cuc:" % len(split))
        for f, v in sorted(split.items()):
            for x in sorted(v, key=lambda y: y["mtu"]):
                print("        %2d manh · %-7s MTU %3d -> %s"
                      % (f, x["cert"], x["mtu"],
                         "xong" if x["success_rate"] > 0.5 else "HONG"))
    else:
        multi = [f for f, v in byfrag.items() if len(v) > 1]
        print("     ✅ khong co gia tri so manh nao cho ca hai ket cuc"
              " (%d gia tri xuat hien o >1 MTU)" % len(multi))

    # A': MTU co du doan duoc khong?
    print("\n  A'. cung MTU voi nhieu so manh khac nhau:")
    bymtu = {}
    for g in grid:
        bymtu.setdefault(g["mtu"], []).append(g)
    msplit = {m: v for m, v in bymtu.items()
              if len(set(x["success_rate"] > 0.5 for x in v)) > 1}
    if msplit:
        print("     ⇒ MTU cung KHONG mot minh quyet dinh: %d MTU cho ca hai ket cuc"
              % len(msplit))
    else:
        print("     ⇒ moi MTU cho mot ket cuc duy nhat, bat ke chung thu")

    # B: ranh gioi theo DON VI DO DUOC
    okd = [g["dg_total_median"] for g in grid
           if g["success_rate"] == 1.0 and g["dg_total_median"]]
    print("\n  B. don vi DO DUOC (datagram qua relay):")
    if okd:
        print("     o luon xong: trung vi datagram tu %d den %d" % (min(okd), max(okd)))
    else:
        print("     (khong o nao luon xong)")

    # C: dong ho
    print("\n  C. cac o hong: bo do giet hay client tu bo cuoc?")
    if longarm:
        tot = sum(g["repeats"] for g in longarm)
        kill = sum(g["killed_by_harness"] for g in longarm)
        self_ = sum(g["self_exited_before_deadline"] for g in longarm)
        rec = sum(g["ok"] for g in longarm)
        print("     %d lan chay voi dong ho %d s: %d xong · %d tu thoat som · %d bi giet"
              % (tot, LONG_TIMEOUT, rec, self_, kill))
        if rec > 0:
            print("     ⛔ %d/%d lan XONG khi cho lau hon. 'Hong' o m3/m5 la ARTEFACT"
                  " CUA DONG HO, khong phai gioi han giao thuc." % (rec, tot))
        elif kill == tot:
            print("     ⛔ MOI lan deu chay het %d s roi bi giet, KHONG lan nao tu bo cuoc."
                  " Cau 'client abandons the handshake on its own retransmission schedule'"
                  " KHONG duoc du lieu nay chong do." % LONG_TIMEOUT)
        elif self_ == tot:
            print("     ✅ moi lan client TU THOAT truoc han. Day dung la client bo cuoc,"
                  " khong phai bo do het kien nhan.")
        else:
            print("     ⚠ hon hop: %d tu thoat, %d bi giet. Phai noi ro ca hai." % (self_, kill))

    doc = {"repeats": REPEATS, "timeout": TIMEOUT, "long_timeout": LONG_TIMEOUT,
           "long_repeats": LONG_REPEATS, "cert_bytes": S,
           "note": "loopback, tre bang 0; est_frags la UOC LUONG ceil(cert/mtu),"
                   " dg_* la PHEP DEM qua relay",
           "relay_disagreements": disagree,
           "grid": grid, "control_direct": ctrl, "long_allowance": longarm}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc, indent=1, ensure_ascii=False))
    print("\n  da ghi %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
