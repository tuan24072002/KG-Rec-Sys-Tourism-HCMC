# Nạp các thư viện cần thiết

import math
import pandas as pd
import warnings
import numpy as np
import time
import torch
from transformers import AutoModel, AutoTokenizer
from pyvi import ViTokenizer
from sklearn.preprocessing import MinMaxScaler

from py2neo import Graph
from graphdatascience import GraphDataScience

from neo4j_tools import run
from neo4j_tools import get_credential


# Bỏ qua các cảnh báo
warnings.filterwarnings("ignore")


# Định nghĩa các hàm

# ## 2) Gợi ý dựa trên Lọc dựa trên nội dung (Content-based Filtering) - Độ tương đồng nút (Node Similarity)
# Thời gian chạy: ~6 phút (đã tối ưu hóa bằng PhoBERT và NumPy)
def algo_2_preparation(gds, graph):

    # Trích xuất dữ liệu thô của nút POI và các thuộc tính liên quan từ GDS
    result = gds.run_cypher("""
    MATCH (poi:Poi)
    OPTIONAL MATCH (poi)-[:BELONGS_TO]->(category:Category)
    OPTIONAL MATCH (poi)-[:LOCATED_AT]->(region:Region)
    RETURN poi.id AS poi_id, 
        poi.name AS name, 
                            
        poi.description AS description, 

        poi.openingHours AS opening_hours, 
        poi.duration AS duration, 
        category.name AS category, 
        region.name AS region,
                            
        poi.price AS price, 
        poi.avgRating AS avg_rating, 
        poi.numReviews AS num_reviews, 
        poi.numReviews_5 AS num_reviews_5, 
        poi.numReviews_4 AS num_reviews_4, 
        poi.numReviews_3 AS num_reviews_3, 
        poi.numReviews_2 AS num_reviews_2, 
        poi.numReviews_1 AS num_reviews_1
    """)

    # Chuyển đổi kết quả truy vấn thành DataFrame
    df_pois = pd.DataFrame(result)

    # Trích xuất các trường poi_id và name (tên POI) duy nhất
    df_distinct_pois = df_pois.copy()
    df_distinct_pois = df_distinct_pois[['poi_id', 'name']].drop_duplicates()

    # Các đặc trưng dạng số (Numerical Features) - Chuẩn hóa Min-Max
    scaler = MinMaxScaler()
    numerical_cols = ['price', 'avg_rating', 'num_reviews', 'num_reviews_5', 'num_reviews_4', 'num_reviews_3', 'num_reviews_2', 'num_reviews_1']
    df_numerical_cols = df_pois.copy()
    df_numerical_cols = df_numerical_cols[['poi_id'] + numerical_cols]
    df_numerical_cols = df_numerical_cols.drop_duplicates()
    df_numerical_cols.fillna(0, inplace=True)
    df_numerical_cols[numerical_cols] = scaler.fit_transform(df_numerical_cols[numerical_cols])

    # Các đặc trưng phân loại (Categorical Features) - Mã hóa One-hot
    categorical_cols = ['category', 'region', 'opening_hours', 'duration']
    df_categorical_cols = df_pois.copy()
    df_categorical_cols = df_categorical_cols[['poi_id'] + categorical_cols]
    df_categorical_cols = pd.get_dummies(df_categorical_cols, columns=categorical_cols)
    df_categorical_cols = df_categorical_cols.groupby('poi_id').max().reset_index()

    # Các đặc trưng văn bản (Textual Features) - PhoBERT Embedding
    textual_cols = ['description']
    df_cols = df_pois.copy()
    df_cols = df_cols[['poi_id', 'name'] + textual_cols]
    df_cols = df_cols.drop_duplicates()
    df_cols['description'] = df_cols['description'].fillna('NULL')
    empty_description = df_cols['description'].str.strip() == ''
    df_cols.loc[empty_description, 'description'] = 'NULL'

    descriptions = df_cols['description'].tolist()

    # Tách từ tiếng Việt bằng PyVi
    print("Đang tiến hành tách từ (word segmentation)...")
    segmented_descriptions = [ViTokenizer.tokenize(desc) for desc in descriptions]

    # Cấu hình thiết bị GPU/CPU
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Sử dụng thiết bị: {device}")

    # Khởi tạo Tokenizer và PhoBERT model
    print("Đang tải mô hình PhoBERT...")
    tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base-v2")
    phobert = AutoModel.from_pretrained("vinai/phobert-base-v2").to(device)
    phobert.eval()

    # Hàm trích xuất embedding
    def get_phobert_embeddings(texts, batch_size=32):
        embeddings = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                inputs = tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=256,
                    return_tensors="pt"
                ).to(device)
                
                outputs = phobert(**inputs)
                cls_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                embeddings.append(cls_embeddings)
                
                if (i + batch_size) % (batch_size * 10) == 0 or (i + batch_size) >= len(texts):
                    print(f"Đã xử lý {min(i + batch_size, len(texts))}/{len(texts)} mô tả...")
                    
        return np.vstack(embeddings)

    print("Đang trích xuất embedding...")
    embeddings = get_phobert_embeddings(segmented_descriptions)

    # Tạo DataFrame lưu trữ vector embedding (768 chiều)
    df_textual_cols = pd.DataFrame(embeddings)
    df_textual_cols.insert(0, 'poi_id', df_cols['poi_id'].values)

    print(f"Hoàn thành! Kích thước ma trận embedding: {df_textual_cols.shape}")

    # Tính toán độ tương đồng cặp giữa các POI bằng NumPy tối ưu
    start_time = time.time()

    # Chuẩn bị dữ liệu dạng dictionary để tìm kiếm O(1) và loại bỏ overhead của Pandas
    categorical_dict = df_categorical_cols.set_index('poi_id').drop(columns=['name'], errors='ignore').to_dict(orient='index')
    categorical_dict = {k: np.array(list(v.values()), dtype=bool) for k, v in categorical_dict.items()}

    numerical_dict = df_numerical_cols.set_index('poi_id').drop(columns=['name'], errors='ignore').to_dict(orient='index')
    numerical_dict = {k: np.array(list(v.values()), dtype=float) for k, v in numerical_dict.items()}

    # Trích xuất và tiền chuẩn hóa vector L2 cho độ tương đồng Cosine nhanh
    textual_dict = df_textual_cols.set_index('poi_id').to_dict(orient='index')
    textual_dict_norm = {}
    for k, v in textual_dict.items():
        arr = np.array(list(v.values()), dtype=float)
        norm = np.linalg.norm(arr)
        textual_dict_norm[k] = arr / norm if norm > 0 else arr

    num_cat_cols = len(categorical_cols)
    num_num_cols = len(numerical_cols)
    num_text_cols = len(textual_cols)
    total_weights = num_cat_cols + num_num_cols + num_text_cols

    poi_ids = df_distinct_pois['poi_id'].tolist()
    n_pois = len(poi_ids)

    print(f"Bắt đầu tính toán độ tương đồng cho {n_pois * (n_pois - 1) // 2} cặp...")

    similarity_pairs = []

    for i in range(n_pois):
        poi1_id = poi_ids[i]
        
        p1_cat = categorical_dict[poi1_id]
        p1_num = numerical_dict[poi1_id]
        p1_text = textual_dict_norm[poi1_id]
        
        for j in range(i + 1, n_pois):
            poi2_id = poi_ids[j]
            
            p2_cat = categorical_dict[poi2_id]
            p2_num = numerical_dict[poi2_id]
            p2_text = textual_dict_norm[poi2_id]
            
            # 1. Jaccard Similarity cho thuộc tính phân loại
            intersection = np.sum(p1_cat & p2_cat)
            union = np.sum(p1_cat | p2_cat)
            cat_cols_similarity = intersection / union if union != 0 else 0.0
            
            # 2. Euclidean Similarity cho thuộc tính số
            euclidean_distance = np.linalg.norm(p1_num - p2_num)
            num_cols_similarity = 1 / (1 + euclidean_distance)
            
            # 3. Cosine Similarity cho thuộc tính văn bản
            text_cols_similarity = np.dot(p1_text, p2_text)
            
            # 4. Trọng số tổng hợp
            similarity = (num_cat_cols * cat_cols_similarity + 
                          num_num_cols * num_cols_similarity + 
                          num_text_cols * text_cols_similarity) / total_weights
            
            # Chỉ lưu các cặp có độ tương đồng lớn hơn hoặc bằng 0.5
            if similarity >= 0.5:
                similarity_pairs.append((poi1_id, poi2_id, similarity))

    # Tạo DataFrame kết quả
    df_similarity = pd.DataFrame(similarity_pairs, columns=['poi1_id', 'poi2_id', 'Similarity'])
    df_similarity = df_similarity.sort_values(by='Similarity', ascending=False).reset_index(drop=True)

    end_time = time.time()
    print(f"Hoàn thành tính toán trong {end_time - start_time:.2f} giây!")
    print(f"Số lượng cặp POI tương đồng (>= 0.5): {len(df_similarity)}")

    # Ghi dữ liệu vào Neo4j theo lô (Batch write)
    data_list = df_similarity.to_dict(orient='records')
    
    batch_query = """
    UNWIND $rows AS row
    MATCH (poi1:Poi {id: row.poi1_id})
    MATCH (poi2:Poi {id: row.poi2_id})
    MERGE (poi1)-[s1:CBF_SIMILAR]->(poi2)
    ON CREATE SET s1.score = row.Similarity
    MERGE (poi1)<-[s2:CBF_SIMILAR]-(poi2)
    ON CREATE SET s2.score = row.Similarity
    """
    
    batch_size = 50000
    total_rows = len(data_list)
    
    print("Bắt đầu ghi dữ liệu quan hệ vào Neo4j...")
    for i in range(0, total_rows, batch_size):
        batch = data_list[i : i + batch_size]
        graph.run(batch_query, rows=batch)
        print(f"Đã ghi xong từ {i} đến {min(i + batch_size, total_rows)}")
        
    print("Hoàn thành ghi toàn bộ dữ liệu quan hệ vào Neo4j!")

    return


