# 03 Động cơ gợi ý - Thử nghiệm và Đánh giá thuật toán
Thư mục này chứa các sổ tay Jupyter cho việc phát triển và đánh giá các tác vụ của thuật toán gợi ý liên quan đến dự án.

## Giới thiệu

Phân hệ bao gồm một số Sổ tay Jupyter:

### 01 cc-heuristic.ipynb

Sổ tay này tìm hiểu phương pháp heuristic cho Lọc dựa trên nội dung (Content-Based Filtering - CC) trong hệ thống gợi ý. Nó đi sâu vào các khái niệm cơ bản và chi tiết triển khai của phương pháp gợi ý dựa trên heuristic.

### 02 cc-node similarity.ipynb

Sổ tay này nghiên cứu việc sử dụng các độ đo tương đồng giữa các nút (node similarity) trong gợi ý dựa trên nội dung (CC). Nó khám phá các phép đo độ tương đồng nút khác nhau và tác động của chúng đối với hiệu quả của thuật toán gợi ý.

#### Lý thuyết & Cải tiến: Trích xuất Đặc trưng Mô tả bằng PhoBERT Embedding
Trong phương pháp lọc dựa trên nội dung truyền thống, thuộc tính văn bản (`description`) của các địa điểm du lịch thường được xử lý bằng Bag-of-Words (CountVectorizer) hoặc TF-IDF. Hạn chế lớn của các phương pháp này là chỉ đếm tần suất từ mà không hiểu được ngữ nghĩa hay ngữ cảnh tiếng Việt (ví dụ: không nhận biết được từ đồng nghĩa).

Để khắc phục, hệ thống đã được nâng cấp bằng việc tích hợp **PhoBERT** (`vinai/phobert-base-v2`) - mô hình ngôn ngữ pre-trained dựa trên kiến trúc RoBERTa được tối ưu hóa đặc biệt cho tiếng Việt.

Quy trình hoạt động bao gồm:
1. **Phân đoạn từ tiếng Việt (Word Segmentation)**: Sử dụng thư viện `PyVi` (`ViTokenizer.tokenize`) để chuyển đổi các từ ghép tiếng Việt (ví dụ: từ "thành phố" thành "thành_phố"), giúp PhoBERT hiểu đúng cấu trúc từ vựng tiếng Việt.
2. **Trích xuất Vector nhúng (Embedding Extraction)**: Đưa văn bản đã phân đoạn qua tokenizer và mô hình PhoBERT pre-trained để thu về các vector biểu diễn. Sử dụng vector trạng thái ẩn cuối cùng (last hidden state) tại vị trí token đặc biệt `[CLS]` làm vector nhúng dense đại diện cho toàn bộ mô tả của địa điểm (kích thước **768 chiều**).
3. **Tính toán Độ tương đồng**: Sử dụng độ đo **Cosine Similarity** trên các vector nhúng dense này để xác định mức độ tương đồng về nội dung và ngữ nghĩa giữa các địa điểm, giúp kết quả gợi ý chính xác và thông minh hơn.

### 03 cf-userKnn fastRP.ipynb

Trong sổ tay này, phương pháp Lọc cộng tác (Collaborative Filtering - CF) kết hợp kỹ thuật K-Láng giềng gần nhất dựa trên người dùng (User-Based KNN) và Fast Random Projection (FastRP) được khám phá. Nó kiểm tra sự kết hợp giữa độ tương đồng dựa trên người dùng và các phương pháp giảm chiều dữ liệu để nâng cao hiệu suất gợi ý.

### 04 cf-itemKnn fastRP.ipynb

Tương tự như sổ tay trước, sổ tay này tập trung vào phương pháp Lọc cộng tác (CF) nhưng sử dụng kỹ thuật K-Láng giềng gần nhất dựa trên mục (Item-Based KNN) và Fast Random Projection (FastRP). Nó phân tích cách độ tương đồng dựa trên mục và giảm chiều dữ liệu có thể cải thiện độ chính xác và hiệu quả của hệ thống gợi ý.

### 05 ensemble - max voting.ipynb

Sổ tay này khám phá các kỹ thuật học kết hợp (ensemble), cụ thể là phương pháp Biểu quyết đa số (Majority Voting / Max Voting), để kết hợp các dự đoán từ nhiều mô hình gợi ý khác nhau. Nó nghiên cứu cách học kết hợp có thể nâng cao hiệu suất gợi ý bằng cách tổng hợp kết quả đầu ra của từng mô hình đơn lẻ.

## Hướng dẫn sử dụng

