# GIẢI THÍCH CHI TIẾT THUẬT TOÁN 1: CƠ CHẾ LỌC ĐỒNG THUẬN ĐA SỐ VÀ HỢP NHẤT THỨ HẠNG CÓ TRỌNG SỐ
*(Majority Consensus and Weighted Rank Fusion)*

---

## I. TỔNG QUAN VÀ BỐI CẢNH TOÁN HỌC

### 1. Vấn đề thực tế đặt ra
Trong hệ thống gợi ý du lịch dựa trên đồ thị tri thức, chúng ta có **$M = 4$ mô hình thành phần** hoạt động theo các nguyên lý hoàn toàn khác nhau:
1. **Thuật toán 1 (Heuristic-CBF):** Lọc theo luật vị trí địa lý, danh mục hoạt động, quan hệ lân cận đi bộ ($\le 1,5$ km) và điểm đánh giá trung bình. Điểm số là tổng tuyến tính có trọng số các biến nhị phân và điểm sao.
2. **Thuật toán 2 (NodeSim-CBF):** Lọc theo độ tương đồng đặc trưng nút, kết hợp khoảng cách Euclidean trên đặc trưng số, chỉ số Jaccard trên danh mục, và **Cosine Similarity trên vector nhúng 768 chiều từ PhoBERT**. Điểm số nằm trong đoạn $[0, 1]$.
3. **Thuật toán 3 (UserKNN-FastRP):** Lọc cộng tác người dùng trên không gian biểu diễn tô-pô FastRP 256 chiều ($topK = 9$). Điểm số là tổng độ tương đồng nhân với rating của láng giềng.
4. **Thuật toán 4 (ItemKNN-FastRP):** Lọc cộng tác địa điểm trên không gian FastRP 256 chiều ($topK = 1$). Điểm số là độ tương đồng giữa các cặp địa điểm.

> **Thách thức cốt lõi:**  
> Mỗi mô hình xuất ra điểm số (score) theo **các thang đo, phân phối và miền giá trị hoàn toàn khác nhau**. Chúng ta không thể cộng trực tiếp các điểm số thô này lại với nhau (ví dụ: điểm Cosine 0.85 của PhoBERT không thể cộng thô với điểm tích lũy rating 15.2 của UserKNN).

### 2. Ý tưởng giải pháp của Thuật toán 1
Thuật toán giải quyết vấn đề bằng **chiến lược 2 giai đoạn (Two-stage Hybrid Architecture)**:
- **Giai đoạn 1 (Lọc đồng thuận đa số - Majority Consensus Filtering):** Sử dụng cơ chế bỏ phiếu phi tham số (non-parametric voting) để triệt tiêu các địa điểm nhiễu chỉ do một mô hình đơn lẻ đề xuất.
- **Giai đoạn 2 (Hợp nhất thứ hạng có trọng số - Weighted Rank Normalization & Fusion):** Chuyển đổi thứ hạng tương đối (rank position) của từng mô hình về thang chuẩn hóa nghịch đảo $[0, 1]$, sau đó kết hợp tuyến tính có trọng số.
- **Sắp xếp ưu tiên kép (Two-tier Lexicographical Sorting):** Ưu tiên số phiếu bầu trước; nếu bằng phiếu thì phân định bằng điểm hợp nhất thứ hạng.

---

## II. ĐẶC TẢ ĐẦU VÀO VÀ ĐẦU RA (REQUIRE & ENSURE)

```latex
Require: Danh sách đề xuất từ M = 4 thuật toán: {Rec_m(u)}_{m=1}^M, 
         Trọng số mô hình {w_m}_{m=1}^M, 
         Ngưỡng đồng thuận V_min = 2, 
         Độ dài gợi ý K = 10.
Ensure:  Danh sách gợi ý Top-K cuối cùng Rec_final(u).
```

### 1. Đầu vào (Require)
- **$M = 4$**: Số lượng thuật toán thành phần tham gia biểu quyết.
- **$\{\text{Rec}_m(u)\}_{m=1}^M$**: Danh sách địa điểm đề xuất của từng mô hình $m$ dành cho người dùng $u$. Mỗi danh sách chứa các địa điểm đã được xếp hạng từ tốt nhất đến kém hơn (thường lấy Top 10 đến Top 20 ứng viên ban đầu của từng mô hình).
- **$\{w_m\}_{m=1}^M$**: Vector trọng số gán cho từng mô hình, thỏa mãn điều kiện $\sum_{m=1}^M w_m = 1$. Trong thực nghiệm mặc định của bài báo, các mô hình được gán trọng số đều nhau:
  $$w_1 = w_2 = w_3 = w_4 = 0,25$$
  *(Trong tương lai, các trọng số này có thể được học tự động thông qua mô hình Learning-to-Rank như XGBoost Ranker).*
