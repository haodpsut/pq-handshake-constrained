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


def texify(rows, header, caption, label, colspec, note=None):
    L = [r"\begin{table}[t]", r"\centering",
         r"\caption{%s}" % caption, r"\label{%s}" % label,
         r"\begin{tabular}{%s}" % colspec, r"\hline",
         " & ".join(header) + r" \\", r"\hline"]
    L += [" & ".join(str(c) for c in r) + r" \\" for r in rows]
    L += [r"\hline", r"\end{tabular}"]
    if note:
        L.append(r"\\[2pt]{\footnotesize %s}" % note)
    L.append(r"\end{table}")
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
               label="cổ điển, chế độ chữ ký (%.2f×)" % (M.D_CLASSIC / M.E_SIG))
    ax.axhline(M.D_CLASSIC / M.E_STATIC_DH, color=C["orange"], ls=":", lw=1.0,
               label="cổ điển, Static DH (%.2f×) — KHÔNG có bản PQC"
                     % (M.D_CLASSIC / M.E_STATIC_DH))
    ax.axhline(1.0, color=C["gray"], lw=0.6)
    ax.set_xticks(list(x)); ax.set_xticklabels(names)
    ax.set_ylabel("DTLS / EDHOC (tỉ số byte)")
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
            label="EDHOC/CoAP block-wise (mô hình)")
    ax.axhline(M.DTLS_FLIGHT_RT, color=C["verm"], ls="--", lw=1.2,
               label="DTLS 1.3 theo flight [RFC 9147]")
    ax.axvline(M.FRAME_PAYLOAD, color=C["gray"], ls=":", lw=0.8)
    # ⚠ LUẬT rút ra sau BỐN lần đè trong cùng một buổi vẽ: chữ đặt trong vùng vẽ phải cạnh
    # tranh chỗ với dữ liệu VÀ với chú giải, mà cả hai đều đổi theo dữ liệu. Nên chú thích
    # mốc đặt ở MÉP DƯỚI bằng toạ độ tương đối, chỗ duy nhất chắc chắn trống ở mọi hình này.
    ax.text(M.FRAME_PAYLOAD + 90, 4.5, "khung 802.15.4 (%d B)" % M.FRAME_PAYLOAD,
            fontsize=6.5, color=C["gray"], va="bottom")

    if m1:
        mx = [r["bytes"] for r in m1["rows"]]
        my = [r["measured_c2s"] for r in m1["rows"]]
        ax.plot(mx, my, "o", color="black", ms=4, mfc="none", mew=0.9,
                label="ĐO ĐƯỢC (aiocoap, %d/%d khớp)"
                      % (m1["n_match"], m1["n_match"] + m1["n_mismatch"]))
    ax.set_xlabel("kích thước bản tin bắt tay (byte)")
    ax.set_ylabel("số lượt trao đổi")
    ax.set_xlim(0, 5200); ax.set_ylim(0, 88)
    ax.legend(loc="upper left")
    save(fig, "fig2-exchanges")


