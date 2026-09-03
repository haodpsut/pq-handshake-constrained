"""Sinh TOÀN BỘ hình và bảng của bài, từ mô hình và từ JSON đo được.

LUẬT ÁP DỤNG, lấy từ những lần hỏng trước:
  - Không con số nào gõ tay. Mô hình lấy từ `analysis/model.py`, số đo lấy từ `results/*.json`.
  - Mỗi tệp ra có ĐÚNG MỘT bộ sinh. Không tệp nào bị hai chỗ cùng ghi.
  - Hình phân biệt bằng MARKER và NÉT, không chỉ bằng màu (in đen trắng vẫn đọc được).
  - Bảng xuất ra .tex để `\\input`, KHÔNG dán số vào bản thảo.
  - Thiếu tệp đo thì DỪNG và nói thiếu cái gì, không vẽ hình rỗng.

Chạy: python3 figures/make_figures.py
"""

import json
import os
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import model as M                                            # noqa: E402

OUT = os.path.join(HERE, "out")
RES = os.path.join(ROOT, "results")

# ── stylesheet, theo bộ style của nhà (transaction-figure-kit) ────────────────
mpl.rcParams.update({
    "font.family": "serif", "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.direction": "in", "ytick.direction": "in",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "lines.linewidth": 1.1, "lines.markersize": 4.5,
    "legend.frameon": False, "figure.dpi": 130,
    "pdf.fonttype": 42, "ps.fonttype": 42,
})
# Okabe-Ito, an toàn cho người mù màu
C = {"blue": "#0072B2", "verm": "#D55E00", "green": "#009E73",
     "gray": "#555555", "orange": "#E69F00", "purple": "#CC79A7"}

# Khổ hình: một cột IEEE = 3.5 in, hai cột = 7.16 in.
# ⚠ Hình ngang phải TRẢI HAI CỘT, đây là luật của nhà rút ra từ một lần chữ bị co còn 3,9 pt.
W1, W2 = 3.5, 7.16


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, "%s.%s" % (name, ext)), bbox_inches="tight")
    plt.close(fig)
    print("    → %s.pdf / .png" % name)


def load(fname, what, expect=None):
    """Nạp JSON đo được VÀ IN XUẤT XỨ của nó.

    ⚠ Một tệp kết quả CŨ nằm đúng chỗ trông y hệt tệp mới. Hình 4 từng vẽ ra MỘT cài đặt
    thay vì ba, vì `results/m3_*.json` còn là bản chạy trên máy khác từ trước và rsync không
    đè do tệp đích mới hơn. Không cổng nào bắt được, vì tệp có tồn tại và JSON hợp lệ.
    ⇒ Bộ sinh phải IN ra nó đang đọc cái gì, và KÊU khi nội dung khác kỳ vọng.
    """
    p = os.path.join(RES, fname)
    if not os.path.exists(p):
        print("  ⛔ THIẾU %s (%s). Chạy phép đo tương ứng trước." % (fname, what))
        return None
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    rows = d.get("rows", [])
    impls = sorted({r["impl"] for r in rows}) if rows and "impl" in rows[0] else []
    stamp = int(os.path.getmtime(p))
    print("    %-28s %3d dòng%s  [mtime %d]"
          % (fname, len(rows), ("  cài đặt: " + ", ".join(impls)) if impls else "", stamp))
    if expect and impls and sorted(expect) != impls:
        print("      ⚠ KỲ VỌNG %s NHƯNG CÓ %s. Tệp có thể là bản CŨ. Kiểm trước khi vẽ."
              % (", ".join(sorted(expect)), ", ".join(impls)))
    return d


def _esc(x):
    """Thoat ky tu dac biet cua LaTeX.

    ⚠ Ban truoc khong thoat, nen mot ten truong hop chua `msg_1` sinh ra 56 loi
    "Missing $ inserted". Bo sinh phai an toan KE CA khi nguon khong sach: du lieu do duoc
    khong co nghia vu biet no se di vao LaTeX.
    """
    s = str(x)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
                 ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s


def texify(rows, header, caption, label, colspec, note=None, wide=False):
    """Sinh bang .tex.

    ⚠ `wide=True` dung moi truong `table*` de TRAI HAI COT. Bang rong hon cot ma van dung
    `table` thi LaTeX bao "Overfull \\hbox ... too wide" -- mot CANH BAO chu khong phai loi,
    nen no de bi bo qua, va chu se tran ra le. Do duoc: 38,7pt va 12,1pt o hai bang dau tien.
    Luat cua nha: gioi han that la MEP COT, khong phai mep trang.
    """
    env = "table*" if wide else "table"
    L = [r"\begin{%s}[t]" % env, r"\centering",
         r"\caption{%s}" % caption, r"\label{%s}" % label,
         r"\footnotesize", r"\begin{tabular}{%s}" % colspec, r"\hline",
         " & ".join(header) + r" \\", r"\hline"]
    L += [" & ".join(_esc(c) for c in r) + r" \\" for r in rows]
    L += [r"\hline", r"\end{tabular}"]
    if note:
        L.append(r"\\[2pt]{\footnotesize %s}" % note)
    L.append(r"\end{%s}" % env)
    return "\n".join(L) + "\n"


