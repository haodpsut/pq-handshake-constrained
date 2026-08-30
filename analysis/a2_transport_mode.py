"""SPIKE 2 (BẢN 2) — hậu quả của kích thước PQC trên đường truyền RÀNG BUỘC.

⛔ SPIKE, KHÔNG PHẢI KẾT QUẢ BÀI BÁO. Mọi tham số phải đối chiếu nguồn trước khi trích.

╔══════════════════════════════════════════════════════════════════════════════════════╗
║ ⛔ BẢN 1 CỦA TỆP NÀY SAI VỀ CƠ CHẾ, VÀ TÔI GIỮ LẠI LỜI KHAI ĐÓ Ở ĐÂY.                ║
║                                                                                      ║
║ Bản 1 giả định flight lớn bị 6LoWPAN cắt mảnh và mất MỘT mảnh là mất CẢ datagram,    ║
║ nên P(tới nơi) = (1-p)^n. Nó cho bảng "PQ ⇒ P = 0,452" nghe rất kêu. Nó SAI hai lần: ║
║                                                                                      ║
║   (1) RFC 7959 nói block-wise sinh ra CHÍNH ĐỂ TRÁNH phân mảnh tầng thích ứng        ║
║       6LoWPAN. Nên với CoAP, phân mảnh không phải hành vi được khuyến nghị.          ║
║   (2) RFC 9147 §5.5: DTLS 1.3 TỰ cắt bản tin bắt tay bằng fragment_offset /          ║
║       fragment_length, mỗi mảnh nằm gọn một datagram UDP. Nên DTLS cũng KHÔNG rơi    ║
║       vào cảnh mất-một-mảnh-mất-tất.                                                 ║
║                                                                                      ║
║ Mô hình all-or-nothing sai cho CẢ HAI giao thức. Nếu không bắt bây giờ thì 0,452 đã  ║
║ thành số headline, và phản biện đầu tiên hiểu CoAP sẽ giết bài ở đúng dòng đó.       ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

CƠ CHẾ ĐÚNG, và nó ngược chiều nhau ở đúng chỗ quyết định:

  DTLS 1.3 — THEO FLIGHT. Cắt ở tầng bắt tay thành các bản ghi cỡ MTU, bắn LIÊN TIẾP cả
      flight rồi mới chờ. Số vòng = số flight, tức là HẰNG SỐ (~2 cho bắt tay đầy đủ),
      KHÔNG phụ thuộc kích thước. Kích thước chỉ làm flight dày thêm.  [RFC 9147 §5.5]

  EDHOC trên CoAP — THEO KHỐI, LOCK-STEP. RFC 7959 nói rõ block-wise là "multiple
      request-response pairs", và "the transfer of each block is acknowledged". Nghĩa là
      MỖI KHỐI tốn MỘT VÒNG, tuần tự. Số vòng NỞ TUYẾN TÍNH theo kích thước.  [RFC 7959]

⭐ NGƯỠNG mới là chỗ đau, không phải tỉ số. Block-wise chỉ KÍCH HOẠT khi bản tin vượt cỡ
gói. EDHOC cổ điển (101 B tổng, mỗi bản tin vài chục byte) nằm GỌN trong một khung, nên chi
phí lock-step BẰNG KHÔNG. EDHOC hậu lượng tử thì không nằm gọn được nữa. Vậy PQC không chỉ
bào mòn lợi thế kích thước từ 4,14x về ~1,1x: nó ĐẨY EDHOC QUA MỘT NGƯỠNG, sang một chế độ
truyền tải mà DTLS không bao giờ bước vào. Lợi thế không co lại. Nó ĐẢO CHIỀU.

⭐⭐⭐ CHUẨN ĐÃ TỰ KHAI RỦI RO NÀY, VÀ CHƯA AI ĐO. RFC 9668 §1 (EDHOC over CoAP/OSCORE):

    "The performance advantage of using this optimization CAN BE LOST when used in
     combination with Block-wise transfers [RFC7959] that rely on specific parameter
     values and block sizes."

và ngay trên đó, điều kiện để có hai vòng được nêu tường minh:

    "...since the message_3 of the EDHOC protocol can be made RELATIVELY SMALL ...
     thus allowing additional OSCORE-protected CoAP data WITHIN TARGET MTU SIZES."

⇒ Toàn bộ lợi thế hai vòng của EDHOC-trên-CoAP TREO VÀO một điều kiện kích thước. PQC phá
đúng điều kiện đó, ở MỌI bộ tham số NIST. Và §3.2.2 Step 3.1 còn có đường lui chuẩn tắc:
vượt MAX_UNFRAGMENTED_SIZE thì client "MUST abandon the Block-wise transfer" và chuyển sang
"sequential workflow". Chuẩn viết sẵn đường lui, chưa ai đo bao giờ nó bị kích hoạt.

ĐÓ LÀ BÀI: chuẩn nói "có thể mất"; ta chỉ ra PQC LÀM NÓ MẤT, định lượng, và chỉ ra DTLS 1.3
KHÔNG suy giảm ở đúng chế độ đó vì nó theo flight.

✅ PHẢN BIỆN (a) ĐÃ TRẢ LỜI, bằng mã nguồn chứ không bằng tóm tắt:
  - Contiki-NG cài block-wise trong tệp tên `coap-blocking-api.c`, dùng PT_YIELD_UNTIL chờ
    hồi đáp rồi mới tăng block_num  ⇒ LOCK-STEP nằm trong mã.
  - RIOT gcoap: "the client sends a new request to request the next blockwise payload".
  - Q-Block (RFC 9177, lối thoát NON) KHÔNG có trong Contiki-NG, KHÔNG có trong RIOT.
    Có trong libcoap nhưng là CỜ BẬT TAY: COAP_BLOCK_TRY_Q_BLOCK 0x04, và còn phải
    COAP_BLOCK_FORCE_Q_BLOCK 0x200 khi không kiểm được hỗ trợ đầu kia.
  - RFC 9668 và RFC 9528 nhắc RFC 9177: **0 lần**. Lối thoát không nằm trong hồ sơ EDHOC.

⚠ CÒN PHẢI KIỂM: MAC_AND_SEC=25 · RTT thực đo trên mesh 6LoWPAN nhiều chặng · tách kích
thước theo từng bản tin EDHOC thay vì chia đều · MAX_UNFRAGMENTED_SIZE thực tế của OSCORE.
"""