## 3) Gợi ý dựa trên Lọc cộng tác (Collaborative Filtering) - kNN dựa trên người dùng (User-Based) dùng các vector nhúng FastRP

def algo_3_4_preparation(gds):

    # Đồ thị chiếu (Projection Graph)
    # Thời gian chạy: ~20 giây

    # Định nghĩa cách chiếu cơ sở dữ liệu vào GDS
    node_projection = ["User", "Poi"]
    relationship_projection = {"REVIEWED": {"orientation": "UNDIRECTED", "properties": "rating"}}

    # Tiến hành chiếu đồ thị
    G, result = gds.graph.project("myGraph", node_projection, relationship_projection)


    # Tạo các vector nhúng FastRP (Fast RP embeddings)

    # Chạy thuật toán FastRP và thay đổi (mutate) đồ thị chiếu của chúng ta với kết quả
    result = gds.fastRP.mutate(
        G,
        randomSeed=42,
        embeddingDimension=256,
        relationshipWeightProperty="rating",
        iterationWeights=[0, 1, 1, 1],
        mutateProperty="embedding"
    )

    #print(f"Number of embedding vectors produced: {result['nodePropertiesWritten']}")

    # Tính độ tương đồng với thuật toán KNN dựa trên người dùng (User-based KNN)

    # Chạy thuật toán kNN với siêu tham số topK tối ưu và ghi lại vào cơ sở dữ liệu
    # Thời gian chạy: ~3 phút

    topK_best = 10

    result = gds.knn.write(
        G,
        topK=topK_best,
        nodeLabels=['User'],
        nodeProperties=["embedding"],
        randomSeed=42,
        concurrency=1,
        sampleRate=1.0,
        deltaThreshold=0.0,
        writeRelationshipType="CF_SIMILAR_USER",
        writeProperty="score",

    )

    #print(f"Relationships produced: {result['relationshipsWritten']}")
    #print(f"Nodes compared: {result['nodesCompared']}")
    #print(f"Mean similarity: {result['similarityDistribution']['mean']}")


    # Tính độ tương đồng với thuật toán KNN dựa trên sản phẩm (Item-based KNN)

    # Chạy thuật toán kNN với siêu tham số topK tối ưu và ghi lại vào cơ sở dữ liệu

    topK_best = 1

    result = gds.knn.write(
        G,
        topK=topK_best,
        nodeLabels = ['Poi'],
        nodeProperties=["embedding"],
        randomSeed=42,
        concurrency=1,
        sampleRate=1.0,
        deltaThreshold=0.0,
        similarityCutoff = 0.5,
        writeRelationshipType="CF_SIMILAR_POI",
        writeProperty="score"
    )

    #print(f"Relationships produced: {result['relationshipsWritten']}")
    #print(f"Nodes compared: {result['nodesCompared']}")
    #print(f"Mean similarity: {result['similarityDistribution']['mean']}")

    # Loại bỏ đồ thị chiếu của chúng ta khỏi danh mục đồ thị GDS
    G.drop()

    

    return



