"""ĐO THẬT (BẢN 2) — số lượt trao đổi CoAP block-wise trên cài đặt RFC 7959 ĐỘC LẬP.

VÌ SAO. Spike 2/3/4 đều dựa vào MỘT mô hình do chính tôi viết: số lượt = số khối. Kiểm nội bộ
chỉ chứng minh nhất quán; muốn chứng minh ĐÚNG phải có cài đặt độc lập đối chiếu. Cài đặt đó
là **aiocoap**, không phải mã của tôi.

⛔ BẢN 1 ĐẾM SAI ĐƠN VỊ, ghi lại để không lặp. Bản 1 đếm số lần server gọi hàm tài nguyên
(`render_get`). Nhưng `aiocoap/blockwise.py` có `Block2Cache`: nó gọi hàm tài nguyên ĐÚNG MỘT
LẦN, dựng trọn thân bản tin, rồi cắt từng khối TỪ BỘ NHỚ ĐỆM. Nên số đếm luôn ra 1 dù có bao
nhiêu lượt trên dây. Bản 1 báo "1/7 khớp" trong khi thật ra nó đo 0 đơn vị, và ca "khớp" duy
nhất là khớp NHẦM.

⇒ Bản 2 đếm **datagram UDP thật đi qua dây**, bằng một relay đặt giữa client và server. Đây
là đại lượng vật lý cần đo, và cách đếm này KHÔNG phụ thuộc ruột của aiocoap.

⚠ ĐÂY KHÔNG PHẢI THIẾT BỊ RÀNG BUỘC. Không 6LoWPAN, không 802.15.4. Phép đo này trả lời ĐÚNG
MỘT câu: **số lượt block-wise có bằng số khối như mô hình giả định không.** Trễ và năng lượng
phải đo ở nơi khác.
"""

import asyncio
import json
import os
import sys

import aiocoap
import aiocoap.interfaces
import aiocoap.resource as resource
from aiocoap.optiontypes import BlockOption

# Cỡ khối 64 B, đúng mặc định VÀ trần biên dịch của Contiki-NG và RIOT.
# CoAP: cỡ khối = 2^(SZX+4). SZX=2 -> 64.
#
# ⛔ HAI BẢN TRƯỚC ĐỀU VÁ RUỘT THƯ VIỆN, VÀ CÁCH ĐÓ HỎNG THEO PHIÊN BẢN.
# Bản trước gán thẳng `aiocoap.interfaces.EndpointAddress.maximum_block_size_exp = 2`.
# Ở aiocoap 0.4.7 đó là thuộc tính lớp thường nên gán được; ở **0.4.17 nó là `property`**,
# nên phép gán KHÔNG có tác dụng và **thất bại IM LẶNG**. Hậu quả đo được: cùng script,
# máy Mac (0.4.7) báo 7/7 khớp, máy Linux (0.4.17) báo 2/7 -- vì Linux vẫn dùng khối 1024
# mặc định (4415 B ra 5 lượt = 4415/1024, không phải 69 lượt = 4415/64).
#
# ⇒ Con số "7/7" cũ là ăn may theo phiên bản, không phải kết quả. Bản này KHÔNG vá ruột nữa:
# client TỰ KHAI Block2 trong yêu cầu, đúng cơ chế RFC 7959 cho phép bên nhận đề nghị cỡ
# khối, rồi KIỂM LẠI cỡ khối thực nhận và DỪNG nếu khác. Cách này không phụ thuộc phiên bản.
SZX = 2
BLOCK_SIZE = 2 ** (SZX + 4)

# NGƯỠNG KÍCH HOẠT block-wise. aiocoap mặc định `maximum_payload_size = 1124`
# (interfaces.py:153), dùng ở blockwise.py:114 làm điều kiện quyết định. Đó là con số hợp lý
# cho máy để bàn, KHÔNG phải cho 802.15.4. Hạ về payload khung thật để mô phỏng đường truyền
# ràng buộc: 127 - 25 (MAC + AES-CCM*) = 102.
#
# ⚠ Đây là chỗ phép đo và mô hình PHẢI dùng CÙNG một ngưỡng, nếu không thì lệch là do cấu
# hình chứ không do mô hình sai. Bản 2 chạy lần đầu lệch 3/7 đúng vì lý do này.
FRAME_PAYLOAD = 102

SERVER_PORT = 15683
RELAY_PORT = 15684

CASES = [
    ("EDHOC msg_1 cổ điển",              37),
    ("EDHOC msg_2 cổ điển",             111),
    ("EDHOC msg_3 cổ điển",              77),
    ("EDHOC msg_1 + ML-KEM-512",        808),
    ("EDHOC msg_1 + ML-KEM-768",       1192),
    ("EDHOC msg_2 + K768/D65",         4415),
    ("EDHOC msg_3 + K768/D65",         3322),
]


class Payload(resource.Resource):
    def __init__(self):
        super().__init__()
        self.size = 0

    async def render_get(self, request):
        return aiocoap.Message(payload=b"A" * self.size)


