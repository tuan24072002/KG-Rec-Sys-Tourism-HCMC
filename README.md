# Xây dựng Đồ thị Tri thức và Phát triển Hệ thống Gợi ý Du lịch TP.HCM

Kho lưu trữ này chứa mã nguồn và tài liệu hướng dẫn cho việc phát triển một hệ thống gợi ý du lịch tại TP.HCM. Dự án được chia thành nhiều mô-đun, mỗi mô-đun tập trung vào một khía cạnh cụ thể, bao gồm thu thập dữ liệu (data scraping), tiền xử lý, thử nghiệm công cụ gợi ý và phát triển ứng dụng web.

Chi tiết hơn có thể được tìm thấy trong báo cáo dự án "[FYP Report-Xiong Ying.pdf](https://github.com/xiong-ying/KG-Rec-Sys-Tourism-SG/blob/main/FYP%20Report-Xiong%20Ying.pdf)".

## Giới thiệu

### 01-TripAdvisor-Scraper

Mô-đun này chứa mã nguồn để thu thập thông tin du lịch từ TripAdvisor.

### 02-Data-Preprocessing-EDA

Tiến hành tiền xử lý dữ liệu và phân tích khám phá dữ liệu (EDA).

### 03-Recommender-Engine-Experiments

Mô-đun này bao gồm việc thử nghiệm với nhiều thuật toán gợi ý khác nhau.

### 04-Recommender-System-Web-App

Cuối cùng là phần phát triển ứng dụng web cho hệ thống gợi ý.

## Hướng dẫn sử dụng

Mỗi mô-đun đều có hướng dẫn riêng. Vui lòng tham khảo tệp README.md trong thư mục của từng mô-đun để biết chi tiết cụ thể về cách sử dụng mã nguồn và chạy các mã lệnh (script).

## Cài đặt

Để cài đặt và sử dụng dự án, hãy làm theo các bước sau:

1. Clone kho lưu trữ này về máy tính cá nhân của bạn.
2. Di chuyển đến thư mục của mô-đun mong muốn.
3. Làm theo các hướng dẫn được cung cấp trong tệp README.md của mô-đun đó để cài đặt và sử dụng.

## Người đóng góp

Xiong Ying
Trần Lê Anh Tuấn

## Giấy phép

Dự án này được cấp phép theo [Giấy phép MIT](LICENSE).

```bash
python -m venv venv
venv\Scripts\Activate.ps1

# PyTorch (chọn 1):
# RTX 5060/50xx (Blackwell sm_120):
pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128
# RTX 30xx/40xx:
pip install torch --index-url https://download.pytorch.org/whl/cu124
# CPU only:
pip install torch

# Các dependencies khác
pip install -r requirements.txt
```