# --- tham số đường truyền, PHẢI đối chiếu nguồn ---
IEEE802154_FRAME = 127      # byte, khung tối đa
MAC_AND_SEC      = 25       # ước lượng header MAC + AES-CCM*  ⚠ CHƯA KIỂM
# ✅ ĐÃ KIỂM TẬN MÃ NGUỒN, hai ngăn xếp độc lập đều mặc định 64:
#   Contiki-NG  os/net/app-layer/coap/coap-conf.h:58   COAP_MAX_CHUNK_SIZE 64
#   RIOT        sys/include/net/nanocoap.h:153         CONFIG_NANOCOAP_BLOCKSIZE_DEFAULT
#                                                      = COAP_BLOCKSIZE_64
COAP_BLOCK       = 64

# Ngưỡng kích hoạt block-wise: bản tin vượt payload gói thì phải cắt khối.
FITS_IN_ONE_FRAME = IEEE802154_FRAME - MAC_AND_SEC

DTLS_FLIGHT_RT = 2          # bắt tay DTLS 1.3 đầy đủ, theo flight, KHÔNG theo kích thước
RTT_MS = (100, 300, 500)    # RTT mesh 6LoWPAN nhiều chặng, dải hay gặp  ⚠ CHƯA KIỂM

# --- kích thước flight, từ spike 1 (đã đối chiếu bảng gốc) ---
HYBRID_KEX = 2400           # "A Hybrid EDHOC Protocol", MobiSec'25, tự báo ≈2300–2400 B
EDHOC = {
    "EDHOC Static DH (cổ điển)":                101,
    "EDHOC Signature (cổ điển)":                216,
    "EDHOC hybrid KEM (MobiSec'25)":            216 - 64 + HYBRID_KEX,
    "EDHOC Signature + ML-KEM-768/ML-DSA-65":  7586,
}
DTLS = {
    "DTLS 1.3 RPK+ECDHE (cổ điển)":             894,
    "DTLS 1.3 + ML-KEM-768/ML-DSA-65":         8264,
}
N_EDHOC_MSG = 3             # EDHOC có 3 bản tin, mỗi bản tin cắt khối riêng