def write_tex(name, body):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write("%% SINH TU figures/make_figures.py -- KHONG sua tay.\n")
        f.write(body)
    print("    → %s" % name)


# ══════════════════════════════════════════════════════════════════════════════
# HÌNH 1 — trục BYTE: lợi thế kích thước co lại
# ══════════════════════════════════════════════════════════════════════════════
def fig_size_ratio():
    names, ratios, es, ds = [], [], [], []
    for kem, sig in M.PARAM_SETS:
        e, d, r = M.size_ratio(kem, sig)
        names.append("%s\n%s" % (kem.replace("ML-KEM-", "K"), sig.replace("ML-DSA-", "D")))
        ratios.append(r); es.append(e); ds.append(d)

    fig, ax = plt.subplots(figsize=(W2, 2.5))
    x = range(len(names))
    ax.bar(x, ratios, color=C["blue"], width=0.6, edgecolor="black", linewidth=0.4)
    ax.axhline(M.D_CLASSIC / M.E_SIG, color=C["verm"], ls="--", lw=1.0,
               label="classical, signature mode (%.2f$\\times$)" % (M.D_CLASSIC / M.E_SIG))
    ax.axhline(M.D_CLASSIC / M.E_STATIC_DH, color=C["orange"], ls=":", lw=1.0,
               label="classical, Static DH (%.2f$\\times$), no PQ variant"
                     % (M.D_CLASSIC / M.E_STATIC_DH))
    ax.axhline(1.0, color=C["gray"], lw=0.6)
    ax.set_xticks(list(x)); ax.set_xticklabels(names)
    ax.set_ylabel("DTLS / EDHOC (byte ratio)")
    ax.set_ylim(0, 9.6)
    # Đặt vào DẢI TRỐNG giữa hai đường mốc, không đặt "upper right" nơi chú giải đè lên
    # chính đường 8,85x mà nó đang giải thích.
    ax.legend(loc="center left", bbox_to_anchor=(0.02, 0.62), ncol=1)
    for i, r in enumerate(ratios):
        ax.text(i, r + 0.12, "%.2f" % r, ha="center", fontsize=7)
    save(fig, "fig1-size-ratio")
    return ratios


# ══════════════════════════════════════════════════════════════════════════════
# HÌNH 2 — trục SỐ LƯỢT: chỗ lợi thế đảo chiều, kèm ĐIỂM ĐO
# ══════════════════════════════════════════════════════════════════════════════
def fig_exchanges(m1):
    sizes = list(range(40, 5200, 20))
    coap = [M.exchanges_for_message(s) for s in sizes]

    fig, ax = plt.subplots(figsize=(W1, 2.4))
    ax.plot(sizes, coap, color=C["blue"], lw=1.2,
            label="EDHOC over CoAP, block-wise (model)")
    ax.axhline(M.DTLS_FLIGHT_RT, color=C["verm"], ls="--", lw=1.2,
               label="DTLS 1.3, flight-based [RFC 9147]")
    ax.axvline(M.FRAME_PAYLOAD, color=C["gray"], ls=":", lw=0.8)
    # ⚠ LUẬT rút ra sau BỐN lần đè trong cùng một buổi vẽ: chữ đặt trong vùng vẽ phải cạnh
    # tranh chỗ với dữ liệu VÀ với chú giải, mà cả hai đều đổi theo dữ liệu. Nên chú thích
    # mốc đặt ở MÉP DƯỚI bằng toạ độ tương đối, chỗ duy nhất chắc chắn trống ở mọi hình này.
    # Nhan moc dat DUOI truc, ngoai vung ve, de khong tranh cho voi duong du lieu.
    ax.annotate("802.15.4 frame\n(%d B)" % M.FRAME_PAYLOAD,
                xy=(M.FRAME_PAYLOAD, 8), xytext=(950, 30),
                fontsize=6.5, color=C["gray"], ha="left", va="center",
                arrowprops=dict(arrowstyle="-", lw=0.5, color=C["gray"]))

    if m1:
        mx = [r["bytes"] for r in m1["rows"]]
        my = [r["measured_c2s"] for r in m1["rows"]]
        # ⚠ Doc ngoai: hinh nay LAN datagram voi cap yeu-cau/hoi-dap. Diem do la so datagram
        # THEO MOT CHIEU (client -> server), va vi block-wise la lock-step nen no BANG so
        # luot. Phai noi ro trong nhan, khong de nguoi doc tu suy.
        ax.plot(mx, my, "o", color="black", ms=4, mfc="none", mew=0.9,
                label="measured: client$\\to$server datagrams (aiocoap, %d/%d agree)"
                      % (m1["n_match"], m1["n_match"] + m1["n_mismatch"]))
    ax.set_xlabel("handshake message size (byte)")
    ax.set_ylabel("exchanges (request--response pairs)")
    ax.set_xlim(0, 5200); ax.set_ylim(0, 88)
    # ⚠ Chu giai o "upper left" de len duong du lieu o canh phai cua khung chu, vi duong
    # di tu duoi trai len tren phai. Vung trong that su la DUOI PHAI.
    # ⚠ Duong chay CHEO tu duoi trai len tren phai, nen CA HAI goc con lai deu bi chu giai
    # dai cham vao. Da thu "upper left" va "lower right", hong ca hai. Dat NGOAI khung ve.
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=1,
              handlelength=1.6, borderaxespad=0.0)
    save(fig, "fig2-exchanges")


