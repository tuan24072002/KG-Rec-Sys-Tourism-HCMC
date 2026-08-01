# 02 Tiền xử lý dữ liệu và Phân tích khám phá dữ liệu (EDA)

Thư mục này chứa các sổ tay Jupyter (Jupyter notebooks) cho các tác vụ tiền xử lý dữ liệu và phân tích khám phá dữ liệu (EDA) liên quan đến dự án.

## Giới thiệu

Phân hệ bao gồm một số Sổ tay Jupyter:

### 01_preprocessing_EDA.ipynb

Sổ tay này tập trung vào việc tiền xử lý dữ liệu và các tác vụ phân tích khám phá dữ liệu ban đầu. Nó bao gồm các bước như làm sạch dữ liệu, xây dựng đặc trưng (feature engineering) và phân tích thống kê cơ bản.

### 02_neo4j_dataloading.ipynb

Sổ tay này minh họa quá trình tải dữ liệu đã tiền xử lý vào Neo4j, một cơ sở dữ liệu đồ thị. Nó bao gồm mã nguồn để kết nối với Neo4j và tải dữ liệu từ các DataFrame của pandas vào cơ sở dữ liệu.

Sổ tay Jupyter này phụ thuộc vào các tệp CSV đầu ra được tạo bởi `01_preprocessing_EDA.ipynb`.

### 03_exploratory_queries.ipynb

Sổ tay này chứa các truy vấn khám phá được viết bằng Cypher, ngôn ngữ truy vấn được sử dụng bởi Neo4j. Nó khám phá các mối quan hệ và mô hình trong dữ liệu được lưu trữ trong cơ sở dữ liệu đồ thị Neo4j.

## Hướng dẫn sử dụng

Làm theo các bước sau:

1. Đảm bảo các thư viện phụ thuộc bắt buộc đã được cài đặt.
2. Lưu thông tin đăng nhập cần thiết để kết nối với cơ sở dữ liệu Neo4j vào một tệp tên là `neo4j.ini` và đặt ở thư mục gốc của phân hệ này.
   Tệp mẫu `neo4j.ini`:

```
[NEO4J]
HOST = bolt://[IP]:[PORT]
USERNAME = neo4j
DATABASE = neo4j
PASSWORD = [PASSWORD]
```

3. Chạy sổ tay mong muốn.

## Thư viện phụ thuộc

- `Python 3.x`
- `pandas`
- `neo4j`
- `matplotlib`

## Người thực hiện

Xiong Ying

## Giấy phép

Dự án này được cấp phép theo [Giấy phép MIT](LICENSE).

## Quy trình thực thi và Cách chạy từng file

Quy trình xử lý dữ liệu và tải dữ liệu vào cơ sở dữ liệu Neo4j cần tuân theo thứ tự dưới đây:

### Bước 1: Tiền xử lý dữ liệu (EDA)

Khởi động Jupyter Notebook hoặc một môi trường chạy Notebook (ví dụ: VS Code, JupyterLab) và chạy các ô (cells) trong sổ tay:

- **`01_preprocessing_EDA.ipynb`**
  Kịch bản này sẽ làm sạch các tệp dữ liệu cào được từ TripAdvisor (nằm trong thư mục `01-TripAdvisor-Scraper/output`), chuyển đổi kiểu dữ liệu, xử lý giá trị khuyết thiếu và lưu kết quả thành các file CSV đã làm sạch phục vụ cho bước tiếp theo.

### Bước 2: Cấu hình kết nối cơ sở dữ liệu Neo4j

Tạo một tệp cấu hình tên là `neo4j.ini` trong thư mục `02-Data-Preprocessing-EDA` với nội dung cấu hình như sau:

```ini
[NEO4J]
HOST = bolt://localhost:7687
DATABASE = neo4j
PASSWORD = mat_khau_cua_ban
```

_(Hãy thay thế địa chỉ HOST và PASSWORD bằng thông tin thực tế của máy chủ Neo4j của bạn)._

### Bước 3: Tải dữ liệu vào Neo4j

Chạy sổ tay:

