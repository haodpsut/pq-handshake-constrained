"""SPIKE P3: lợi thế kích thước của EDHOC so với DTLS 1.3 có sống dưới PQC không?

⛔ ĐÂY LÀ SPIKE, KHÔNG PHẢI KẾT QUẢ BÀI BÁO. Mục đích duy nhất: biết trong vài phút xem
tiền đề có đáng theo đuổi không. Mọi con số vào đây đều phải kiểm lại ở nguồn gốc trước khi
trích vào bất kỳ bản thảo nào.

TIỀN ĐỀ CẦN THỬ. EDHOC tồn tại vì nó nhỏ hơn DTLS 1.3 khoảng 3 lần (233 so với 736 byte,
theo draft-ietf-iotops-security-protocol-comparison). Khoản tiết kiệm đó đến từ mã hoá COSE
gọn, tức là một HẰNG SỐ vài trăm byte. PQC thêm hàng KILOBYTE vào CẢ HAI giao thức. Nếu vậy
tỉ số phải sụp về gần 1, và lý do tồn tại của giao thức mất theo.

CÁCH TÍNH. Không mô hình hoá lại toàn bộ bản tin (spike không cần). Chỉ cần:

    tỉ số cổ điển   = D / E
    tỉ số sau PQC   = (D + X) / (E + X)

với X là lượng byte PQC thêm vào, GIỐNG NHAU cho hai giao thức vì cả hai đều phải mang đúng
những khoá, bản mã và chữ ký ấy. Đây là chỗ mạnh của lập luận: X không cần chính xác tuyệt
đối, chỉ cần đúng bậc độ lớn, và kết luận không đổi trong cả một dải X rộng.

⚠ KÍCH THƯỚC PQC dưới đây lấy theo FIPS 203/204. PHẢI đối chiếu lại với văn bản chuẩn trước
khi dùng ngoài spike này.
"""

# (tên, khoá công khai KEM, bản mã KEM)
KEM = {
    "ML-KEM-512":  (800, 768),
    "ML-KEM-768":  (1184, 1088),
    "ML-KEM-1024": (1568, 1568),
}
# (tên, khoá công khai chữ ký, chữ ký)
SIG = {
    "ML-DSA-44": (1312, 2420),
    "ML-DSA-65": (1952, 3309),
    "ML-DSA-87": (2592, 4627),
}
# Bảng gốc dùng P-256 + ECDSA (thuật toán bắt buộc), không phải X25519/Ed25519.
P256_PK, ECDSA_SIG = 33, 64   # nén; chữ ký ECDSA P-256 trong COSE

# ⛔ SỐ ĐÃ SỬA 29/08 sau khi đọc BẢN GỐC. Lần đầu tôi dùng 233/736 lấy từ trí nhớ thứ cấp;
# bảng thật trong draft-ietf-iotops-security-protocol-comparison-09 (Figure 1, thuật toán
# bắt buộc CCM_8 + P-256 + ECDSA) cho số KHÁC, và khác theo hướng làm luận điểm MẠNH HƠN:
#
#   DTLS 1.3 - RPKs, ECDHE                  185  454  255  = 894
#   EDHOC - Signature RPKs, kid, ECDHE       37  102   77  = 216   -> 4,14x
#   EDHOC - Static DH RPKs, kid, ECDHE       37   45   19  = 101   -> 8,85x
#
# ⭐ Chế độ cho lợi thế LỚN NHẤT (8,85x) chính là Static DH, và đó đúng là chế độ KHÔNG
# instantiate được bằng KEM hậu lượng tử. Nên bài không chỉ nói "tỉ số co lại" mà nói
# "chế độ mang lại lợi thế biến mất, chế độ còn lại thì co về gần 1".
D_CLASSIC   = 894   # DTLS 1.3 - RPKs, ECDHE
E_SIG       = 216   # EDHOC - Signature RPKs, kid, ECDHE  (còn sống dưới PQC)
E_STATIC_DH = 101   # EDHOC - Static DH RPKs, kid, ECDHE  (KHÔNG có bản PQC)
E_CLASSIC   = E_SIG