- **$V_{\min} = 2$**: Ngưỡng đồng thuận tối thiểu. Một địa điểm bắt buộc phải xuất hiện trong danh sách của **ít nhất 2 mô hình khác nhau** thì mới được xem xét đưa vào danh sách đề xuất cuối cùng.
- **$K = 10$**: Số lượng địa điểm tối ưu cần chọn ra để hiển thị cho người dùng.

### 2. Đầu ra (Ensure)
- **$\text{Rec}_{\text{final}}(u)$**: Danh sách Top 10 điểm đến du lịch được xếp hạng từ cao xuống thấp theo sự đồng thuận và chất lượng thứ hạng.

---

## III. GIẢI THÍCH CHI TIẾT TỪNG BƯỚC THUẬT TOÁN (LINE-BY-LINE WALKTHROUGH)

```
1:  Khởi tạo tập ứng viên P <- Union(Rec_m(u))
2:  for all p in P do
3:      Tính số phiếu đồng thuận: V(p) <- sum_{m=1}^M 1[p in Rec_m(u)]
4:  end for
5:  Lọc tập đồng thuận: P_filtered <- {p in P | V(p) >= V_min}
6:  for all p in P_filtered do
7:      for m = 1 to M do
8:          if p in Rec_m(u) then
9:              Lấy thứ hạng gốc r_m(p) trong mô hình m
10:             r^_m(p) <- (r_max - r_m(p)) / (r_max - r_min + epsilon) (nếu r_max = r_min thì r^_m(p) <- 1.0)
11:         else
12:             r^_m(p) <- 0.0
13:         end if
14:     end for
15:     Tính điểm hợp nhất: S_ens(p) <- sum_{m=1}^M w_m * r^_m(p)
16: end for
17: Sắp xếp các địa điểm trong P_filtered theo thứ tự ưu tiên: V(p) giảm dần, sau đó theo S_ens(p) giảm dần.
18: Rec_final(u) <- Top-K(P_filtered)
19: return Rec_final(u)
```

---

### Bước 1: Khởi tạo không gian ứng viên chung (Dòng 1)
$$\mathcal{P} \leftarrow \bigcup_{m=1}^M \text{Rec}_m(u)$$
- **Mục đích:** Hợp nhất tất cả các tập đề xuất đơn lẻ thành một tập hợp duy nhất $\mathcal{P}$.
- **Cơ chế:** Phép toán hợp tập (Set Union) sẽ tự động loại bỏ các phần tử trùng lặp. Ví dụ, nếu cả 4 mô hình đều đề xuất *Dinh Độc Lập*, địa điểm này chỉ xuất hiện 1 lần trong $\mathcal{P}$.
- **Quy mô:** Nếu mỗi mô hình đề xuất 10 địa điểm, tập $\mathcal{P}$ sẽ có từ 10 đến tối đa 40 ứng viên độc lập.

---

### Bước 2: Đếm số phiếu đồng thuận (Dòng 2 – Dòng 4)
$$V(p) \leftarrow \sum_{m=1}^M \mathbf{1}[p \in \text{Rec}_m(u)]$$
- **Hàm chỉ thị (Indicator Function) $\mathbf{1}[\cdot]$:**
  - Nhận giá trị $1$ nếu địa điểm $p$ có nằm trong danh sách $\text{Rec}_m(u)$ của mô hình thứ $m$.
  - Nhận giá trị $0$ nếu mô hình thứ $m$ không đề xuất địa điểm $p$.
- **Ý nghĩa:** $V(p) \in \{1, 2, 3, 4\}$ chính là **tổng số mô hình độc lập cùng "bỏ phiếu" lựa chọn địa điểm $p$**.
  - $V(p) = 4$: Tuyệt đối đồng thuận (cả 4 trường phái Heuristic, NodeSim, UserKNN, ItemKNN đều ủng hộ).
  - $V(p) = 1$: Đơn lẻ, cá biệt (chỉ có duy nhất 1 mô hình tìm ra).

---

