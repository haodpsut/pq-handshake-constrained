# Đề cương P3 cho Computer Communications (Elsevier, hybrid, nộp thường miễn phí)

Trạng thái 29/08/2026. Bốn spike đã chạy, ba phép kiểm đã bác hoặc sửa chính lập luận của
tôi. Đây là đề cương, KHÔNG phải bản thảo.

---

## 0. Một câu

Chuẩn EDHOC-trên-CoAP tự khai lợi thế hai vòng của nó **"có thể mất"** khi gặp block-wise, và
treo lợi thế đó vào điều kiện bản tin đủ nhỏ để lọt MTU. Hậu lượng tử phá đúng điều kiện ấy ở
**mọi** bộ tham số NIST, và không có cấu hình nào chỉnh lại được.

## 1. Tên tạm

*When the Lightweight Handshake Stops Being Light: EDHOC under Post-Quantum Credentials on
Constrained Links*

Tránh chữ "reality check" vì đã có bài QUNAP dùng. Tránh "revisited" vì Computer Networks vừa
có một bài. Nhan đề nên nêu ĐIỀU KIỆN, vì đóng góp là chỉ ra điều kiện chứ không phải bác bỏ
giao thức.

## 2. Vì sao là bài KIỂM TOÁN chứ không phải bài phương pháp

Theo [[feedback-tim-de-tai-kiem-toan-khong-phai-cho-trong]]: hỏi **giả định chịu lực nào chưa
ai đo**, không hỏi chỗ trống nào chưa ai chiếm.

Giả định chịu lực ở đây là **"EDHOC nhẹ hơn DTLS nên hợp cho thiết bị ràng buộc"**. Nó có mặt
trong chính RFC, trong tài liệu quảng bá, và trong quần thể bài trích lại. Chưa ai đo nó
**dưới điều kiện hậu lượng tử**, mà điều kiện đó đang tới.

⚠ Venue: **Computer Communications** có tiền lệ đúng dạng, bài *"From theory to practice"* về
cấp phát SF trong LoRaWAN (2025). ⛔ **Không** gửi Computers & Security (cấm bài AI/ML, không
liên quan nhưng nhớ luật đọc danh sách loại trừ ở vị trí 0).

## 3. Đóng góp, xếp theo sức nặng

**C1. Một giới hạn không phụ thuộc thiết kế.** Khoá đóng gói ML-KEM-512 là 800 B, tức **7,8
lần** payload khung 802.15.4 (102 B). Nên CoAP block-wise bị kích hoạt **ngay ở message_1**,
ở mọi bộ tham số, bất kể chọn xác thực thế nào. Không thiết kế lại được, vì khoá công khai
KEM bắt buộc lên dây.

**C2. Lợi thế ĐẢO CHIỀU chứ không co lại.** DTLS 1.3 cắt ở tầng bắt tay và truyền theo
flight, nên số vòng là hằng số bất kể kích thước (RFC 9147 §5.5). EDHOC trên CoAP truyền theo
khối và **lock-step** (RFC 7959: *"multiple request-response pairs"*), nên số vòng nở tuyến
tính. Cổ điển hai bên hoà ở 2 vòng; hậu lượng tử EDHOC lên 140 còn DTLS vẫn 2.

**C3. Không gian chỉnh đã quét hết, không có lối ra.** Quét toàn dải cỡ khối RFC 7959 cho
phép: tối ưu vẫn thua 4 đến 8 lần, tối ưu nằm ở BIÊN chứ không phải điểm trong, và tối ưu
**không với tới** trên RIOT vì `CONFIG_NANOCOAP_BLOCK_SIZE_MAX = COAP_BLOCKSIZE_64` là trần
biên dịch. Thêm: tối ưu độ trễ (1024) và tối ưu năng lượng (512) **nằm ở hai chỗ khác nhau**.

**C4. Lối thoát chuẩn tắc tồn tại trên giấy nhưng vắng mặt tại chỗ cần.** Q-Block (RFC 9177)
cho phép NON và ít lượt hơn, nhưng: không có trong Contiki-NG, không có trong RIOT, ở libcoap
là cờ phải bật tay, và **RFC 9668 lẫn RFC 9528 nhắc RFC 9177 đúng 0 lần**.

⚠ **C5 (chỉ khi làm được đo thật)** đo trên testbed, xem mục 6.

## 4. Bố cục

| mục | nội dung | trạng thái |
|---|---|---|
| 1 | Mở đầu: giả định chịu lực và vì sao nó tới hạn | chưa viết |
| 2 | Nền: EDHOC, DTLS 1.3, CoAP block-wise, 6LoWPAN | chưa viết |
| 3 | **Điều kiện mà chuẩn tự khai**: RFC 9668 §1 và §3.2.2 Step 3.1 | ✅ có trích dẫn gốc |
| 4 | Mô hình chi phí: byte, lượt trao đổi, khung phải phát | ✅ spike 2+4 |
| 5 | Kết quả phân tích, 9 bộ tham số NIST | ✅ spike 1+4 |
| 6 | Không gian chỉnh: đường cong cỡ khối, **HÌNH CHÍNH** | ✅ spike 3 |
| 7 | Khảo sát cài đặt: Contiki-NG, RIOT, libcoap | ✅ đã đọc mã |
| 8 | Đo trên testbed | ⛔ CHƯA LÀM |
| 9 | Bàn luận: hàm ý cho thiết kế hồ sơ EDHOC hậu lượng tử | chưa viết |
| 10 | Đe doạ tới tính hợp lệ | ✅ đã liệt kê, mục 7 dưới đây |

