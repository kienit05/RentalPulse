# Sổ nguồn dữ liệu (Data Sources Register)

Mục đích: ghi lại mỗi nguồn dữ liệu được dùng hay cân nhắc, vì sao, và điều kiện dùng. Dự án này chỉ phục vụ học tập và portfolio, không có mục đích thương mại.

## Quy ước trạng thái
- **Đang dùng**: đã có collector và dữ liệu trong Bronze.
- **Đang dùng có điều kiện**: dùng được, nhưng có hạn chế kỹ thuật hoặc điều khoản chưa xác minh hết.
- **Ứng viên**: đang cân nhắc, chưa có code.
- **Không dùng**: đã loại, kèm lý do.

## Nguồn đang dùng

### Mock (giả lập)
- Trạng thái: đang dùng.
- Vai trò: kiểm thử với đáp án biết trước (đổi giá, tin biến mất và quay lại, đăng lại với mã mới).
- Mọi bản ghi mock phải được đánh dấu mô phỏng (`is_simulated`) khi vào PostgreSQL.

### Batdongsan (batdongsan.com.vn)
- Trạng thái: đang dùng có điều kiện.
- Trang: danh sách cho thuê phòng trọ Hà Nội, sắp theo tin mới nhất, 6 trang mỗi ngày (khoảng 120 tin).
- Cách lấy: tải tự động bị trả HTTP 403 (ngày 2026-11-20), nên collector dừng đúng thiết kế và không vượt chặn. Ban đầu dùng cách người dùng tự mở trang bằng trình duyệt, lưu HTML, rồi chạy `--html-file` (`method: "manual_save"` ghi trong batch). Hiện nay mỗi ngày lưu 6 trang vào `data/inbox/raw/`, rồi `name_inbox` và `ingest_inbox` trong Airflow đặt tên và nạp.
- Cách đọc: BeautifulSoup trên thẻ `div.js__card-full-web`; giá đọc từ chữ ("1,8 triệu/tháng") bằng Decimal; "Thỏa thuận" thành NULL, không phải 0.
- Trường lưu: mã tin, tiêu đề, giá (chữ và số), diện tích, tỉnh, ngày đăng, đường dẫn tin.
- Điều khoản sử dụng: chưa đọc được bằng công cụ, cần mở bằng trình duyệt (xem checklist).

### Nhà Tốt (nhatot.com)
- Trạng thái: đang dùng có điều kiện.
- Trang: danh sách thuê phòng trọ Hà Nội, 6 trang mỗi ngày (khoảng 120 tin).
- Cách lấy: người dùng tự lưu HTML bằng trình duyệt (ban đầu qua `--html-file`, hiện qua `data/inbox/raw/`). Collector từ chối tải tự động.
- Cách đọc: JSON trong thẻ `__NEXT_DATA__` (`props.initialState.adlisting.data.ads`). Ổn định hơn dò thẻ HTML vì giá là số.
- Trường lưu: mã tin, vị trí trên trang, tiêu đề, giá, giá gốc (để thấy tin giảm giá), diện tích, loại, tỉnh, quận, phường, đường, vĩ độ, kinh độ, tiền cọc, thời điểm đăng (đổi từ mili-giây sang ISO UTC), trạng thái.
- Không đọc: hồ sơ người đăng (account, full_name, avatar, seller_info), số điện thoại, mô tả, ảnh.
- Ghi chú: ngày đăng có sẵn trong `orig_list_time`; JSON-LD trong trang lặp lại tin nên không dùng.

## Vì sao thu thập thủ công
Batdongsan chặn yêu cầu tự động (HTTP 403), và điều khoản của từng nguồn chưa được xem xét đủ để tự động hóa việc lấy trang. Vì vậy dự án chỉ nạp các trang HTML do người vận hành lưu mỗi ngày. Phần tự động hóa bắt đầu từ `name_inbox` và `ingest_inbox` trở đi; thu thập tự động chưa làm.

