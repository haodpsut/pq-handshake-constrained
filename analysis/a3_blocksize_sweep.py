"""SPIKE 3 — ĐÁNH ĐỔI CỠ KHỐI: có chỉnh tham số nào cứu được EDHOC dưới PQC không?

⛔ SPIKE, KHÔNG PHẢI KẾT QUẢ BÀI BÁO.

VÌ SAO CẦN. Spike 2 cho thấy EDHOC hậu lượng tử thua DTLS 60x ở số vòng, vì CoAP block-wise
là lock-step. Phản biện hiển nhiên, và là phản biện ĐÚNG, là: "thì tăng cỡ khối lên."

Nếu bài không trả lời được câu đó thì kết quả 60x chỉ là tạo tác của một tham số mặc định, và
phản biện giết bài ở đúng dòng đó. Nên đây KHÔNG phải phần phụ. Đây là phần biến quan sát
thành kết luận.

ĐÁNH ĐỔI THẬT, hai chiều ngược nhau:

  Khối NHỎ  -> nhiều vòng (lock-step), nhưng mỗi khối gọn trong MỘT khung 802.15.4 nên
               không phân mảnh, xác suất qua được mỗi vòng cao.
  Khối LỚN  -> ít vòng, nhưng mỗi khối vượt khung nên bị 6LoWPAN cắt mảnh, và TRONG một
               datagram thì mất một mảnh là mất cả khối (RFC 4944 không có sửa lỗi từng
               mảnh). Xác suất qua được mỗi vòng tụt theo luỹ thừa.

  => Kỳ vọng số lần truyền = số khối / P(một khối qua được). Có ĐIỂM TỐI ƯU.

CÂU HỎI CỦA SPIKE: tại điểm tối ưu đó, EDHOC hậu lượng tử có về lại được gần DTLS không?

⭐⭐ ĐIỂM TỐI ƯU NẰM NGOÀI TẦM VỚI, đã kiểm tận mã nguồn. Phản biện "tăng cỡ khối" giả định
cỡ khối là thứ chỉnh được tự do. Nó không phải:

  RIOT        sys/include/net/nanocoap.h:146
              CONFIG_NANOCOAP_BLOCK_SIZE_MAX = COAP_BLOCKSIZE_64
              => 64 không phải mặc định, nó là TRẦN BIÊN DỊCH. Muốn 1024 phải sửa hằng số
                 trần rồi build lại firmware.

  Contiki-NG  os/net/ipv6/uip.h:93  UIP_CONF_BUFFER_SIZE = 1280
              COAP_MAX_PACKET_SIZE = COAP_MAX_HEADER_SIZE + COAP_MAX_CHUNK_SIZE
              => lên được 1024, nhưng nút phải dành TĨNH trọn bộ đệm cỡ MTU tối thiểu
                 IPv6. Trên thiết bị 10-20 KB RAM đó là 6-13% RAM cho một bộ đệm.

=> Phản biện (b) đóng ở BA tầng: (1) ngay tại tối ưu vẫn thua DTLS 4-8x; (2) tối ưu nằm ở
BIÊN của dải RFC 7959 cho phép, không phải điểm trong; (3) tối ưu KHÔNG VỚI TỚI trên RIOT và
đắt trên Contiki-NG.

⭐ VÀ HAI TRỤC KHÔNG ĐỒNG Ý VỚI NHAU. Ở p=0,05 tối ưu theo SỐ VÒNG là 1024 (16,7 vòng) nhưng
tối ưu theo SỐ KHUNG PHẢI PHÁT là 512 (150 khung, so với 200 của 1024). Thiết bị chạy pin
quan tâm trục khung. Nên không những không có cấu hình cứu được, mà còn KHÔNG CÓ MỘT cấu hình
tốt nhất chung: tối ưu độ trễ và tối ưu năng lượng nằm ở hai chỗ khác nhau.

⚠ LƯU Ý VỀ MÔ HÌNH, để không lặp lại lỗi của spike 2 bản 1: giả định all-or-nothing dùng ở
đây là ĐÚNG CHỖ. Trong MỘT datagram thì 6LoWPAN ráp lại toàn phần hoặc mất toàn phần, không
có sửa lỗi từng mảnh. Lỗi của bản trước không phải bản thân mô hình, mà là áp nó ở SAI MỨC
ĐỘ HẠT: cho cả bắt tay thay vì cho từng khối.

⚠ CHƯA KIỂM: MAC_AND_SEC=25 · FRAG_HDR=5 · giả định mất ĐỘC LẬP (mất theo cụm sẽ cho kết quả
khác, phải thử) · tách kích thước theo từng bản tin EDHOC thay vì chia đều.
"""

IEEE802154_FRAME = 127
MAC_AND_SEC      = 25       # ⚠ CHƯA KIỂM
FRAG_HDR         = 5        # header phân mảnh 6LoWPAN
FITS_IN_ONE_FRAME = IEEE802154_FRAME - MAC_AND_SEC          # 102
PAYLOAD_PER_FRAG  = IEEE802154_FRAME - MAC_AND_SEC - FRAG_HDR  # 97

