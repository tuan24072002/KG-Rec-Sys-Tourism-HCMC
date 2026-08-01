import textwrap
import pandas as pd

from neo4j import GraphDatabase
from graphdatascience import GraphDataScience

from neo4j_tools import run
from neo4j_tools import get_credential

# Thuật toán 1: Gợi ý Lọc dựa trên nội dung (Content Based Filtering) - Phương pháp phỏng đoán (Heuristic Method)

# HÀM: Đưa ra gợi ý dựa trên Lọc dựa trên nội dung - Phương pháp phỏng đoán
# ĐẦU VÀO: poi_id
# ĐẦU RA: dataframe[poi_id, rec_poi_id]

def heuristic_recommendation(user_id, poi_id, k=10):
    # Lấy các POI trong cùng khu vực với POI đã được người dùng đánh giá
    records_region = run(driver, textwrap.dedent("""\
        MATCH (user {id: $user_id})-[:REVIEWED]->(poi:Poi {id: $poi_id})-[:LOCATED_AT]->(region:Region)<-[:LOCATED_AT]-(other_poi:Poi)<-[rated:RATED]-(review:Review)
        WHERE poi <> other_poi
        WITH user, poi, other_poi, region, count(DISTINCT rated) AS num_reviews
        RETURN user.id AS user_id, poi.id AS poi_id, other_poi.id AS rec_poi_id, other_poi.name AS rec_poi_name, region.name AS region, num_reviews AS occurrences
        """),
        params = {'user_id': user_id, 'poi_id': poi_id}
    )
    # print(f"Tìm thấy {len(records_region)} records POI có CÙNG KHU VỰC.")
    # Lấy các POI trong cùng danh mục với POI đã được người dùng đánh giá 
    records_category = run(driver, textwrap.dedent("""\
        MATCH (user {id: $user_id})-[:REVIEWED]->(poi:Poi {id: $poi_id})-[:BELONGS_TO]->(category:Category)<-[:BELONGS_TO]-(other_poi:Poi)<-[rated:RATED]-(review:Review)
        WHERE poi <> other_poi
        WITH user, poi, other_poi, category, count(DISTINCT rated) AS num_reviews
        RETURN user.id AS user_id, poi.id AS poi_id, other_poi.id AS rec_poi_id, other_poi.name AS rec_poi_name, category.name AS category_name, num_reviews AS occurrences
        """),
        params = {'user_id': user_id, 'poi_id': poi_id}
    )
    # print(f"Tìm thấy {len(records_category)} records POI có CÙNG DANH MỤC.")
    # Lấy các POI lân cận (NEARBY - trong bán kính 1.5km)
    records_nearby = run(driver, textwrap.dedent("""\
        MATCH (user {id: $user_id})-[:REVIEWED]->(poi:Poi {id: $poi_id})-[n:NEARBY]->(other_poi:Poi)<-[rated:RATED]-(review:Review)
        WHERE poi <> other_poi
        WITH user, poi, other_poi, n.distance_km AS distance, count(DISTINCT rated) AS num_reviews
        RETURN user.id AS user_id, poi.id AS poi_id, other_poi.id AS rec_poi_id, other_poi.name AS rec_poi_name, distance, num_reviews AS occurrences
        """),
        params = {'user_id': user_id, 'poi_id': poi_id}
    )
    # print(f"Tìm thấy {len(records_nearby)} records POI LÂN CẬN (< 1.5km).")
    
    
    # Convert kết quả sang DataFrame và gom nhóm tính trọng số (weight)
    if records_region:
        df_records_region = pd.DataFrame([dict(record) for record in records_region])
        # Group by 'poi_id', 'poi_name', and 'occurrences', then aggregate the count of occurrences
        df_records_region_agg = df_records_region.groupby(['user_id', 'poi_id', 'rec_poi_id', 'rec_poi_name', 'occurrences']).size().reset_index(name='weight_region')
        # print(f"[Khu vực] Rút gọn còn {len(df_records_region_agg)} records sau khi gom nhóm.")
    else:
        df_records_region_agg = pd.DataFrame(columns=['user_id', 'poi_id', 'rec_poi_id', 'rec_poi_name', 'occurrences', 'weight_region'])
        # print(f"[Khu vực] Không tìm thấy record nào.")

    if records_category:
        df_records_category = pd.DataFrame([dict(record) for record in records_category])
        # Group by 'poi_id', 'poi_name', and 'occurrences', then aggregate the count of occurrences
        df_records_category_agg = df_records_category.groupby(['user_id', 'poi_id', 'rec_poi_id', 'rec_poi_name', 'occurrences']).size().reset_index(name='weight_category')
        # print(f" [Danh mục] Rút gọn còn {len(df_records_category_agg)} records (tính trùng lặp thể loại).")
    else:
       df_records_category_agg = pd.DataFrame(columns=['user_id', 'poi_id', 'rec_poi_id', 'rec_poi_name', 'occurrences', 'weight_category'])
       print(f"[Danh mục] Không tìm thấy record nào.")
    if records_nearby:
        df_nearby = pd.DataFrame([dict(r) for r in records_nearby])
        df_nearby_agg = df_nearby.groupby(['user_id', 'poi_id', 'rec_poi_id', 'rec_poi_name', 'occurrences']).size().reset_index(name='weight_nearby')
    else:
        df_nearby_agg = pd.DataFrame(columns=['user_id', 'poi_id', 'rec_poi_id', 'rec_poi_name', 'occurrences', 'weight_nearby'])
    

    df_records_region_agg.rename(columns={'user_id': 'user_id_region', 'poi_id': 'poi_id_region', 'occurrences': 'occurrences_region'}, inplace=True)
    df_records_category_agg.rename(columns={'user_id': 'user_id_category', 'poi_id': 'poi_id_category', 'occurrences': 'occurrences_category'}, inplace=True)
    df_nearby_agg.rename(columns={'user_id': 'user_id_nearby', 'poi_id': 'poi_id_nearby', 'occurrences': 'occurrences_nearby'}, inplace=True)

    # Tính tần suất xuất hiện của POI trong cả hai danh sách
    # Gộp DataFrame dựa trên 'rec_poi_id'
    recommended_interactions = pd.merge(df_records_region_agg, df_records_category_agg, on=['rec_poi_id', 'rec_poi_name'], suffixes=('_region', '_category'), how='outer')
    recommended_interactions = pd.merge(recommended_interactions, df_nearby_agg, on=['rec_poi_id', 'rec_poi_name'], suffixes=('', '_nearby'), how='outer')
    # print(f"Gộp 3 danh sách (Outer Join): Tổng cộng có {len(recommended_interactions)} records.")

     # Điền giá trị fallback cho user_id, poi_id, occurrences
    recommended_interactions['user_id'] = recommended_interactions['user_id_region'].fillna(recommended_interactions['user_id_category']).fillna(recommended_interactions['user_id_nearby']).fillna(user_id)
    recommended_interactions['poi_id'] = recommended_interactions['poi_id_region'].fillna(recommended_interactions['poi_id_category']).fillna(recommended_interactions['poi_id_nearby']).fillna(poi_id)
    recommended_interactions['occurrences'] = recommended_interactions['occurrences_region'].fillna(recommended_interactions['occurrences_category']).fillna(recommended_interactions['occurrences_nearby']).fillna(0)

    # Điền các giá trị NaN bằng 0 cho các cột 'weight'
    recommended_interactions['weight_region'] = recommended_interactions['weight_region'].fillna(0)
    recommended_interactions['weight_category'] = recommended_interactions['weight_category'].fillna(0)
    recommended_interactions['weight_nearby'] = recommended_interactions['weight_nearby'].fillna(0)

    # print(f"Số record VỪA cùng [khu vực] VỪA cùng [danh mục]: {len(recommended_interactions)}")
    
    # Cộng các cột 'weight' để tính tổng trọng số
    recommended_interactions['total_weight'] = recommended_interactions['weight_region'] + recommended_interactions['weight_category'] + recommended_interactions['weight_nearby']

    # Loại bỏ các cột 'weight' riêng lẻ nếu cần
    recommended_interactions.drop(['user_id_category', 'user_id_nearby', 
                                    'poi_id_category', 'poi_id_nearby', 
                                    'occurrences_category', 'occurrences_nearby', 
                                    'weight_region', 'weight_category', 'weight_nearby'], axis=1, inplace=True, errors='ignore')
    # Sắp xếp DataFrame theo 'total_weight' giảm dần, sau đó theo 'occurrences'
    recommended_interactions = recommended_interactions.sort_values(by=['total_weight', 'occurrences'], ascending=[False, False])

    # Khởi tạo lại chỉ mục cho DataFrame
    recommended_interactions.reset_index(drop=True, inplace=True)
    # Sắp xếp lại các cột
    recommended_interactions = recommended_interactions[['user_id', 'poi_id', 'rec_poi_id', 'rec_poi_name']]
    # Loại bỏ trùng lặp
    recommended_interactions = recommended_interactions.drop_duplicates()

    # Hiển thị DataFrame đã gộp
    return recommended_interactions.head(k)