## Ứng viên và đã loại
- **API tin đăng công khai tại Việt Nam**: chưa tìm thấy. Sẽ tìm tiếp sau; có thể liên hệ site bằng email để xin quyền truy cập.
- **vietnam-provinces / vn-open-api-provinces**: dữ liệu tham chiếu đơn vị hành chính, dùng để chuẩn hóa tỉnh, quận, phường ở Staging.
- **Nominatim (OpenStreetMap)**: geocoding ở Giai đoạn 4; chính sách 1 yêu cầu/giây, User-Agent định danh.
- **Bộ dữ liệu HuggingFace tinixai/vietnam-real-estates**: CC BY-NC 4.0, nguồn gốc chưa rõ; chỉ tham khảo.
- **RentCast**: không dùng, dữ liệu Mỹ, không phù hợp mục tiêu thị trường Việt Nam.
- **Threads / Facebook**: không thu thập tự động (cần đăng nhập, điều khoản cấm, rủi ro cao). Chỉ ghi nhận là nguồn tồn tại.

## Quy tắc thu thập
1. Chỉ lưu trang bằng tay qua trình duyệt, 6 trang mỗi nguồn mỗi ngày; collector không tải tự động. Nếu sau này có tải tự động thì giãn cách tối thiểu 10 giây giữa các yêu cầu.
2. Nếu có tải tự động: User-Agent trung thực: `RentalPulse/0.1 (academic student project)`.
3. Kiểm tra robots.txt trước; không tải trang bị cấm. Lưu ý robots.txt không thay cho điều khoản sử dụng.
4. Gặp 403, 429, captcha hay trang Cloudflare thì dừng; không vượt chặn, không dùng proxy hay trình duyệt ẩn danh tự động.
5. Nguồn bị chặn thì dùng lưu tay (`--html-file`) thay vì tải tự động.
6. Dữ liệu công khai được lưu như hiển thị trên trang, chỉ để học tập, chỉ ở máy local; dữ liệu thô (`data/`, Bronze) không lên GitHub và không xuất hiện trong ảnh, dashboard hay README. Parser vẫn không đọc hồ sơ người đăng, số điện thoại, mô tả và ảnh vì không cần cho phân tích giá.
7. Tiêu đề và đường dẫn tin trong Bronze là dữ liệu thô nguyên văn; khi trình bày portfolio chỉ dùng số liệu tổng hợp.

## Nhật ký kiểm tra
| Ngày | Nguồn | Việc | Kết quả |
|---|---|---|---|
| 2026-11-20 | Batdongsan | Tải tự động bằng Python | HTTP 403, collector dừng đúng thiết kế |
| 2026-11-20 | Batdongsan | Lưu tay trang 1, `--html-file` | 20 tin vào Bronze |
| 2026-11-20 | Nhà Tốt | Đọc robots.txt và chính sách quyền riêng tư | Ghi nhận; điều khoản sử dụng đã xem |
| 2026-11-20 | Nhà Tốt | Lưu tay trang 1, parse `__NEXT_DATA__` | 20 tin, 2 tin giảm giá, không có hồ sơ người đăng |
| 2026-11-23 trở đi | Nhà Tốt, Batdongsan | Lưu tay 6 trang mỗi nguồn mỗi ngày vào `data/inbox/raw/` | Ngày 2026-11-25: 120 tin mỗi nguồn nạp vào Staging |

## Checklist còn lại
- [ ] Mở điều khoản sử dụng của Batdongsan bằng trình duyệt, ghi kết luận vào đây.
- [ ] Tìm nguồn dữ liệu qua API hoặc xin quyền bằng email.
- [ ] Đọc điều khoản của từng nguồn trước khi cân nhắc tự động hóa việc lấy trang, ghi kết luận vào đây.
- [ ] Rà soát lại sổ này mỗi khi thêm nguồn mới.