- **`02_neo4j_dataloading.ipynb`**
  Sổ tay này sẽ đọc các tệp CSV đã được xử lý từ **Bước 1**, thực hiện kết nối tới cơ sở dữ liệu Neo4j bằng thông tin trong `neo4j.ini`, sau đó khởi tạo các ràng buộc (constraints), các nút (nodes) và các mối quan hệ (relationships) trên đồ thị tri thức.

### Bước 4: Chạy các truy vấn khám phá đồ thị

Chạy sổ tay:

- **`03_exploratory_queries.ipynb`**
  Sổ tay này chứa các câu lệnh truy vấn đồ thị bằng ngôn ngữ Cypher để kiểm tra cấu trúc đồ thị, phân tích sự liên kết và khám phá các đặc trưng dữ liệu du lịch đã lưu trong Neo4j.

---

### Cách chạy chung cho các file `.ipynb` (Jupyter Notebook):

1. Cài đặt các thư viện cần thiết bằng lệnh:
   ```bash
   pip install pandas neo4j matplotlib notebook
   ```
2. Khởi chạy Jupyter Server tại thư mục hiện tại:
   ```bash
   jupyter notebook
   ```
3. Trên giao diện trình duyệt mở ra, nhấp vào từng file `.ipynb` theo thứ tự và nhấn **Run All** hoặc chạy từng ô code từ trên xuống dưới.

### 🗺️ Bổ sung Ontology Ánh xạ Địa giới Hành chính mới (Sáp nhập Phường/Quận tại TP.HCM)

#### 1. Bối cảnh hành chính

Trong những năm gần đây (đặc biệt là năm 2021 và giai đoạn sáp nhập 2024-2025), Thành phố Hồ Chí Minh có sự thay đổi lớn về địa giới hành chính cấp Quận/Huyện và Phường/Xã:

- **Sáp nhập Quận:** Quận 2, Quận 9 và Quận Thủ Đức sáp nhập thành **Thành phố Thủ Đức** (đơn vị hành chính tương đương cấp quận, không còn đơn vị "Quận" trực thuộc).
- **Sáp nhập Phường:** Nhiều phường cũ sáp nhập vào nhau để hình thành các phường mới (ví dụ: _Phường Võ Thị Sáu_ được sáp nhập từ Phường 6, 7, 8 của Quận 3; _Phường An Khánh_ tại Thủ Đức được sáp nhập từ Phường Bình An, Bình Khánh, An Khánh cũ, v.v.).

#### 2. Thiết kế Ontology trong Cơ sở dữ liệu Đồ thị (Neo4j)

Để lưu trữ cả **quá khứ (địa chỉ cũ)** và **hiện tại (địa chỉ mới)** của các địa điểm du lịch (POIs), giúp hệ thống truy vấn và ánh xạ linh hoạt, chúng ta thiết kế mô hình Ontology hành chính gồm:

##### Các Node (Thực thể):

- `(d:District)`: Thực thể Quận/Huyện/Thành phố trực thuộc (ví dụ: `Quận 1`, `Quận 3`, `Thành phố Thủ Đức`).
- `(w:Ward)`: Thực thể Phường/Xã (chứa các thuộc tính: mã phường `ward_code`, tên phường `name`, mã tỉnh `province_code`).

##### Các Relationship (Mối quan hệ):

1. **`(w:Ward)-[:BELONGS_TO]->(d:District)`**: Xác định Phường/Xã thuộc Quận/Huyện nào.
2. **`(poi:Poi)-[:LOCATED_IN]->(w:Ward)`**: Địa điểm du lịch (POI) nằm tại Phường/Xã **cũ** tương ứng với thời điểm thu thập dữ liệu (để giữ thông tin lịch sử chính xác).
3. **`(old_w:Ward)-[:MERGED_TO]->(new_w:Ward)`**: Thể hiện lịch sử sáp nhập hành chính (ví dụ: `Phường 12 cũ` sáp nhập thành `Phường Hòa Hưng mới`, `Phường Bình An cũ` sáp nhập thành `Phường An Khánh mới`).

##### Biểu đồ mối quan hệ hành chính & lịch sử sáp nhập:

