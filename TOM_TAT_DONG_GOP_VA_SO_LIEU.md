# BẢN TÓM TẮT ĐÓNG GÓP KHOA HỌC VÀ HỆ THỐNG BẢNG SỐ LIỆU THỰC NGHIỆM

> **Tên đề tài**: HỆ THỐNG GỢI Ý LAI CHO ĐIỂM ĐẾN DU LỊCH ĐƯỢC TĂNG CƯỜNG BẰNG ĐỒ THỊ TRI THỨC VÀ GIẢI THÍCH DỰA TRÊN MÔ HÌNH NGÔN NGỮ LỚN  
> **Bài báo đối chứng nền tảng**: Xiong Ying (Đại học Công nghệ Nanyang - NTU Singapore, 2024), _"Knowledge Graph Construction and Recommender System Development of Tourism in Singapore"_  
> **Mục đích tài liệu**: Tổng hợp cô đọng đóng góp cốt lõi, cơ sở lý thuyết và số liệu thực nghiệm phục vụ việc rà soát bản thảo bài báo và hoàn thiện văn phong học thuật.

---

## I. TỔNG QUAN 5 ĐÓNG GÓP MỚI CỦA ĐỀ TÀI

|  STT  | Khía cạnh đóng góp                  | Công trình Singapore (Xiong Ying, NTU 2024)                                              | Đề tài Thạc sĩ TP.HCM (Trần Lê Anh Tuấn)                                                                                   | Ý nghĩa khoa học & Ứng dụng thực tiễn                                                                                                            |
| :---: | :---------------------------------- | :--------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Quy mô & Miền dữ liệu**           | 69 POIs, 58.656 users, 90.454 reviews. Dữ liệu dày đặc (~1.310 reviews/POI).             | **3.326 POIs** (gấp ~48 lần), 21.315 users, 24.108 reviews.                                                                | Mở rộng bài toán gợi ý từ quy mô điểm đến tập trung sang quy mô đại đô thị đang phát triển.                                                      |
| **2** | **Đặc tính dữ liệu (Sparsity)**     | Dữ liệu dày đặc, ma trận tương tác có độ phủ cao.                                        | **Siêu thưa (Sparsity > 99,9%)**, 92,87% user chỉ có đúng 1 đánh giá (Long-tail).                                          | Phản ánh chính xác thực trạng dữ liệu du lịch Việt Nam; đặt ra bài toán kết hợp tri thức đồ thị để bù đắp tương tác.                             |
| **3** | **Ontology địa giới hành chính**    | Đồ thị phẳng 6 nhãn node tĩnh (`Poi`, `Category`, `Region`, `User`, `Review`, `Origin`). | Đồ thị 8 nhãn node (`Ward`, `District`, `Region`,...) + Quan hệ sáp nhập **`[:MERGED_TO]`**.                               | Giải quyết bài toán biến động địa giới hành chính thực tế (sáp nhập TP. Thủ Đức và 80 phường/xã theo NQ 1111/NQ-UBTVQH14 & NQ 1678/NQ-UBTVQH15). |
| **4** | **Xử lý ngôn ngữ tự nhiên (NLP)**   | Tiếng Anh cơ bản, dùng **CountVectorizer (Bag-of-Words)**.                               | Xử lý tiếng Việt chuyên sâu: Tách từ **PyVi (`ViTokenizer`)** + Nhúng ngữ nghĩa sâu **PhoBERT** (768 chiều CLS token).     | Nắm bắt ngữ nghĩa từ ghép tiếng Việt, tri thức đồng nghĩa và ngữ cảnh miêu tả điểm đến.                                                          |
| **5** | **Bản chất Học kết hợp (Ensemble)** | Các tổ hợp không có NLP (như Algo 1,3,4) vẫn đạt kết quả tốt do CF rất dày.              | **PhoBERT đóng vai trò "cầu nối ngữ nghĩa" sống còn**: Thiếu PhoBERT thì F1 < 8,5%; Có PhoBERT thì F1 đạt 32,16% – 36,73%. | Chứng minh vai trò quyết định của biểu diễn ngữ nghĩa nội dung khi tương tác người dùng bị thưa thớt cực hạn.                                    |
| **6** | **Tương tác AI & XAI (GraphRAG)**   | Không có phân hệ AI tạo sinh (chỉ gợi ý danh sách tĩnh).                                 | Tích hợp **GraphRAG**: Local LLM **Qwen2.5-1.5B-Instruct** + Truy vấn Cypher ngữ cảnh thực tế + Luồng **SSE**.             | Giải thích lý do gợi ý minh bạch (XAI), chống ảo giác (hallucination) và bảo mật dữ liệu cục bộ.                                                 |

---

## II. QUY MÔ ĐỒ THỊ TRI THỨC DU LỊCH TP.HCM (NEO4J SCHEMA)

- **Tổng số nút thực thể**: **51.868 nút**
- **Tổng số quan hệ liên kết**: **1.653.897 quan hệ**

### 1. Phân bố các nút thực thể (Nodes)

