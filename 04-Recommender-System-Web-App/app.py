from flask import Flask, render_template, request, session, redirect, url_for, jsonify, Response, stream_with_context, json

from neo4j import GraphDatabase
from graphdatascience import GraphDataScience

# Các mô-đun tự định nghĩa
from neo4j_tools import get_credential
import recommender
import data_loader
import pre_training
from rag_agent import GraphRAGAgent, format_vietnamese_opening_hours

# Khởi tạo Graph RAG Agent
rag_agent = GraphRAGAgent()


# Kết nối tới Neo4j

# Lấy thông tin đăng nhập để kết nối Neo4j
HOST, USERNAME, DATABASE, PASSWORD = get_credential()

# Tạo driver Python cho Neo4j
driver = GraphDatabase.driver(HOST, auth=(USERNAME, PASSWORD))

# Kết nối sử dụng thư viện GDS (Graph Data Science)
gds = GraphDataScience(HOST, auth=(USERNAME, PASSWORD))
gds.set_database(DATABASE)

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# Khóa bí mật phục vụ quản lý session
app.secret_key = 'secret'

# Đăng ký filter Jinja2 chuyển đổi giờ mở cửa
app.jinja_env.filters['format_opening_hours'] = format_vietnamese_opening_hours


REGION_PRIORITY = [
    "Quận 1",
    "Thành phố Thủ Đức",
    "Quận 3",
    "Quận 7",
    "Quận 10",
    "Quận 4",
    "Quận 5",
    "Quận Bình Thạnh",
    "Quận Phú Nhuận",
    "Quận Tân Phú",
    "Quận 11",
    "Quận 12",
    "Quận Tân Bình",
    "Quận 8",
    "Quận 6",
    "Quận Gò Vấp",
    "Huyện Củ Chi",
    "Huyện Bình Chánh",
    "Quận Bình Tân",
    "Huyện Nhà Bè",
    "Huyện Hóc Môn",
    "Thành phố Hồ Chí Minh"
]


# Route Trang chủ
@app.route('/')
def index():
    import re
    uuid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-')

    # Kiểm tra xem 'user_id' có tồn tại trong session không, lấy user id
    user_id = session.get('user_id')
    if user_id:
        rec_pois = recommender.recommend(gds=gds, user_id=user_id)
    else:
        rec_pois = []

    # Lấy dữ liệu từ cơ sở dữ liệu
    with driver.session(database=DATABASE) as neo4j_session:
        # Top 7 POI phổ biến nhất hiển thị ở Sidebar bên phải
        popular_records = neo4j_session.run("MATCH (poi:Poi) RETURN poi ORDER BY poi.numReviews DESC LIMIT 7")
        popular_pois = [rec['poi'] for rec in popular_records]
        popular_ids = set(p['id'] for p in popular_pois)

        # Lấy vị trí / khu vực của người dùng nếu đã đăng nhập
        user_regions = []
        if user_id:
            # 1. Khu vực xuất xứ (Origin) của User
            origin_res = neo4j_session.run("MATCH (u:User{id: $user_id})-[:FROM]->(o:Origin) RETURN o.name AS origin_name", user_id=user_id).single()
            if origin_res and origin_res['origin_name']:
                user_regions.append(origin_res['origin_name'])
            
            # 2. Các khu vực POI người dùng đã từng đánh giá
            interacted_res = neo4j_session.run(
                "MATCH (u:User{id: $user_id})-[:WROTE]->(:Review)-[:RATED]->(p:Poi)-[:LOCATED_AT]->(r:Region) RETURN r.name AS rname, count(p) as cnt ORDER BY cnt DESC",
                user_id=user_id
            )
            for r in interacted_res:
                if r['rname'] and r['rname'] not in user_regions:
                    user_regions.append(r['rname'])

        # Lấy tất cả các nút POI kèm theo thuộc tính khu vực (Region)
        records = neo4j_session.run("""
            MATCH (poi:Poi)
            OPTIONAL MATCH (poi)-[:LOCATED_AT]->(r:Region)
            RETURN poi, r.name AS region_name
            ORDER BY poi.numReviews DESC
        """)

        clean_pois = []
        for rec in records:
            p = rec['poi']
            r_name = rec['region_name'] or 'Thành phố Hồ Chí Minh'
            name = str(p.get('name', '')).strip()
            if not name or uuid_pattern.match(name) or name.startswith('#'):
                continue
            poi_dict = dict(p)
            poi_dict['region_name'] = r_name
            poi_dict['rating'] = float(p.get('avgRating') or 0.0)
            clean_pois.append(poi_dict)

        # Hàm xác định ưu tiên hiển thị POI
        def get_sort_key(p):
            r_name = p['region_name']
            
            # Nếu người dùng đã đăng nhập: ưu tiên các POI thuộc vị trí/khu vực của người dùng
            if user_regions:
                matched_user_idx = None
                for idx, ur in enumerate(user_regions):
                    if r_name in ur or ur in r_name:
                        matched_user_idx = idx
                        break
                if matched_user_idx is not None:
                    return (0, matched_user_idx, -(p.get('numReviews', 0) or 0))
            
            # Nếu chưa đăng nhập (hoặc POI ngoài khu vực người dùng): ưu tiên theo thứ tự bảng phân bố khu vực
            region_idx = REGION_PRIORITY.index(r_name) if r_name in REGION_PRIORITY else 999
            return (1, region_idx, -(p.get('numReviews', 0) or 0))

        # Sắp xếp danh sách POI và loại trừ 7 POI ở sidebar để tránh trùng lặp
        pois_sorted = [p for p in sorted(clean_pois, key=get_sort_key) if p['id'] not in popular_ids]

    return render_template('index.html', pois=pois_sorted, rec_pois=rec_pois, popular_pois=popular_pois)


