# Nạp các thư viện cần thiết

from neo4j import GraphDatabase
import textwrap

from neo4j_tools import run
from neo4j_tools import get_credential

def get_file_url(filename):
    return f"file:///{filename}"

url_node_category = get_file_url('df_node_category.csv')
url_node_origin = get_file_url('df_node_origin.csv')
url_node_poi = get_file_url('df_node_poi.csv')
url_node_region = get_file_url('df_node_region.csv')
url_node_review_1 = get_file_url('df_node_review_1.csv')
url_node_review_2 = get_file_url('df_node_review_2.csv')
url_node_user = get_file_url('df_node_user.csv')
url_poi_belongsto_category = get_file_url('df_poi_belongsto_category.csv')
url_poi_locatedat_region = get_file_url('df_poi_locatedat_region.csv')
url_user_from_origin = get_file_url('df_user_from_origin.csv')
url_user_reviewed_poi = get_file_url('df_user_reviewed_poi.csv')

# Ontology địa chỉ mới bổ sung từ thực nghiệm
url_node_district = get_file_url('df_node_district.csv')
url_node_ward = get_file_url('df_node_ward.csv')
url_poi_locatedin_ward = get_file_url('df_poi_locatedin_ward.csv')
url_ward_mergedto_ward = get_file_url('df_ward_mergedto_ward.csv')


# Định nghĩa các hàm


# HÀM: thiết lập ràng buộc khóa chính trong cơ sở dữ liệu đồ thị
def set_constrain(driver):

    run(driver,'CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (user:User) REQUIRE user.id IS UNIQUE')
    run(driver,'CREATE CONSTRAINT origin_id_unique IF NOT EXISTS FOR (origin:Origin) REQUIRE origin.id IS UNIQUE')
    run(driver,'CREATE CONSTRAINT poi_id_unique IF NOT EXISTS FOR (poi:Poi) REQUIRE poi.id IS UNIQUE')
    run(driver,'CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (category:Category) REQUIRE category.id IS UNIQUE')
    run(driver,'CREATE CONSTRAINT region_id_unique IF NOT EXISTS FOR (region:Region) REQUIRE region.id IS UNIQUE')
    run(driver,'CREATE CONSTRAINT review_id_unique IF NOT EXISTS FOR (review:Review) REQUIRE review.id IS UNIQUE')
    
    # Ràng buộc mới bổ sung từ thực nghiệm
    run(driver,'CREATE CONSTRAINT ward_code_unique IF NOT EXISTS FOR (w:Ward) REQUIRE w.code IS UNIQUE')
    run(driver,'CREATE CONSTRAINT district_id_unique IF NOT EXISTS FOR (d:District) REQUIRE d.id IS UNIQUE')
    run(driver,'CREATE CONSTRAINT district_name_unique IF NOT EXISTS FOR (d:District) REQUIRE d.name IS UNIQUE')
    return