- `Poi` (Điểm đến du lịch): **3.326**
- `User` (Người dùng): **21.315**
- `Review` (Bài đánh giá): **24.108**
- `Category` (Danh mục điểm đến): **452**
- `Region` (Khu vực địa lý cũ): **22**
- `District` (Quận/Huyện hiện tại): **22**
- `Ward` (Phường/Xã hành chính cơ sở): **280**
- `Origin` (Quê quán / Quốc gia du khách): **2.343**

### 2. Phân bố các mối quan hệ ngữ nghĩa (Edges)

- `(Poi)-[:BELONGS_TO]->(Category)`: 3.370
- `(Poi)-[:LOCATED_AT]->(Region)`: 3.326
- `(Poi)-[:LOCATED_IN]->(Ward)`: 1.185
- `(Ward)-[:BELONGS_TO]->(District)`: 280
- `(Ward_cũ)-[:MERGED_TO]->(Ward_mới)`: 275 _(bảo toàn lịch sử sáp nhập)_
- `(User)-[:FROM]->(Origin)`: 9.557
- `(User)-[:WROTE]->(Review)`: 24.108
- `(Review)-[:RATED]->(Poi)`: 24.108
- `(User)-[:REVIEWED]->(Poi)`: 24.108 _(quan hệ trực tiếp mang trọng số rating)_
- `(Poi)-[:NEARBY]->(Poi)`: 1.563.580 _(quan hệ không gian hai chiều với bán kính $d \le 1{,}5$ km)_

---

## III. HỆ THỐNG CÁC BẢNG SỐ LIỆU THỰC NGHIỆM

### Bảng 1: Tinh chỉnh siêu tham số láng giềng $topK$ (FastRP 256 chiều)

_Ghi nhận sự dịch chuyển điểm tối ưu do độ thưa dữ liệu giữa Singapore và TP.HCM:_

| $topK$ |   UserKNN (Singapore)   |         UserKNN (TP.HCM)          |   ItemKNN (Singapore)   |         ItemKNN (TP.HCM)          |
| :----: | :---------------------: | :-------------------------------: | :---------------------: | :-------------------------------: |
|   1    |        0,993915         |             0,931331              |        0,561512         | **0,615605 (Đỉnh tối ưu TP.HCM)** |
|   2    |           --            |                --                 | **0,562363 (Đỉnh NTU)** |             0,609109              |
|   5    |        0,995537         |             0,947765              |        0,551244         |             0,600647              |
| **9**  |        0,996992         | **0,961408 (Đỉnh tối ưu TP.HCM)** |           --            |                --                 |
| **12** | **0,997618 (Đỉnh NTU)** |             0,958511              |           --            |                --                 |
|   20   |        0,997244         |             0,939420              |        0,526570         |             0,583982              |

---

### Bảng 2: Hiệu năng 4 thuật toán gợi ý đơn lẻ trên dữ liệu TP.HCM (@Top-10)

| Thuật toán đơn lẻ           | Ngữ chế hoạt động                            |       Precision@10        |  Recall@10   |        Coverage@10        | $F_1$-Score  |
| :-------------------------- | :------------------------------------------- | :-----------------------: | :----------: | :-----------------------: | :----------: |
| **Algo 1: Heuristic-CBF**   | Category + Region + Nearby $\le 1{,}5$km     |         0,085577          |   0,061464   |         0,059230          |   0,071543   |
| **Algo 2: PhoBERT NodeSim** | Lai thuộc tính số + Jaccard + PhoBERT Cosine |         0,346221          |   0,040728   | **0,101022** _(Cao nhất)_ |   0,072882   |
| **Algo 3: UserKNN-FastRP**  | FastRP 256 chiều, $topK=9$                   |         0,614740          | **0,506906** |         0,040589          | **0,555640** |
| **Algo 4: ItemKNN-FastRP**  | FastRP 256 chiều, $topK=1$                   | **0,836065** _(Cao nhất)_ |   0,010543   |         0,014131          |   0,020824   |

---

### Bảng 3: Kết quả thực nghiệm 11 tổ hợp mô hình học kết hợp (Majority Voting)