# ══════════════════════════════════════════════════════════════════════════════
# HÌNH 3 — HÌNH CHÍNH: quét cỡ khối, hai trục tối ưu LỆCH nhau, trần RIOT
# ══════════════════════════════════════════════════════════════════════════════
def fig_blocksize(m4=None):
    msgs = M.pq_messages("ML-KEM-768", "ML-DSA-65")
    # Moc DTLS: (so vong, so datagram) DO DUOC, lay tu M4. Khong co M4 thi khong ve moc,
    # thay vi ve mot moc trich tu RFC roi de nguoi doc tuong la do duoc.
    dtls_ref = None
    if m4:
        ok = [r for r in m4["rows"] if r["handshake_ok"]]
        if ok:
            dtls_ref = (ok[0]["turns"], max(r["datagrams"] for r in ok))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 2.6))

    for ax, idx, ylab, ttl in ((a1, 0, "expected exchanges", "(a) latency axis"),
                               (a2, 1, "expected frame transmissions", "(b) energy axis")):
        for p, col, mk, ls in ((0.00, C["blue"], "o", "-"),
                               (0.01, C["green"], "s", "--"),
                               (0.05, C["verm"], "^", "-.")):
            ys = [M.blocksize_cost(msgs, b, p)[idx] for b in M.BLOCK_SIZES]
            ax.plot(M.BLOCK_SIZES, ys, color=col, marker=mk, ls=ls,
                    label="frame loss p=%.2f" % p)
            best = min(range(len(ys)), key=lambda i: ys[i])
            ax.plot(M.BLOCK_SIZES[best], ys[best], "*", color=col, ms=11, mec="black",
                    mew=0.4, zorder=5)
        ax.axvspan(M.RIOT_BLOCK_MAX, M.BLOCK_SIZES[-1] * 1.15, color="black", alpha=0.06)
        # ⚠ Doc ngoai: bang (b) gan nhan truc NANG LUONG ma khong co cot doi chieu DTLS, nen
        # nguoi doc khong biet duong cong dang so voi cai gi. Ve moc DTLS DO DUOC o ca hai
        # bang: (a) so vong, (b) so khung phai phat.
        if dtls_ref is not None and dtls_ref[idx] is not None:
            ax.axhline(dtls_ref[idx], color=C["gray"], ls="--", lw=0.9)
        ax.set_xscale("log", base=2); ax.set_yscale("log")
        ax.set_xlim(M.BLOCK_SIZES[0] * 0.8, M.BLOCK_SIZES[-1] * 1.15)
        ax.set_xticks(M.BLOCK_SIZES)
        ax.set_xticklabels([str(b) for b in M.BLOCK_SIZES])
        ax.set_xlabel("CoAP block size (byte)"); ax.set_ylabel(ylab)
        ax.set_title(ttl, fontsize=8)
    if dtls_ref:
        a1.text(0.03, 0.06, "DTLS measured = %d" % dtls_ref[0],
                transform=a1.transAxes, fontsize=7, color=C["gray"])
        a2.text(0.03, 0.06, "DTLS measured = %d" % dtls_ref[1],
                transform=a2.transAxes, fontsize=7, color=C["gray"])
    a1.legend(loc="lower left", bbox_to_anchor=(0.0, 0.13))

    # ⚠ Ý nghĩa vùng tô thuộc về CAPTION, không thuộc về mặt hình. Hai lần đặt nó lên hình
    # là hai lần đè: lần đầu đè đường dữ liệu ở (a) và nhãn trục ở (b) vì dùng toạ độ dữ liệu
    # tuyệt đối; lần sau đè tiêu đề bảng vì đẩy lên trên. Chữ trên hình phải cạnh tranh chỗ
    # với dữ liệu, còn caption thì không. Chỉ để lại một vạch mốc.
    for ax in (a1, a2):
        ax.axvline(M.RIOT_BLOCK_MAX, color=C["gray"], ls="-", lw=0.8, alpha=0.8)
    save(fig, "fig3-blocksize-tradeoff")