# Thuật toán 2: Gợi ý Lọc dựa trên nội dung - Độ tương đồng nút (Node Similarity)

# HÀM: Đưa ra gợi ý dựa trên Lọc dựa trên nội dung - Độ tương đồng nút
# ĐẦU VÀO: poi_id
# ĐẦU RA: dataframe[poi_id, rec_poi_id]

def similar_poi_recommendation(gds, poi_id, k=10):
    result = gds.run_cypher(
        """
            MATCH (p1:Poi {id: $target_poi})-[s:CBF_SIMILAR]->(p2:Poi)
            RETURN p1.id as poi_id, p2.id as rec_poi_id
            ORDER BY s.score DESC
        """, params = {'target_poi': poi_id}
    )
    result = result.drop_duplicates()
    return result.head(k)


# Thuật toán 3: Gợi ý Lọc cộng tác (Collaborative Filtering) - Dựa trên người dùng (User-Based)

# HÀM: Đưa ra gợi ý dựa trên Lọc cộng tác - kNN dựa trên người dùng với các vector nhúng FastRP
# ĐẦU VÀO: user_id
# ĐẦU RA: dataframe[user_id, rec_poi_id]

def userKNN_recommendation(gds, user_id):

    result = gds.run_cypher(
        """
            MATCH (u1:User {id: $target_user})-[s:CF_SIMILAR_USER]->(u2:User)-[:REVIEWED]->(p:Poi)
            WITH u1, p, s.score AS user_similarity
            RETURN u1.id as user_id, p.id as rec_poi_id
            ORDER BY user_similarity DESC, p.avgRating DESC
        """, params = {'target_user': user_id}
    )
    result = result.drop_duplicates()
    return result


