"""
Graph RAG Agent - Trợ lý Du lịch Thông minh TP.HCM
Kết hợp Đồ thị Tri thức (Neo4j Knowledge Graph) và Mô hình Ngôn ngữ Lớn Cục bộ (Local LLM)
Tích hợp Ontology sáp nhập địa chính (Phường/Xã/Quận HCM) & Suy luận Đồ thị (Graph Inference)
"""

import os
import re
import configparser
import unicodedata
from datetime import datetime
from threading import Thread

# Bộ nhớ đệm toàn cục cho mô hình Python Local LLM (Transformers)
_local_transformers_pipeline = None


def norm_str(txt):
    """Chuẩn hóa chuỗi tiếng Việt sang dạng Unicode NFC"""
    if not txt:
        return ""
    return unicodedata.normalize('NFC', str(txt))


def get_unicode_variants(kw):
    """Tạo cả 2 định dạng Unicode NFC và NFD để khớp chính xác trong Neo4j DB"""
    if not kw:
        return []
    nfc = unicodedata.normalize('NFC', str(kw)).lower()
    nfd = unicodedata.normalize('NFD', str(kw)).lower()
    return list(set([nfc, nfd]))


def format_vietnamese_opening_hours(hours_val):
    """Chuyển đổi toàn bộ chuỗi giờ mở cửa tiếng Anh sang Tiếng Việt chuẩn"""
    if not hours_val:
        return "Mở cửa hàng ngày (08:00 - 22:00)"

    if isinstance(hours_val, list):
        formatted_list = [format_vietnamese_opening_hours(h) for h in hours_val]
        return " | ".join(formatted_list)

    s = str(hours_val).strip()
    if not s or s.lower() in ["none", "null", "nan", ""]:
        return "Mở cửa hàng ngày (08:00 - 22:00)"

    # 1. Các trường hợp mở cửa 24/7 / đặc biệt
    s_lower = s.lower()
    if any(k in s_lower for k in ["always open", "open 24 hours", "24 hours", "24/7"]):
        return "Mở cửa 24/7"

    # 2. Quy tắc thay thế tiếng Anh -> Tiếng Việt
    day_map = [
        (r'\bTueseday\b', 'Thứ 3'),
        (r'\bWenesday\b', 'Thứ 4'),
        (r'\bMonday\b', 'Thứ 2'),
        (r'\bTuesday\b', 'Thứ 3'),
        (r'\bWednesday\b', 'Thứ 4'),
        (r'\bThursday\b', 'Thứ 5'),
        (r'\bFriday\b', 'Thứ 6'),
        (r'\bSaturday\b', 'Thứ 7'),
        (r'\bSunday\b', 'Chủ Nhật'),
        (r'\bMon\b', 'Thứ 2'),
        (r'\bTue\b', 'Thứ 3'),
        (r'\bWed\b', 'Thứ 4'),
        (r'\bThu\b', 'Thứ 5'),
        (r'\bFri\b', 'Thứ 6'),
        (r'\bSat\b', 'Thứ 7'),
        (r'\bSun\b', 'Chủ Nhật'),
        (r'\bMo-Su\b', 'Thứ 2 - Chủ Nhật'),
        (r'\bMo-Fr\b', 'Thứ 2 - Thứ 6'),
        (r'\bMo-Sa\b', 'Thứ 2 - Thứ 7'),
        (r'\bSa-Su\b', 'Thứ 7 & Chủ Nhật'),
        (r'\bTu-Su\b', 'Thứ 3 - Chủ Nhật'),
        (r'\bWe-Su\b', 'Thứ 4 - Chủ Nhật'),
        (r'\bTh-Su\b', 'Thứ 5 - Chủ Nhật'),
        (r'\bFr-Su\b', 'Thứ 6 - Chủ Nhật'),
        (r'\bMo\b', 'Thứ 2'),
        (r'\bTu\b', 'Thứ 3'),
        (r'\bWe\b', 'Thứ 4'),
        (r'\bTh\b', 'Thứ 5'),
        (r'\bFr\b', 'Thứ 6'),
        (r'\bSa\b', 'Thứ 7'),
        (r'\bSu\b', 'Chủ Nhật'),
        (r'\bfrom\b', 'từ'),
        (r'\bto\b', '-'),
        (r'\bthrough\b', '-'),
        (r'\btill\b', '-'),
        (r'\buntil\b', '-'),
        (r'\band\b', '&'),
    ]

    for pattern, replacement in day_map:
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)

    s = re.sub(r'\s+', ' ', s).strip()
    s = s.replace("từ -", "từ").replace("- &", "-").replace("& -", "-")
    return s


def get_local_python_llm(model_name):
    """Tải và nạp mô hình HuggingFace Transformers trực tiếp trong tiến trình Python"""
    global _local_transformers_pipeline
    if not model_name:
        return None

    if _local_transformers_pipeline is None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            print(f"GraphRAGAgent: Đang nạp mô hình Python Local LLM '{model_name}'...")
            device = "GPU" if torch.cuda.is_available() else "CPU"
            print(f"GraphRAGAgent: Thiết bị tính toán: {device}")

            tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            model_kwargs = {
                "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                "trust_remote_code": True
            }
            if torch.cuda.is_available():
                model_kwargs["device_map"] = "auto"

            model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

            _local_transformers_pipeline = {
                'tokenizer': tokenizer,
                'model': model,
                'pipe': pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    max_new_tokens=2048,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    repetition_penalty=1.1
                )
            }
            print("GraphRAGAgent: Khởi chạy mô hình Local LLM thành công!")
        except Exception as e:
            print(f"GraphRAGAgent: Lỗi nạp mô hình Transformers trực tiếp ({e})")
            _local_transformers_pipeline = False

    return _local_transformers_pipeline if _local_transformers_pipeline else None