# ══════════════════════════════════════════════════════════════════════════════
# HÌNH 4 — khảo sát CÀI ĐẶT: ba giới hạn khác nhau trên link ràng buộc
# ══════════════════════════════════════════════════════════════════════════════
def fig_implementations(m3):
    if not m3:
        return
    impls = sorted({r["impl"] for r in m3["rows"]})
    mtus = sorted({r["mtu"] for r in m3["rows"]})
    fig, axes = plt.subplots(1, len(impls), figsize=(W2, 2.5), sharey=True)
    if len(impls) == 1:
        axes = [axes]
    for ax, impl in zip(axes, impls):
        rs = [r for r in m3["rows"] if r["impl"] == impl]
        okx = [r["mtu"] for r in rs if r["handshake_ok"]]
        oky = [r["frags_est"] for r in rs if r["handshake_ok"]]
        bdx = [r["mtu"] for r in rs if not r["handshake_ok"]]
        bdy = [r["frags_est"] for r in rs if not r["handshake_ok"]]
        ax.plot(okx, oky, "o", color=C["green"], ms=5, label="handshake completes")
        ax.plot(bdx, bdy, "x", color=C["verm"], ms=6, mew=1.4, label="fails")
        ax.axvline(M.FRAME_PAYLOAD, color=C["gray"], ls=":", lw=0.9)
        ax.set_xscale("log"); ax.set_yscale("log")
        # ⚠ Để matplotlib tự đánh vạch trên thang log thì các nhãn phụ chồng lên nhau thành
        # "2x10^3x10^4x10^5x10^2", không đọc được. Đặt vạch TƯỜNG MINH đúng các MTU đã đo và
        # tắt vạch phụ. Cùng lớp lỗi với chú thích đặt bằng toạ độ tuyệt đối: mặc định của
        # thư viện đúng cho khổ khác, không đúng cho khổ này.
        ax.set_xticks(mtus)
        ax.set_xticklabels([str(m) for m in mtus], fontsize=6.5, rotation=45)
        ax.xaxis.set_minor_locator(mpl.ticker.NullLocator())
        ax.set_yticks([2, 5, 10, 20, 50])
        ax.set_yticklabels(["2", "5", "10", "20", "50"])
        ax.yaxis.set_minor_locator(mpl.ticker.NullLocator())
        ax.set_xlabel("MTU (byte)")
        ax.set_title(impl, fontsize=8)
    axes[0].set_ylabel("fragments per message")
    # Chú giải đặt NGOÀI vùng vẽ để không tranh chỗ với điểm dữ liệu.
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=7,
               bbox_to_anchor=(0.5, -0.16))
    save(fig, "fig4-implementations")


# ══════════════════════════════════════════════════════════════════════════════
# HÌNH 5 — phân rã theo bản tin: chỗ VƯỢT NGƯỠNG, và SÀN của lập luận
# ══════════════════════════════════════════════════════════════════════════════
def fig_per_message():
    labels = ["message_1", "message_2", "message_3"]
    classic = [M.CLASSIC_MSG[k] for k in labels]
    floor = M.pq_messages("ML-KEM-512", "ML-DSA-44", pq_sign=False)
    full = M.pq_messages("ML-KEM-768", "ML-DSA-65")

    fig, ax = plt.subplots(figsize=(W1, 2.3))
    x = range(3); w = 0.26
    ax.bar([i - w for i in x], classic, w, label="classical", color=C["gray"],
           edgecolor="black", lw=0.4)
    ax.bar(list(x), [floor[k] for k in labels], w, label="floor: ML-KEM-512 only",
           color=C["orange"], edgecolor="black", lw=0.4)
    ax.bar([i + w for i in x], [full[k] for k in labels], w,
           label="K768 + D65", color=C["blue"], edgecolor="black", lw=0.4)
    ax.axhline(M.FRAME_PAYLOAD, color=C["verm"], ls="--", lw=1.1)
    # Đặt ngay TRÊN vạch và ở KHOẢNG TRỐNG giữa hai nhóm cột, không đặt ở mép phải nơi cột
    # K768 vươn cao. Vị trí trống phụ thuộc dữ liệu, nên phải nhìn hình rồi mới chốt.
    ax.text(0.52, M.FRAME_PAYLOAD * 1.12, "802.15.4 frame (%d B)" % M.FRAME_PAYLOAD,
            fontsize=6.5, color=C["verm"], ha="center", va="bottom")
    ax.set_yscale("log"); ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.set_ylabel("byte")
    ax.legend(loc="upper left", fontsize=7)
    save(fig, "fig5-per-message")


