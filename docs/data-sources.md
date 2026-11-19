# Nguồn dữ liệu

Mỗi nguồn dữ liệu của RentalPulse được ghi và đánh giá ở đây trước khi viết code thu thập.

## Nguồn đang dùng

| Nguồn | Cách truy cập | Quyền sử dụng | Tần suất | Dữ liệu cá nhân | Ghi chú |
|---|---|---|---|---|---|
| mock | Sinh bằng code (`collectors/mock_source.py`) | Dữ liệu tự tạo | Theo tham số `--day` | Không | Có kịch bản kiểm thử và dữ liệu bẩn có chủ ý |

## Nguồn ứng viên

| Nguồn | Cách truy cập | Quyền sử dụng | Trạng thái |
|---|---|---|---|
| (website tin đăng bạn chọn) | Thu thập trang web | Chưa kiểm tra | Chưa đánh giá |
| (bộ dữ liệu có sẵn) | Tải file | Chưa kiểm tra giấy phép | Chưa đánh giá |
| Dữ liệu từ đơn vị thực tập | Chưa rõ | Chưa hỏi | Chưa đánh giá |

## Nguồn không dùng

| Nguồn | Lý do |
|---|---|
| Nhóm và bài đăng Facebook | Nền tảng hạn chế thu thập tự động; bài đăng chứa dữ liệu cá nhân của người đăng |

## Checklist đánh giá một nguồn mới

1. `robots.txt`: đường dẫn định lấy có bị `Disallow` không, có `Crawl-delay` không.
2. Điều khoản sử dụng: có cấm thu thập tự động hay sao chép nội dung không.
3. Dữ liệu cá nhân: nguồn có số điện thoại, tên người đăng không, và mình chỉ giữ phần cần thiết.
4. Tốc độ: giãn cách bao lâu giữa các yêu cầu, tối đa bao nhiêu trang mỗi lần chạy.
5. Dùng để làm gì, có đưa lên repo công khai không.
6. Có cách hợp lệ hơn không (file, API, xin phép).