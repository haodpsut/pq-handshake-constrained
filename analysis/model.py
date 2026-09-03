"""NGUỒN DUY NHẤT của mọi con số suy ra bằng mô hình.

VÌ SAO TỆP NÀY TỒN TẠI. Bốn script a1..a4 mỗi cái tự định nghĩa lại kích thước bản tin, cỡ
khung, cỡ khối. Khi hình và bảng cũng tự tính lại thì có SÁU chỗ cài đặt cùng một phép tính,
và chỉ cần sửa một chỗ là bài mâu thuẫn với chính nó mà không cổng nào bắt được. Luật của nhà:
mỗi con số phải có ĐÚNG MỘT chỗ ở, và bảng/hình phải SINH RA chứ không gõ tay.

⇒ Mọi thứ dưới đây là hằng số hoặc hàm thuần. Không in, không vẽ, không ghi tệp.

XUẤT XỨ TỪNG HẰNG SỐ được ghi ngay cạnh nó. Cái nào chưa có nguồn thì đánh dấu CHƯA KIỂM,
và bài không được trích cái đó mà không khai.
"""

# ── đường truyền ──────────────────────────────────────────────────────────────
IEEE802154_FRAME = 127      # byte, khung tối đa IEEE 802.15.4
MAC_AND_SEC = 25            # header MAC + AES-CCM*   ⚠ CHƯA KIỂM, là ước lượng
FRAG_HDR = 5                # header phân mảnh 6LoWPAN, mảnh tiếp theo
FRAME_PAYLOAD = IEEE802154_FRAME - MAC_AND_SEC              # 102
PAYLOAD_PER_FRAG = IEEE802154_FRAME - MAC_AND_SEC - FRAG_HDR  # 97

# ✅ ĐÃ KIỂM TẬN MÃ NGUỒN, hai ngăn xếp độc lập đều mặc định 64:
#   Contiki-NG  os/net/app-layer/coap/coap-conf.h:58   COAP_MAX_CHUNK_SIZE 64
#   RIOT        sys/include/net/nanocoap.h:153         CONFIG_NANOCOAP_BLOCKSIZE_DEFAULT
# và RIOT còn đặt TRẦN biên dịch cùng giá trị (nanocoap.h:146).
COAP_BLOCK = 64
RIOT_BLOCK_MAX = 64
BLOCK_SIZES = (16, 32, 64, 128, 256, 512, 1024)   # dải RFC 7959 cho phép, 2^(4..10)

DTLS_FLIGHT_RT = 2          # bắt tay DTLS 1.3 đầy đủ, theo flight  [RFC 9147]

# RFC 9177 (Q-Block1/Q-Block2). Đọc tận nguồn 03/09/2026:
#   "all the blocks can be transmitted serially (akin to fragmented IP packets) WITHOUT
#    HAVING TO WAIT for a response or next request from the remote CoAP peer"
#   "MAX_PAYLOADS should be configurable with a DEFAULT VALUE OF 10"
# Cơ chế: bắn MAX_PAYLOADS khối liên tiếp, server xác nhận cả cụm bằng một 2.31 (Continue),
# rồi tới cụm sau. Nên số vòng = trần(số khối / MAX_PAYLOADS), không phải mỗi khối một vòng.
QBLOCK_MAX_PAYLOADS = 10
N_EDHOC_MSG = 3

# ── cỡ khoá hậu lượng tử, FIPS 203/204 ────────────────────────────────────────
KEM = {"ML-KEM-512": (800, 768), "ML-KEM-768": (1184, 1088), "ML-KEM-1024": (1568, 1568)}
SIG = {"ML-DSA-44": (1312, 2420), "ML-DSA-65": (1952, 3309), "ML-DSA-87": (2592, 4627)}
G_LEN, SIG_LEN, CBOR_LONG = 32, 64, 3

# ── kích thước cổ điển, từ draft-ietf-iotops-security-protocol-comparison ─────
D_CLASSIC = 894     # DTLS 1.3, RPKs, ECDHE
E_SIG = 216         # EDHOC Signature RPKs, kid, ECDHE   (còn sống dưới PQC)
E_STATIC_DH = 101   # EDHOC Static DH RPKs, kid, ECDHE   (KHÔNG có bản PQC)

# RFC 9528 §3.2, bảng Method Type Value: method 0 = "Signature Key / Signature Key",
# tức CẢ HAI BÊN đều ký. DTLS xác thực hai chiều cũng vậy.
N_SIG = 2

# Phân rã theo từng bản tin, suy từ cấu trúc RFC 9528 §5. Tổng phải TÁI TẠO được E_SIG:
# đó là phép tự kiểm của chính phân rã, xem `decomposition_error()`.
CLASSIC_MSG = {
    "message_1": 1 + 1 + (32 + 2) + 1,               # METHOD, SUITES_I, G_X, C_I
    "message_2": (32 + 2) + (1 + 3 + 64 + 8) + 1,    # G_Y, CIPHERTEXT_2
    "message_3": (3 + 64 + 8) + 2,                   # CIPHERTEXT_3
}