### Bước 3: Lọc bỏ ứng viên nhiễu theo ngưỡng đồng thuận (Dòng 5)
$$\mathcal{P}_{\text{filtered}} \leftarrow \{p \in \mathcal{P} \mid V(p) \ge V_{\min}\}$$
- Với $V_{\min} = 2$, hệ thống **loại bỏ thẳng tay toàn bộ những địa điểm chỉ đạt 1 phiếu bầu ($V(p) = 1$)**.
- **Ý nghĩa khoa học sâu sắc:**
  - Trong điều kiện ma trận tương tác siêu thưa ($S > 99.9\%$), các mô hình lọc cộng tác rất dễ bị "nhiễu" do vài tương tác ngẫu nhiên.
  - Việc yêu cầu ít nhất 2 mô hình cùng đề xuất đóng vai trò như một **bộ lọc thông dải (noise filter)**: Một mô hình có thể phán đoán sai, nhưng khi 2 trường phái thuật toán khác nhau (ví dụ: một bên nhìn vào ngữ nghĩa PhoBERT, một bên nhìn vào cấu trúc lân cận FastRP) cùng đề xuất chung một địa điểm, xác suất địa điểm đó chính xác tăng lên gấp nhiều lần.

---

### Bước 4: Chuẩn hóa nghịch đảo thứ hạng Min-Max (Dòng 6 – Dòng 14)
Với mỗi địa điểm $p$ đã vượt qua vòng lọc đồng thuận, hệ thống tính toán điểm vị trí của nó trong từng mô hình $m$:

#### 1. Trường hợp địa điểm có mặt trong mô hình $m$ (Dòng 8 – 10):
Hệ thống lấy thứ hạng gốc $r_m(p)$ của địa điểm $p$ trong mô hình $m$.
- *Quy ước thứ hạng:* $r = 1$ là vị trí số 1 (tốt nhất), $r = 10$ là vị trí thứ 10 (thấp nhất trong Top 10).
- **Công thức chuyển đổi nghịch đảo Min-Max (Inverse Min-Max Normalization):**
  $$\hat{r}_m(p) \leftarrow \frac{r_m^{\max} - r_m(p)}{r_m^{\max} - r_m^{\min} + \epsilon}$$
  - $r_m^{\min}$: Thứ hạng cao nhất trong danh sách (thông thường $r_m^{\min} = 1$).
  - $r_m^{\max}$: Thứ hạng thấp nhất trong danh sách (ví dụ $r_m^{\max} = 10$).
  - $\epsilon = 10^{-6}$: Hằng số rất nhỏ nhằm triệt tiêu nguy cơ lỗi chia cho 0 trong lập trình.
  - *Tại sao phải nghịch đảo?* Trong bảng xếp hạng, số thứ hạng càng nhỏ thì càng giỏi ($r=1$ tốt hơn $r=10$). Công thức này đảo ngược lại:
    - Nếu địa điểm đứng **hạng 1** ($r = 1$): Điểm số chuẩn hóa đạt mức cao nhất:
      $$\hat{r}_m(p) = \frac{10 - 1}{10 - 1} = \mathbf{1.0}$$
    - Nếu địa điểm đứng **hạng cuối** ($r = 10$): Điểm số chuẩn hóa bằng:
      $$\hat{r}_m(p) = \frac{10 - 10}{10 - 1} = \mathbf{0.0}$$
    - Các thứ hạng ở giữa sẽ nhận điểm phân bổ đều đặn từ $0.0$ đến $1.0$ (ví dụ hạng 2 được $\approx 0.889$, hạng 5 được $\approx 0.556$).
  - *Điều kiện biên:* Nếu danh sách chỉ có đúng 1 địa điểm ($r_m^{\max} = r_m^{\min}$), hệ thống tự động gán thẳng $\hat{r}_m(p) \leftarrow 1.0$.

#### 2. Trường hợp địa điểm KHÔNG có mặt trong mô hình $m$ (Dòng 11 – 12):
$$\hat{r}_m(p) \leftarrow 0.0$$
Mô hình nào không đề xuất địa điểm này thì địa điểm đó nhận điểm 0 từ mô hình đó.

---