# ⛔ SỬA 29/08, do spike 4 (tách theo bản tin) lộ ra. RFC 9528 §3.2, bảng Method Type Value:
# method 0 là "Signature Key / Signature Key", tức CẢ HAI BÊN ĐỀU KÝ. Bản trước tính n_sig=1
# nên THIẾU một chữ ký ML-DSA (3309 B ở mức 65). DTLS 1.3 xác thực hai chiều cũng hai chữ ký,
# nên sửa áp cho CẢ HAI và tỉ số càng co về 1: sửa làm luận điểm MẠNH lên.
N_SIG = 2


def pq_overhead(kem, sig, n_sig=N_SIG, n_cert_pk=1):
    """Byte PQC THÊM so với cổng cổ điển tương ứng.

    Trừ đi phần cổ điển đang chiếm chỗ, vì con số 233/736 đã bao gồm khoá X25519 và chữ ký
    Ed25519. Không trừ thì tính thừa khoảng 200 byte, đủ để làm lệch tỉ số ở đầu nhỏ.
    """
    ek, ct = KEM[kem]
    pk, sg = SIG[sig]
    add = (ek - P256_PK) + (ct - P256_PK) + n_sig * (sg - ECDSA_SIG) + n_cert_pk * (pk - P256_PK)
    return add


print("  === CỔ ĐIỂN (nguồn: draft-...-comparison-09, Figure 1) ===")
print("  DTLS 1.3 RPK+ECDHE           %4d byte" % D_CLASSIC)
print("  EDHOC Signature RPK+ECDHE    %4d byte  -> loi the %.2fx" % (E_SIG, D_CLASSIC/E_SIG))
print("  EDHOC Static DH RPK+ECDHE    %4d byte  -> loi the %.2fx  <-- KHONG CO BAN PQC"
      % (E_STATIC_DH, D_CLASSIC/E_STATIC_DH))
print()
print("  %-24s %8s %9s %9s %8s" % ("bộ tham số", "X thêm", "EDHOC", "DTLS 1.3", "tỉ số"))
print("  " + "-" * 64)
rows = []
for kem in KEM:
    for sig in SIG:
        X = pq_overhead(kem, sig)
        e, d = E_CLASSIC + X, D_CLASSIC + X
        r = d / e
        rows.append(r)
        print("  %-24s %8d %9d %9d %7.2fx" % (kem + " + " + sig, X, e, d, r))

print("\n  tỉ số sau PQC: nhỏ nhất %.2fx, lớn nhất %.2fx" % (min(rows), max(rows)))
print("  ⇒ lợi thế %.2fx của EDHOC co về khoảng %.2f–%.2fx"
      % (D_CLASSIC / E_CLASSIC, min(rows), max(rows)))

# ⛔ Độ nhạy: kết luận có phụ thuộc vào con số X không? Nếu chỉ đúng ở một giá trị X thì
# nó là tạo tác của giả định, không phải phát hiện.
print("\n  ĐỘ NHẠY — tỉ số theo X, để xem kết luận có mong manh không:")
for X in (500, 1000, 2000, 4000, 8000, 16000):
    print("    X = %6d byte  ⇒  tỉ số %.2fx" % (X, (D_CLASSIC + X) / (E_CLASSIC + X)))

# Ngưỡng: X bằng bao nhiêu thì lợi thế tụt xuống dưới 1.5x (mức thường được coi là đáng kể)?
# (D+X)/(E+X) = 1.5  ⇒  X = (D - 1.5E) / 0.5
X_half = (D_CLASSIC - 1.5 * E_CLASSIC) / 0.5
print("\n  Lợi thế tụt xuống 1.5x khi X = %.0f byte." % X_half)
print("  Ngay cả bộ PQC NHỎ NHẤT đã thêm %d byte ⇒ vượt ngưỡng đó %.1f lần."
      % (pq_overhead("ML-KEM-512", "ML-DSA-44"),
         pq_overhead("ML-KEM-512", "ML-DSA-44") / X_half))