# ══════════════════════════════════════════════════════════════════════════════
# BẢNG
# ══════════════════════════════════════════════════════════════════════════════
def tables(m1, m3):
    # B1: kích thước và tỉ số, 9 bộ tham số
    rows = []
    for kem, sig in M.PARAM_SETS:
        e, d, r = M.size_ratio(kem, sig)
        msgs = M.pq_messages(kem, sig)
        rows.append([kem.replace("ML-KEM-", "K"), sig.replace("ML-DSA-", "D"),
                     e, d, "%.2f" % r, M.edhoc_exchanges(msgs), M.DTLS_FLIGHT_RT])
    write_tex("tab1-parameter-sets.tex", texify(
        rows, ["KEM", "SIG", "EDHOC (B)", "DTLS (B)", "ratio", "EDHOC exch.", "DTLS exch."],
        "Handshake size and exchange count for the nine NIST parameter sets. The classical "
        "ratio is %.2f$\\times$ in signature mode and %.2f$\\times$ for Static DH, which has "
        "no post-quantum variant." % (M.D_CLASSIC / M.E_SIG, M.D_CLASSIC / M.E_STATIC_DH),
        "tab:params", "llrrrrr",
        "EDHOC exchanges assume a %d~B block size, the default in Contiki-NG and RIOT. "
        "The DTLS count is from RFC~9147 and is not measured here." % M.COAP_BLOCK))

    # B2: mô hình so với ĐO ĐƯỢC
    if m1:
        # ⚠ KHONG dat lenh LaTeX (\checkmark) vao o bang: `_esc` thoat het ky tu dac biet
        # nen no in ra nguyen van "\{ }checkmark". Do chinh ban sua thoat ky tu gay ra. Dung
        # ky tu thuong, bo sinh khong can biet gi ve LaTeX.
        rows = [[r["case"], r["bytes"], r["predicted"], r["measured_c2s"],
                 "yes" if r["match"] else "NO"] for r in m1["rows"]]
        write_tex("tab2-model-vs-measured.tex", texify(
            rows, ["case", "byte", "model", "measured", "agree"],
            "Exchange-count model against an independent CoAP implementation (%s). Datagrams "
            "are counted by a UDP relay between client and server; %d/%d agree."
            % (m1["implementation"], m1["n_match"], m1["n_match"] + m1["n_mismatch"]),
            "tab:validation", "lrrrc",
            "Block size %d~B, engaging above %d~B. This validates the counting only; latency "
            "and energy are not measured here." % (m1["block_size"], m1["frame_payload"]),
            wide=True))

    # B3: giới hạn của từng cài đặt
    if m3:
        rows = []
        for impl in sorted({r["impl"] for r in m3["rows"]}):
            rs = [r for r in m3["rows"] if r["impl"] == impl]
            ok = [r for r in rs if r["handshake_ok"]]
            bad = [r for r in rs if not r["handshake_ok"]]
            at102 = [r for r in rs if r["mtu"] == 102]
            ok102 = sum(1 for r in at102 if r["handshake_ok"])
            if not bad:
                bound = "none found in range"
            elif max(r["frags_est"] for r in ok) < min(r["frags_est"] for r in bad):
                bound = "fragments: %d ok / %d fails" % (
                    max(r["frags_est"] for r in ok), min(r["frags_est"] for r in bad))
            elif min(r["mtu"] for r in ok) > max(r["mtu"] for r in bad):
                bound = "MTU floor: %d fails / %d ok" % (
                    max(r["mtu"] for r in bad), min(r["mtu"] for r in ok))
            else:
                bound = "no separating axis"
            rows.append([impl, "%d/%d" % (len(ok), len(rs)),
                         "%d/%d" % (ok102, len(at102)) if at102 else "--", bound])
        write_tex("tab3-implementations.tex", texify(
            rows, ["implementation", "cells", "at frame MTU", "bounded by"],
            "Bounding quantity for each DTLS implementation. `Cells' counts configurations "
            "completing a handshake out of those swept; `at frame MTU' restricts that to "
            "MTU~%d~B." % M.FRAME_PAYLOAD,
            "tab:impls", "llll",
            "The three are bounded by different quantities, so these results characterise the "
            "implementations and not the DTLS protocol.", wide=True))