def ceil_div(a, b):
    return -(-a // b)


def edhoc_round_trips(total_bytes):
    """Số vòng lock-step của EDHOC trên CoAP.

    Nếu MỖI bản tin nằm gọn một khung thì không cần block-wise: 3 bản tin, ~2 vòng, đúng
    như tài liệu EDHOC quảng cáo. Nếu không thì mỗi khối một vòng.
    """
    per_msg = total_bytes / N_EDHOC_MSG
    if per_msg <= FITS_IN_ONE_FRAME:
        return 2, False                                   # không kích hoạt block-wise
    # cắt khối từng bản tin rồi cộng, cộng thêm phần dư của mỗi bản tin
    blocks = sum(ceil_div(int(per_msg), COAP_BLOCK) for _ in range(N_EDHOC_MSG))
    return blocks, True


print("  Ngưỡng kích hoạt block-wise: bản tin > %d byte (khung %d - mac/sec %d)"
      % (FITS_IN_ONE_FRAME, IEEE802154_FRAME, MAC_AND_SEC))
print("  DTLS 1.3 theo FLIGHT nên luôn %d vòng, KHÔNG phụ thuộc kích thước.\n" % DTLS_FLIGHT_RT)

print("  %-42s %7s %8s %7s   %s" % ("", "byte", "mỗi bản", "vòng", "trễ bắt tay (ms)"))
print("  %-42s %7s %8s %7s   %s"
      % ("", "", "tin", "", "  ".join("RTT=%d" % r for r in RTT_MS)))
print("  " + "-" * 100)

rows = {}
for name, nb in EDHOC.items():
    rt, blockwise = edhoc_round_trips(nb)
    rows[name] = rt
    lat = "  ".join("%7.0f" % (rt * r) for r in RTT_MS)
    mark = " ⚠block-wise" if blockwise else ""
    print("  %-42s %7d %8d %7d   %s%s" % (name, nb, nb // N_EDHOC_MSG, rt, lat, mark))

for name, nb in DTLS.items():
    rows[name] = DTLS_FLIGHT_RT
    lat = "  ".join("%7.0f" % (DTLS_FLIGHT_RT * r) for r in RTT_MS)
    print("  %-42s %7d %8s %7d   %s" % (name, nb, "flight", DTLS_FLIGHT_RT, lat))

print()
print("  === TRỤC SỐ VÒNG: lợi thế của EDHOC TRƯỚC và SAU PQC ===")
for e, d, lbl in (("EDHOC Static DH (cổ điển)", "DTLS 1.3 RPK+ECDHE (cổ điển)", "cổ điển, gọn nhất"),
                  ("EDHOC Signature (cổ điển)", "DTLS 1.3 RPK+ECDHE (cổ điển)", "cổ điển, chữ ký"),
                  ("EDHOC hybrid KEM (MobiSec'25)", "DTLS 1.3 RPK+ECDHE (cổ điển)", "hybrid vs DTLS cổ điển"),
                  ("EDHOC Signature + ML-KEM-768/ML-DSA-65",
                   "DTLS 1.3 + ML-KEM-768/ML-DSA-65", "PQ đầy đủ")):
    re_, rd = rows[e], rows[d]
    verdict = "EDHOC THUA %.0fx" % (re_ / rd) if re_ > rd else ("hoà" if re_ == rd else "EDHOC thắng")
    print("  %-26s EDHOC %4d vòng  vs  DTLS %2d vòng   →  %s" % (lbl, re_, rd, verdict))

print()
print("  ⇒ ĐỌC BẢNG. Cổ điển, cả hai đều 2 vòng: EDHOC không thua, và lợi thế của nó nằm ở")
print("    BYTE chứ không ở vòng. Sau PQC, DTLS VẪN 2 vòng vì nó theo flight, còn EDHOC bị")
print("    đẩy sang lock-step nên số vòng nở theo kích thước. Đây KHÔNG phải lợi thế co lại,")
print("    mà là lợi thế ĐẢO CHIỀU, và nó đảo vì đổi CHẾ ĐỘ TRUYỀN TẢI chứ không vì đổi số.")
print()
print("  ✅ PHẢN BIỆN (a) ĐÃ ĐÓNG bằng mã nguồn: Q-Block (RFC 9177) vắng mặt ở Contiki-NG và")
print("     RIOT, ở libcoap là cờ bật tay, và RFC 9668/9528 nhắc nó 0 lần. Cỡ khối 64 là mặc")
print("     định ĐÃ KIỂM ở cả hai ngăn xếp. Lock-step nằm trong tệp tên coap-blocking-api.c.")
print()
print("  ⛔ CÒN LẠI, phải trả lời trong bài:")
print("    (b) Tăng cỡ khối thì lại rơi về phân mảnh 6LoWPAN, đổi trục chứ không thoát.")
print("        Đây là ĐÁNH ĐỔI phải VẼ RA, và nó có thể thành hình chính của bài.")
print("    (c) Phải khai phạm vi là EDHOC-trên-CoAP đúng cấu hình RFC 9668.")