# Thuật toán 4: Gợi ý Lọc cộng tác - kNN dựa trên sản phẩm (Item-Based)

# HÀM: Đưa ra gợi ý dựa trên Lọc cộng tác - kNN dựa trên sản phẩm với các vector nhúng FastRP
# ĐẦU VÀO: poi_id
# ĐẦU RA: dataframe[poi_id, rec_poi_id]

def itemKNN_recommendation(gds, poi_id):
    result = gds.run_cypher(
        """
            MATCH (p1:Poi {id: $target_poi})-[s:CF_SIMILAR_POI]->(p2:Poi)
            RETURN p1.id as poi_id, p2.id as rec_poi_id
            ORDER BY s.score DESC, p2.avgRating DESC
        """, params = {'target_poi': poi_id}
    )
    result = result.drop_duplicates()
    return result



# Hàm bổ trợ cho học kết hợp (ensemble learning)
# HÀM: Hỗ trợ làm sạch từng DataFrame sau khi gọi thuật toán gợi ý, chuẩn bị cho học kết hợp
def df_cleaning (df):
    if not df.empty:    # Đặt lại chỉ mục, lấy xếp hạng, và sắp xếp lại các cột
        df.reset_index(drop=True, inplace=True)          
        df = df.reset_index().rename(columns={'index': 'rank'})
        df['rank'] += 1
        df = df.reindex(columns=['user_id', 'poi_id', 'rec_poi_id', 'rank', 'df_name'])

    return df


# HÀM: Đưa ra gợi ý dựa trên Học kết hợp - Đa số biểu quyết (Majority Voting)
# ĐẦU VÀO: poi_id, user_id, algo_combination
# ĐẦU RA: dataframe[poi_id, user_id, rec_poi_id]