def captions(m1, m3, m4=None):
    """Sinh CAPTION ra .tex.

    Caption chứa số (tỉ số, số ô khớp, ngưỡng), nên nó cũng là bề mặt tuyên bố và cũng phải
    SINH RA. Gõ tay caption là cách bài mâu thuẫn với chính hình của nó sau một lần chạy lại.
    """
    n_ok = m1["n_match"] if m1 else 0
    n_all = (m1["n_match"] + m1["n_mismatch"]) if m1 else 0
    impl_txt = ""
    if m3:
        parts = []
        for impl in sorted({r["impl"] for r in m3["rows"]}):
            rs = [r for r in m3["rows"] if r["impl"] == impl]
            parts.append("%s %d/%d" % (impl, sum(1 for r in rs if r["handshake_ok"]), len(rs)))
        impl_txt = "; ".join(parts)

    defs = {
        "capSizeRatio":
            "EDHOC's size advantage over DTLS~1.3 across the nine NIST parameter sets. Dashed: "
            "the classical ratio in signature mode ($%.2f\\times$). Dotted: Static DH "
            "($%.2f\\times$), a mode with no post-quantum variant, since methods~1--3 of "
            "RFC~9528 rest on static Diffie--Hellman."
            % (M.D_CLASSIC / M.E_SIG, M.D_CLASSIC / M.E_STATIC_DH),
        "capExchanges":
            "Exchanges against handshake message size. EDHOC over CoAP uses lock-step "
            "block-wise transfer, so its count grows linearly; DTLS~1.3 is flight-based and "
            "holds at %d exchanges whatever the size [RFC~9147]. Open circles are measured on "
            "an independent CoAP implementation, agreeing with the model in %d of %d cases. "
            "The DTLS figure is cited, not measured here."
            % (M.DTLS_FLIGHT_RT, n_ok, n_all),
        "capBlocksize":
            "Sweep of every block size RFC~7959 permits, for an ML-KEM-768 with ML-DSA-65 "
            "handshake. Stars mark each curve's optimum. The shaded region and the vertical "
            "rule at %d~B mark RIOT's compile-time ceiling "
            "(\\texttt{CONFIG\\_NANOCOAP\\_BLOCK\\_SIZE\\_MAX}); block sizes to its right "
            "require rebuilding the firmware. The two panels place their optima differently, "
            "so no single setting is best for both latency and energy."
            % M.RIOT_BLOCK_MAX,
        "capImplementations":
            "Three DTLS implementations on a constrained link; the dotted rule is the payload "
            "of an IEEE~802.15.4 frame (%d~B). Cells completing a handshake: %s. The three are "
            "bounded by different quantities, so this characterises the implementations rather "
            "than the DTLS protocol."
            % (M.FRAME_PAYLOAD, impl_txt),
        "capPerMessage":
            "Size of each EDHOC message. The dashed rule is the payload of an IEEE~802.15.4 "
            "frame (%d~B). The middle bars are the floor of the argument: the lightest "
            "post-quantum variant conceivable, ML-KEM-512 with classical authentication and "
            "credentials by reference. Even there the encapsulation key alone is %d~B, "
            "$%.1f\\times$ the frame payload, so block-wise engages in message\\_1 under any "
            "design."
            % (M.FRAME_PAYLOAD, M.KEM["ML-KEM-512"][0],
               M.KEM["ML-KEM-512"][0] / M.FRAME_PAYLOAD),
    }
    body = "\n".join(r"\newcommand{\%s}{%s}" % (k, v) for k, v in defs.items())
    write_tex("captions.tex", body + "\n")

    # ── SỐ cho hình TikZ ──────────────────────────────────────────────────────
    # Hình flow vẽ bằng TikZ nên không gọi được Python. Nếu gõ số vào .tex thì có HAI chỗ
    # cài đặt cùng một con số, và chạy lại mô hình sẽ không cập nhật hình. Nên xuất ra macro.
    m768 = M.pq_messages("ML-KEM-768", "ML-DSA-65")
    nums = {
        "numFramePayload": M.FRAME_PAYLOAD,
        "numCoapBlock": M.COAP_BLOCK,
        "numDtlsRT": M.DTLS_FLIGHT_RT,
        "numMsgOneClassic": M.CLASSIC_MSG["message_1"],
        "numMsgOnePQ": m768["message_1"],
        "numMsgTwoPQ": m768["message_2"],
        "numExchOnePQ": M.exchanges_for_message(m768["message_1"]),
        "numExchTwoPQ": M.exchanges_for_message(m768["message_2"]),
        "numExchTotalPQ": M.edhoc_exchanges(m768),
        "numKemFiveOneTwo": M.KEM["ML-KEM-512"][0],
    }
    # Số ĐO ĐƯỢC cũng phải thành macro. Nếu chỉ mô hình có macro còn số đo gõ tay thì bản
    # thảo lại có hai chỗ ở cho cùng một con số, đúng lỗi đã sinh ra "+0,76 chép 12 lần".
    if m1:
        nums["numMOneMatch"] = m1["n_match"]
        nums["numMOneTotal"] = m1["n_match"] + m1["n_mismatch"]
        nums["numMOneImpl"] = m1["implementation"]
    if m3:
        for impl in sorted({r["impl"] for r in m3["rows"]}):
            rs = [r for r in m3["rows"] if r["impl"] == impl]
            ok = [r for r in rs if r["handshake_ok"]]
            bad = [r for r in rs if not r["handshake_ok"]]
            cap = impl.capitalize()
            nums["num%sOk" % cap] = len(ok)
            nums["num%sTotal" % cap] = len(rs)
            at = [r for r in rs if r["mtu"] == M.FRAME_PAYLOAD]
            nums["num%sAtFrame" % cap] = "%d/%d" % (
                sum(1 for r in at if r["handshake_ok"]), len(at)) if at else "--"
            if ok and bad:
                if max(r["frags_est"] for r in ok) < min(r["frags_est"] for r in bad):
                    nums["num%sFragOk" % cap] = max(r["frags_est"] for r in ok)
                    nums["num%sFragBad" % cap] = min(r["frags_est"] for r in bad)
                if min(r["mtu"] for r in ok) > max(r["mtu"] for r in bad):
                    nums["num%sMtuBad" % cap] = max(r["mtu"] for r in bad)
                    nums["num%sMtuOk" % cap] = min(r["mtu"] for r in ok)
    # Số SUY RA cũng cần macro. Viết "7,8 lần" hay "khoảng 2,3 kB" vào bản thảo là tạo một
    # chỗ ở thứ hai: đổi MAC_AND_SEC trong model.py thì hình đổi mà câu văn thì không.
    nums["numKemFrameRatio"] = "%.1f" % (M.KEM["ML-KEM-512"][0] / M.FRAME_PAYLOAD)
    nums["numDecompError"] = "%.1f" % abs(M.decomposition_error()[2])
    # Toi uu co khoi va ti so so voi DTLS: doc ngoai bat duoc bai noi "an order of magnitude"
    # trong khi so that la 5,5x. Con so nay phai SINH RA, khong duoc mo ta bang tinh tu.
    _m = M.pq_messages("ML-KEM-768", "ML-DSA-65")
    _best = min(M.BLOCK_SIZES, key=lambda b: M.blocksize_cost(_m, b, 0.0)[0])
    _rt = M.blocksize_cost(_m, _best, 0.0)[0]
    nums["numBestBlock"] = _best
    nums["numBestExch"] = "%.0f" % _rt
    nums["numBestRatio"] = "%.1f" % (_rt / M.DTLS_FLIGHT_RT)
    # RFC 9177 Q-Block: doc ngoai doi mo hinh hoa thay vi gat di vi "chua ai cai".
    _lock = M.edhoc_exchanges(_m)
    _qb = M.qblock_exchanges(_m)
    nums["numQBlockMaxPayloads"] = M.QBLOCK_MAX_PAYLOADS
    nums["numQBlockExch"] = _qb
    nums["numQBlockGain"] = "%.1f" % (_lock / _qb)
    nums["numFramePayloadSecured"] = M.FRAME_PAYLOAD_SECURED
    nums["numMacOverhead"] = M.MAC_OVERHEAD
    nums["numFramePayloadFrame"] = M.IEEE802154_FRAME
    nums["numLinkSec"] = M.LINK_SEC_CCM128
    # Khoang sai so do phan ra lan sang so luot: doc ngoai doi bao khoang, khong bao diem.
    _e = abs(M.decomposition_error()[2]) / 100.0
    _lo = {k: int(v * (1 - _e)) for k, v in _m.items()}
    _hi = {k: int(v * (1 + _e)) for k, v in _m.items()}
    nums["numExchLo"] = M.edhoc_exchanges(_lo)
    nums["numExchHi"] = M.edhoc_exchanges(_hi)
    # ⭐ Hai truc cho hai ti so RAT KHAC NHAU, va do la luan diem cua bai: chi phi nam o CAU
    # TRUC lock-step chu khong o byte tren day. Chi tinh duoc khi da co moc DTLS DO DUOC.
    if m4:
        _ok = [r for r in m4["rows"] if r["handshake_ok"]]
        if _ok:
            _dt_turns = _ok[0]["turns"]
            _dt_dg = max(r["datagrams"] for r in _ok)
            _rtb, _frb, _, _ = M.blocksize_cost(_m, _best, 0.0)
            nums["numRatioRounds"] = "%.1f" % (_rtb / _dt_turns)
            nums["numRatioFrames"] = "%.2f" % (_frb / _dt_dg)
            nums["numBestFrames"] = "%.0f" % _frb
            # Ti so o co khoi MAC DINH (64 B), tuc cai that su duoc trien khai VA la tran
            # bien dich cua RIOT. Day moi la phep so dung voi thuc te, khong phai o toi uu.
            _rtd, _, _, _ = M.blocksize_cost(_m, M.COAP_BLOCK, 0.0)
            nums["numRatioDefault"] = "%.0f" % (_rtd / _dt_turns)
    if m3:
        g = [r for r in m3["rows"] if r["impl"] == "gnutls"]
        gok = [r["frags_est"] for r in g if r["handshake_ok"]]
        if gok:
            nums["numGnutlsCapKB"] = "%.1f" % (max(gok) * M.FRAME_PAYLOAD / 1000.0)
        mb = [r for r in m3["rows"] if r["impl"] == "mbedtls" and r["handshake_ok"]]
        if mb:
            nums["numMbedtlsMaxFrag"] = max(r["frags_est"] for r in mb)
        # Phản ví dụ cho OpenSSL: hỏng với ÍT mảnh, chạy với NHIỀU mảnh. Đây là bằng chứng
        # trục số mảnh không giải thích được nó, nên hai số này phải lấy từ dữ liệu.
        o = [r for r in m3["rows"] if r["impl"] == "openssl"]
        bad = [r for r in o if not r["handshake_ok"]]
        ok = [r for r in o if r["handshake_ok"]]
        if bad and ok:
            nums["numOpensslFewFragFail"] = min(r["frags_est"] for r in bad)
            nums["numOpensslManyFragOk"] = max(r["frags_est"] for r in ok)
    # M4: so vong DTLS DO DUOC o co hau luong tu. Doc ngoai bat dung lo nay -- truoc do bai
    # so mot so luot EDHOC do duoc voi mot so vong DTLS TRICH TU RFC.
    if m4:
        ok = [r for r in m4["rows"] if r["handshake_ok"]]
        if ok:
            nums["numDtlsMeasTurns"] = ok[0]["turns"]
            nums["numDtlsMaxFrag"] = max(r["frags_est"] for r in ok)
            nums["numDtlsMinFrag"] = min(r["frags_est"] for r in ok)
            nums["numDtlsDatagramLo"] = min(r["datagrams"] for r in ok)
            nums["numDtlsDatagramHi"] = max(r["datagrams"] for r in ok)
            nums["numDtlsDatagramGrowth"] = "%.2f" % (
                max(r["datagrams"] for r in ok) / min(r["datagrams"] for r in ok))
            nums["numDtlsImpl"] = m4["impl"]
            nums["numDtlsMeasVersion"] = m4["dtls_version"]
    write_tex("numbers.tex",
              "\n".join(r"\newcommand{\%s}{%s}" % (k, v) for k, v in nums.items()) + "\n")