# HÀM: Chuẩn bị dữ liệu phục vụ đưa ra gợi ý (pre-training)
def pre_training(gds):

    # Chuẩn bị cho thuật toán 2
    if gds.run_cypher("""MATCH ()-[r:CBF_SIMILAR]->() RETURN r LIMIT 10""").empty:

        print("Đang bắt đầu chuẩn bị thuật toán 2 (algo_2_preparation)...")

        # Kết nối Neo4j

        # Lấy thông tin xác thực để kết nối Neo4j
        HOST, USERNAME, DATABASE, PASSWORD = get_credential()

        # Kết nối sử dụng thư viện py2neo
        graph = Graph(HOST, auth=(USERNAME, PASSWORD), name=DATABASE)

        algo_2_preparation(gds, graph)

        print("Đã hoàn thành chuẩn bị thuật toán 2.")

    else:
        print("Thuật toán 2 đã được chuẩn bị trước đó.")

    # Chuẩn bị cho thuật toán 3 và 4
    if gds.run_cypher("""MATCH ()-[r:CF_SIMILAR_POI]->() RETURN r LIMIT 10""").empty:

        print("Đang bắt đầu chuẩn bị thuật toán 3 và 4 (algo_3_4_preparation)...")

        algo_3_4_preparation(gds)

        print("Đã hoàn thành chuẩn bị thuật toán 3 và 4.")

    else:
        print("Thuật toán 3 và 4 đã được chuẩn bị trước đó.")

    return

    

# Điểm khởi chạy (entry point)
if __name__ == '__main__':

    # Lấy thông tin xác thực để kết nối Neo4j
    HOST, USERNAME, DATABASE, PASSWORD = get_credential()
    
    # Kết nối sử dụng thư viện GDS
    gds = GraphDataScience(HOST, auth=(USERNAME, PASSWORD))
    gds.set_database(DATABASE)

    pre_training(gds)

    # Đóng kết nối được tạo bằng thư viện GDS
    gds.close()