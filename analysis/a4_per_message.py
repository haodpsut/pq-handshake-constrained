"""SPIKE 4 — TÁCH THEO TỪNG BẢN TIN, và tìm SÀN của lập luận.

⛔ SPIKE, KHÔNG PHẢI KẾT QUẢ BÀI BÁO.

VÌ SAO CẦN. Spike 2 và 3 chia đều tổng byte cho 3 bản tin. Đó là chỗ mềm nhất của cả lập
luận: EDHOC phân bổ RẤT lệch, message_2 gánh gần hết. Chia đều có thể làm số vòng SAI theo
cả hai chiều, và phản biện chỉ cần một dòng để chỉ ra.

⛔ VÀ NÓ LỘ RA MỘT LỖI CỦA SPIKE 1. RFC 9528 §3.2, bảng Method Type Value: method 0 là
"Signature Key / Signature Key", tức CẢ HAI BÊN ĐỀU KÝ. Spike 1 tính pq_overhead với
n_sig=1, tức THIẾU một chữ ký ML-DSA (3309 B ở mức 65). Con số 7586 là tính THIẾU.

Cấu trúc bản tin, RFC 9528 §5:
    message_1 : METHOD, SUITES_I, G_X, C_I, EAD_1
    message_2 : G_Y, CIPHERTEXT_2 { C_R, ID_CRED_R, Signature_or_MAC_2, EAD_2 }
    message_3 : CIPHERTEXT_3 { ID_CRED_I, Signature_or_MAC_3, EAD_3 }

Với biến thể hậu lượng tử dựa KEM: G_X -> khoá đóng gói (ek), G_Y -> bản mã (ct), và mỗi
Signature_or_MAC -> chữ ký ML-DSA. Dùng `kid` thì khoá công khai KHÔNG lên dây.
"""

IEEE802154_FRAME  = 127
MAC_AND_SEC       = 25          # ⚠ CHƯA KIỂM
FITS_IN_ONE_FRAME = IEEE802154_FRAME - MAC_AND_SEC      # 102
COAP_BLOCK        = 64          # ✅ mặc định VÀ trần của RIOT

KEM = {"ML-KEM-512": (800, 768), "ML-KEM-768": (1184, 1088), "ML-KEM-1024": (1568, 1568)}
SIG = {"ML-DSA-44": (1312, 2420), "ML-DSA-65": (1952, 3309), "ML-DSA-87": (2592, 4627)}

# Nền cổ điển của từng bản tin, method 0 + RPK theo `kid`. Suy từ cấu trúc §5, và tổng phải
# TÁI TẠO được con số 216 của bảng gốc -- đó là phép kiểm của chính phân rã này.
CLASSIC = {
    "message_1": 1 + 1 + (32 + 2) + 1,               # METHOD, SUITES_I, G_X, C_I
    "message_2": (32 + 2) + (1 + 3 + 64 + 8) + 1,    # G_Y, CIPHERTEXT_2
    "message_3": (3 + 64 + 8) + 2,                   # CIPHERTEXT_3
}
CLASSIC_REF = 216   # bảng gốc, "EDHOC Signature RPKs, kid, ECDHE"

G_LEN, SIG_LEN, CBOR_LONG = 32, 64, 3