**Hình chính** (mục 6): trục hoành cỡ khối 16…1024, trục tung E[lượt] và E[khung] hai thang,
đường ngang của DTLS nằm dưới hẳn, vạch đứng ở trần RIOT = 64, đánh dấu hai điểm tối ưu khác
nhau của hai trục. Một hình kể trọn C2 và C3.

⭐ Dùng bộ style nhà: `transaction-figure-kit`. Hình ngang của kit là để TRẢI HAI CỘT.

## 5. Định vị so với công trình liên quan

**Mục tiêu kiểm toán có tên**: *A Hybrid EDHOC Protocol* (MobiSec'25, 12/2025). Bài đó đề
xuất EDHOC hậu lượng tử bằng KEM tạm thời và **tự báo** payload đi từ ≈64 B lên ≈2300–2400 B.
Trong toàn văn: **"DTLS" 3 lần, "6LoWPAN" và "fragment" 0 lần**. Tính theo mô hình ở đây, đề
xuất đó rơi vào **42 lượt**, tức thua DTLS 1.3 **cổ điển** 21 lần.

⚠ Viết mục này ở giọng **kiểm toán chứ không phải đối đầu**. Bài đó không sai trong phạm vi
nó tự đặt; điều nó bỏ sót là trục truyền tải. Đó chính là chỗ bài này bổ vào.

## 6. ⛔ Việc THỰC NGHIỆM còn thiếu, và vì sao không bỏ qua được

Luật của nhà: **thực nghiệm TRƯỚC, rồi mới viết từng section**
([[feedback-sua-theo-section-va-qa-tung-buoc]]). Hiện tại bài mới có **phân tích + đọc chuẩn +
đọc mã**, chưa có **đo**. Với Computer Communications, nơi tiền lệ là *"from theory to
practice"*, nộp bản chỉ có phân tích là hở đúng chỗ phản biện sẽ chọc.

Tối thiểu phải có:

1. **Chạy thật trên Contiki-NG hoặc RIOT** trong Cooja/native, đo số lượt và thời gian bắt
   tay khi bơm payload cỡ hậu lượng tử. Không cần cài ML-KEM thật: chỉ cần **độn payload**
   đúng kích thước, vì lập luận nằm ở KÍCH THƯỚC chứ không ở phép toán.
2. **Đối chiếu DTLS 1.3** trên cùng nền, cùng đường truyền.
3. **Mất theo cụm** thay giả định độc lập.

⚠ Điểm 1 là chỗ rẻ bất ngờ: **không cần phần cứng lượng tử, không cần cài PQC**, chỉ cần độn
byte. Đây là lý do hướng này khả thi trong khi bốn hướng quantum trước đều chết.

## 7. Đe doạ tới tính hợp lệ, khai trước

| đe doạ | mức | xử lý |
|---|---|---|
| `MAC_AND_SEC = 25` là ước lượng | thấp | 800 so với 102 thì vài byte header không lật được kết luận. Vẫn phải trích nguồn. |
| Giả định mất ĐỘC LẬP | **trung bình** | Mất theo cụm CÓ LỢI cho khối lớn ⇒ có thể dịch điểm tối ưu. Phải chạy Gilbert-Elliott. |
| Phân rã theo bản tin lệch 4,2% so bảng gốc | thấp | Đã khai. Không dùng cho số tuyệt đối. |
| Phạm vi chỉ là EDHOC-trên-CoAP | **phải khai rõ** | Đúng cấu hình RFC 9668. Nền khác thì lập luận không áp. |
| RTT mesh 100–500 ms chưa có nguồn | trung bình | Lấy từ đo thật ở mục 6, đừng trích dải. |
| DTLS 1.3 "luôn 2 vòng" | trung bình | Đúng cho bắt tay đầy đủ 1-RTT. Phải khai điều kiện, và kiểm khi flight rất dày. |

## 8. Việc tiếp theo, xếp theo thứ tự

1. Dựng testbed và đo (mục 6). **Đây là nút thắt, mọi thứ khác chờ nó.**
2. Mất theo cụm.
3. Trục quần thể: đếm bài còn trích lợi thế EDHOC không kèm điều kiện.
4. Chốt tham số còn treo.
5. Viết, theo luật từng section QA xong mới sang cái khác.

---

⛔ **Nhắc**: IoT-70170 hạn 23/09 là hạn CỨNG duy nhất, gói đã sẵn từ 27/08.
Bài này không có hạn.