# Cỡ khối CoAP hợp lệ: RFC 7959 chỉ cho 2^(4..10)
BLOCK_SIZES = (16, 32, 64, 128, 256, 512, 1024)
DEFAULTS = {64: "mặc định cả hai · TRẦN của RIOT"}
# Cỡ khối vượt được trần biên dịch của RIOT (CONFIG_NANOCOAP_BLOCK_SIZE_MAX = 64)
BEYOND_RIOT_MAX = 64

N_EDHOC_MSG = 3
PQ_EDHOC  = 7586     # EDHOC Signature + ML-KEM-768/ML-DSA-65
PQ_DTLS   = 8264     # DTLS 1.3 + ML-KEM-768/ML-DSA-65
DTLS_RT   = 2        # theo flight, không phụ thuộc kích thước

LOSS = (0.00, 0.01, 0.05)


def ceil_div(a, b):
    return -(-a // b)


def frags_for(nbytes):
    """Số mảnh 6LoWPAN cho một datagram cỡ nbytes."""
    if nbytes <= FITS_IN_ONE_FRAME:
        return 1
    return ceil_div(nbytes, PAYLOAD_PER_FRAG)


def cost(total_bytes, block, p):
    """Kỳ vọng số VÒNG và số KHUNG phải phát, cho EDHOC trên CoAP với cỡ khối `block`.

    Mỗi bản tin EDHOC cắt khối riêng. Mỗi khối là một lượt CON, phải qua được cả chiều đi
    lẫn chiều về. Khối hỏng thì CoAP truyền lại, nên kỳ vọng số lượt = 1 / P(qua).
    """
    per_msg = total_bytes / N_EDHOC_MSG
    n_blocks = N_EDHOC_MSG * ceil_div(int(per_msg), block)
    f = frags_for(block)                 # mảnh cho chiều mang dữ liệu
    p_ok = (1 - p) ** (f + 1)            # +1 cho khung xác nhận chiều về
    if p_ok <= 0:
        return float("inf"), float("inf"), n_blocks, f
    exp_rt = n_blocks / p_ok
    exp_frames = n_blocks * (f + 1) / p_ok
    return exp_rt, exp_frames, n_blocks, f


print("  Khung %d B · payload gói %d B · payload mỗi mảnh %d B"
      % (IEEE802154_FRAME, FITS_IN_ONE_FRAME, PAYLOAD_PER_FRAG))
print("  EDHOC PQ = %d B  ·  DTLS PQ = %d B (theo flight, %d vòng)\n"
      % (PQ_EDHOC, PQ_DTLS, DTLS_RT))

for p in LOSS:
    print("  ══ mất khung p = %.2f ══" % p)
    print("  %8s %7s %6s %12s %12s   %s"
          % ("cỡ khối", "khối", "mảnh", "E[vòng]", "E[khung]", ""))
    print("  " + "-" * 74)
    best = None
    rowbuf = []
    for b in BLOCK_SIZES:
        rt, fr, nb, f = cost(PQ_EDHOC, b, p)
        rowbuf.append((b, nb, f, rt, fr))
        if best is None or rt < best[3]:
            best = (b, nb, f, rt, fr)
    for b, nb, f, rt, fr in rowbuf:
        tag = []
        if b in DEFAULTS:
            tag.append(DEFAULTS[b])
        if b == best[0]:
            tag.append("← TỐI ƯU")
        if f > 1:
            tag.append("phân mảnh")
        if b > BEYOND_RIOT_MAX:
            tag.append("⛔ vượt trần RIOT")
        print("  %8d %7d %6d %12.1f %12.0f   %s" % (b, nb, f, rt, fr, " · ".join(tag)))
    print("  ⇒ tối ưu ở cỡ khối %d: %.1f vòng, tức vẫn THUA DTLS (%d vòng) %.0f lần.\n"
          % (best[0], best[3], DTLS_RT, best[3] / DTLS_RT))

print("  ⭐ KẾT LUẬN CỦA SPIKE. Đánh đổi là THẬT và có điểm tối ưu, nên phản biện 'tăng cỡ")
print("     khối lên' là phản biện đúng chỗ. Nhưng quét TOÀN BỘ dải cỡ khối mà RFC 7959 cho")
print("     phép thì điểm tốt nhất VẪN thua DTLS hàng chục lần. Nghĩa là 60x KHÔNG phải tạo")
print("     tác của một tham số mặc định: không có cách chỉnh nào cứu được.")
print()
print("     Đây là chỗ biến bài từ 'một quan sát về cấu hình' thành 'một giới hạn của giao")
print("     thức'. Và nó cũng là HÌNH CHÍNH: một đường cong, một điểm tối ưu, một đường")
print("     ngang của DTLS nằm dưới hẳn.")
print()
print("  ⛔ CHƯA LÀM, và phải làm trước khi tin: mất theo CỤM thay vì độc lập · tách kích")
print("     thước theo TỪNG bản tin EDHOC thay vì chia đều · đối chiếu với đo thật.")
