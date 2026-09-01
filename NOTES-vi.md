# Đề cương P3, BẢN 2 (01/09/2026) — viết lại sau occupied-check lần hai

⚠ **Bản 1 đã bỏ.** Nó dựng bài trên bốn trục, và occupied-check lần hai giết mất hai.
Lý do và bằng chứng ở sổ: `reference-pq-edhoc-fraile-da-chiem`.

---

## 0. Chỗ đứng, một bảng

| | Fedrecheski, WCNC 2024 | Fraile et al., IEEE Access 2025 | **bài này** |
|---|---|---|---|
| so EDHOC với DTLS | ✅ | ❌ | ✅ |
| chứng thư hậu lượng tử | ❌ cổ điển | ✅ | ✅ |
| link IEEE 802.15.4 | ✅ | ❌ (BLE) | ✅ |
| **đếm SỐ LƯỢT trao đổi** | ❌ (đo thời lượng) | ❌ (đo RTT) | ✅ |
| **khảo sát NHIỀU cài đặt DTLS** | ❌ | ❌ | ✅ |

Bài này **không cạnh tranh** với hai bài trên. Nó nằm ở **giao** của chúng, và phải viết
đúng như vậy ngay từ phần mở đầu.

## 1. Câu chuyện, ba câu

Fedrecheski đo được EDHOC nhỏ hơn DTLS **×6 đến ×14 về cỡ gói**, nhưng thời lượng bắt tay
chỉ cải thiện **×1,44**. Lợi thế kích thước đã không chuyển thành lợi thế tương xứng, **ngay
ở chế độ cổ điển**. Bài này hỏi chuyện gì xảy ra khi chứng thư hậu lượng tử đẩy kích thước
qua ngưỡng khung.

⭐ Câu mở đầu **mượn số của chính bài chuẩn đối chiếu**. Đó là cách mở mạnh nhất cho bài kiểm
toán: không phải tôi nghi ngờ, mà chính phép đo của họ đã hé ra.

## 2. Tên tạm

*Does the Lightweight Handshake Stay Lightweight? EDHOC, DTLS 1.3 and Post-Quantum
Credentials on IEEE 802.15.4 Links*

## 3. Đóng góp, xếp lại theo sức nặng THẬT

**C1 (MẠNH NHẤT, và không bài nào chạm tới) — ba cài đặt DTLS, ba giới hạn khác nhau.**
Đo ở MTU 102 B, payload một khung 802.15.4:

| | tại MTU 102 | thứ chặn nó |
|---|---|---|
| mbedTLS 3.6.2 | chạy, kể cả 32 mảnh | không thấy giới hạn trong dải quét |
| GnuTLS 3.8.13 | tới ~23 mảnh | **số mảnh**, 23 được / 28 hỏng |
| OpenSSL 3.6.4 | **không chạy được** | **sàn MTU 256** (`DTLS1_MIN_MTU`) |

Hai trục **trực giao**, mỗi trục tách sạch đúng cài đặt của nó. Hệ quả thực tiễn: **OpenSSL
không chạy DTLS trên link 802.15.4 ở BẤT KỲ cỡ chứng thư nào**, kể cả cổ điển. Đây là thứ
người triển khai cần biết mà chưa tài liệu nào nói.

⚠ Ba cài đặt lệch nhau quá xa nên **không được viết thành tuyên bố về giao thức DTLS**. Chỉ
là tuyên bố về từng cài đặt. Script tự in đúng cảnh báo đó.

**C2 — đổi CHẾ ĐỘ TRUYỀN TẢI, không phải đổi con số.**
DTLS cắt ở tầng bắt tay và đi theo flight nên số lượt là hằng số [RFC 9147]. EDHOC trên CoAP
đi theo khối và **lock-step**, RFC 7959 ghi rõ *"multiple request-response pairs"*, nên số
lượt nở tuyến tính. Cổ điển hai bên hoà; hậu lượng tử thì tách hẳn.
✅ Đã đo: mô hình khớp aiocoap **7/7** trên datagram thật, ở cả macOS lẫn Linux.

**C3 — điều kiện mà CHÍNH CHUẨN tự khai, chưa ai đo.**
RFC 9668 §1: lợi thế *"can be lost"* khi gặp block-wise, và hai lượt chỉ đạt được khi
`message_3` *"relatively small ... within target MTU sizes"*. §3.2.2 Step 3.1 còn có đường lui
chuẩn tắc. Chưa ai đo bao giờ điều kiện đó vỡ.