# Route Chi tiết POI (Điểm du lịch)
@app.route('/poi/<poi_id>')
def poi(poi_id):

    # Kiểm tra xem 'user_id' có tồn tại trong session không, lấy user id
    if 'user_id' in session:
        user_id = session['user_id']
    else:
        user_id = 0

    # Chuyển đổi chuỗi thành số nguyên
    poi_id = int(poi_id)

    # Lấy danh sách gợi ý
    rec_pois = recommender.recommend(gds=gds, poi_id=poi_id, user_id=user_id)

    # Lấy danh sách địa điểm lân cận (< 1.5km)
    nearby_pois = recommender.get_nearby_pois(driver, poi_id, k=5)

    # Lấy dữ liệu từ cơ sở dữ liệu
    with driver.session(database=DATABASE) as neo4j_session:
        # Lấy thông tin nút POI mục tiêu từ Neo4j
        pois = neo4j_session.run('''
                MATCH (poi:Poi{id: $target_poi}) 
                RETURN poi
                ''', target_poi=poi_id)
        poi = pois.single()['poi']   #<class 'neo4j.graph.Node'>

        # Lấy danh sách các đánh giá (reviews) của POI từ Neo4j
        review_records = neo4j_session.run('''
                MATCH (u:User)-[:WROTE]->(r:Review)-[:RATED]->(p:Poi{id: $target_poi})
                RETURN u.name AS user_name, r.rating AS rating, r.title AS title, r.content AS content, toString(r.date) AS date
                ORDER BY r.date DESC
                ''', target_poi=poi_id)
        reviews = [dict(record) for record in review_records]

    return render_template('poi.html', poi=poi, rec_pois=rec_pois, reviews=reviews, nearby_pois=nearby_pois)

@app.route('/poi/nearby/<poi_id>')
def poi_nearby(poi_id):
    if 'user_id' in session:
        user_id = session['user_id']
    else:
        user_id = 0

    poi_id = int(poi_id)

    # 1. Lấy danh sách gợi ý cơ bản
    rec_pois = recommender.recommend(gds=gds, poi_id=poi_id, user_id=user_id)

    # 2. Lấy danh sách POI lân cận (< 1.5km) để du khách đi bộ
    nearby_pois = recommender.get_nearby_pois(driver, poi_id, k=10)

    with driver.session(database=DATABASE) as neo4j_session:
        # Lấy thông tin POI hiện tại
        pois = neo4j_session.run("MATCH (poi:Poi{id: $target_poi}) RETURN poi", target_poi=poi_id)
        poi = pois.single()['poi']

        # Lấy danh sách đánh giá
        review_records = neo4j_session.run("""
            MATCH (u:User)-[:WROTE]->(r:Review)-[:RATED]->(p:Poi{id: $target_poi})
            RETURN u.name AS user_name, r.rating AS rating, r.title AS title, r.content AS content, toString(r.date) AS date
            ORDER BY r.date DESC LIMIT 100
        """, target_poi=poi_id)
        reviews = [dict(record) for record in review_records]

    return render_template('poi.html', poi=poi, rec_pois=rec_pois, reviews=reviews, nearby_pois=nearby_pois)