def ceil_div(a, b):
    return -(-a // b)


def decomposition_error():
    """Lệch giữa tổng phân rã và con số bảng gốc, theo phần trăm. Trên 5% thì đừng dùng."""
    tot = sum(CLASSIC_MSG.values())
    return tot, E_SIG, 100.0 * (tot - E_SIG) / E_SIG


def pq_overhead(kem, sig, n_sig=N_SIG, n_cert_pk=1):
    """Byte PQC THÊM so với cổng cổ điển tương ứng, GIỐNG NHAU cho cả hai giao thức."""
    ek, ct = KEM[kem]
    pk, sg = SIG[sig]
    return (ek - 32) + (ct - 32) + n_sig * (sg - SIG_LEN) + n_cert_pk * (pk - 32)


def size_ratio(kem, sig):
    """(byte EDHOC, byte DTLS, tỉ số) sau khi thêm PQC."""
    x = pq_overhead(kem, sig)
    e, d = E_SIG + x, D_CLASSIC + x
    return e, d, d / e


def pq_messages(kem, sig, pq_sign=True):
    """Kích thước TỪNG bản tin EDHOC hậu lượng tử.

    pq_sign=False mô hình biến thể NHẸ NHẤT có thể hình dung: chỉ KEM hậu lượng tử, xác thực
    vẫn cổ điển, chứng thư theo tham chiếu. Dùng để tìm SÀN của lập luận.
    """
    ek, ct = KEM[kem]
    _, sg = SIG[sig]
    d_sig = (sg - SIG_LEN) if pq_sign else 0
    return {
        "message_1": CLASSIC_MSG["message_1"] - G_LEN + ek + CBOR_LONG,
        "message_2": CLASSIC_MSG["message_2"] - G_LEN + ct + CBOR_LONG + d_sig,
        "message_3": CLASSIC_MSG["message_3"] + d_sig,
    }


def exchanges_for_message(nbytes, block=COAP_BLOCK):
    """Số lượt trao đổi CoAP cho MỘT bản tin. Lọt khung thì 1 lượt, không thì mỗi khối 1 lượt.

    ✅ Hàm này đã được ĐO đối chiếu: `measure/m1_coap_blockwise.py` chạy aiocoap thật, đếm
    datagram qua relay, khớp 7/7 ở cả macOS lẫn Linux.
    """
    if nbytes <= FRAME_PAYLOAD:
        return 1
    return ceil_div(nbytes, block)


def edhoc_exchanges(msgs, block=COAP_BLOCK):
    return sum(exchanges_for_message(v, block) for v in msgs.values())


def frags_for(nbytes):
    """Số mảnh 6LoWPAN cho một datagram. Trong MỘT datagram thì ráp toàn phần hoặc mất cả."""
    return 1 if nbytes <= FRAME_PAYLOAD else ceil_div(nbytes, PAYLOAD_PER_FRAG)


def blocksize_cost(msgs, block, p_loss):
    """Kỳ vọng (số lượt, số khung phải phát) cho một cỡ khối, dưới tỉ lệ mất khung p_loss.

    Mỗi khối là một lượt CON, phải qua được cả chiều đi lẫn chiều về; khối hỏng thì truyền
    lại, nên kỳ vọng số lượt = số khối / P(qua).

    ⛔ BẢN TRƯỚC NHẬN `total_bytes` RỒI CHIA ĐỀU CHO 3. Đó là xấp xỉ tôi đã bỏ ở
    `pq_messages()` nhưng QUÊN bỏ ở đây, nên `model.py` tự mâu thuẫn với chính nó: hai hàm
    trong cùng một tệp trả lời khác nhau cho cùng một câu hỏi. Đọc ngoài bắt được: ở cỡ khối
    1024 thì chia đều cho 9 lượt, còn tính đúng từng bản tin cho **11** (2+5+4). Nay nhận
    THẲNG dict kích thước từng bản tin để không thể lặp lại.
    """
    n_blocks = sum(ceil_div(v, block) for v in msgs.values())
    f = frags_for(block)
    p_ok = (1 - p_loss) ** (f + 1)
    if p_ok <= 0:
        return float("inf"), float("inf"), n_blocks, f
    return n_blocks / p_ok, n_blocks * (f + 1) / p_ok, n_blocks, f


def qblock_exchanges(msgs, block=COAP_BLOCK, max_payloads=QBLOCK_MAX_PAYLOADS):
    """Số vòng nếu dùng RFC 9177 Q-Block với bản tin NON, thay cho RFC 7959 lock-step.

    Đọc ngoài yêu cầu mô hình hoá cái này thay vì gạt đi vì "chưa ai cài". Đúng: gạt một
    phương án chỉ vì chưa được cài đặt là phát biểu kết luận ở mức CẤU TRÚC dựa trên một sự
    kiện NHẤT THỜI.

    Mỗi bản tin EDHOC vẫn cắt khối riêng, nhưng trong một bản tin thì các khối đi liên tiếp
    theo cụm MAX_PAYLOADS, mỗi cụm tốn một lượt xác nhận.
    """
    return sum(max(1, ceil_div(ceil_div(v, block), max_payloads)) for v in msgs.values())


PARAM_SETS = [(k, s) for k in KEM for s in SIG]