class GraphRAGAgent:
    """Graph RAG Agent - Trợ lý du lịch thông minh kết hợp Đồ thị tri thức & Local LLM"""

    INTENT_MAP = {
        'coffee': ['cà phê', 'cafe', 'coffee', 'trà', 'quán cà phê', 'quán trà', 'trà sữa', 'ngắm cảnh', 'làm việc', 'chill', 'yên tĩnh', 'bánh ngọt', 'bistro', 'dessert', 'matcha', 'americano', 'capuchino', 'latte'],
        'food': ['ăn uống', 'nhà hàng', 'quán ăn', 'ẩm thực', 'chợ', 'ăn đêm', 'món ăn', 'đặc sản', 'phở', 'cơm tấm', 'lẩu', 'nướng', 'hải sản', 'bún riêu', 'hủ tiếu', 'bánh mì', 'đồ ăn', 'nhậu', 'buffet', 'đồ ăn vặt'],
        'history': ['bảo tàng', 'di tích', 'lịch sử', 'dinh', 'chùa', 'nhà thờ', 'kiến trúc', 'văn hóa', 'cổ kính', 'thăm quan', 'thắng cảnh', 'bến cảng', 'tưởng niệm', 'di sản', 'nghệ thuật', 'triển lãm'],
        'nightlife': ['bar', 'pub', 'câu lạc bộ', 'vũ trường', 'bùi viện', 'phố đi bộ', 'đi dạo', 'rooftop', 'cocktail', 'quầy bar', 'nhạc sống', 'acoustic', 'quẩy', 'quẩy đêm'],
        'shopping': ['mua sắm', 'trung tâm thương mại', 'chợ', 'bến thành', 'mall', 'shopping', 'mua quà', 'siêu thị', 'đồ lưu niệm', 'thời trang', 'quần áo'],
        'nature_park': ['công viên', 'cây xanh', 'dã ngoại', 'hóng mát', 'đi dạo', 'thảo cầm viên', 'bến thả hoa', 'sông sài gòn', 'ven sông', 'ngắm hoàng hôn', 'picnic'],
        'spa': ['spa', 'massage', 'làm đẹp', 'thư giãn', 'chăm sóc da', 'gội đầu dưỡng sinh', 'xông hơi'],
        'view_photo': ['sống ảo', 'chụp hình', 'checkin', 'check-in', 'ngắm cảnh', 'ngắm hoàng hôn', 'đài quan sát', 'landmark', 'bitexco', 'view đẹp', 'view sông', 'hoàng hôn']
    }

    def __init__(self, ini_path='neo4j.ini'):
        self.use_local_llm = True
        self.local_mode = "python_transformers"
        self.local_llm_model = ""

        # Nạp cấu hình từ file ini
        if os.path.exists(ini_path):
            config = configparser.RawConfigParser()
            config.read(ini_path)

            if 'LOCAL_LLM' in config:
                sec = config['LOCAL_LLM']
                self.use_local_llm = sec.get('ENABLED', 'true').lower() in ['true', '1', 'yes']
                self.local_mode = sec.get('MODE', self.local_mode)
                self.local_llm_model = sec.get('MODEL', self.local_llm_model)

        # Đè cấu hình bằng biến môi trường (nếu được khai báo)
        if os.getenv("USE_LOCAL_LLM"):
            self.use_local_llm = os.getenv("USE_LOCAL_LLM").lower() in ['true', '1', 'yes']
        if os.getenv("LOCAL_MODE"):
            self.local_mode = os.getenv("LOCAL_MODE")
        if os.getenv("LOCAL_LLM_MODEL"):
            self.local_llm_model = os.getenv("LOCAL_LLM_MODEL")

        # Nạp trước mô hình Local LLM (HuggingFace Transformers)
        if self.use_local_llm and self.local_llm_model:
            get_local_python_llm(self.local_llm_model)

        print(f"GraphRAGAgent Sẵn sàng: Chế độ='HuggingFace Transformers', Mô hình='{self.local_llm_model}'")

    def _extract_regions(self, session, norm_query):
        """Trích xuất tên khu vực, quận huyện, phường xã từ Neo4j KG (Bao gồm Ontology Ward, District, Graph Inference & MERGED_TO)"""
        regions = session.run("MATCH (r:Region) RETURN r.name AS rname").data()
        wards = session.run("MATCH (w:Ward) RETURN w.name AS wname").data()
        districts = session.run("MATCH (d:District) RETURN d.name AS dname").data()

        # 1. Trích xuất Region & District
        region_search_terms = []
        for r in regions + districts:
            rname = r.get('rname') or r.get('dname')
            if not rname:
                continue
            rname_norm = norm_str(rname)
            region_search_terms.append((len(rname_norm), rname_norm.lower(), rname_norm))

            # Thêm các tên rút gọn (bỏ 'Quận', 'Huyện', 'Thành phố')
            short_name = re.sub(r'^(quận|huyện|thành phố)\s+', '', rname_norm, flags=re.IGNORECASE).strip()
            if short_name and short_name.lower() != rname_norm.lower():
                region_search_terms.append((len(short_name), short_name.lower(), rname_norm))

            # Thêm ký hiệu viết tắt như Q1, Q.1, Q2...
            q_match = re.match(r'^quận\s+(\d+)$', rname_norm, flags=re.IGNORECASE)
            if q_match:
                q_num = q_match.group(1)
                region_search_terms.append((len(f"q{q_num}"), f"q{q_num}", rname_norm))
                region_search_terms.append((len(f"q.{q_num}"), f"q.{q_num}", rname_norm))

        region_search_terms.sort(key=lambda x: x[0], reverse=True)

        detected_regions_raw = []
        for _, alias, full_rname in region_search_terms:
            pattern = r'(?<!\w)' + re.escape(alias) + r'(?!\w)'
            if re.search(pattern, norm_query, re.IGNORECASE):
                if full_rname not in detected_regions_raw:
                    detected_regions_raw.append(full_rname)

        # 2. Trích xuất Ward (Phường / Xã)
        ward_search_terms = []
        for w in wards:
            wname = w.get('wname')
            if not wname:
                continue
            wname_norm = norm_str(wname)
            ward_search_terms.append((len(wname_norm), wname_norm.lower(), wname_norm))

            # Rút gọn bỏ 'Phường', 'Xã', 'Thị trấn'
            short_wname = re.sub(r'^(phường|xã|thị trấn)\s+', '', wname_norm, flags=re.IGNORECASE).strip()
            if short_wname and short_wname.lower() != wname_norm.lower():
                if not short_wname.isdigit():
                    ward_search_terms.append((len(short_wname), short_wname.lower(), wname_norm))
                else:
                    p_num = short_wname
                    ward_search_terms.append((len(f"p{p_num}"), f"p{p_num}", wname_norm))
                    ward_search_terms.append((len(f"p.{p_num}"), f"p.{p_num}", wname_norm))

        ward_search_terms.sort(key=lambda x: x[0], reverse=True)

        detected_wards_raw = []
        for _, alias, full_wname in ward_search_terms:
            pattern = r'(?<!\w)' + re.escape(alias) + r'(?!\w)'
            if re.search(pattern, norm_query, re.IGNORECASE):
                if full_wname not in detected_wards_raw:
                    detected_wards_raw.append(full_wname)

        # 3. TỰ ĐỘNG SUY LUẬN QUẬN/HUYỆN TỪ ĐỒ THỊ TRI THỨC (Graph Inference):
        # Nếu người dùng nhập Phường theo địa chỉ mới (bỏ qua tên Quận), tự động tra cứu (Ward)-[:BELONGS_TO]->(District) trong Neo4j
        if detected_wards_raw:
            try:
                inferred_districts = session.run("""
                    MATCH (w:Ward)-[:BELONGS_TO]->(d:District)
                    WHERE ANY(wname IN $wards WHERE toLower(w.name) = toLower(wname))
                    RETURN DISTINCT d.name AS dname
                """, wards=detected_wards_raw).data()

                for rec in inferred_districts:
                    dname = rec.get('dname')
                    if dname and dname not in detected_regions_raw:
                        detected_regions_raw.append(dname)
            except Exception as e:
                print(f"GraphRAGAgent: Lỗi suy luận District từ Ward ({e})")

        detected_regions_vars = []
        for reg in detected_regions_raw:
            detected_regions_vars.extend(get_unicode_variants(reg))

        detected_wards_vars = []
        for w in detected_wards_raw:
            detected_wards_vars.extend(get_unicode_variants(w))

        return detected_regions_raw, detected_regions_vars, detected_wards_raw, detected_wards_vars

    def _extract_intents(self, norm_query):
        """Trích xuất từ khóa chủ đề du lịch từ câu hỏi bằng Ranh giới từ Regex"""
        detected_raw = []
        for topic, keywords in self.INTENT_MAP.items():
            for kw in keywords:
                pattern = r'(?<!\w)' + re.escape(kw.lower()) + r'(?!\w)'
                if re.search(pattern, norm_query, re.IGNORECASE):
                    detected_raw.append(kw)

        detected_vars = []
        for kw in detected_raw:
            detected_vars.extend(get_unicode_variants(kw))
        return detected_raw, detected_vars

    def _get_personalized_recommendations(self, user_id, recommender, gds, detected_regions_raw, detected_intents_raw, detected_wards_raw=None):
        """Lấy danh sách POI cá nhân hóa phù hợp với tiêu chí khu vực/phường/ý định"""
        context_items = []
        matched_pois = []
        if not (user_id and recommender and gds):
            return context_items, matched_pois

        try:
            rec_pois = recommender.recommend(gds=gds, user_id=user_id, top_n=10)
            if rec_pois:
                filtered_recs = []
                for p in rec_pois:
                    p_name = norm_str(p.get('name', ''))
                    p_reg = norm_str(p.get('region_name', ''))
                    p_desc = norm_str(p.get('description', ''))
                    p_cat = norm_str(p.get('category_name', ''))
                    p_addr = norm_str(p.get('address', ''))

                    match_region = not detected_regions_raw or any(r.lower() in (p_reg + " " + p_name + " " + p_addr).lower() for r in detected_regions_raw)
                    match_ward = not detected_wards_raw or any(w.lower() in (p_addr + " " + p_name).lower() for w in detected_wards_raw)
                    match_intent = not detected_intents_raw or any(kw.lower() in (p_name + " " + p_cat + " " + p_desc).lower() for kw in detected_intents_raw)

                    if match_region and match_ward and match_intent:
                        filtered_recs.append(p)

                target_recs = filtered_recs[:5] if filtered_recs else rec_pois[:4]
                if target_recs:
                    context_items.append("### Danh sách địa điểm Gợi ý Cá nhân hóa cho du khách:")
                    for idx, p in enumerate(target_recs, 1):
                        p_name = norm_str(p.get('name', 'N/A'))
                        p_rating = p.get('rating', 'N/A')
                        p_desc = norm_str(p.get('description', ''))[:150] or 'Địa điểm du lịch hấp dẫn'
                        p_reg = norm_str(p.get('region_name', 'TP.HCM')) or 'TP.HCM'
                        p_addr = norm_str(p.get('address')) or p_reg
                        p_hours = format_vietnamese_opening_hours(p.get('openingHours') or p.get('opening_hours'))
                        p_dur = norm_str(p.get('duration') or '1 - 2 giờ')

                        context_items.append(
                            f"{idx}. **{p_name}** | Khu vực chính xác: {p_reg}\n"
                            f"   - Địa chỉ: {p_addr}\n"
                            f"   - Giờ mở cửa: {p_hours}\n"
                            f"   - Thời gian dự kiến tham quan: {p_dur}\n"
                            f"   - Đánh giá: {p_rating}★ | Mô tả: {p_desc}..."
                        )
                        matched_pois.append({'id': p.get('id'), 'name': p_name})
        except Exception as e:
            print(f"GraphRAGAgent: Lỗi gọi Recommender Engine ({e})")

        return context_items, matched_pois

    def _query_cypher_pois(self, session, detected_regions_vars, detected_intents_vars, norm_query, seen_pids, detected_wards_vars=None):
        """Truy vấn địa điểm khớp điều kiện chính xác từ Neo4j KG bao gồm sáp nhập Phường/Xã (MERGED_TO), District & Region với cơ chế Fallback đa tầng"""
        context_items = []
        matched_pois = []

        def build_and_run(use_regions, use_wards, use_intents):
            cypher_query = "MATCH (p:Poi) WHERE 1=1"
            conditions = []
            params = {}

            if use_regions and detected_regions_vars:
                conditions.append("""(
                    ANY(reg IN $regions WHERE toLower(p.address) CONTAINS reg)
                    OR EXISTS { MATCH (p)-[:LOCATED_AT]->(r:Region) WHERE ANY(reg IN $regions WHERE toLower(r.name) = reg OR toLower(r.name) CONTAINS reg OR reg CONTAINS toLower(r.name)) }
                    OR EXISTS { MATCH (p)-[:LOCATED_IN]->(w:Ward)-[:BELONGS_TO]->(d:District) WHERE ANY(reg IN $regions WHERE toLower(d.name) = reg OR toLower(d.name) CONTAINS reg OR reg CONTAINS toLower(d.name)) }
                )""")
                params['regions'] = [r.lower() for r in detected_regions_vars]

            if use_wards and detected_wards_vars:
                conditions.append("""(
                    ANY(w IN $wards WHERE toLower(p.address) CONTAINS w)
                    OR EXISTS {
                        MATCH (p)-[:LOCATED_IN]->(target_w:Ward)
                        MATCH (target_w)-[:MERGED_TO*0..1]-(matched_w:Ward)
                        WHERE ANY(w IN $wards WHERE toLower(matched_w.name) = w OR toLower(matched_w.name) CONTAINS w OR w CONTAINS toLower(matched_w.name))
                    }
                )""")
                params['wards'] = [w.lower() for w in detected_wards_vars]

            if use_intents and detected_intents_vars:
                conditions.append("""(
                    ANY(kw IN $intents WHERE toLower(p.name) CONTAINS kw)
                    OR EXISTS { MATCH (p)-[:BELONGS_TO]->(cat:Category) WHERE ANY(kw IN $intents WHERE toLower(cat.name) CONTAINS kw) }
                )""")
                params['intents'] = detected_intents_vars

            if conditions:
                cypher_query += " AND " + " AND ".join(conditions)

            cypher_query += """
                OPTIONAL MATCH (p)-[:LOCATED_AT]->(r:Region)
                OPTIONAL MATCH (p)-[:LOCATED_IN]->(w:Ward)
                OPTIONAL MATCH (w)-[:BELONGS_TO]->(d:District)
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
                RETURN DISTINCT p.id AS id, p.name AS name, r.name AS rname, w.name AS wname, d.name AS dname, c.name AS cname, p.address AS address, p.avgRating AS avgRating, p.rating AS rating, p.numReviews AS reviews, p.openingHours AS openingHours, p.duration AS duration, p.description AS description
                ORDER BY p.numReviews DESC LIMIT 8
            """
            return session.run(cypher_query, **params).data()

        records = []
        if detected_regions_vars or detected_intents_vars or detected_wards_vars:
            # Truy vấn lọc đúng theo các tiêu chí thực thể đã trích xuất (Phường / Quận / Ý định)
            records = build_and_run(use_regions=True, use_wards=True, use_intents=True)
        else:
            words = [w for w in re.findall(r'\w+', norm_query) if len(w) > 2]
            if words:
                cypher_query = """
                    MATCH (p:Poi)
                    WHERE ANY(word IN $words WHERE toLower(p.name) CONTAINS toLower(word) OR toLower(p.address) CONTAINS toLower(word))
                    OPTIONAL MATCH (p)-[:LOCATED_AT]->(r:Region)
                    OPTIONAL MATCH (p)-[:LOCATED_IN]->(w:Ward)
                    OPTIONAL MATCH (w)-[:BELONGS_TO]->(d:District)
                    OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
                    RETURN DISTINCT p.id AS id, p.name AS name, r.name AS rname, w.name AS wname, d.name AS dname, c.name AS cname, p.address AS address, p.avgRating AS avgRating, p.rating AS rating, p.numReviews AS reviews, p.openingHours AS openingHours, p.duration AS duration, p.description AS description
                    ORDER BY p.numReviews DESC LIMIT 6
                """
                records = session.run(cypher_query, words=words).data()

        if records:
            context_items.append("\n### Danh sách địa điểm phù hợp trong Đồ thị tri thức (Knowledge Graph):")
            for rec in records:
                pid = rec['id']
                if pid in seen_pids:
                    continue
                seen_pids.add(pid)

                p_name = norm_str(rec.get('name', ''))
                p_rating = rec.get('avgRating') or rec.get('rating') or 'N/A'
                p_desc = norm_str(rec.get('description'))[:150] or norm_str(rec.get('cname')) or 'Địa điểm du lịch nổi tiếng'
                p_reg = norm_str(rec.get('rname')) or 'Thành phố Hồ Chí Minh'
                p_wname = norm_str(rec.get('wname'))
                p_dname = norm_str(rec.get('dname'))

                loc_info = p_reg
                if p_wname and p_dname:
                    loc_info += f" ({p_wname}, {p_dname})"
                elif p_wname:
                    loc_info += f" ({p_wname})"
                elif p_dname:
                    loc_info += f" ({p_dname})"

                p_addr = norm_str(rec.get('address')) or loc_info
                p_hours = format_vietnamese_opening_hours(rec.get('openingHours'))
                p_dur = norm_str(rec.get('duration') or '1 - 2 giờ')

                context_items.append(
                    f"- **{p_name}** | Khu vực chính xác: {loc_info}\n"
                    f"  + Địa chỉ: {p_addr}\n"
                    f"  + Giờ mở cửa: {p_hours}\n"
                    f"  + Thời gian dự kiến tham quan: {p_dur}\n"
                    f"  + Đánh giá: {p_rating}★ | Đặc điểm: {p_desc}"
                )
                matched_pois.append({'id': pid, 'name': p_name})

        return context_items, matched_pois

    def _query_popular_pois(self, session, seen_pids):
        """Lấy các POI phổ biến nhất hệ thống làm dự phòng nếu không tìm thấy POI theo khu vực"""
        context_items = []
        matched_pois = []
        pop_records = session.run("""
            MATCH (p:Poi)
            OPTIONAL MATCH (p)-[:LOCATED_AT]->(r:Region)
            OPTIONAL MATCH (p)-[:LOCATED_IN]->(w:Ward)
            OPTIONAL MATCH (w)-[:BELONGS_TO]->(d:District)
            OPTIONAL MATCH (p)-[:BELONGS_TO]->(c:Category)
            RETURN p.id AS id, p.name AS name, r.name AS rname, w.name AS wname, d.name AS dname, c.name AS cname, p.rating AS rating, p.numReviews AS reviews, p.openingHours AS openingHours, p.duration AS duration, p.description AS description
            ORDER BY p.numReviews DESC LIMIT 6
        """).data()

        context_items.append("\n### Danh sách địa điểm tham khảo bổ sung (Các khu vực khác tại TP.HCM):")
        for rec in pop_records:
            pid = rec['id']
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            p_name = norm_str(rec.get('name', ''))
            p_reg = norm_str(rec.get('rname')) or 'Thành phố Hồ Chí Minh'
            p_wname = norm_str(rec.get('wname'))
            p_dname = norm_str(rec.get('dname'))

            loc_info = p_reg
            if p_wname and p_dname:
                loc_info += f" ({p_wname}, {p_dname})"
            elif p_wname:
                loc_info += f" ({p_wname})"

            p_cat = norm_str(rec.get('cname')) or 'Tham quan du lịch'
            p_addr = norm_str(rec.get('address')) or loc_info
            p_hours = format_vietnamese_opening_hours(rec.get('openingHours'))
            p_dur = norm_str(rec.get('duration') or '1 - 2 giờ')

            context_items.append(
                f"- **{p_name}** | Khu vực chính xác: {loc_info}\n"
                f"  + Địa chỉ: {p_addr}\n"
                f"  + Giờ mở cửa: {p_hours}\n"
                f"  + Thời gian dự kiến tham quan: {p_dur}\n"
                f"  + Thể loại: {p_cat}"
            )
            matched_pois.append({'id': pid, 'name': p_name})

        return context_items, matched_pois

    def retrieve_context(self, neo4j_driver, database, query_text, user_id=None, recommender=None, gds=None):
        """Trích xuất ngữ cảnh thực thể và quan hệ từ Neo4j KG dựa trên ý định du khách"""
        context_items = []
        matched_pois = []
        norm_query = norm_str(query_text).lower()

        with neo4j_driver.session(database=database) as session:
            # 1. Trích xuất Khu vực, Phường/Xã & Ý định chính xác
            detected_regions_raw, detected_regions_vars, detected_wards_raw, detected_wards_vars = self._extract_regions(session, norm_query)
            detected_intents_raw, detected_intents_vars = self._extract_intents(norm_query)

            # 2. Gợi ý cá nhân hóa từ Recommender Engine
            rec_items, rec_pois = self._get_personalized_recommendations(
                user_id, recommender, gds, detected_regions_raw, detected_intents_raw, detected_wards_raw
            )
            context_items.extend(rec_items)
            matched_pois.extend(rec_pois)

            # 3. Truy vấn Cypher khớp theo Ý định / Khu vực / Phường xã sáp nhập / Từ khóa
            seen_pids = {p['id'] for p in matched_pois}
            cypher_items, cypher_pois = self._query_cypher_pois(
                session, detected_regions_vars, detected_intents_vars, norm_query, seen_pids, detected_wards_vars
            )
            context_items.extend(cypher_items)
            matched_pois.extend(cypher_pois)

            # 4. Dự phòng & Kiểm tra Từ chối:
            if not context_items:
                # Chỉ lấy popular POIs nếu là câu hỏi hoàn toàn chung chung không nêu ý định hay khu vực cụ thể
                if not (detected_regions_vars or detected_wards_vars or detected_intents_vars):
                    is_general_travel = any(kw in norm_query for kw in [
                        'gợi ý', 'phù hợp', 'du lịch', 'đi đâu', 'tham quan', 'chơi gì',
                        'tp.hcm', 'tphcm', 'sài gòn', 'saigon', 'nổi tiếng', 'địa điểm',
                        'cho tôi', 'tư vấn', 'chủ đề', 'có gì hay', 'ở đâu'
                    ])
                    if is_general_travel:
                        pop_items, pop_pois = self._query_popular_pois(session, seen_pids)
                        context_items.extend(pop_items)
                        matched_pois.extend(pop_pois)

        if not context_items:
            return "(Không tìm thấy địa điểm nào phù hợp)", []

        return "\n".join(context_items), matched_pois

    def _get_system_msg(self):
        now = datetime.now()
        day_names = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"]
        current_day_vn = day_names[int(now.strftime("%w"))]
        current_time_str = f"{now.strftime('%H:%M')} ({current_day_vn}, {now.strftime('%d/%m/%Y')})"

        return (
            f"Bạn là Trợ lý Du lịch Thông minh TP.HCM – một hướng dẫn viên bản địa am hiểu sâu sắc về văn hóa, ẩm thực và các điểm đến tại Thành phố Hồ Chí Minh.\n"
            f"Thời gian hệ thống hiện tại là: {current_time_str}.\n\n"
            "QUY TẮC TỪ CHỐI BẮT BUỘC:\n"
            "1. Nếu câu hỏi của du khách KHÔNG liên quan đến du lịch/khám phá TP.HCM (như giải toán, lập trình, chơi game điện tử, thời tiết, tâm sự ngoài lề...) HOẶC phần DỮ LIỆU THỰC THỂ bên dưới ghi '(Không tìm thấy địa điểm nào phù hợp)', bạn BẮT BUỘC PHẢI TỪ CHỐI MỘT CÁCH LỊCH SỰ.\n"
            "2. Mẫu câu từ chối chuẩn: 'Xin lỗi bạn, tôi là Trợ lý Du lịch TP.HCM. Hiện tại tôi chưa có thông tin địa điểm hoặc dịch vụ phù hợp với yêu cầu của bạn. Bạn có thể hỏi tôi về các điểm tham quan di tích, nhà hàng, quán cà phê, mua sắm hoặc giải trí tại TP.HCM nhé!'\n"
            "3. TUYỆT ĐỐ KHÔNG TỰ BỊA RA LÝ DO GIẢ TẠO để ép các địa điểm không liên quan thành nơi phục vụ yêu cầu không phù hợp!\n\n"
            "CẤU TRÚC PHẢN HỒI KHI CÓ ĐỊA ĐIỂM PHÙ HỢP:\n"
            "Mở đầu bằng một câu chào du khách ngắn gọn. Sau đó trình bày từng địa điểm theo cấu trúc chính xác sau:\n\n"
            "1. **Tên Địa Điểm 1**\n"
            "- **Lý do**: Lý do phù hợp với mong muốn của du khách.\n"
            "- **Địa chỉ**: Địa chỉ trích dẫn từ dữ liệu.\n"
            "- **Giờ mở cửa**: Thông tin giờ mở cửa từ dữ liệu (có thể kèm nhận xét ngắn như 'Hiện đang mở cửa' hoặc 'Hiện đã đóng cửa').\n"
            "- **Thời gian dự kiến tham quan**: Thời gian tham quan ước tính từ dữ liệu.\n\n"
            "QUY TẮC NGHIÊM NGẶT:\n"
            "1. TUYỆT ĐỐ KHÔNG LẶP LẠI BẤT KỲ CỤM TỪ HƯỚNG DẪN NÀO TRONG TỆP MẪU SYSTEM PROMPT.\n"
            "2. BẮT BUỘC đặt Tên Địa Điểm lên đầu tiên ở dạng danh sách số (1. **Tên POI**, 2. **Tên POI**...).\n"
            "3. Mỗi địa điểm gồm đúng 4 gạch đầu dòng con: Lý do, Địa chỉ, Giờ mở cửa, Thời gian dự kiến tham quan.\n"
            "4. CHỈ GIỚI THIỆU CÁC ĐỊA ĐIỂM CÓ TRONG DANH SÁCH DỮ LIỆU ĐƯỢC CUNG CẤP. Tuyệt đối không tự bịa địa điểm ngoài danh sách.\n"
            "5. ĐẶC BIỆT CHÚ Ý KHU VỰC: Kiểm tra thuộc tính 'Khu vực chính xác'. Nếu du khách hỏi về một Quận/Huyện cụ thể (ví dụ: Bình Chánh, Tân Bình, Củ Chi, Quận 1...), không được giới thiệu địa điểm thuộc Quận/Huyện khác!\n"
            "6. TRÍCH DẪN NGUYÊN VĂN ĐỊA CHỈ: Giữ nguyên 100% thuộc tính 'Địa chỉ' và 'Khu vực chính xác' trích dẫn từ DỮ LIỆU THỰC THỂ. Tuyệt đối không tự ý sửa đổi tên phường/quận trong địa chỉ để khớp với câu hỏi (Ví dụ: Không được tự đổi 'Phường Bến Thành' thành 'Phường Vườn Lài'). Không được tự bịa ra bất kỳ tên địa điểm giả nào."
        )

    def generate_response_python_transformers(self, prompt, llm_params=None):
        """Sinh câu trả lời đồng bộ trong tiến trình Python sử dụng Transformers"""
        if not self.local_llm_model:
            return None

        llm_obj = get_local_python_llm(self.local_llm_model)
        if llm_obj:
            try:
                tokenizer = llm_obj['tokenizer']
                pipe = llm_obj['pipe']

                messages = [
                    {"role": "system", "content": self._get_system_msg()},
                    {"role": "user", "content": prompt}
                ]

                formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                
                # Áp dụng thông số tùy chỉnh từ giao diện
                p = llm_params or {}
                max_tokens = int(p.get('max_new_tokens', 2048))
                temp = float(p.get('temperature', 0.7))
                top_p_val = float(p.get('top_p', 0.9))
                rep_penalty = float(p.get('repetition_penalty', 1.1))

                out = pipe(
                    formatted_prompt,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=temp,
                    top_p=top_p_val,
                    repetition_penalty=rep_penalty
                )

                if out and len(out) > 0 and 'generated_text' in out[0]:
                    full_text = out[0]['generated_text']
                    if "<|im_start|>assistant" in full_text:
                        reply = full_text.split("<|im_start|>assistant")[-1].replace("<|im_end|>", "").strip()
                    else:
                        reply = full_text[len(formatted_prompt):].strip()

                    print("GraphRAGAgent: Đã tạo câu trả lời thành công qua Python Transformers Local LLM!")
                    return reply
            except Exception as e:
                print(f"GraphRAGAgent: Lỗi Python Transformers ({e})")
        return None

    def generate_response_stream_python_transformers(self, prompt, llm_params=None):
        """Sinh câu trả lời dạng STREAMING qua Python Transformers bằng TextIteratorStreamer"""
        if not self.local_llm_model:
            return

        llm_obj = get_local_python_llm(self.local_llm_model)
        if llm_obj:
            try:
                from transformers import TextIteratorStreamer

                tokenizer = llm_obj['tokenizer']
                model = llm_obj['model']

                messages = [
                    {"role": "system", "content": self._get_system_msg()},
                    {"role": "user", "content": prompt}
                ]

                formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer([formatted_prompt], return_tensors="pt")
                if hasattr(model, "device"):
                    inputs = inputs.to(model.device)

                p = llm_params or {}
                max_tokens = int(p.get('max_new_tokens', 2048))
                temp = float(p.get('temperature', 0.7))
                top_p_val = float(p.get('top_p', 0.9))
                rep_penalty = float(p.get('repetition_penalty', 1.1))

                streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
                generation_kwargs = dict(
                    inputs,
                    streamer=streamer,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=temp,
                    top_p=top_p_val,
                    repetition_penalty=rep_penalty
                )

                thread = Thread(target=model.generate, kwargs=generation_kwargs)
                thread.start()

                for new_text in streamer:
                    if new_text:
                        yield new_text
            except Exception as e:
                print(f"GraphRAGAgent: Lỗi Python Transformers Stream ({e})")


    def generate_response(self, query_text, context_str, user_name="Du khách", llm_params=None):
        """Sinh câu trả lời đồng bộ từ Python Transformers, Ollama, hoặc Fallback RAG"""
        is_no_match = "Không tìm thấy địa điểm nào phù hợp" in context_str

        if is_no_match:
            prompt = f"""Du khách cần tư vấn: {user_name}
Câu hỏi / Yêu cầu của du khách: "{query_text}"

DỮ LIỆU THỰC THỂ TỪ ĐỒ THỊ TRI THỨC (KNOWLEDGE GRAPH):
{context_str}

QUY TẮC PHẢN HỒI:
Yêu cầu của du khách không có địa điểm phù hợp trong cơ sở dữ liệu hoặc không liên quan đến du lịch TP.HCM.
BẮT BUỘC TỪ CHỐI LỊCH SỰ theo mẫu:
"Xin lỗi {user_name}, tôi là Trợ lý Du lịch TP.HCM. Hiện tại tôi chưa có thông tin địa điểm hoặc dịch vụ phù hợp với yêu cầu '{query_text}' của bạn. Bạn có thể hỏi tôi về các điểm tham quan di tích, nhà hàng, quán cà phê, mua sắm hoặc giải trí tại TP.HCM nhé!"

TUYỆT ĐỐ KHÔNG TỰ BỊA RA LÝ DO GIẢ TẠO ĐỂ ÉP BẤT KỲ ĐỊA ĐIỂM NÀO VÀO CÂU TRẢ LỜI!
"""
        else:
            prompt = f"""Du khách cần tư vấn: {user_name}
Câu hỏi / Yêu cầu của du khách: "{query_text}"

DỮ LIỆU THỰC THỂ TỪ ĐỒ THỊ TRI THỨC (KNOWLEDGE GRAPH):
{context_str}

BẮT BUỘC TRÌNH BÀY THEO CẤU TRÚC:
1. Mở đầu bằng một câu chào {user_name} ấm áp và ngắn gọn (ví dụ: "Chào bạn! Dưới đây là các địa điểm phù hợp dành cho bạn:").
2. Danh sách các địa điểm theo đúng mẫu sau:

    1. **[Tên Địa Điểm 1]**
    - **Lý do**: [Nêu ngắn gọn lý do tại sao địa điểm này phù hợp với mong muốn của du khách]
    - **Địa chỉ**: [Địa chỉ cụ thể trích dẫn từ dữ liệu]
    - **Giờ mở cửa**: [Giờ mở cửa từ dữ liệu]. [Đối chiếu với thời gian hiện tại để đưa ra nhận xét tự nhiên bằng tiếng Việt như: (Hiện đang trong giờ mở cửa) hoặc (Hiện đã đóng cửa, khuyên ghé vào sáng mai), TUYỆT ĐỐ KHÔNG viết cụm từ thô '(Trong khoảng thời gian này)']
    - **Thời gian dự kiến tham quan**: [Thời gian ước tính từ dữ liệu, ví dụ: 1 - 2 giờ]

    Các địa điểm tiếp theo trình bày tương tự mẫu trên.

3. Kết thúc bằng 1 câu hỏi hoặc lời chúc ngắn gọn, thân thiện (ví dụ: "Chúc bạn có những trải nghiệm tuyệt vời! Bạn có muốn mình tìm hiểu thêm thông tin gì về các địa điểm này không?").

CHÚ Ý: BẮT BUỘC Phải có câu chào mở đầu và câu kết ở cuối!
"""

        # 1. Thử Python Transformers Local LLM (HuggingFace)
        if self.use_local_llm:
            py_reply = self.generate_response_python_transformers(prompt, llm_params=llm_params)
            if py_reply:
                return py_reply

        # 2. Phản hồi cấu trúc mặc định nếu chưa bật LLM hoặc từ chối
        if is_no_match:
            return f"Xin lỗi **{user_name}**, tôi là Trợ lý Du lịch TP.HCM. Hiện tại tôi chưa có thông tin địa điểm hoặc dịch vụ phù hợp với yêu cầu **'{query_text}'** của bạn.\n\nBạn có thể hỏi tôi về các điểm tham quan di tích, nhà hàng, quán cà phê, mua sắm hoặc địa điểm giải trí tại TP.HCM nhé!"

        print("GraphRAGAgent: Đang sử dụng phản hồi cấu trúc RAG Đồ thị tri thức.")
        fallback = f"Xin chào **{user_name}**! Dựa trên thông tin trích xuất từ Đồ thị tri thức Du lịch TP.HCM, tôi xin gợi ý cho bạn các địa điểm phù hợp nhất:\n\n"
        fallback += context_str
        fallback += "\n\nBạn có muốn tìm hiểu thêm thông tin chi tiết về địa điểm nào trong danh sách trên không?"
        return fallback

    def generate_response_stream(self, query_text, context_str, user_name="Du khách", llm_params=None):
        """Sinh câu trả lời dạng STREAMING token-by-token"""
        is_no_match = "Không tìm thấy địa điểm nào phù hợp" in context_str

        if is_no_match:
            prompt = f"""Du khách cần tư vấn: {user_name}
Câu hỏi / Yêu cầu của du khách: "{query_text}"

DỮ LIỆU THỰC THỂ TỪ ĐỒ THỊ TRI THỨC (KNOWLEDGE GRAPH):
{context_str}

QUY TẮC PHẢN HỒI:
Yêu cầu của du khách không có địa điểm phù hợp trong cơ sở dữ liệu hoặc không liên quan đến du lịch TP.HCM.
BẮT BUỘC TỪ CHỐI LỊCH SỰ theo mẫu:
"Xin lỗi {user_name}, tôi là Trợ lý Du lịch TP.HCM. Hiện tại tôi chưa có thông tin địa điểm hoặc dịch vụ phù hợp với yêu cầu '{query_text}' của bạn. Bạn có thể hỏi tôi về các điểm tham quan di tích, nhà hàng, quán cà phê, mua sắm hoặc giải trí tại TP.HCM nhé!"

TUYỆT ĐỐ KHÔNG TỰ BỊA RA LÝ DO GIẢ TẠO ĐỂ ÉP BẤT KỲ ĐỊA ĐIỂM NÀO VÀO CÂU TRẢ LỜI!
"""
        else:
            prompt = f"""Du khách cần tư vấn: {user_name}
Câu hỏi / Yêu cầu của du khách: "{query_text}"

DỮ LIỆU THỰC THỂ TỪ ĐỒ THỊ TRI THỨC (KNOWLEDGE GRAPH):
{context_str}

BẮT BUỘC TRÌNH BÀY THEO CẤU TRÚC:
1. Mở đầu bằng một câu chào {user_name} ấm áp và ngắn gọn (ví dụ: "Chào bạn! Dưới đây là các địa điểm phù hợp dành cho bạn:").
2. Danh sách các địa điểm theo đúng mẫu sau:

1. **Tên Địa Điểm 1**
- **Lý do**: ...
- **Địa chỉ**: ...
- **Giờ mở cửa**: ... (Kèm lời khuyên đối chiếu thời gian hiện tại)
- **Thời gian dự kiến tham quan**: ...

2. **Tên Địa Điểm 2**
- **Lý do**: ...
- **Địa chỉ**: ...
- **Giờ mở cửa**: ...
- **Thời gian dự kiến tham quan**: ...

3. Kết thúc bằng 1 câu hỏi hoặc lời chúc ngắn gọn, thân thiện (ví dụ: "Chúc bạn có những trải nghiệm tuyệt vời! Bạn có muốn mình tìm hiểu thêm thông tin gì về các địa điểm này không?").

CHÚ Ý: BẮT BUỘC Phải có câu chào mở đầu và câu kết ở cuối!
"""

        stream_success = False

        # 1. Thử Python Transformers Stream (HuggingFace)
        if self.use_local_llm:
            for chunk in self.generate_response_stream_python_transformers(prompt, llm_params=llm_params):
                stream_success = True
                yield chunk
            if stream_success:
                return

        # 2. Phản hồi cấu trúc mặc định dạng stream nếu không có LLM
        print("GraphRAGAgent: Đang sử dụng phản hồi cấu trúc RAG Đồ thị tri thức (Stream).")
        if is_no_match:
            fallback = f"Xin lỗi **{user_name}**, tôi là Trợ lý Du lịch TP.HCM. Hiện tại tôi chưa có thông tin địa điểm hoặc dịch vụ phù hợp với yêu cầu **'{query_text}'** của bạn.\n\nBạn có thể hỏi tôi về các điểm tham quan di tích, nhà hàng, quán cà phê, mua sắm hoặc địa điểm giải trí tại TP.HCM nhé!"
        else:
            fallback = f"Xin chào **{user_name}**! Dựa trên thông tin trích xuất từ Đồ thị tri thức Du lịch TP.HCM, tôi xin gợi ý cho bạn các địa điểm phù hợp nhất:\n\n"
            fallback += context_str
            fallback += "\n\nBạn có muốn tìm hiểu thêm thông tin chi tiết về địa điểm nào trong danh sách trên không?"

        for word in fallback.split(' '):
            yield word + ' '

    def chat(self, neo4j_driver, database, query_text, user_id=None, recommender=None, gds=None, user_name="Du khách", llm_params=None):
        """Hàm chính xử lý yêu cầu chat đồng bộ"""
        context_str, matched_pois = self.retrieve_context(
            neo4j_driver=neo4j_driver,
            database=database,
            query_text=query_text,
            user_id=user_id,
            recommender=recommender,
            gds=gds
        )

        reply = self.generate_response(query_text=query_text, context_str=context_str, user_name=user_name, llm_params=llm_params)

        smart_pois = []
        seen_ids = set()
        reply_lower = norm_str(reply).lower()

        for p in matched_pois:
            p_name = norm_str(p.get('name', '')).strip()
            if p_name and p_name.lower() in reply_lower and p['id'] not in seen_ids:
                smart_pois.append(p)
                seen_ids.add(p['id'])

        if not smart_pois:
            for p in matched_pois:
                if p['id'] not in seen_ids:
                    smart_pois.append(p)
                    seen_ids.add(p['id'])

        return {
            'reply': reply,
            'pois': smart_pois if smart_pois else matched_pois
        }

    def chat_stream(self, neo4j_driver, database, query_text, user_id=None, recommender=None, gds=None, user_name="Du khách", llm_params=None):
        """Hàm chính xử lý yêu cầu chat STREAMING"""
        context_str, matched_pois = self.retrieve_context(
            neo4j_driver=neo4j_driver,
            database=database,
            query_text=query_text,
            user_id=user_id,
            recommender=recommender,
            gds=gds
        )

        # 1. Gửi metadata toàn bộ POI candidate trước
        yield {'type': 'meta', 'pois': matched_pois}

        # 2. Stream các token nội dung
        for token in self.generate_response_stream(query_text=query_text, context_str=context_str, user_name=user_name, llm_params=llm_params):
            yield {'type': 'token', 'content': token}

        # 3. Kết thúc stream
        yield {'type': 'done'}