# Route Đăng nhập & Đăng ký
@app.route('/login', methods=['GET', 'POST'])
def login():
    mode = request.args.get('mode', 'login')

    # Lấy danh sách các khu vực / xuất xứ, ưu tiên các quận/huyện TP.HCM lên đầu
    origins = list(REGION_PRIORITY)
    try:
        with driver.session(database=DATABASE) as neo4j_session:
            res = neo4j_session.run("MATCH (o:Origin) RETURN DISTINCT o.name AS name ORDER BY name")
            for rec in res:
                name = rec['name']
                if name and name not in origins:
                    origins.append(name)
    except Exception:
        pass

    if request.method == 'POST':
        action = request.form.get('action', 'login')

        if action == 'register':
            username = request.form.get('username', '').strip()
            fullname = request.form.get('fullname', '').strip()
            origin_name = request.form.get('origin', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            # Kiểm tra dữ liệu đầu vào
            if not username or not fullname or not origin_name or not password:
                return render_template('login.html', error_register='Vui lòng điền đầy đủ thông tin đăng ký', mode='register', origins=origins)

            if password != confirm_password:
                return render_template('login.html', error_register='Mật khẩu xác nhận không khớp', mode='register', origins=origins)

            # Lưu người dùng vào Neo4j DB
            try:
                with driver.session(database=DATABASE) as neo4j_session:
                    # Kiểm tra tên đăng nhập đã tồn tại chưa
                    existing = neo4j_session.run(
                        "MATCH (u:User) WHERE toLower(coalesce(u.username, u.name)) = toLower($username) RETURN u LIMIT 1",
                        username=username
                    ).single()

                    if existing:
                        return render_template('login.html', error_register='Tên đăng nhập đã tồn tại, vui lòng chọn tên khác', mode='register', origins=origins)

                    # Lấy ID lớn nhất của User hiện tại để tự động tăng ID
                    res = neo4j_session.run("MATCH (u:User) RETURN max(u.id) AS max_id").single()
                    max_id = res['max_id'] if res and res['max_id'] is not None else 10000
                    new_id = int(max_id) + 1

                    # Tạo nút User mới trong Neo4j
                    neo4j_session.run(
                        "CREATE (u:User {id: $id, name: $name, username: $username, password: $password})",
                        id=new_id, name=fullname, username=username, password=password
                    )

                    # Liên kết người dùng với khu vực xuất xứ (:User)-[:FROM]->(:Origin) để gợi ý vị trí
                    if origin_name:
                        neo4j_session.run("""
                            MERGE (o:Origin {name: $origin_name})
                            WITH o
                            MATCH (u:User {id: $id})
                            MERGE (u)-[:FROM]->(o)
                        """, origin_name=origin_name, id=new_id)

                    # Tự động đăng nhập sau khi đăng ký thành công
                    session['user_id'] = new_id
                    return redirect(url_for('index'))
            except Exception as e:
                return render_template('login.html', error_register=f'Lỗi hệ thống khi đăng ký: {str(e)}', mode='register', origins=origins)

        else:
            # Xử lý Đăng nhập
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()

            # 1. Kiểm tra các tài khoản mặc định thử nghiệm
            if username == 'user1' and password == 'user1':
                session['user_id'] = 174
                return redirect(url_for('index'))
            elif username == 'user2' and password == 'user2':
                session['user_id'] = 433 
                return redirect(url_for('index'))
            elif username == 'user3' and password == 'user3':
                session['user_id'] = 10 
                return redirect(url_for('index'))
            
            # 2. Kiểm tra tài khoản đã đăng ký trong cơ sở dữ liệu Neo4j
            try:
                with driver.session(database=DATABASE) as neo4j_session:
                    user_res = neo4j_session.run(
                        "MATCH (u:User) WHERE (toLower(coalesce(u.username, u.name)) = toLower($username)) AND u.password = $password RETURN u LIMIT 1",
                        username=username, password=password
                    ).single()
                    if user_res:
                        session['user_id'] = user_res['u']['id']
                        return redirect(url_for('index'))
            except Exception:
                pass

            return render_template('login.html', error='Tên đăng nhập hoặc mật khẩu không hợp lệ', mode='login', origins=origins)

    return render_template('login.html', mode=mode, origins=origins)


# Route Đăng ký (chuyển hướng tiện lợi)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return redirect(url_for('login', mode='register'))
    return login()


# Route Đăng xuất
# Quay lại trang hiện tại, hoặc quay lại trang chủ nếu trang hiện tại là trang cá nhân (user profile)
@app.route('/logout', methods=['POST'])
def logout():
    # Lấy URL của trang trước đó (trang gửi yêu cầu đăng xuất)
    referrer = request.referrer

    # Xóa khóa 'user_id' khỏi session
    session.pop('user_id', None)

    # Kiểm tra nếu trang trước đó là trang cá nhân user_profile
    if referrer and referrer.endswith('/user_profile'):
        return redirect(url_for('index'))  # Nếu là trang cá nhân, chuyển hướng về trang chủ
    else:
        return redirect(referrer or url_for('index'))  # Quay lại trang trước đó nếu khả dụng, ngược lại về trang chủ


# Route Trang cá nhân người dùng
@app.route('/user_profile')
def user_profile():

    # Kiểm tra xem 'user_id' có tồn tại trong session không
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Chuyển hướng về trang chủ nếu chưa đăng nhập

    # Lấy thông tin người dùng
    with driver.session(database=DATABASE) as neo4j_session:
                
        user_id = session['user_id']
        #print(f'user_id:{user_id}')

        user_node = neo4j_session.run("MATCH (user:User{id: $target_user}) RETURN user", target_user=user_id)
        user = user_node.single()['user']   #<class 'neo4j.graph.Node'>

        origin_node = neo4j_session.run("MATCH (user:User{id: $target_user})-[:FROM]->(origin:Origin) RETURN origin", target_user=user_id)
        origin_single = origin_node.single()
        origin = origin_single['origin'] if origin_single else None   #<class 'neo4j.graph.Node'>

        review_count = neo4j_session.run("MATCH (user:User{id: $target_user})-[:WROTE]->(review:Review) RETURN COUNT(review) AS review_count", target_user=user_id)
        review_count = review_count.single()['review_count']   #<class 'neo4j.graph.Node'>
        #print(review_count)

    return render_template('user_profile.html', user=user, origin=origin, review_count=review_count)


# API Chatbot Graph RAG
@app.route('/api/chat', methods=['POST'])
def api_chat():
    req_data = request.get_json() or {}
    message = req_data.get('message', '').strip()
    stream_requested = req_data.get('stream', True)
    llm_params = req_data.get('params', {})

    if not message:
        return jsonify({'reply': 'Xin chào! Bạn có thể đặt câu hỏi về các địa điểm du lịch TP.HCM.', 'pois': []})

    user_id = session.get('user_id')
    user_name = "Du khách"

    if user_id:
        with driver.session(database=DATABASE) as neo4j_session:
            u_node = neo4j_session.run("MATCH (u:User{id: $uid}) RETURN u.name AS uname", uid=user_id).single()
            if u_node and u_node['uname']:
                user_name = u_node['uname']

    if stream_requested:
        def generate():
            for event in rag_agent.chat_stream(
                neo4j_driver=driver,
                database=DATABASE,
                query_text=message,
                user_id=user_id,
                recommender=recommender,
                gds=gds,
                user_name=user_name,
                llm_params=llm_params
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    else:
        response_data = rag_agent.chat(
            neo4j_driver=driver,
            database=DATABASE,
            query_text=message,
            user_id=user_id,
            recommender=recommender,
            gds=gds,
            user_name=user_name
        )
        return jsonify(response_data)


if __name__ == '__main__':

    # Chuẩn bị dữ liệu
    # Khi cơ sở dữ liệu trống được khởi tạo lần đầu, sẽ mất khoảng 12 phút để tải dữ liệu và huấn luyện trước.
    data_loader.data_loading(driver)
    pre_training.pre_training(gds)

    # Chạy ứng dụng Flask
    app.run(debug=True)