def main():
    print("  Sinh hình và bảng. Mô hình: analysis/model.py · Số đo: results/*.json\n")
    tot, ref, err = M.decomposition_error()
    print("  Tự kiểm phân rã: tổng %d B so với bảng gốc %d B, lệch %.1f%%" % (tot, ref, err))
    if abs(err) > 5:
        print("  ⛔ DỪNG: lệch quá 5%, phân rã không dùng được."); return 1
    print()
    print("  XUẤT XỨ SỐ ĐO:")
    m1 = load("m1_coap_blockwise.json", "M1 CoAP block-wise")
    m4 = load("m4_dtls_pq_rounds.json", "M4 số vòng DTLS ở cỡ PQ")
    m3 = load("m3_fragment_threshold.json", "M3 khảo sát cài đặt",
              expect=("gnutls", "mbedtls", "openssl"))
    print()
    print("  HÌNH:")
    fig_size_ratio()
    fig_exchanges(m1)
    fig_blocksize(m4)
    fig_implementations(m3)
    fig_per_message()
    print("  BẢNG:")
    tables(m1, m3)
    print("  CAPTION:")
    captions(m1, m3, m4)
    print()
    missing = [n for n, v in (("M1", m1), ("M3", m3)) if v is None]
    if missing:
        print("  ⚠ THIẾU số đo: %s. Hình/bảng tương ứng KHÔNG được sinh." % ", ".join(missing))
        return 2
    print("  ✅ xong. Bản thảo \\input các .tex trong figures/out/, không dán số.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