### Bước 5: Tính điểm hợp nhất có trọng số (Dòng 15)
$$S_{\text{ens}}(p) \leftarrow \sum_{m=1}^M w_m \cdot \hat{r}_m(p)$$
- Điểm hợp nhất $S_{\text{ens}}(p)$ là tích chập tuyến tính giữa vector trọng số $w_m$ và điểm thứ hạng chuẩn hóa $\hat{r}_m(p)$.
- Giá trị $S_{\text{ens}}(p) \in [0, 1]$. Điểm này phản ánh: *Sau khi được các mô hình đồng thuận, địa điểm này có vị trí trung bình cao hay thấp trong bảng xếp hạng nội bộ của từng mô hình*.

---

### Bước 6: Cơ chế sắp xếp ưu tiên kép (Dòng 17)
$$\text{Sắp xếp theo thứ tự ưu tiên: } V(p) \downarrow \quad \longrightarrow \quad S_{\text{ens}}(p) \downarrow$$
Đây là **thuật toán sắp xếp thứ tự từ điển (Lexicographical Sorting / Tie-Breaking Rule)** cực kỳ chặt chẽ:
1. **Khóa ưu tiên 1 (Primary Key):** Sắp xếp theo **số phiếu bầu $V(p)$ giảm dần**.
   - Địa điểm được 4 mô hình đồng thuận sẽ LUÔN LUÔN đứng trên địa điểm được 3 mô hình đồng thuận.
   - Địa điểm 3 mô hình đồng thuận sẽ LUÔN LUÔN đứng trên địa điểm 2 mô hình.
2. **Khóa ưu tiên 2 (Secondary Key / Tie-Breaker):** Nếu hai địa điểm có **cùng số phiếu bầu** (ví dụ cùng đạt 2 phiếu), hệ thống sẽ so sánh **điểm hợp nhất thứ hạng $S_{\text{ens}}(p)$**.
   - Địa điểm nào có thứ hạng gốc cao hơn trong các mô hình (tổng $S_{\text{ens}}$ lớn hơn) sẽ xếp trên.

---

### Bước 7: Cắt Top-$K$ và trả về kết quả (Dòng 18 – 19)
$$\text{Rec}_{\text{final}}(u) \leftarrow \text{Top-}K(\mathcal{P}_{\text{filtered}})$$
- Hệ thống trích xuất $K = 10$ địa điểm đứng đầu sau khi đã sắp xếp.
- Trả về danh sách gợi ý cuối cùng cho người dùng.

---

## IV. VÍ DỤ TÍNH TOÁN BẰNG SỐ CỤ THỂ (NUMERICAL WALKTHROUGH)

Giả sử hệ thống cần gợi ý cho người dùng $u$. Mỗi mô hình thành phần trả về danh sách Top 5 ứng viên ($r^{\min} = 1, r^{\max} = 5$). Bảng dưới đây thể hiện thứ hạng gốc của 3 địa điểm tiêu biểu:

| Địa điểm | Algo 1 (Heuristic) | Algo 2 (PhoBERT) | Algo 3 (UserKNN) | Algo 4 (ItemKNN) |
| :--- | :---: | :---: | :---: | :---: |
| **$P_A$ (Bảo tàng Lịch sử)** | Hạng 1 | Hạng 2 | Hạng 4 | *Không có* |
| **$P_B$ (Chợ Bến Thành)** | Hạng 2 | *Không có* | Hạng 1 | Hạng 1 |
| **$P_C$ (Điểm ngách quận 7)**| Hạng 1 | *Không có* | *Không có* | *Không có* |

Trọng số các mô hình bằng nhau: $w_1 = w_2 = w_3 = w_4 = 0,25$.

---

### Thực thi từng bước:

#### Bước 1 & 2: Hợp tập ứng viên và đếm phiếu
- Địa điểm $P_A$: xuất hiện ở Algo 1, Algo 2, Algo 3 $\rightarrow$ **$V(P_A) = 3$ phiếu**.
- Địa điểm $P_B$: xuất hiện ở Algo 1, Algo 3, Algo 4 $\rightarrow$ **$V(P_B) = 3$ phiếu**.
- Địa điểm $P_C$: chỉ xuất hiện ở Algo 1 $\rightarrow$ **$V(P_C) = 1$ phiếu**.

#### Bước 3: Lọc đồng thuận ($V_{\min} = 2$)
- $P_C$ có $V(P_C) = 1 < 2 \rightarrow$ **Bị loại ngay lập tức (loại trừ nhiễu)**.
- Tập còn lại: $\mathcal{P}_{\text{filtered}} = \{P_A, P_B\}$.