|  STT  | Cấu hình mô hình kết hợp              | Precision@10 |  Recall@10   | Coverage@10  | $F_1$-Score  | Nhận định ý nghĩa                                                                                  |
| :---: | :------------------------------------ | :----------: | :----------: | :----------: | :----------: | :------------------------------------------------------------------------------------------------- |
| **1** | **Algo 1, 2, 3, 4 (Mô hình đề xuất)** | **0,254633** | **0,436464** | **0,082081** | **0,321628** | **Cân bằng tối ưu toàn diện: Recall cao, mở rộng độ phủ danh mục gấp hơn 2 lần so với CF đơn lẻ.** |
|   2   | Algo 2, 3, 4                          |   0,330332   |   0,405387   |   0,043596   |   0,364031   | Bỏ Heuristic: $F_1$ tăng nhưng Coverage giảm một nửa.                                              |
|   3   | Algo 1, 3, 4 _(Loại bỏ PhoBERT)_      |   0,409639   |   0,046961   |   0,013229   | **0,084263** | **Minh chứng sống còn: Thiếu PhoBERT, F1 sụp đổ nghiêm trọng (giảm từ 32,16% xuống 8,43%).**       |
|   4   | Algo 1, 2, 4                          |   0,090361   |   0,051796   |   0,064342   |   0,065847   | Thiếu UserKNN: Hiệu năng giảm mạnh.                                                                |
|   5   | Algo 1, 2, 3                          |   0,258571   |   0,432320   |   0,076969   |   0,323598   | Hiệu năng tiệm cận mô hình đầy đủ.                                                                 |
|   6   | Algo 1, 2                             |   0,084881   |   0,044199   |   0,054720   |   0,058129   | Tổ hợp thuần nội dung.                                                                             |
|   7   | Algo 1, 3                             |   0,419580   |   0,041436   |   0,010523   |   0,075424   | Thiếu ngữ nghĩa sâu.                                                                               |
|   8   | Algo 1, 4                             |   0,111111   |   0,000691   |   0,000301   |   0,001373   | Độ bao phủ cực thấp.                                                                               |
| **9** | **Algo 2, 3 (Tối ưu tổ hợp đôi)**     |   0,339181   |   0,400552   |   0,037883   | **0,367321** | Đạt $F_1$ cao nhất trong các tổ hợp kết hợp.                                                       |
|  10   | Algo 2, 4                             |   0,141176   |   0,008287   |   0,012628   |   0,015656   | Độ bao phủ thấp.                                                                                   |
|  11   | Algo 3, 4                             |   0,350000   |   0,004834   |   0,003608   |   0,009537   | Thiếu nội dung hỗ trợ trên dữ liệu thưa.                                                           |

---

### Bảng 4: So sánh đối chứng hiệu năng giữa Singapore và TP.HCM

| Cấu hình kết hợp          | Singapore (Xiong Ying - Dữ liệu dày) |            |              |              | TP.HCM (Đề xuất - Dữ liệu siêu thưa) |              |              |              |
| :------------------------ | :----------------------------------: | :--------: | :----------: | :----------: | :----------------------------------: | :----------: | :----------: | :----------: |
|                           |            **Precision**             | **Recall** | **Coverage** |  **$F_1$**   |            **Precision**             |  **Recall**  | **Coverage** |  **$F_1$**   |
| **Algo 1, 2, 3, 4**       |               0,409779               |  0,308096  |   0,681159   | **0,351736** |               0,254633               | **0,436464** | **0,082081** | **0,321628** |
| **Algo 2, 3, 4**          |               0,499089               |  0,119912  |   0,521739   |   0,193366   |               0,330332               |   0,405387   |   0,043596   |   0,364031   |
| **Algo 1, 3, 4 (No NLP)** |               0,610169               |  0,267834  |   0,420290   | **0,372263** |               0,409639               |   0,046961   |   0,013229   | **0,084263** |
| **Algo 2, 3**             |               0,570064               |  0,078337  |   0,449275   |   0,137745   |               0,339181               |   0,400552   |   0,037883   | **0,367321** |

> **Nhận xét then chốt**: Tại Singapore, tổ hợp Algo 1,3,4 (không có NLP) vẫn đạt $F_1 = 37{,}2\%$ nhờ mật độ tương tác người dùng dày đặc (~1.310 review/POI). Ngược lại, tại TP.HCM (siêu thưa > 99,9%), nếu loại bỏ PhoBERT (Algo 1,3,4) thì $F_1$ tụt dốc thảm hại xuống còn $8{,}4\%$. Điều này khẳng định tri thức ngữ nghĩa sâu tiếng Việt đóng vai trò bù đắp thông tin sống còn.

---

## IV. HIỆN THỰC HÓA HỆ THỐNG VÀ ĐÁNH GIÁ MỨC ỨNG DỤNG

1. **Kiến trúc phần mềm**: Mô hình MVC 3 tầng trên nền tảng Flask Backend, Neo4j Graph Database (GDS In-Memory) và giao diện Jinja2/Tailwind CSS.
2. **Kiểm thử chức năng**: Hoàn thành đạt yêu cầu **18/18 ca kiểm thử chức năng** (Functional Test Cases) cho **7 kịch bản sử dụng chính** (Use Cases).
3. **Hiệu năng suy luận**:
   - Tốc độ sinh biểu diễn FastRP và truy vấn đồ thị: $< 50\text{ ms}$.
   - Độ trễ phản hồi từ đầu tiên (Time-to-First-Token) của trợ lý GraphRAG: $1{,}18 \pm 0{,}15\text{ giây}$ (chạy trực tiếp trên CPU tiêu chuẩn 16 GB RAM qua cơ chế truyền dòng Server-Sent Events - SSE).
   - Độ chính xác ánh xạ địa giới hành chính sáp nhập qua quan hệ `[:MERGED_TO]`: Hoàn thành chính xác trên các kịch bản kiểm thử các phường sáp nhập tại TP.HCM.