def ceil_div(a, b):
    return -(-a // b)


def blocks(nbytes):
    """Số lượt trao đổi CoAP cho một bản tin. Lọt khung thì 1 lượt, không thì cắt khối."""
    if nbytes <= FITS_IN_ONE_FRAME:
        return 1
    return ceil_div(nbytes, COAP_BLOCK)


def pq_messages(kem, sig, pq_sign=True):
    """Kích thước từng bản tin cho EDHOC hậu lượng tử.

    pq_sign=False mô hình hoá biến thể NHẸ NHẤT CÓ THỂ HÌNH DUNG: chỉ KEM hậu lượng tử,
    xác thực vẫn cổ điển, chứng thư theo tham chiếu. Dùng để tìm SÀN của lập luận.
    """
    ek, ct = KEM[kem]
    _, sg = SIG[sig]
    d_sig = (sg - SIG_LEN) if pq_sign else 0
    return {
        "message_1": CLASSIC["message_1"] - G_LEN + ek + CBOR_LONG,
        "message_2": CLASSIC["message_2"] - G_LEN + ct + CBOR_LONG + d_sig,
        "message_3": CLASSIC["message_3"] + d_sig,
    }


tot = sum(CLASSIC.values())
print("  KIỂM PHÂN RÃ: tổng cổ điển suy ra = %d B, bảng gốc = %d B, lệch %+d B (%.1f%%)"
      % (tot, CLASSIC_REF, tot - CLASSIC_REF, 100.0 * (tot - CLASSIC_REF) / CLASSIC_REF))
print("  ⇒ lệch dưới 5%% thì phân rã dùng được cho spike. Không dùng để trích số tuyệt đối.\n")

print("  %-14s %9s %9s %9s %8s %7s"
      % ("bộ tham số", "msg_1", "msg_2", "msg_3", "tổng", "lượt"))
print("  " + "-" * 66)

print("  %-14s %9d %9d %9d %8d %7d   (cổ điển, mọi bản tin LỌT khung)"
      % ("cổ điển", CLASSIC["message_1"], CLASSIC["message_2"], CLASSIC["message_3"],
         tot, sum(blocks(v) for v in CLASSIC.values())))

for kem in KEM:
    for sig in SIG:
        m = pq_messages(kem, sig)
        n = sum(blocks(v) for v in m.values())
        print("  %-14s %9d %9d %9d %8d %7d"
              % (kem.replace("ML-KEM-", "K") + "+" + sig.replace("ML-DSA-", "D"),
                 m["message_1"], m["message_2"], m["message_3"], sum(m.values()), n))

print()
print("  === SÀN CỦA LẬP LUẬN: biến thể hậu lượng tử NHẸ NHẤT có thể hình dung ===")
print("  Chỉ KEM hậu lượng tử ở mức THẤP NHẤT (ML-KEM-512), xác thực vẫn cổ điển,")
print("  chứng thư theo tham chiếu. Không giao thức nào có thể nhẹ hơn thế này.")
m = pq_messages("ML-KEM-512", "ML-DSA-44", pq_sign=False)
n = sum(blocks(v) for v in m.values())
for k in ("message_1", "message_2", "message_3"):
    fit = "LỌT khung" if m[k] <= FITS_IN_ONE_FRAME else "⚠ phải cắt khối (%d lượt)" % blocks(m[k])
    print("    %-11s %6d B   %s" % (k, m[k], fit))
print("    ⇒ tổng %d lượt, so với DTLS 1.3 luôn 2 lượt: vẫn THUA %.0f lần." % (n, n / 2))

print()
ek512 = KEM["ML-KEM-512"][0]
print("  ⭐⭐⭐ CÂU KHÔNG PHỤ THUỘC THIẾT KẾ, và đây là dạng MẠNH NHẤT của lập luận:")
print("     message_1 của BẤT KỲ EDHOC hậu lượng tử nào cũng phải mang khoá đóng gói KEM.")
print("     Nhỏ nhất trong chuẩn NIST là ML-KEM-512: %d byte, tức %.1f LẦN payload khung"
      % (ek512, ek512 / FITS_IN_ONE_FRAME))
print("     802.15.4 (%d byte). Nên block-wise bị kích hoạt NGAY Ở message_1, ở MỌI bộ tham"
      % FITS_IN_ONE_FRAME)
print("     số, BẤT KỂ chọn xác thực thế nào và bất kể tối ưu hoá mã hoá ra sao.")
print()
print("     ⇒ Đây không phải nhận xét về một cài đặt hay một cấu hình. Không thiết kế lại")
print("        được, vì khoá công khai KEM BẮT BUỘC phải lên dây. Đó là chỗ biến bài thành")
print("        một giới hạn, chứ không phải một phép đo.")
print()
print("  ⛔ HỆ QUẢ NGƯỢC LÊN SPIKE 1: method 0 có HAI chữ ký, spike 1 tính n_sig=1 nên")
print("     THIẾU một chữ ký ML-DSA. Phải sửa spike 1. Tỉ số sẽ co về 1 MẠNH HƠN nữa, vì")
print("     X lớn hơn ⇒ (D+X)/(E+X) gần 1 hơn. Sửa làm luận điểm MẠNH lên, không yếu đi.")