#### Bước 4: Chuẩn hóa nghịch đảo thứ hạng $\hat{r}_m(p) = \frac{5 - r}{5 - 1} = \frac{5 - r}{4}$
- **Với địa điểm $P_A$:**
  - Algo 1 (hạng 1): $\hat{r}_1(P_A) = (5-1)/4 = 1,00$
  - Algo 2 (hạng 2): $\hat{r}_2(P_A) = (5-2)/4 = 0,75$
  - Algo 3 (hạng 4): $\hat{r}_3(P_A) = (5-4)/4 = 0,25$
  - Algo 4 (không có): $\hat{r}_4(P_A) = 0,00$
- **Với địa điểm $P_B$:**
  - Algo 1 (hạng 2): $\hat{r}_1(P_B) = (5-2)/4 = 0,75$
  - Algo 2 (không có): $\hat{r}_2(P_B) = 0,00$
  - Algo 3 (hạng 1): $\hat{r}_3(P_B) = (5-1)/4 = 1,00$
  - Algo 4 (hạng 1): $\hat{r}_4(P_B) = (5-1)/4 = 1,00$

#### Bước 5: Tính điểm hợp nhất $S_{\text{ens}}(p) = \sum 0,25 \times \hat{r}_m(p)$
- $S_{\text{ens}}(P_A) = 0,25 \times (1,00 + 0,75 + 0,25 + 0,00) = 0,25 \times 2,00 = \mathbf{0,500}$
- $S_{\text{ens}}(P_B) = 0,25 \times (0,75 + 0,00 + 1,00 + 1,00) = 0,25 \times 2,75 = \mathbf{0,6875}$

#### Bước 6: Sắp xếp ưu tiên kép
1. Xét số phiếu: Cả $P_A$ và $P_B$ đều đạt **3 phiếu** (hòa nhau ở Khóa 1).
2. Phân định bằng Khóa 2 (Tie-breaker):
   $$S_{\text{ens}}(P_B) = 0,6875 > S_{\text{ens}}(P_A) = 0,500$$
3. **Kết quả:** **$P_B$ xếp trên $P_A$**!

> **Nhận xét trực quan:**  
> Mặc dù cả hai địa điểm đều được 3 mô hình đồng ý đề xuất, nhưng $P_B$ được đứng hạng 1 ở tận 2 mô hình (Algo 3 và 4), trong khi $P_A$ bị tụt xuống hạng 4 ở Algo 3. Thuật toán đã nhận diện chính xác và trao vị trí cao hơn cho $P_B$ một cách hoàn toàn tự động và hợp lý!

---

## V. TẠI SAO THUẬT TOÁN NÀY ĐẠT CHUẨN HỌC THUẬT CAO?

Khi giải trình với Thầy hướng dẫn hoặc Hội đồng phản biện, bạn có thể nêu bật **3 ưu thế học thuật vượt trội** của cơ chế này:

1. **Khắc phục bất tương thích thang đo (Scale Invariance):**
   Thay vì cố gắng chuẩn hóa các điểm số xác suất hoặc khoảng cách toán học vốn có độ lệch phân phối lớn, thuật toán chuẩn hóa trên **thứ hạng tương đối (relative rank)**. Thứ hạng là đại lượng bất biến trước mọi phép biến đổi đơn điệu của hàm điểm số gốc.
2. **Cơ chế đồng thuận phi tham số (Non-parametric Robustness):**
   Trong điều kiện dữ liệu siêu thưa ($S > 99.9\%$), việc áp dụng các mô hình học máy xếp hạng tham số phức tạp (như LambdaMART, ListNet) rất dễ bị quá khớp (over-fitting) do thiếu nhãn phản hồi âm tính (implicit negative feedback). Cơ chế lọc đa số $V(p) \ge 2$ hoạt động như một nguyên lý đồng thuận phân tán, bảo vệ hệ thống khỏi các quyết định sai lầm của một thuật toán đơn lẻ.
3. **Độ phức tạp tính toán tuyến tính $\mathcal{O}(M \cdot |\mathcal{P}|)$:**
   Thuật toán chỉ duyệt qua tập ứng viên hợp nhất (tối đa vài chục phần tử), thời gian chạy tính bằng micro-giây ($\mu s$), không gây nghẽn cổ chai và đáp ứng hoàn hảo yêu cầu phục vụ thời gian thực dưới 50ms trên máy chủ Web.