```
  (poi:Poi) -[:LOCATED_IN]-> (w_old:Ward) -[:MERGED_TO]-> (w_new:Ward) -[:BELONGS_TO]-> (d_new:District)
                                 |
                           [:BELONGS_TO]
                                 v
                            (d_old:District)
```

---

#### Cơ chế hoạt động của Ontology tiền xử lý hành chính

Mục tiêu là duyệt qua địa chỉ thô của tất cả các POI trong `poi_info.csv` và chuẩn hóa chúng về định dạng lịch sử cũ khi lưu xuống Neo4j, đồng thời thiết lập mối quan hệ sáp nhập:

1. **Trích xuất Quận/Huyện:**
   - Sử dụng danh sách từ khóa regex (nhận diện cả các từ khóa tiếng Anh/viết tắt như `Q.2`, `q9`, `dist 1`, `district 10`, v.v.).
   - Nếu không tìm thấy quận trực tiếp, hệ thống sẽ dò tìm tên Phường đặc trưng duy nhất (ví dụ: phường _Thảo Điền_ chỉ có ở Thủ Đức) để **suy luận ra Quận tương ứng** (Inference).
   - Chuẩn hóa toàn bộ các quận thuộc Thủ Đức cũ (Quận 2, Quận 9, Quận Thủ Đức) về một tên duy nhất: `Thành phố Thủ Đức`.
2. **Trích xuất Phường/Xã:**
   - Dò tìm tên phường trong địa chỉ thô theo danh sách phường lịch sử của quận đã được xác định.
   - Chấp nhận các biến thể viết tắt hoặc thiếu dấu (nhờ chuẩn hóa Unicode NFC và so khớp linh hoạt).
3. **Ánh xạ Sang Địa giới mới:**
   - Tìm kiếm phường cũ đã trích xuất trong bảng ánh xạ `hcm_address_mapping.json` (được bổ sung thêm thủ công các phường bị thiếu trong dữ liệu gốc như `Bình An`, `Bình Khánh` và viết tắt `Phường Thạnh`).
   - Lấy ra tên phường mới `new_ward_name`, mã phường mới `new_ward_code`, quận mới `new_district_name` và các thông tin cũ để ánh xạ.
4. **Chuẩn hóa Địa chỉ thô khi lưu xuống Neo4j:**
   - Tách phần số nhà/tên đường (`street_part`).
   - Ráp lại địa chỉ theo **định dạng cũ** (lưu trong thuộc tính `address` của `Poi`): `[Số nhà tên đường], Phường [Cũ], Quận [Cũ], Thành phố Hồ Chí Minh`.
   - POI được kết nối trực tiếp với **Phường cũ** thông qua mối quan hệ `LOCATED_IN`.

#### Cơ chế truy vấn ánh xạ địa chỉ cũ và địa chỉ mới bằng Ontology

Khi người dùng query thông tin địa điểm, chúng ta sử dụng ontology để tự động ánh xạ từ địa chỉ cũ sang địa chỉ mới theo các định dạng sau:
- **Địa chỉ cũ:** `Số nhà tên đường, phường, quận, thành phố`
- **Địa chỉ mới:** `Số nhà tên đường, phường (mới), thành phố`

##### Câu lệnh Cypher ví dụ:
```cypher
MATCH (poi:Poi)-[:LOCATED_IN]->(old_w:Ward)
MATCH (old_w)-[:BELONGS_TO]->(old_d:District)
OPTIONAL MATCH (old_w)-[:MERGED_TO]->(new_w:Ward)
WITH poi, old_w, old_d, coalesce(new_w, old_w) AS active_w
MATCH (active_w)-[:BELONGS_TO]->(active_d:District)
WITH poi, old_w, old_d, active_w, active_d,
     replace(poi.address, ", " + old_w.name + ", " + old_d.name + ", Thành phố Hồ Chí Minh", "") AS street_part
RETURN poi.name AS TenPOI,
       poi.address AS DiaChiCu,
       street_part + ", " + active_w.name + ", " + 
       case when active_d.name = 'Thành phố Thủ Đức' then 'Thành phố Thủ Đức, Thành phố Hồ Chí Minh' else 'Thành phố Hồ Chí Minh' end AS DiaChiMoi
LIMIT 10
```