# HÀM: nạp các nút (nodes)
def nodes_loader(driver):

    # Tải tệp df_node_category
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE(category:Category {id: toInteger(row.id), name: row.name})
        RETURN count(category)
        """),
        params = {'file': url_node_category}
    )

    # Tải tệp df_node_origin
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE(origin:Origin {id: toInteger(row.id), name: row.name})
        RETURN count(origin)
        """),
        params = {'file': url_node_origin}
    )

    # Tải tệp df_node_poi
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE (poi:Poi {id: toInteger(row.id)})
        ON CREATE SET
            poi.name = coalesce(row.name, ''),
            poi.description = coalesce(row.description, ''),
            poi.url = coalesce(row.url, ''),
            poi.openingHours = coalesce(row.openingHours, ''),
            poi.duration = coalesce(row.duration, ''),
            poi.price = toFloat(coalesce(row.price, '0.0')),
            poi.address = coalesce(row.address, ''),
            poi.avgRating = toFloat(coalesce(row.avgRating, '0.0')),
            poi.numReviews = toInteger(coalesce(row.numReviews, '0')),
            poi.numReviews_5 = toInteger(coalesce(row.numReviews_5, '0')),
            poi.numReviews_4 = toInteger(coalesce(row.numReviews_4, '0')),
            poi.numReviews_3 = toInteger(coalesce(row.numReviews_3, '0')),
            poi.numReviews_2 = toInteger(coalesce(row.numReviews_2, '0')),
            poi.numReviews_1 = toInteger(coalesce(row.numReviews_1, '0'))
        RETURN count(poi)
        """),
        params = {'file': url_node_poi}
    )

    # Tải tệp df_node_region
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE(region:Region {id: toInteger(row.id), name: row.name})
        RETURN count(region)
        """),
        params = {'file': url_node_region}
    )

    # Tải tệp df_node_review_1
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE (review:Review {id: toInteger(row.id)})
        ON CREATE SET
            review.title = coalesce(row.title, ''),
            review.date = case when coalesce(row.date, '') = '' then null else date(row.date) end,
                    review.rating = toFloat(coalesce(row.rating, '0.0')),
                    review.content = coalesce(row.content, '')
        RETURN count(review)
        """),
        params = {'file': url_node_review_1}
    )

    # Tải tệp df_node_review_2
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE (review:Review {id: toInteger(row.id)})
        ON CREATE SET
            review.title = coalesce(row.title, ''),
            review.date = case when coalesce(row.date, '') = '' then null else date(row.date) end,
                    review.rating = toFloat(coalesce(row.rating, '0.0')),
                    review.content = coalesce(row.content, '')
        RETURN count(review)
        """),
        params = {'file': url_node_review_2}
    )

    # Tải tệp df_node_user
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE(user:User {id: toInteger(row.id), name: row.name})
        RETURN count(user)
        """),
        params = {'file': url_node_user}
    )

    # Tải tệp df_node_district
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE(district:District {id: toInteger(row.id)})
        ON CREATE SET district.name = row.name
        RETURN count(district)
        """),
        params = {'file': url_node_district}
    )

    # Tải tệp df_node_ward
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MERGE (ward:Ward {code: row.ward_code})
        ON CREATE SET
            ward.name = row.name,
            ward.province_code = row.province_code
        WITH ward, row
        WHERE row.district_id IS NOT NULL
        MATCH (district:District {id: toInteger(row.district_id)})
        MERGE (ward)-[r:BELONGS_TO]->(district)
        RETURN count(ward)
        """),
        params = {'file': url_node_ward}
    )

    return


# HÀM: nạp các mối quan hệ (relationships)
def relationships_loader(driver):
    # Tải mối quan hệ df_poi_belongsto_category (Điểm du lịch thuộc danh mục nào)
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MATCH (poi:Poi {id: toInteger(row.poi_id)})
        MATCH (category:Category {id: toInteger(row.category_id)})
        MERGE (poi)-[r:BELONGS_TO]->(category)
        RETURN count(r) AS BELONGS_TO_count
        """),
        params = {'file': url_poi_belongsto_category}
    )

    # Tải mối quan hệ df_poi_locatedat_region (Điểm du lịch nằm ở khu vực nào)
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MATCH (poi:Poi {id: toInteger(row.poi_id)})
        MATCH (region:Region {id: toInteger(row.region_id)})
        MERGE (poi)-[r:LOCATED_AT]->(region)
        RETURN count(r) AS LOCATED_AT_count
        """),
        params = {'file': url_poi_locatedat_region}
    )

    # Tải mối quan hệ df_user_from_origin (Người dùng đến từ quốc gia/vùng lãnh thổ nào)
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MATCH (user:User {id: toInteger(row.user_id)})
        MATCH (origin:Origin {id: toInteger(row.origin_id)})
        MERGE (user)-[r:FROM]->(origin)
        RETURN count(r) AS FROM_count
        """),
        params = {'file': url_user_from_origin}
    )

    # Tải mối quan hệ df_poi_locatedin_ward (Điểm du lịch nằm ở phường/xã nào)
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MATCH (poi:Poi {id: toInteger(row.poi_id)})
        MATCH (ward:Ward {code: row.ward_code})
        MERGE (poi)-[r:LOCATED_IN]->(ward)
        RETURN count(r) AS LOCATED_IN_count
        """),
        params = {'file': url_poi_locatedin_ward}
    )

    # Tải mối quan hệ df_ward_mergedto_ward (Phường/xã sáp nhập vào phường/xã nào)
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        MATCH (old_w:Ward {code: row.old_ward_code})
        MATCH (new_w:Ward {code: row.new_ward_code})
        MERGE (old_w)-[r:MERGED_TO]->(new_w)
        RETURN count(r) AS MERGED_TO_count
        """),
        params = {'file': url_ward_mergedto_ward}
    )

    # Tải mối quan hệ df_user_reviewed_poi (Người dùng đánh giá điểm du lịch)
    run(driver, textwrap.dedent("""\
        LOAD CSV WITH HEADERS FROM $file AS row
        CALL{
            WITH row
            MATCH (user:User {id: toInteger(row.user_id)})
            MATCH (review:Review {id: toInteger(row.review_id)})
            MATCH (poi:Poi {id: toInteger(row.poi_id)})
            MERGE (user)-[w:WROTE]->(review)
            MERGE (review)-[rated:RATED]->(poi)
            MERGE (user)-[reviewed:REVIEWED ]->(poi)
            ON CREATE SET reviewed.rating = review.rating
            RETURN count(w) AS WROTE_count, count(rated) AS RATED_count, count(reviewed) AS REVIEWED_count
        } IN TRANSACTIONS
        RETURN SUM(WROTE_count) AS total_WROTE_count, SUM(RATED_count) AS total_RATED_count, SUM(REVIEWED_count) AS total_REVIEWED_count
        """),
        params = {'file': url_user_reviewed_poi}
    )

    return


# HÀM: nạp dữ liệu vào cơ sở dữ liệu Neo4j
def data_loading(driver):

    # Lấy số lượng nút hiện tại trong cơ sở dữ liệu
    node_count = run(driver, "MATCH (n) RETURN count(n) AS count")[0][0]  #[<Record count=0>]
    #<class 'list'>, <class 'neo4j._data.Record'>, <class 'int'>

    # Kiểm tra xem cơ sở dữ liệu có trống không trước khi tải
    if  node_count == 0:

        # Tạo ràng buộc cho khóa chính
        print("Đang thiết lập các ràng buộc...")
        set_constrain(driver)
        print("Đã hoàn thành thiết lập các ràng buộc.")

        # Tải các nút vào cơ sở dữ liệu Neo4j
        print("Đang tải các nút (nodes)...")
        nodes_loader(driver)
        print("Đã tải xong các nút.")

        # Tải các mối quan hệ vào cơ sở dữ liệu Neo4j
        print("Đang tải các mối quan hệ (relationships)...")
        relationships_loader(driver)
        print("Đã tải xong các mối quan hệ.")
    
    else:
        print("Cơ sở dữ liệu đã có sẵn dữ liệu.")

    return
    
# Điểm khởi chạy (entry point)
if __name__ == '__main__':

    # Kết nối Neo4j

    # Lấy thông tin xác thực để kết nối Neo4j
    HOST, USERNAME, DATABASE, PASSWORD = get_credential()

    # Tạo driver Python cho Neo4j
    driver = GraphDatabase.driver(HOST, auth=(USERNAME, PASSWORD))

    data_loading(driver)

    # Đóng kết nối driver
    driver.close()