# ══════════════════════════════════════════════════════════════════════════════
# HÌNH 3 — HÌNH CHÍNH: quét cỡ khối, hai trục tối ưu LỆCH nhau, trần RIOT
# ══════════════════════════════════════════════════════════════════════════════
def fig_blocksize():
    total = sum(M.pq_messages("ML-KEM-768", "ML-DSA-65").values())
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W2, 2.6))

    for ax, idx, ylab, ttl in ((a1, 0, "kỳ vọng số lượt", "(a) trục ĐỘ TRỄ"),
                               (a2, 1, "kỳ vọng số khung phải phát", "(b) trục NĂNG LƯỢNG")):
        for p, col, mk, ls in ((0.00, C["blue"], "o", "-"),
                               (0.01, C["green"], "s", "--"),
                               (0.05, C["verm"], "^", "-.")):
            ys = [M.blocksize_cost(total, b, p)[idx] for b in M.BLOCK_SIZES]
            ax.plot(M.BLOCK_SIZES, ys, color=col, marker=mk, ls=ls,
                    label="mất khung p=%.2f" % p)
            best = min(range(len(ys)), key=lambda i: ys[i])
            ax.plot(M.BLOCK_SIZES[best], ys[best], "*", color=col, ms=11, mec="black",
                    mew=0.4, zorder=5)
        ax.axvspan(M.RIOT_BLOCK_MAX, M.BLOCK_SIZES[-1] * 1.15, color="black", alpha=0.06)
        ax.set_xscale("log", base=2); ax.set_yscale("log")
        ax.set_xlim(M.BLOCK_SIZES[0] * 0.8, M.BLOCK_SIZES[-1] * 1.15)
        ax.set_xticks(M.BLOCK_SIZES)
        ax.set_xticklabels([str(b) for b in M.BLOCK_SIZES])
        ax.set_xlabel("cỡ khối CoAP (byte)"); ax.set_ylabel(ylab)
        ax.set_title(ttl, fontsize=8)
    a1.axhline(M.DTLS_FLIGHT_RT, color=C["gray"], ls="--", lw=0.9)
    a1.text(0.03, 0.06, "DTLS 1.3 = %d lượt" % M.DTLS_FLIGHT_RT,
            transform=a1.transAxes, fontsize=7, color=C["gray"])
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
        ax.plot(okx, oky, "o", color=C["green"], ms=5, label="bắt tay xong")
        ax.plot(bdx, bdy, "x", color=C["verm"], ms=6, mew=1.4, label="hỏng")
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
    axes[0].set_ylabel("số mảnh của bản tin")
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
    ax.bar([i - w for i in x], classic, w, label="cổ điển", color=C["gray"],
           edgecolor="black", lw=0.4)
    ax.bar(list(x), [floor[k] for k in labels], w, label="SÀN: chỉ ML-KEM-512",
           color=C["orange"], edgecolor="black", lw=0.4)
    ax.bar([i + w for i in x], [full[k] for k in labels], w,
           label="K768 + D65", color=C["blue"], edgecolor="black", lw=0.4)
    ax.axhline(M.FRAME_PAYLOAD, color=C["verm"], ls="--", lw=1.1)
    # Đặt ngay TRÊN vạch và ở KHOẢNG TRỐNG giữa hai nhóm cột, không đặt ở mép phải nơi cột
    # K768 vươn cao. Vị trí trống phụ thuộc dữ liệu, nên phải nhìn hình rồi mới chốt.
    ax.text(0.52, M.FRAME_PAYLOAD * 1.12, "khung 802.15.4 (%d B)" % M.FRAME_PAYLOAD,
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
        rows, ["KEM", "SIG", "EDHOC (B)", "DTLS (B)", "tỉ số", "lượt EDHOC", "lượt DTLS"],
        "Kích thước bắt tay và số lượt trao đổi cho chín bộ tham số NIST. "
        "Tỉ số cổ điển là %.2f$\\times$ (chế độ chữ ký) và %.2f$\\times$ (Static DH, không có "
        "bản hậu lượng tử)." % (M.D_CLASSIC / M.E_SIG, M.D_CLASSIC / M.E_STATIC_DH),
        "tab:params", "llrrrrr",
        "Số lượt EDHOC tính với cỡ khối %d B, mặc định của Contiki-NG và RIOT. "
        "Số lượt DTLS theo RFC 9147, không đo ở đây." % M.COAP_BLOCK))

    # B2: mô hình so với ĐO ĐƯỢC
    if m1:
        rows = [[r["case"], r["bytes"], r["predicted"], r["measured_c2s"],
                 r"\checkmark" if r["match"] else r"$\times$"] for r in m1["rows"]]
        write_tex("tab2-model-vs-measured.tex", texify(
            rows, ["trường hợp", "byte", "mô hình", "đo được", "khớp"],
            "Đối chiếu mô hình đếm lượt với một cài đặt CoAP độc lập (%s). "
            "Datagram đếm bằng relay UDP đặt giữa client và server; %d/%d khớp."
            % (m1["implementation"], m1["n_match"], m1["n_match"] + m1["n_mismatch"]),
            "tab:validation", "lrrrc",
            "Cỡ khối %d B, ngưỡng kích hoạt %d B. Phép đo xác nhận PHÉP ĐẾM; "
            "trễ và năng lượng KHÔNG đo ở đây." % (m1["block_size"], m1["frame_payload"])))

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
                bound = "không thấy trong dải đã quét"
            elif max(r["frags_est"] for r in ok) < min(r["frags_est"] for r in bad):
                bound = "số mảnh: %d được / %d hỏng" % (
                    max(r["frags_est"] for r in ok), min(r["frags_est"] for r in bad))
            elif min(r["mtu"] for r in ok) > max(r["mtu"] for r in bad):
                bound = "sàn MTU: %d hỏng / %d được" % (
                    max(r["mtu"] for r in bad), min(r["mtu"] for r in ok))
            else:
                bound = "không tách được trên trục nào"
            rows.append([impl, "%d/%d" % (len(ok), len(rs)),
                         "%d/%d" % (ok102, len(at102)) if at102 else "--", bound])
        write_tex("tab3-implementations.tex", texify(
            rows, ["cài đặt", "ô xong", "xong ở MTU 102", "thứ chặn nó"],
            "Ba cài đặt DTLS trên đường truyền ràng buộc. MTU 102 B là payload một khung "
            "IEEE 802.15.4 sau MAC và AES-CCM*.",
            "tab:impls", "llll",
            "Ba cài đặt bị chặn bởi ba thứ KHÁC NHAU, nên kết quả này KHÔNG chống đỡ "
            "một tuyên bố về giao thức DTLS, chỉ về từng cài đặt."))


