# Nguồn dữ liệu

Mỗi nguồn dữ liệu của RentalPulse được ghi và đánh giá ở đây trước khi viết code thu thập.
File này là nguồn sự thật (source of truth) về nguồn dữ liệu. Không tạo file trùng lặp.

## Quy ước

- Mỗi nguồn có: cách truy cập, quyền sử dụng, tần suất, xử lý dữ liệu cá nhân, ghi chú kỹ thuật.
- Trạng thái nguồn: `đang dùng` / `ứng viên` / `không dùng`.
- Chỉ chuyển sang `đang dùng` khi đã kiểm tra `robots.txt` và điều khoản sử dụng.
- Mọi collector phải tham chiếu tên nguồn trong file này.

## Nguồn đang dùng

| Nguồn | Cách truy cập | Quyền sử dụng | Tần suất | Dữ liệu cá nhân | Ghi chú |
|---|---|---|---|---|---|
| mock | Sinh bằng code (`collectors/mock_source.py`) | Dữ liệu tự tạo | Theo tham số `--day` | Không | Có kịch bản kiểm thử và dữ liệu bẩn có chủ ý |
| Chợ Tốt (nha.chotot.com) | Gọi public JSON API (`gateway.chotot.com`), không cần đăng nhập | Chưa xác minh ToS — cần kiểm tra trước khi dùng thương mại | 1 lần/ngày, giãn cách request, xử lý 429 | Mô tả có thể chứa SĐT → chỉ giữ trường cần thiết, không lưu SĐT | Nguồn chính. JSON có cấu trúc, không cần browser, không CAPTCHA |
| Batdongsan.com.vn | cách truy cập chưa quyết định, nếu bị chặn (Cloudflare, captcha, 403/429) thì dừng, không vượt. | Chưa xác minh ToS — cần kiểm tra robots.txt và điều khoản | 1 lần/ngày, giới hạn số trang mỗi lần chạy | Mô tả có thể chứa tên/SĐT → lọc bỏ khi normalize | Nguồn chính. Dữ liệu đã chuẩn hóa (giá, diện tích, số phòng) |

## Nguồn ứng viên

| Nguồn | Cách truy cập | Quyền sử dụng | Trạng thái |
|---|---|---|---|
| Threads API (Meta) | API chính thức `GET /{threads-user-id}/threads` với access token hợp lệ | Theo Threads Platform Terms; chỉ lấy bài của user đã xác định | Chưa đánh giá — chỉ bổ sung nếu xác định được danh sách user thường đăng tin cho thuê |
| Bộ dữ liệu có sẵn (nếu có) | Tải file | Chưa kiểm tra giấy phép | Chưa đánh giá |
| Dữ liệu từ đơn vị thực tập | Chưa rõ | Chưa hỏi | Chưa đánh giá |

## Nguồn không dùng

| Nguồn | Lý do |
|---|---|
| Nhóm và bài đăng Facebook | Chỉ cho phép qua Graph API, không hỗ trợ lấy nội dung Group công khai theo cách cần; bài đăng chứa dữ liệu cá nhân; cào tự động vi phạm Điều khoản Dịch vụ, rủi ro khóa tài khoản |
| Threads (cào giao diện web) | Có API chính thức, không cần cào; cào web vi phạm ToS và không ổn định |

## Checklist đánh giá một nguồn mới

1. `robots.txt`: đường dẫn định lấy có bị `Disallow` không, có `Crawl-delay` không.
2. Điều khoản sử dụng: có cấm thu thập tự động hay sao chép nội dung không.
3. Dữ liệu cá nhân: nguồn có số điện thoại, tên người đăng không, và mình chỉ giữ phần cần thiết.
4. Tốc độ: giãn cách bao lâu giữa các yêu cầu, tối đa bao nhiêu trang mỗi lần chạy.
5. Dùng để làm gì, có đưa lên repo công khai không.
6. Có cách hợp lệ hơn không (file, API, xin phép).

## Ghi chú kỹ thuật theo nguồn

### mock
- File: `collectors/mock_source.py`
- Tham số: `--day` để sinh dữ liệu theo ngày.
- Có dữ liệu bẩn có chủ ý để kiểm thử bước normalize.

### Chợ Tốt
- Endpoint: public JSON API `gateway.chotot.com` (lấy từ network tab của trang).
- Không cần đăng nhập, không CAPTCHA.
- Xử lý rate limit: backoff khi gặp HTTP 429.
- Trường cần lấy: tiêu đề, giá, diện tích, quận/huyện, loại phòng, mô tả, URL nguồn.
- Loại bỏ: số điện thoại, tên người đăng khỏi mô tả trước khi lưu.

### Batdongsan
- Cần headless browser hoặc dịch vụ scraping có xử lý JS + proxy (Cloudflare).
- Giới hạn số trang mỗi lần chạy để tránh quá tải.
- Dữ liệu đã có cấu trúc: giá, diện tích, số phòng ngủ.
- Loại bỏ thông tin liên hệ cá nhân khi normalize.

### Threads
- Chỉ dùng API chính thức, cần access token hợp lệ.
- Chỉ lấy bài của user ID đã xác định trước.
- Không cào giao diện web.

## Việc cần làm trước khi code collector

- [ ] Kiểm tra `robots.txt` của `nha.chotot.com` và ghi kết quả vào cột "Quyền sử dụng".
- [ ] Kiểm tra `robots.txt` của `batdongsan.com.vn` và ghi kết quả.
- [ ] Đọc mục điều khoản về thu thập tự động/sao chép nội dung của từng trang, ghi kết luận.
- [ ] Chốt schema chung để map dữ liệu từ các nguồn về một dạng.
- [ ] Xác nhận có đưa dữ liệu lên repo công khai không (ảnh hưởng đến việc có được lưu mô tả gốc không).