class Relay(asyncio.DatagramProtocol):
    """Relay UDP đếm datagram theo cả hai chiều. Đây là chỗ ĐO."""

    def __init__(self, server_addr):
        self.server_addr = server_addr
        self.transport = None
        self.client_addr = None
        self.c2s = 0
        self.s2c = 0

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if addr == self.server_addr:
            self.s2c += 1
            if self.client_addr is not None:
                self.transport.sendto(data, self.client_addr)
        else:
            self.c2s += 1
            self.client_addr = addr
            self.transport.sendto(data, self.server_addr)

    def reset(self):
        self.c2s = self.s2c = 0


def predicted(nbytes):
    """Dự đoán của MÔ HÌNH, đúng như spike 2/3/4 dùng.

    Lọt khung thì một lượt, không thì cắt khối và mỗi khối một lượt.
    """
    if nbytes <= FRAME_PAYLOAD:
        return 1
    return -(-nbytes // BLOCK_SIZE)


async def main():
    res = Payload()
    site = resource.Site()
    site.add_resource(["p"], res)
    ctx_s = await aiocoap.Context.create_server_context(site, bind=("127.0.0.1", SERVER_PORT))

    loop = asyncio.get_running_loop()
    _, relay = await loop.create_datagram_endpoint(
        lambda: Relay(("127.0.0.1", SERVER_PORT)), local_addr=("127.0.0.1", RELAY_PORT))

    ctx_c = await aiocoap.Context.create_client_context()

    print("  Cỡ khối ép về %d B (SZX=%d), đúng mặc định Contiki-NG + RIOT." % (BLOCK_SIZE, SZX))
    print("  Đếm DATAGRAM UDP thật, qua relay ở giữa. Cài đặt: aiocoap (độc lập).\n")
    print("  %-28s %8s %9s %9s %9s   %s"
          % ("trường hợp", "byte", "mô hình", "ĐO: đi", "ĐO: về", "khớp?"))
    print("  " + "-" * 84)

    ok = bad = 0
    rows = []
    for name, size in CASES:
        res.size = size
        relay.reset()
        req = aiocoap.Message(code=aiocoap.GET, uri="coap://127.0.0.1:%d/p" % RELAY_PORT)
        # Tự khai cỡ khối mong muốn thay vì vá ruột thư viện.
        if size > FRAME_PAYLOAD:
            req.opt.block2 = BlockOption.BlockwiseTuple(0, False, SZX)
        try:
            resp = await asyncio.wait_for(ctx_c.request(req).response, timeout=30)
        except Exception as e:                                   # noqa: BLE001
            print("  %-28s %8d %9s %9s %9s   ⛔ %s"
                  % (name, size, predicted(size), "-", "-", type(e).__name__))
            bad += 1
            continue
        assert len(resp.payload) == size, \
            "payload ve %d, mong doi %d" % (len(resp.payload), size)
        # ⭐ KIỂM CẤU HÌNH ĐÃ CÓ HIỆU LỰC. Nếu cỡ khối thực khác cỡ đã yêu cầu thì phép đo
        # không đo cái mình tưởng, và im lặng bỏ qua chính là cách sinh ra "7/7" giả.
        if size > FRAME_PAYLOAD:
            got_szx = resp.opt.block2.size_exponent if resp.opt.block2 else None
            if got_szx != SZX:
                print("  ⛔ DỪNG: yêu cầu cỡ khối %d (SZX=%d) nhưng nhận SZX=%s."
                      % (BLOCK_SIZE, SZX, got_szx))
                print("     Phép đo sẽ không đo cái mình tưởng. Sửa trước, đừng đọc số.")
                return 3
        pred, meas = predicted(size), relay.c2s
        if pred == meas:
            ok += 1
            match = "✅"
        else:
            bad += 1
            match = "⛔ LỆCH %+d" % (meas - pred)
        print("  %-28s %8d %9d %9d %9d   %s"
              % (name, size, pred, relay.c2s, relay.s2c, match))
        rows.append({"case": name, "bytes": size, "predicted": pred,
                     "measured_c2s": relay.c2s, "measured_s2c": relay.s2c,
                     "match": pred == meas})

    await ctx_s.shutdown()
    await ctx_c.shutdown()
    relay.transport.close()

    print()
    print("  ⇒ %d khớp, %d lệch, trên %d trường hợp." % (ok, bad, len(CASES)))
    if bad == 0:
        print("  ✅ Mô hình 'số lượt = số khối' KHỚP cài đặt độc lập ở mọi cỡ đã thử.")
        print("     Đây là điều kiện CẦN để tin spike 2/3/4, KHÔNG phải điều kiện đủ: nó xác")
        print("     nhận PHÉP ĐẾM, chưa xác nhận trễ và năng lượng trên đường truyền thật.")
    else:
        print("  ⛔ CÓ LỆCH. Phải giải thích được TỪNG ca trước khi dùng mô hình.")

    # Số nào vào bài thì phải TRÍCH TỰ ĐỘNG từ đây, không gõ tay.
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "results", "m1_coap_blockwise.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"block_size": BLOCK_SIZE, "szx": SZX,
                   "frame_payload": FRAME_PAYLOAD,
                   "implementation": "aiocoap 0.4.7",
                   "counted": "UDP datagrams via relay",
                   "n_match": ok, "n_mismatch": bad, "rows": rows}, f,
                  indent=2, ensure_ascii=False)
    print("  → %s" % os.path.basename(out))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