def captions(m1, m3):
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
            "Lợi thế kích thước của EDHOC so với DTLS 1.3 trên chín bộ tham số NIST. "
            "Đường đứt: tỉ số cổ điển ở chế độ chữ ký (%.2f$\\times$). Đường chấm: chế độ "
            "Static DH (%.2f$\\times$), chế độ này KHÔNG có bản hậu lượng tử vì method 1--3 "
            "của RFC 9528 dựa trên Diffie--Hellman tĩnh."
            % (M.D_CLASSIC / M.E_SIG, M.D_CLASSIC / M.E_STATIC_DH),
        "capExchanges":
            "Số lượt trao đổi theo kích thước bản tin bắt tay. EDHOC trên CoAP dùng "
            "block-wise lock-step nên số lượt nở tuyến tính; DTLS 1.3 truyền theo flight nên "
            "giữ nguyên %d lượt bất kể kích thước [RFC 9147]. Vòng tròn rỗng là SỐ ĐO trên "
            "một cài đặt CoAP độc lập, khớp mô hình %d/%d. Con số của DTLS là trích chuẩn, "
            "không đo ở đây." % (M.DTLS_FLIGHT_RT, n_ok, n_all),
        "capBlocksize":
            "Quét toàn dải cỡ khối mà RFC 7959 cho phép, với bắt tay ML-KEM-768 + ML-DSA-65. "
            "Sao là điểm tối ưu của từng đường. Vùng tô và vạch dọc ở %d B là TRẦN BIÊN DỊCH "
            "của RIOT (\\texttt{CONFIG\\_NANOCOAP\\_BLOCK\\_SIZE\\_MAX}); cỡ khối bên phải "
            "vạch không dùng được nếu không sửa firmware. Hai bảng có điểm tối ưu KHÁC NHAU, "
            "nên không tồn tại một cấu hình tốt nhất chung cho cả độ trễ lẫn năng lượng."
            % M.RIOT_BLOCK_MAX,
        "capImplementations":
            "Ba cài đặt DTLS trên đường truyền ràng buộc; vạch chấm là payload một khung IEEE "
            "802.15.4 (%d B). Số ô bắt tay thành công: %s. Ba cài đặt bị chặn bởi ba thứ khác "
            "nhau, nên kết quả này nói về TỪNG CÀI ĐẶT chứ không về giao thức DTLS."
            % (M.FRAME_PAYLOAD, impl_txt),
        "capPerMessage":
            "Kích thước từng bản tin EDHOC. Đường đứt là payload một khung 802.15.4 (%d B). "
            "Cột giữa là SÀN của lập luận: biến thể hậu lượng tử nhẹ nhất có thể hình dung, "
            "chỉ ML-KEM-512 với xác thực cổ điển và chứng thư theo tham chiếu. Ngay ở sàn đó, "
            "riêng khoá đóng gói đã là %d B, tức %.1f lần payload khung, nên block-wise bị "
            "kích hoạt ngay ở message\\_1 với mọi thiết kế."
            % (M.FRAME_PAYLOAD, M.KEM["ML-KEM-512"][0],
               M.KEM["ML-KEM-512"][0] / M.FRAME_PAYLOAD),
    }
    body = "\n".join(r"\newcommand{\%s}{%s}" % (k, v) for k, v in defs.items())
    write_tex("captions.tex", body + "\n")


def main():
    print("  Sinh hình và bảng. Mô hình: analysis/model.py · Số đo: results/*.json\n")
    tot, ref, err = M.decomposition_error()
    print("  Tự kiểm phân rã: tổng %d B so với bảng gốc %d B, lệch %.1f%%" % (tot, ref, err))
    if abs(err) > 5:
        print("  ⛔ DỪNG: lệch quá 5%, phân rã không dùng được."); return 1
    print()
    print("  XUẤT XỨ SỐ ĐO:")
    m1 = load("m1_coap_blockwise.json", "M1 CoAP block-wise")
    m3 = load("m3_fragment_threshold.json", "M3 khảo sát cài đặt",
              expect=("gnutls", "mbedtls", "openssl"))
    print()
    print("  HÌNH:")
    fig_size_ratio()
    fig_exchanges(m1)
    fig_blocksize()
    fig_implementations(m3)
    fig_per_message()
    print("  BẢNG:")
    tables(m1, m3)
    print("  CAPTION:")
    captions(m1, m3)
    print()
    missing = [n for n, v in (("M1", m1), ("M3", m3)) if v is None]
    if missing:
        print("  ⚠ THIẾU số đo: %s. Hình/bảng tương ứng KHÔNG được sinh." % ", ".join(missing))
        return 2
    print("  ✅ xong. Bản thảo \\input các .tex trong figures/out/, không dán số.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