def ensemble_recommendation(gds, poi_id, user_id, algo_combination):

    # Dựa trên sự kết hợp các thuật toán đã chọn, quyết định có gọi từng hàm gợi ý hay không
    if 1 in algo_combination:  
        rec_CBF_heuristic = heuristic_recommendation(gds, poi_id)            # ĐẦU RA: dataframe[poi_id, rec_poi_id]
        rec_CBF_heuristic['df_name'] = 'rec_CBF_heuristic'              # Thêm tên DataFrame thành một cột
        rec_CBF_heuristic['user_id'] = user_id                          # Thêm cột còn thiếu
        rec_CBF_heuristic = df_cleaning (rec_CBF_heuristic)             # Làm sạch DataFrame cho học kết hợp
    else:
        rec_CBF_heuristic = pd.DataFrame()

    if 2 in algo_combination:
        rec_CBF_similarity = similar_poi_recommendation(gds, poi_id)         # ĐẦU RA: dataframe[poi_id, rec_poi_id]
        rec_CBF_similarity['df_name'] = 'rec_CBF_similarity'            # Thêm tên DataFrame thành một cột
        rec_CBF_similarity['user_id'] = user_id                         # Thêm cột còn thiếu
        rec_CBF_similarity = df_cleaning (rec_CBF_similarity)           # Làm sạch DataFrame cho học kết hợp
    else:
        rec_CBF_similarity = pd.DataFrame()

    if 3 in algo_combination:
        rec_CF_userKnn =  userKNN_recommendation(gds, user_id)               # ĐẦU RA: dataframe[user_id, rec_poi_id]
        rec_CF_userKnn['df_name'] = 'rec_CF_userKnn'                    # Thêm tên DataFrame thành một cột
        rec_CF_userKnn['poi_id'] = poi_id                               # Thêm cột còn thiếu
        rec_CF_userKnn = df_cleaning (rec_CF_userKnn)                   # Làm sạch DataFrame cho học kết hợp
    else:
        rec_CF_userKnn = pd.DataFrame()

    if 4 in algo_combination:
        rec_CF_itemKnn = itemKNN_recommendation(gds, poi_id)                 # ĐẦU RA: dataframe[poi_id, rec_poi_id]
        rec_CF_itemKnn['df_name'] = 'rec_CF_itemKnn'                    # Thêm tên DataFrame thành một cột
        rec_CF_itemKnn['user_id'] = user_id                             # Thêm cột còn thiếu
        rec_CF_itemKnn = df_cleaning (rec_CF_itemKnn)                   # Làm sạch DataFrame cho học kết hợp
    else:
        rec_CF_itemKnn = pd.DataFrame()
    
    # Ghép nối các DataFrame theo các hàng
    merged_df = pd.concat([rec_CF_itemKnn, rec_CF_userKnn, rec_CBF_similarity, rec_CBF_heuristic])
    #print(f'merged_df: \n{merged_df}')

    # Kiểm tra nếu DataFrame đã gộp không trống
    if not merged_df.empty:
        # Nhóm theo user_id, poi_id, rec_poi_id và tính toán thứ hạng trung bình và số lượng
        grouped_df = merged_df.groupby(['user_id', 'poi_id', 'rec_poi_id']).agg({'rank': 'mean', 'df_name': 'count'}).reset_index()

        # Đổi tên cột đếm thành count
        grouped_df.rename(columns={'df_name': 'count'}, inplace=True)
        if not grouped_df[grouped_df['count'] > 1].empty:
            # Loại bỏ bất kỳ mục nào có số lượng bằng 1
            grouped_df = grouped_df[grouped_df['count'] > 1]

            # Sắp xếp theo số lượng (count) giảm dần và thứ hạng trung bình (rank) tăng dần
            sorted_df = grouped_df.sort_values(by=['count', 'rank'], ascending=[False, True])
            #print(f'sorted_df: \n{sorted_df}')
        else:
            # Nếu không có POI nào trùng nhau, lấy xếp hạng theo rank trung bình
            sorted_df = grouped_df.sort_values(by=['rank'], ascending=True)

        # Loại bỏ các cột 'count' và 'rank'
        result = sorted_df.drop(columns=['count', 'rank'], errors='ignore')
        #result = sorted_df.copy()
        result.reset_index(drop=True, inplace=True)
    else:
        result = merged_df.drop(columns=['df_name'])

    return result


# HÀM: Tìm các POI mà người dùng đã đánh giá
def reviewed_poi(gds, user_id):
    df_reviewed_poi = gds.run_cypher("""
        MATCH (user:User {id: $user_id})-[:REVIEWED]->(poi:Poi)
        RETURN poi.id AS reviewed_poi_id
        """, params = {'user_id': user_id})
    # Trích xuất các ID của POI đã đánh giá từ DataFrame
    reviewed_poi_ids = df_reviewed_poi['reviewed_poi_id'].tolist()
    return reviewed_poi_ids

