# 01 TripAdvisor Scraper (Công cụ Thu thập Dữ liệu TripAdvisor)

Phân hệ này chứa mã nguồn để thu thập dữ liệu thông tin du lịch từ TripAdvisor.

## Giới thiệu

Phân hệ bao gồm một số kịch bản Python:

### 1. MySpider.py

Kịch bản này định nghĩa lớp `Spider` chịu trách nhiệm lấy nội dung HTML từ các URL bằng cả yêu cầu HTTP thông thường và Selenium WebDriver. Nó sử dụng một User-Agent ngẫu nhiên cho mỗi yêu cầu để giả lập các trình duyệt khác nhau. Ngoài ra, nó cũng cung cấp chức năng ghi nội dung HTML ra tệp để phục vụ cho việc gỡ lỗi.

### 2. PoiUrlScraper.py

Kịch bản này chứa lớp `PoiUrlScraper`, được sử dụng để trích xuất các URL của các địa điểm tham quan (POI) từ các trang danh sách của TripAdvisor. Nó truy xuất các trang danh sách của tất cả các địa điểm tham quan ở Thành phố Hồ Chí Minh (hoặc các khu vực khác tùy chỉnh), phân tích cú pháp nội dung HTML để trích xuất URL của từng trang chi tiết POI đồng thời lưu thể loại cụ thể của từng địa điểm từ trang danh sách vào tệp mapping `output/poi_categories.json`.

Các URL này sau đó được lưu trữ trong tệp `output/poi_urls.txt`.

### 3. PoiInfoScraper.py

Lớp `PoiInfoScraper` được định nghĩa trong kịch bản này chịu trách nhiệm thu thập thông tin chi tiết về từng POI từ trang chi tiết tương ứng của nó. Nó sử dụng lớp `Spider` để lấy nội dung HTML của từng trang và phân tích cú pháp để trích xuất thông tin.

Để tránh lỗi không tải được thể loại (do TripAdvisor tải động bằng JavaScript trên trang chi tiết), kịch bản này sẽ đọc file ánh xạ thể loại sạch từ `output/poi_categories.json` và điền trực tiếp vào cột `type`. Ngoài ra, kịch bản cũng áp dụng bộ lọc thông minh để loại bỏ review của user hoặc thông tin SEO khuôn mẫu để giữ trống cột `description` nếu địa điểm không có phần mô tả chính thức.

Dữ liệu trích xuất sau đó được lưu trữ trong tệp CSV `output/poi_info.csv`.

### 4. ReviewScraper.py

Kịch bản này triển khai lớp `ReviewScraper`, được sử dụng để thu thập các đánh giá cho từng POI từ TripAdvisor. Đầu tiên, nó truy xuất các URL đánh giá cho mỗi POI, sau đó trích xuất thông tin liên quan như tên đăng nhập của người đánh giá, địa điểm, tiêu đề đánh giá, ngày tháng, xếp hạng, nhóm người dùng và nội dung đánh giá. Dữ liệu thu thập được lưu trong một tệp CSV để phân tích sâu hơn.

Kịch bản này phụ thuộc vào tệp CSV đầu ra được tạo bởi `PoiInfoScraper.py`.

**Mỗi kịch bản đều chứa các bình luận chi tiết giải thích mục đích của mã nguồn và cách thức hoạt động.**

## Hướng dẫn sử dụng

Để sử dụng phân hệ thu thập dữ liệu TripAdvisor, hãy làm theo các bước sau:

1. Đảm bảo các thư viện phụ thuộc bắt buộc (như `Selenium` và `BeautifulSoup`) đã được cài đặt.
2. Chạy kịch bản mong muốn.
3. Làm theo hướng dẫn trong phần bình luận của từng kịch bản để tùy chỉnh quá trình thu thập dữ liệu hoặc xử lý các lỗi phát sinh.

## Thư viện phụ thuộc

- `Python 3.x`
- `Selenium`
- `BeautifulSoup4`
- `Requests`
- `Pandas`
- `Fake User-Agent`
- `undetected-chromedriver`
- `setuptools` (để hỗ trợ Python 3.12+)

## Người thực hiện

Xiong Ying
Trần Lê Anh Tuấn

## Giấy phép

Dự án này được cấp phép theo [Giấy phép MIT](LICENSE).

## Quy trình thực thi và Cách chạy từng file

Quy trình thu thập dữ liệu cần tuân theo thứ tự phụ thuộc dữ liệu dưới đây:

### Bước 1: Chuẩn bị thư mục chứa dữ liệu tạm thời và dữ liệu đầu ra

Đảm bảo các thư mục `html` và `output` đã được tạo sẵn trong thư mục `01-TripAdvisor-Scraper`:

```bash
mkdir html
mkdir output
```

### Bước 2: Lấy danh sách URL và Thể loại của các POI (Địa điểm tham quan)

Chạy kịch bản `PoiUrlScraper.py` để cào tất cả liên kết dẫn đến các trang chi tiết địa điểm du lịch. Kết quả các liên kết sẽ được lưu vào tệp `output/poi_urls.txt` và sơ đồ ánh xạ thể loại tương ứng sẽ được lưu vào `output/poi_categories.json`.

```bash
python PoiUrlScraper.py
```

### Bước 3: Cào thông tin chi tiết của từng POI

Chạy kịch bản `PoiInfoScraper.py`. File này sẽ đọc danh sách liên kết từ `output/poi_urls.txt`, truy cập từng địa điểm để thu thập thông tin chi tiết (tên, thể loại, rating, v.v.), và lưu kết quả vào tệp CSV `output/poi_info.csv`.

```bash
python PoiInfoScraper.py
```

### Bước 4: Cào các đánh giá (Reviews) của từng POI

Chạy kịch bản `ReviewScraper.py`. File này sẽ đọc tệp `output/poi_info.csv` để lấy danh sách POI, sau đó tiến hành cào các đánh giá của người dùng tại các địa điểm đó, lưu kết quả vào tệp `output/reviews.csv`.

```bash
python ReviewScraper.py
```

_Lưu ý:_ `MySpider.py` là một lớp tiện ích phục vụ việc kết nối mạng và gửi các yêu cầu giả lập trình duyệt, được các kịch bản khác import và sử dụng tự động. Bạn không cần chạy trực tiếp file này (nếu chạy trực tiếp `python MySpider.py` để test, cần đảm bảo đã tạo trước thư mục `html` để tránh lỗi FileNotFoundError).