Làm theo các bước sau:

1. Đảm bảo các thư viện phụ thuộc bắt buộc đã được cài đặt.
2. Lưu thông tin đăng nhập cần thiết để kết nối với cơ sở dữ liệu Neo4j vào một tệp tên là `neo4j.ini` và đặt ở thư mục gốc của phân hệ này.
Tệp mẫu `neo4j.ini`:
```
[NEO4J]
HOST = bolt://[IP]:[PORT]
DATABASE = neo4j
PASSWORD = [PASSWORD]
```
3. Chạy sổ tay mong muốn.

## Thư viện phụ thuộc

- `Python 3.x`
- `neo4j`
- `pandas`
- `scikit-learn`
- `matplotlib`
- `py2neo`
- `graphdatascience`
- `torch`
- `transformers`
- `pyvi`

## Người thực hiện

Xiong Ying

## Giấy phép

Dự án này được cấp phép theo [Giấy phép MIT](LICENSE).

## Quy trình thực thi và Cách chạy từng file

Thư mục này được sử dụng để tiến hành thử nghiệm độc lập trên nhiều hướng tiếp cận gợi ý du lịch khác nhau. Các sổ tay có thể chạy độc lập, nhưng khuyên dùng chạy theo trình tự phát triển thuật toán sau:

### Bước 1: Cấu hình kết nối Neo4j
Tạo một tệp cấu hình kết nối tên là `neo4j.ini` trong thư mục `03-Recommender-Engine-Experiments` để các sổ tay kết nối tới cơ sở dữ liệu đồ thị Neo4j chứa dữ liệu đã nạp ở module `02`.
Nội dung file cấu hình:
```ini
[NEO4J]
HOST = bolt://localhost:7687
DATABASE = neo4j
PASSWORD = mat_khau_cua_ban
```

### Bước 2: Chạy thử nghiệm các mô hình Gợi ý dựa trên nội dung (Content-Based)
Chạy lần lượt hai sổ tay sau để đánh giá hiệu suất phương pháp lọc dựa trên nội dung:
- **`01 cc-heuristic.ipynb`**: Sử dụng luật heuristic (như lọc danh mục, khu vực ưa thích) để đưa ra gợi ý POI.
- **`02 cc-node similarity.ipynb`**: Sử dụng các độ đo tương đồng nút (như Jaccard, Cosine) trên các thuộc tính của địa điểm để tìm kiếm địa điểm tương tự.

### Bước 3: Chạy thử nghiệm các mô hình Lọc cộng tác (Collaborative Filtering)
Chạy lần lượt các sổ tay dưới đây để thử nghiệm thuật toán KNN kết hợp kỹ thuật nhúng đồ thị FastRP (Fast Random Projection):
- **`03 cf-userKnn fastRP.ipynb`**: Tìm kiếm sự tương đồng giữa các người dùng (User-User KNN) dựa trên biểu diễn nhúng từ FastRP để gợi ý địa điểm.
- **`04 cf-itemKnn fastRP.ipynb`**: Tìm kiếm sự tương đồng giữa các địa điểm (Item-Item KNN) để gợi ý các địa điểm liên quan cho người dùng.

### Bước 4: Chạy thử nghiệm mô hình Học kết hợp (Ensemble Learning)
- **`05 ensemble - max voting.ipynb`**
Chạy sổ tay này để tổng hợp kết quả dự đoán của các mô hình đơn lẻ ở trên bằng phương pháp biểu quyết đa số (Majority Voting) nhằm cải thiện độ chính xác và tính đa dạng của hệ thống gợi ý tổng thể.

---

### Cách chạy chung cho các file `.ipynb` (Jupyter Notebook):
1. Cài đặt các thư viện cần thiết bằng lệnh:
   ```bash
   pip install pandas neo4j matplotlib scikit-learn py2neo graphdatascience torch transformers pyvi notebook
   ```
   hoặc cài đặt từ file `requirements.txt`:
   ```bash
   pip install -r requirements.txt notebook
   ```
   *(Lưu ý: Đối với việc trích xuất PhoBERT embedding, nếu máy tính của bạn có GPU hỗ trợ CUDA, hãy cài đặt phiên bản PyTorch tương thích CUDA để tăng tốc độ xử lý).*
2. Khởi chạy Jupyter Server tại thư mục hiện tại:
   ```bash
   jupyter notebook
   ```
3. Trên giao diện trình duyệt mở ra, nhấp vào từng file `.ipynb` và thực hiện chạy các khối mã (cells) từ đầu đến cuối.