**C4 — giới hạn KHÔNG phụ thuộc thiết kế.**
Khoá đóng gói ML-KEM-512 là **800 B**, tức **7,8 lần** payload khung 802.15.4 (102 B).
Block-wise kích hoạt **ngay ở message_1**, ở mọi bộ tham số, bất kể chọn xác thực thế nào.
Không thiết kế lại được, vì khoá công khai KEM bắt buộc lên dây.

## 4. Cái gì ĐÃ BỎ khỏi bản 1, và vì sao

| bỏ | lý do |
|---|---|
| trục "kích thước EDHOC hậu lượng tử" làm đóng góp | Fraile et al. đã làm, **trên nRF52840 thật kèm năng lượng** |
| trục "quét cỡ khối CoAP" làm đóng góp | Fraile et al. đã quét đúng dải 32–1024 |
| mọi phát biểu về **giây** và **năng lượng** | không đo được ở đây, và hai bài kia đã đo tốt hơn |

⇒ Hai trục đó **vẫn giữ trong bài**, nhưng ở vai **nền dẫn có trích dẫn**, không phải đóng góp.

## 5. Bố cục

| mục | nội dung | trạng thái |
|---|---|---|
| 1 | Mở đầu: mượn ×6–14 so với ×1,44 của Fedrecheski làm câu hỏi | ✅ có số |
| 2 | Nền: EDHOC, DTLS 1.3, CoAP block-wise, 802.15.4 | chưa viết |
| 3 | Điều kiện chuẩn tự khai (RFC 9668 §1, §3.2.2) | ✅ có trích gốc |
| 4 | Mô hình chi phí: byte, lượt, khung phải phát | ✅ `analysis/model.py` |
| 5 | Đối chiếu mô hình với cài đặt độc lập (7/7) | ✅ M1 |
| 6 | **Khảo sát ba cài đặt** ← ĐÓNG GÓP CHÍNH | ✅ M3 |
| 7 | Bàn luận: hàm ý cho hồ sơ EDHOC hậu lượng tử | chưa viết |
| 8 | Đe doạ tới tính hợp lệ | ✅ đã liệt kê |

**Hình**: `fig0` cơ chế (TikZ) · `fig1` tỉ số byte · `fig2` số lượt kèm điểm đo ·
`fig3` quét cỡ khối · **`fig4` khảo sát cài đặt, hình chính** · `fig5` phân rã bản tin.
Tất cả sinh bằng `bash figures/build.sh`.

## 6. Đe doạ tới tính hợp lệ, khai trước

| đe doạ | mức | xử lý |
|---|---|---|
| Không đo trên phần cứng ràng buộc | **cao** | Khai thẳng. Trục số lượt là tính chất giao thức nên đo được ở tầng vận chuyển; trục giây và năng lượng **không tuyên bố gì** |
| Ba cài đặt lệch nhau ⇒ không suy ra giao thức | trung bình | Đã khai trong chính script và trong bảng |
| `MAC_AND_SEC = 25` là ước lượng | thấp | 800 so với 102 thì vài byte không lật kết luận |
| Giả định mất ĐỘC LẬP | trung bình | Chưa chạy mất theo cụm. Khai, hoặc bỏ hẳn trục xác suất |
| Phạm vi chỉ EDHOC-trên-CoAP | phải khai | Đúng cấu hình RFC 9668 |
| Mới có **abstract** Fedrecheski | **phải xử lý** | Lấy toàn văn trước khi viết mục 1 |

## 7. Việc còn lại, theo thứ tự

1. **Lấy toàn văn Fedrecheski** (HAL chặn bot; thử qua thư viện trường hoặc hỏi tác giả).
2. Xác nhận họ không đếm số lượt và không bàn lock-step.
3. Viết mục 6 trước, vì đó là đóng góp chính và số đã có sẵn.
4. Cân nhắc chạy **artifact PQ-EDHOC của Fraile** để có nhánh EDHOC thật thay vì mô hình.

---

⛔ **Nhắc**: IoT-70170 hạn **23/09** và TAI hạn **29/09** là hai hạn CỨNG. Bài này không có hạn.