'''
# HÀM: Lấy danh sách gợi ý (Hàm cũ để tham khảo)
def recommend(gds, poi_id=0, user_id=0):

    # Nếu có ID người dùng, tìm các POI người dùng đã đánh giá, loại trừ chúng khỏi kết quả
    reviewed = reviewed_poi(gds, user_id) if user_id else []

    # Khi có cả user_id và poi_id, sử dụng mô hình học kết hợp ensemble 1234
    if poi_id and user_id:

        # Sự kết hợp các thuật toán cho học kết hợp
        algo_combination = [1,2,3,4]

        #(1) Lọc dựa trên nội dung - Phỏng đoán            #heuristic_recommendation(poi_id)
        #(2) Lọc dựa trên nội dung - Độ tương đồng nút      #similar_poi_recommendation(poi_id)
        #(3) Lọc cộng tác - UserKnn với FastRP            #userKNN_recommendation(user_id)
        #(4) Lọc cộng tác - ItemKnn với FastRP            #itemKNN_recommendation(poi_id)

        result = ensemble_recommendation(gds, poi_id, user_id, algo_combination)['rec_poi_id'].tolist()  # mô hình kết hợp (ensemble)
        #result = ensemble_recommendation(gds, poi_id, user_id, algo_combination)  # mô hình kết hợp (ensemble)
        # Loại bỏ các POI người dùng đã đánh giá
        #result = result[~result['rec_poi_id'].isin(reviewed)]
        result = list(filter(lambda x: x not in reviewed, result))

        # PHƯƠNG ÁN DỰ PHÒNG
        # Nếu kết quả trống, lần lượt sử dụng thuật toán 3, thuật toán 2, thuật toán 4, thuật toán 1
        if len(result)==0:
            result = userKNN_recommendation(gds, user_id)['rec_poi_id'].tolist()                 # thuật toán 3
            # Loại bỏ các POI người dùng đã đánh giá
            result = list(filter(lambda x: x not in reviewed, result))

            if len(result)==0:
                result = similar_poi_recommendation(gds, poi_id)['rec_poi_id'].tolist()          # thuật toán 2

                if len(result)==0:
                    result = itemKNN_recommendation(gds, poi_id)['rec_poi_id'].tolist()          # thuật toán 4

                    if len(result)==0:
                        result = heuristic_recommendation(gds, poi_id)['rec_poi_id'].tolist()    # thuật toán 1

        
    # Khi chỉ có user_id, sử dụng thuật toán 3, là thuật toán duy nhất khả dụng trong trường hợp này
    elif user_id and (poi_id == 0):
        
        result = userKNN_recommendation(gds, user_id)['rec_poi_id'].tolist()     # thuật toán 3
        # Loại bỏ các POI người dùng đã đánh giá
        result = list(filter(lambda x: x not in reviewed, result))
    
    # Khi chỉ có poi_id, sử dụng thuật toán 2
    elif poi_id and (user_id == 0):

        result = similar_poi_recommendation(gds, poi_id)['rec_poi_id'].tolist()  # thuật toán 2

        # Nếu kết quả thuật toán 2 trống, sử dụng thuật toán 4, thuật toán 1
        if len(result)==0:
            result = itemKNN_recommendation(gds, poi_id)['rec_poi_id'].tolist()  # thuật toán 4

            if len(result)==0:
                result = heuristic_recommendation(gds, poi_id)['rec_poi_id'].tolist()    # thuật toán 1
    
    # Ngược lại trả về danh sách trống
    else:
        result = []
        print("Không có gợi ý nào.")

    # Lấy tên và ID của POI
    df_result = gds.run_cypher(
    """
    MATCH (p:Poi)
    WHERE p.id IN $poi_ids
    RETURN p.id AS id, p.name AS name
    """,
    params={'poi_ids': result})
    list_result = df_result.to_dict(orient='records')

    # Trả về danh sách gồm ID và tên các POI được gợi ý
    return list_result
'''


