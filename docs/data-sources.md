# Nguồn dữ liệu

Mỗi nguồn dữ liệu của RentalPulse được ghi và đánh giá ở đây trước khi viết code thu thập.
File này là nguồn sự thật (source of truth) về nguồn dữ liệu. Không tạo file trùng lặp.

## Quy ước

- Mỗi nguồn có: cách truy cập, quyền sử dụng, tần suất, xử lý dữ liệu cá nhân, ghi chú kỹ thuật.
- Trạng thái nguồn: `đang dùng` / `đang dùng có điều kiện` / `ứng viên` / `không dùng`.
- `đang dùng` chỉ khi đã kiểm tra cả `robots.txt` và điều khoản sử dụng. Nếu điều khoản chưa đọc được hoặc chưa rõ thì ghi `đang dùng có điều kiện` kèm điều kiện cụ thể.
- Mọi collector phải tham chiếu tên nguồn trong file này.

## Nguồn đang dùng

| Nguồn | Cách truy cập | Quyền sử dụng | Tần suất | Dữ liệu cá nhân | Ghi chú |
|---|---|---|---|---|---|
| mock | Sinh bằng code (`collectors/mock_source.py`) | Dữ liệu tự tạo | Theo tham số `--day` | Không | Nguồn kiểm thử. Có kịch bản với đáp án biết trước và dữ liệu bẩn có chủ ý |
| Batdongsan.com.vn | Người dùng tự mở trang danh sách (chỉ trang 1) bằng trình duyệt và lưu HTML; pipeline đọc file đó (`--html-file`). Tải tự động bị site chặn (HTTP 403, 20/11/2026) nên không dùng | `robots.txt` (20/11/2026): cho phép `/`, có `Crawl-delay: 10` cho các bot có tên. Điều khoản sử dụng: chưa đọc được (trang không mở bằng công cụ tự động). Trạng thái: đang dùng có điều kiện, mục đích học tập | 1 lần/ngày, thủ công | Không lưu mã người đăng, tên, số điện thoại | Dữ liệu thô không đưa lên GitHub |

## Nguồn ứng viên

| Nguồn | Cách truy cập | Quyền sử dụng | Trạng thái |
|---|---|---|---|
| Nhà Tốt (nhatot.com, trước là Chợ Tốt) | `gateway.chotot.com` thấy ở tab Network là API nội bộ của app, không phải API công khai có tài liệu | `robots.txt` (20/11/2026): cấm `/*page=` và `/*q=` (không phân trang, không tìm kiếm), có `Content-Signal: ai-train=no`. Điều khoản: không có chữ "robot" hay "crawl" nhưng cấm sao chép, phân phối nội dung khi chưa có văn bản đồng ý và chỉ cho dùng cá nhân | Chưa triển khai. Cần xin phép trước hoặc dùng thủ công như Batdongsan |
| Threads API (Meta) | API chính thức `GET /{threads-user-id}/threads` với access token hợp lệ | Theo Threads Platform Terms; chỉ lấy bài của user đã xác định | Chưa đánh giá. Chỉ bổ sung nếu xác định được danh sách user thường đăng tin cho thuê |
| Bộ dữ liệu có sẵn (nếu có) | Tải file | Chưa kiểm tra giấy phép | Chưa đánh giá |
| Dữ liệu từ đơn vị thực tập | Chưa rõ | Chưa hỏi | Chưa đánh giá |

## Nguồn không dùng

| Nguồn | Lý do |
|---|---|
| Nhóm và bài đăng Facebook | Chỉ cho phép qua Graph API, không hỗ trợ lấy nội dung Group công khai theo cách cần; bài đăng chứa dữ liệu cá nhân; cào tự động vi phạm Điều khoản Dịch vụ, rủi ro khóa tài khoản |
| Threads (cào giao diện web) | `robots.txt` của Threads có `User-agent: * / Disallow: /` và ghi chú cấm thu thập tự động khi chưa có văn bản cho phép; có API chính thức nên không cần cào |

## Quy tắc thu thập

- Giãn cách ít nhất 10 giây giữa hai yêu cầu; User-Agent trung thực (`RentalPulse/0.1 (academic student project)`).
- Chỉ lấy trang 1 của danh sách, số lượng nhỏ.
- Gặp 403, 429 hoặc trang thử thách (Cloudflare, captcha): dừng, không thử lại, không vượt.
- Không dùng proxy, headless browser hay đổi User-Agent để né chặn.
- Không lưu số điện thoại, tên hay mã người đăng.
- Không đưa dữ liệu thô lên GitHub. Repo chỉ chứa code và dữ liệu mẫu tự viết.
- Dự án học tập, không dùng thương mại.

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
- Tham số: `--day` để sinh dữ liệu theo ngày, `--seed` cho hạt giống.
- Có dữ liệu bẩn có chủ ý để kiểm thử bước normalize.

### Batdongsan
- Tải tự động bằng Python nhận HTTP 403 (20/11/2026). Dừng, không dùng proxy, headless browser hay đổi User-Agent để vượt.
- Cách dùng hiện tại: người dùng lưu HTML trang 1 bằng trình duyệt (DevTools, Copy outerHTML), rồi chạy `python -m collectors.collector --source batdongsan --html-file <file> --snapshot-date <ngày>`.
- Chỉ lấy tin ở khối danh sách chính (`js__card-full-web`). Parser cố ý không đọc `uid` (mã người đăng).
- Dữ liệu thô lưu trong `data/` (Git bỏ qua), Bronze lưu các trường đã tách.

### Nhà Tốt (ứng viên, chưa triển khai)
- Không phân trang, không tìm kiếm tự động (`robots.txt`).
- Chưa viết collector. Nếu dùng: chỉ trang 1, thủ công, hoặc xin phép.

### Threads
- Chỉ dùng API chính thức, cần access token hợp lệ.
- Chỉ lấy bài của user ID đã xác định trước.
- Không cào giao diện web.

## Nhật ký kiểm tra

| Ngày | Việc | Kết quả |
|---|---|---|
| 2026-11-20 | `robots.txt` Batdongsan | Cho phép `/`, `Crawl-delay: 10` cho bot có tên |
| 2026-11-20 | `robots.txt` Nhà Tốt | Cấm `/*page=`, `/*q=`; `ai-train=no` |
| 2026-11-20 | `robots.txt` Threads | `User-agent: * / Disallow: /` |
| 2026-11-20 | Điều khoản Nhà Tốt | Không nhắc robot/crawl; cấm sao chép khi chưa có văn bản đồng ý |
| 2026-11-20 | Điều khoản Batdongsan | Chưa đọc được |
| 2026-11-20 | Tải tự động Batdongsan | HTTP 403, dừng |

## Việc còn lại

- [x] Kiểm tra `robots.txt` của Nhà Tốt và Batdongsan.
- [x] Đọc điều khoản Nhà Tốt.
- [ ] Đọc điều khoản Batdongsan (tự mở trang trong trình duyệt).
- [ ] Chốt schema chung để map dữ liệu của mock và Batdongsan về một dạng (làm ở tầng Staging).
- [x] Không đưa dữ liệu thô lên GitHub.