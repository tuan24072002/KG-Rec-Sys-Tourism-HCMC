# 04 Ứng dụng Web Hệ thống Gợi ý

Phân hệ này bao gồm mã nguồn cho ứng dụng web được thiết kế nhằm trình diễn sự tích hợp giữa động cơ gợi ý dựa trên đồ thị tri thức (Graph Recommender Engine) với giao diện web tương tác và Trợ lý AI du lịch thông minh (Graph RAG Agent).

## Giới thiệu các Mô-đun Cốt lõi

Phân hệ bao gồm các kịch bản Python chính:

### app.py

Kịch bản này đóng vai trò cốt lõi của ứng dụng web. Sử dụng Flask làm Web Framework, tích hợp Neo4j cho cơ sở dữ liệu và cung cấp API Chatbot hỗ trợ phản hồi dạng Server-Sent Events (SSE) Streaming (`/api/chat`).

### rag_agent.py

Phân hệ **Graph RAG Agent** - Trợ lý du lịch thông minh kết hợp Đồ thị tri thức & Local LLM (hỗ trợ cả Python Transformers trực tiếp và Ollama API). Đảm nhận các chức năng:

- **Trích xuất Ý định & Khu vực chính xác**: Sử dụng Regex ranh giới từ Unicode (`(?<!\w)...(?!\w)`) tránh trùng lặp substring (như Quận 1 trong Quận 10).
- **Tích hợp Động cơ Gợi ý Cá nhân hóa**: Kết hợp thuật toán gợi ý đồ thị (`recommender.py`) với bộ lọc khu vực/thể loại.
- **Phản hồi Real-time Streaming**: Hỗ trợ xuất dữ liệu từng token (token-by-token) cho giao diện người dùng.

### recommender.py

Kịch bản định nghĩa các thuật toán gợi ý dựa trên Neo4j và thư viện Graph Data Science (GDS) (Collaborative Filtering, Content-based Filtering, Graph Embeddings FastRP/KNN).

### data_loader.py

Kịch bản tự động tải dữ liệu nút (Nodes), quan hệ (Relationships) và thiết lập ràng buộc (Constraints) vào Neo4j từ các tệp CSV.

### pre_training.py

Bao gồm các bước chuẩn bị dữ liệu, trích xuất đặc trưng ngữ nghĩa câu mô tả địa điểm bằng PhoBERT (`vinai/phobert-base-v2`) và huấn luyện trước cho các thuật toán gợi ý.

### neo4j_tools.py

Cung cấp các hàm tiện ích quản lý kết nối driver và truy vấn cơ sở dữ liệu Neo4j.

---

## Hướng dẫn Cấu hình & Sử dụng

### 1. Cấu hình tệp `neo4j.ini`

Tạo hoặc cập nhật tệp `neo4j.ini` tại thư mục `04-Recommender-System-Web-App`:

```ini
[NEO4J]
HOST = bolt://localhost:7687
USERNAME = neo4j
DATABASE = neo4j
PASSWORD = mat_khau_cua_ban

[LOCAL_LLM]
ENABLED = true
MODE = python_transformers
URL = http://localhost:11434/api/generate
MODEL = Qwen/Qwen2.5-7B-Instruct
```

_Ghi chú về `MODE`:_

- `python_transformers`: Nạp mô hình HuggingFace trực tiếp trong tiến trình Python bằng GPU/CPU.
- `ollama`: Gọi mô hình Local LLM thông qua server Ollama HTTP API (`http://localhost:11434`).

### 2. Khởi chạy Ứng dụng Web

Thực hiện lệnh:

```bash
python app.py
```

- Lần đầu chạy trên cơ sở dữ liệu trống, hệ thống sẽ mất **5 đến 10 phút** để tự động tải dữ liệu và tiền huấn luyện.
- Sau khi hoàn tất, truy cập ứng dụng web tại địa chỉ: `http://127.0.0.1:5000`.

---

## Thư viện Phụ thuộc

- `Python 3.x`
- `Flask`
- `neo4j`
- `graphdatascience`
- `pandas`
- `scikit-learn`
- `py2neo`
- `torch` (Thư viện Deep Learning hỗ trợ tính toán GPU)
- `transformers` (Nạp mô hình HuggingFace LLM & PhoBERT)
- `pyvi` (Tách từ tiếng Việt chuẩn)

---

## Người thực hiện & Giấy phép

- **Tác giả**: Xiong Ying - Trần Lê Anh Tuấn
- **Giấy phép**: [MIT License](LICENSE).