# HÀM: Từ danh sách các ID của POI, lấy tên POI, lưu thông tin POI {id, name} vào một danh sách
def get_poi_name(gds, poi_ids):
    # Lấy tên và ID của POI
    df_result = gds.run_cypher(
    """
    MATCH (p:Poi)
    WHERE p.id IN $poi_ids
    RETURN p.id AS id, p.name AS name
    """,
    params={'poi_ids': poi_ids})
    result_list = df_result.to_dict(orient='records')
    print(f"Gợi ý POI: {result_list}")

    return result_list

# HÀM: Lấy danh sách các POI lân cận
def get_nearby_pois(driver, poi_id, k=5):
    """Lấy danh sách các POI lân cận (trong bán kính 1.5km) kèm khoảng cách"""
    with driver.session() as session:
        result = session.run("""
            MATCH (p1:Poi {id: $poi_id})-[n:NEARBY]->(p2:Poi)
            OPTIONAL MATCH (p2)-[:BELONGS_TO]->(c:Category)
            RETURN p2.id AS id, p2.name AS name, p2.avgRating AS avgRating, 
                   p2.numReviews AS numReviews, c.name AS category_name, n.distance_km AS distance_km
            ORDER BY n.distance_km ASC
            LIMIT $k
        """, poi_id=poi_id, k=k)
        return [dict(r) for r in result]


# HÀM: Lấy danh sách gợi ý các POI ID
def get_rec_poi_id(gds, poi_id=0, user_id=0, n=10):

    # Nếu có ID người dùng, tìm các POI người dùng đã đánh giá, loại trừ chúng khỏi kết quả
    reviewed = reviewed_poi(gds, user_id) if user_id else []
    print(f'Các POI đã được người dùng đánh giá: {reviewed}')

    # Khởi tạo danh sách kết quả
    result = []

    # Chỉ khi cả poi_id và user_id đều tồn tại, lấy gợi ý từ mô hình học kết hợp (ensemble) với thuật toán 1234
    if poi_id and user_id:

        try:
            algo_combination = [1,2,3,4]
            #(1) Lọc dựa trên nội dung - Phỏng đoán            #heuristic_recommendation(poi_id)
            #(2) Lọc dựa trên nội dung - Độ tương đồng nút      #similar_poi_recommendation(poi_id)
            #(3) Lọc cộng tác - UserKnn với FastRP            #userKNN_recommendation(user_id)
            #(4) Lọc cộng tác - ItemKnn với FastRP            #itemKNN_recommendation(poi_id)

            result_ensemble = ensemble_recommendation(gds, poi_id, user_id, algo_combination)['rec_poi_id'].tolist()  # mô hình kết hợp (ensemble)

            # Loại bỏ các mục cũng xuất hiện trong danh sách đã đánh giá
            result_ensemble = list(filter(lambda x: x not in reviewed, result_ensemble))

            # Thêm vào kết quả, kiểm tra tính duy nhất của mục
            for item in result_ensemble:
                if item not in result:
                    result.append(item)
            
            print(f'Kết quả gợi ý từ mô hình kết hợp (Ensemble 1234): {result_ensemble}')
        except: # Khi một trong các tham số không khả dụng
            #result_ensemble = []  # Đặt kết quả thành danh sách trống
            print(f'Không thể áp dụng mô hình học kết hợp (Ensemble).')

        # Nếu đã có nhiều hơn hoặc bằng n kết quả, trả về n kết quả đầu tiên để bỏ qua tính toán cho các thuật toán khác
        if len(result) >= n:
            return result[:n]   

    # Chỉ khi user_id tồn tại, lấy gợi ý từ thuật toán 3 (UserKNN)
    if user_id:

        try:
            result_algo3 = userKNN_recommendation(gds, user_id)['rec_poi_id'].tolist()

            # Loại bỏ các mục cũng xuất hiện trong danh sách đã đánh giá
            result_algo3 = list(filter(lambda x: x not in reviewed, result_algo3))

            # Thêm vào kết quả, kiểm tra tính duy nhất của mục
            for item in result_algo3:
                if item not in result:
                    result.append(item)

            print(f'Kết quả gợi ý từ thuật toán 3 (UserKNN): {result_algo3}')
        except:
            #result_algo3 = []
            print(f'Thuật toán 3 không khả dụng.')

        
        # Kiểm tra điều kiện trả về
        if len(result) >= n:
            return result[:n]

    # Chỉ khi poi_id tồn tại, lấy gợi ý từ thuật toán 2 (CBF Similarity)
    if poi_id:

        try:
            result_algo2 = similar_poi_recommendation(gds, poi_id)['rec_poi_id'].tolist()

            # Loại bỏ các mục cũng xuất hiện trong danh sách đã đánh giá
            result_algo2 = list(filter(lambda x: x not in reviewed, result_algo2))

            # Thêm vào kết quả, kiểm tra tính duy nhất của mục
            for item in result_algo2:
                if item not in result:
                    result.append(item)
                
            print(f'Kết quả gợi ý từ thuật toán 2 (CBF Similarity): {result_algo2}')
        except:
            #result_algo2 = []
            print(f'Thuật toán 2 không khả dụng.')

        # Kiểm tra điều kiện trả về
        if len(result) >= n:
            return result[:n]

    # Chỉ khi poi_id tồn tại, lấy gợi ý từ thuật toán 4 (ItemKNN)
    if poi_id:

        try:
            result_algo4 = itemKNN_recommendation(gds, poi_id)['rec_poi_id'].tolist()

            # Loại bỏ các mục cũng xuất hiện trong danh sách đã đánh giá
            result_algo4 = list(filter(lambda x: x not in reviewed, result_algo4))

            # Thêm vào kết quả, kiểm tra tính duy nhất của mục
            for item in result_algo4:
                if item not in result:
                    result.append(item)
            
            print(f'Kết quả gợi ý từ thuật toán 4 (ItemKNN): {result_algo4}')
        except:
            # result_algo4 = []
            print(f'Thuật toán 4 không khả dụng.')
    
        # Kiểm tra điều kiện trả về
        if len(result) >= n:
            return result[:n]
        
    # Chỉ khi poi_id tồn tại, lấy gợi ý từ thuật toán 1 (CBF Heuristic)
    if poi_id:

        try:
            result_algo1 = heuristic_recommendation(gds, poi_id)['rec_poi_id'].tolist()

            # Loại bỏ các mục cũng xuất hiện trong danh sách đã đánh giá
            result_algo1 = list(filter(lambda x: x not in reviewed, result_algo1))

            # Thêm vào kết quả, kiểm tra tính duy nhất của mục
            for item in result_algo1:
                if item not in result:
                    result.append(item)
            
            print(f'Kết quả gợi ý từ thuật toán 1 (CBF Heuristic): {result_algo1}')
        except:
            #result_algo1 = []
            print(f'Thuật toán 1 không khả dụng.')

    # Trả về n kết quả đầu tiên
    return result[:n]
    

# HÀM: Lấy gợi ý POI bao gồm cả ID và tên
def recommend(gds, poi_id=0, user_id=0):

    # Lấy danh sách ID của POI được gợi ý, với tối đa n=10 kết quả
    rec_poi_ids = get_rec_poi_id(gds, poi_id, user_id, n=10)

    # Lấy tên và ID của POI dưới dạng danh sách
    poi_id_name = get_poi_name(gds, rec_poi_ids)

    # Trả về một danh sách gồm ID và tên các POI được gợi ý
    return poi_id_name


# Điểm khởi chạy (entry point)
if __name__ == '__main__':

    # Kết nối Neo4j

    # Lấy thông tin xác thực để kết nối Neo4j
    HOST, USERNAME, DATABASE, PASSWORD = get_credential()

    # Tạo driver Python cho Neo4j
    driver = GraphDatabase.driver(HOST, auth=(USERNAME, PASSWORD))

    # Kết nối sử dụng thư viện GDS
    gds = GraphDataScience(HOST, auth=(USERNAME, PASSWORD))
    gds.set_database(DATABASE)

    # Kiểm thử (testing)

    # ID người dùng mục tiêu
    user_id = 1322 # Đã đánh giá: 34 POI, gợi ý từ UserKNN: [1888873, 317421, 317473, 678639, 2138910]
    user_id = 433  # Đã đánh giá: 5 POI [1888873, 1888876, 4400781, 310900, 2149128], gợi ý từ UserKNN: [8016698, 317415]
    user_id = 6 # Đã đánh giá: 1 POI, gợi ý từ UserKNN: []
    #user_id = 0 # mô phỏng khi user_id không tồn tại

    # ID của POI mục tiêu
    poi_id = 4552853
    # poi_id = 0 # mô phỏng khi poi_id không tồn tại

    # Đưa ra gợi ý
    print(recommend(gds, poi_id=poi_id, user_id=user_id))