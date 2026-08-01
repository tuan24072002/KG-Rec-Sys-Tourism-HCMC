import re
from bs4 import BeautifulSoup
import time
import pandas as pd
import os
import random
import csv
import json
import sys
from deep_translator import GoogleTranslator

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Thư viện tự định nghĩa
import MySpider
import PoiUrlScraper

# Danh sách từ khóa lọc mô tả không hợp lệ (như review hoặc chính sách của website)
BLACKLIST = [
    "this is the version of our website",
    "makes no guarantees",
    "not responsible for any content",
    "is not a booking agent",
    "ai-selected", "ai selected",
    "cookie", "terms of use", "our agreement",
    "does not warrant", "privacy policy",
    "excellent", "very good", "average", "poor", "terrible",
    "view reviews", "write a review"
]

def is_english(text):
    if not text:
        return False
    english_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'it', 'for', 'not', 'on', 'with', 'as', 'at', 'this', 'but', 'by', 'from', 'or', 'an', 'will', 'all', 'would', 'there', 'their', 'if', 'about', 'who', 'which'}
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    if not words:
        return False
    eng_count = sum(1 for w in words if w in english_words)
    return (eng_count / len(words)) > 0.08

def translate_duration(text):
    if not text:
        return ''
    text_clean = text.lower().strip()
    mappings = {
        'more than 3 hours': 'Hơn 3 giờ',
        '2-3 hours': '2-3 giờ',
        '1-2 hours': '1-2 giờ',
        'less than 1 hour': 'Dưới 1 giờ',
        '< 1 hour': 'Dưới 1 giờ',
        '1 hour': '1 giờ',
        '2 hours': '2 giờ',
        '3 hours': '3 giờ'
    }
    for eng, vi in mappings.items():
        if eng in text_clean:
            return vi
    translated = text.replace('hours', 'giờ').replace('hour', 'giờ').replace('More than', 'Hơn').replace('Less than', 'Dưới')
    return translated


# Thu thập tất cả thông tin của một POI từ trang chi tiết
class PoiInfolScraper(object):

    def __init__(self):

        poi_url_scraper = PoiUrlScraper.PoiUrlScraper()
        self.urls = poi_url_scraper.get_poi_urls()

        self.filename = "output/poi_info.csv"
        self.categories_filename = "output/poi_categories.json"

        self.poi_info_df = pd.DataFrame()
        self.poi_categories = {}

        if os.path.exists(self.categories_filename):
            try:
                with open(self.categories_filename, 'r', encoding='utf-8') as file:
                    self.poi_categories = json.load(file)
            except Exception as e:
                print(f"Cảnh báo: Không thể tải ánh xạ thể loại: {e}")
        

    def get_poi_info(self):

        scraped_urls = set()
        if os.path.exists(self.filename):
            try:
                self.poi_info_df = pd.read_csv(self.filename)
                if 'url' in self.poi_info_df.columns:
                    scraped_urls = set(self.poi_info_df['url'].dropna().tolist())
                print(f"\nĐã tải {len(scraped_urls)} POI đã cào từ file {self.filename}")
            except Exception as e:
                print(f"Cảnh báo: Không thể đọc file CSV hiện tại {self.filename}: {e}")
                self.poi_info_df = pd.DataFrame()
        else:
            self.poi_info_df = pd.DataFrame()

        # Tải danh mục thể loại nếu chưa được tải
        if not self.poi_categories and os.path.exists(self.categories_filename):
            try:
                with open(self.categories_filename, 'r', encoding='utf-8') as file:
                    self.poi_categories = json.load(file)
            except Exception as e:
                print(f"Cảnh báo: Không thể tải file thể loại: {e}")

        # Lọc danh sách URL để chỉ cào những địa điểm còn lại
        urls_to_scrape = [url for url in self.urls if url not in scraped_urls]
        total_num = len(self.urls)
        completed_count = len(scraped_urls)

        if not urls_to_scrape:
            print("\n[+] Tất cả các URL đã được cào thành công trước đó!")
            return self.poi_info_df

        # Danh sách để lưu trữ thông tin các POI
        poi_info_list = []
        failed_urls = []

        # Khởi tạo một phiên bản spider để tái sử dụng cùng cửa sổ Chrome
        poi_spider = MySpider.Spider()

        for url in urls_to_scrape:

            completed_count += 1
            print(f"\nTiến trình: {completed_count}/{total_num}")

            try:
                # Sử dụng tên miền tiếng Việt (.com.vn) mặc định để lấy dữ liệu tiếng Việt chuẩn
                poi_spider.url = url

                # Lấy nội dung HTML
                html = poi_spider.get_html()

                # Kiểm tra nếu lấy nội dung HTML thành công, nếu không thì bỏ qua vòng lặp này
                if not html or "<html" not in html.lower():
                    failed_urls.append(url)
                    print("Đã thêm URL vào danh sách lỗi (failed_urls).")
                    continue

                # Phân tích cú pháp HTML
                soup = BeautifulSoup(html, 'html.parser')

                # Từ điển lưu trữ thông tin của một POI duy nhất
                poi_info = {}

                # Trích xuất ID địa điểm bằng biểu thức chính quy (regular expression) từ URL gốc
                poi_info['id'] = re.search(r'd(\d+)-', url).group(1) if re.search(r'd(\d+)-', url) else None
                print("id:", poi_info['id']) if poi_info['id'] else print("Không tìm thấy ID POI trong URL")

                # Lưu URL tiếng Việt gốc vào kết quả đầu ra
                poi_info['url'] = url
                print("url:", poi_info['url'])

                # 1. Phân tích cú pháp JSON-LD nếu có
                json_ld_data = {}
                scripts = soup.find_all('script', type='application/ld+json')
                target_types = {'LocalBusiness', 'TouristAttraction', 'Museum', 'Place', 'LandmarksOrHistoricalBuildings'}
                for s in scripts:
                    try:
                        script_text = s.text or s.string
                        if not script_text:
                            continue
                        data = json.loads(script_text)
                        if isinstance(data, dict):
                            if data.get("@type") in target_types:
                                json_ld_data = data
                                break
                            if "@graph" in data and isinstance(data["@graph"], list):
                                for item in data["@graph"]:
                                    if isinstance(item, dict) and item.get("@type") in target_types:
                                        json_ld_data = item
                                        break
                            if json_ld_data:
                                break
                    except:
                        pass

                # Thu thập dữ liệu POI và in ra màn hình
                # Tên (name)
                poi_info['name'] = json_ld_data.get('name', '')
                if not poi_info['name']:
                    h1 = soup.find('h1')
                    poi_info['name'] = h1.text.strip() if h1 else ''
                print("name:", poi_info['name'])

                # Thể loại (type / categories) - Ánh xạ từ trang danh sách hoặc lấy từ json-ld
                poi_info['type'] = self.poi_categories.get(url, '')
                if not poi_info['type'] and json_ld_data.get('@type'):
                    # Dự phòng lấy type của JSON-LD nếu là thể loại cụ thể (không phải LocalBusiness)
                    j_type = json_ld_data.get('@type')
                    if j_type != 'LocalBusiness':
                        poi_info['type'] = j_type
                print("type:", poi_info['type'])

                # Giờ mở cửa (openingHours)
                poi_info['openingHours'] = json_ld_data.get('openingHours', '')
                if not poi_info['openingHours']:
                    oh_tag = soup.find('span', class_='EFKKt')
                    poi_info['openingHours'] = oh_tag.text.strip() if oh_tag else ''
                print("openingHours:", poi_info['openingHours'])

                # Tọa độ địa lý (latitude & longitude)
                poi_info['latitude'] = ''
                poi_info['longitude'] = ''
                poi_info['source_coord'] = ''
                geo = json_ld_data.get('geo', {})
                if isinstance(geo, dict) and 'latitude' in geo and 'longitude' in geo:
                    poi_info['latitude'] = str(geo['latitude'])
                    poi_info['longitude'] = str(geo['longitude'])
                print("latitude:", poi_info['latitude'])
                print("longitude:", poi_info['longitude'])


                # Mô tả (description) và thời lượng tham quan (duration)
                poi_info['description'] = ''
                about_div_vi = soup.find(attrs={"data-automation": "attractionsAboutContent"})
                if about_div_vi:
                    desc_vi = about_div_vi.text.strip()
                    if not any(b.lower() in desc_vi.lower() for b in BLACKLIST):
                        poi_info['description'] = desc_vi
                poi_info['duration'] = ''

                # Giá cả (price)
                poi_info['price'] = ''
                print("price:", poi_info['price'])

                # Địa chỉ (address)
                address_data = json_ld_data.get('address', {})
                if isinstance(address_data, dict):
                    parts = []
                    if address_data.get('streetAddress'):
                        parts.append(address_data.get('streetAddress'))
                    if address_data.get('addressLocality'):
                        parts.append(address_data.get('addressLocality'))
                    if address_data.get('postalCode'):
                        parts.append(address_data.get('postalCode'))
                    poi_info['address'] = ", ".join(parts) if parts else ''
                else:
                    poi_info['address'] = address_data if address_data else ''
                if not poi_info['address']:
                    addr_div = soup.find('div', class_='wgNTK')
                    if addr_div:
                        poi_info['address'] = addr_div.text.strip()
                print("address:", poi_info['address'])

                # Khu vực (region)
                if isinstance(address_data, dict):
                    poi_info['region'] = address_data.get('addressLocality', '')
                else:
                    poi_info['region'] = ''
                if not poi_info['region']:
                    region_div = soup.find('div', class_='wgNTK')
                    if region_div:
                        region_mk = region_div.find('div', class_='MK')
                        if region_mk:
                            region_fotgx = region_mk.find('div', class_='biGQs _P fiohW fOtGX')
                            if region_fotgx and ": " in region_fotgx.text:
                                poi_info['region'] = region_fotgx.text.split(": ")[1].strip()
                
                # Chuẩn hóa tên vùng Thành phố Hồ Chí Minh sang Tiếng Việt
                if poi_info['region'] and any(h in poi_info['region'].lower() for h in ["ho chi minh", "hcm", "tphcm"]):
                    poi_info['region'] = "Thành phố Hồ Chí Minh"
                print("region:", poi_info['region'])

                # Xếp hạng trung bình & số lượng review (avgRating & numReviews)
                rating_data = json_ld_data.get('aggregateRating', {})
                if isinstance(rating_data, dict):
                    poi_info['avgRating'] = rating_data.get('ratingValue', '')
                    poi_info['numReviews'] = rating_data.get('reviewCount', 0)
                else:
                    poi_info['avgRating'] = ''
                    poi_info['numReviews'] = 0
                print("avgRating:", poi_info['avgRating'])
                print("numReviews:", poi_info['numReviews'])

                # Phân tích chi tiết số lượng review (đếm số sao 5, 4, 3, 2, 1)
                poi_info['numReviews_5'] = 0
                poi_info['numReviews_4'] = 0
                poi_info['numReviews_3'] = 0
                poi_info['numReviews_2'] = 0
                poi_info['numReviews_1'] = 0
                try:
                    page_text_clean = re.sub(r'\s+', '', soup.text)
                    # English
                    match = re.search(r'Excellent([\d,]+)(?:Very)?Good([\d,]+)Average([\d,]+)Poor([\d,]+)Terrible([\d,]+)', page_text_clean)
                    if match:
                        poi_info['numReviews_5'] = match.group(1).replace(',', '')
                        poi_info['numReviews_4'] = match.group(2).replace(',', '')
                        poi_info['numReviews_3'] = match.group(3).replace(',', '')
                        poi_info['numReviews_2'] = match.group(4).replace(',', '')
                        poi_info['numReviews_1'] = match.group(5).replace(',', '')
                    else:
                        # Tiếng Việt
                        # TripAdvisor tiếng Việt sử dụng cả 2 dạng: "Xuất sắc", "Tốt", "Trung bình", "Kém", "Rất tệ"
                        # và "Tuyệt vời", "Rất tốt", "Trung bình", "Tồi", "Kinh khủng"
                        pattern_vi = r'(?:Xuấtsắc|Tuyệtvời)([\d,.]+)(?:Tốt|Rấttốt)([\d,.]+)Trungbi[nh\u0300nh]*([\d,.]+)(?:Kém|Tồi)([\d,.]+)(?:Rấttệ|Kinhkhủng)([\d,.]+)'
                        match_vi = re.search(pattern_vi, page_text_clean)
                        if match_vi:
                            poi_info['numReviews_5'] = match_vi.group(1).replace(',', '').replace('.', '')
                            poi_info['numReviews_4'] = match_vi.group(2).replace(',', '').replace('.', '')
                            poi_info['numReviews_3'] = match_vi.group(3).replace(',', '').replace('.', '')
                            poi_info['numReviews_2'] = match_vi.group(4).replace(',', '').replace('.', '')
                            poi_info['numReviews_1'] = match_vi.group(5).replace(',', '').replace('.', '')
                except Exception as e:
                    pass
                print("numReviews_5:", poi_info['numReviews_5'])
                print("numReviews_4:", poi_info['numReviews_4'])
                print("numReviews_3:", poi_info['numReviews_3'])
                print("numReviews_2:", poi_info['numReviews_2'])
                print("numReviews_1:", poi_info['numReviews_1'])

                # 2. Truy cập tên miền tiếng Anh (.com) để bóc tách thông tin description và duration
                try:
                    english_url = url.replace("https://www.tripadvisor.com.vn", "https://www.tripadvisor.com")
                    poi_spider.url = english_url
                    eng_html = poi_spider.get_html()
                    
                    if eng_html and "<html" in eng_html.lower():
                        eng_soup = BeautifulSoup(eng_html, 'html.parser')
                        
                        # 2.1. Phân tích cú pháp JSON-LD của trang tiếng Anh
                        eng_json_ld_data = {}
                        eng_scripts = eng_soup.find_all('script', type='application/ld+json')
                        for s in eng_scripts:
                            try:
                                script_text = s.text or s.string
                                if not script_text:
                                    continue
                                data = json.loads(script_text)
                                if isinstance(data, dict):
                                    if data.get("@type") in target_types:
                                        eng_json_ld_data = data
                                        break
                                    if "@graph" in data and isinstance(data["@graph"], list):
                                        for item in data["@graph"]:
                                            if isinstance(item, dict) and item.get("@type") in target_types:
                                                eng_json_ld_data = item
                                                break
                                    if eng_json_ld_data:
                                        break
                            except Exception as e:
                                pass

                        # Bổ sung tọa độ dự phòng từ trang tiếng Anh nếu trang tiếng Việt thiếu
                        if not poi_info['latitude'] or not poi_info['longitude']:
                            eng_geo = eng_json_ld_data.get('geo', {})
                            if isinstance(eng_geo, dict) and 'latitude' in eng_geo and 'longitude' in eng_geo:
                                poi_info['latitude'] = str(eng_geo['latitude'])
                                poi_info['longitude'] = str(eng_geo['longitude'])
                                poi_info['source_coord'] = 'TripAdvisor'

                        # 2.2. Trích xuất mô tả (description)
                        needs_translation = False
                        if not poi_info['description']:
                            about_div_en = eng_soup.find(attrs={"data-automation": "attractionsAboutContent"})
                            if about_div_en:
                                desc_en = about_div_en.text.strip()
                                if not any(b.lower() in desc_en.lower() for b in BLACKLIST):
                                    poi_info['description'] = desc_en
                                    needs_translation = True

                        if poi_info['description'] and is_english(poi_info['description']):
                            needs_translation = True

                        # Dịch mô tả sang tiếng Việt
                        if poi_info['description'] and needs_translation:
                            print("Mô tả tiếng Anh gốc:", poi_info['description'])
                            try:
                                translated = GoogleTranslator(source='en', target='vi').translate(poi_info['description'])
                                if translated:
                                    poi_info['description'] = translated.strip()
                            except Exception as e:
                                print("Lỗi dịch thuật mô tả, tiến hành thử lại:", e)
                                for attempt in range(2):
                                    time.sleep(2)
                                    try:
                                        translated = GoogleTranslator(source='en', target='vi').translate(poi_info['description'])
                                        if translated:
                                            poi_info['description'] = translated.strip()
                                            break
                                    except Exception as re_e:
                                        print(f"Thử lại dịch lần {attempt+1} thất bại:", re_e)
                        
                        # 2.3. Trích xuất thời lượng (duration) - Chỉ tìm trong phần giới thiệu (About) để tránh lấy nhầm tour quảng cáo
                        about_section = eng_soup.find(attrs={"data-automation": "WebPresentation_AttractionAboutSectionGroup"}) or eng_soup.find(id="AR_ABOUT")
                        if about_section:
                            for s in about_section.find_all(string=re.compile(r"Duration:", re.I)):
                                parent = s.parent
                                if parent and parent.name not in ['script', 'style', 'head']:
                                    text = parent.text.strip()
                                    if len(text) < 100:
                                        poi_info['duration'] = text.replace("Duration: ", "").replace("Duration:", "").strip()
                                        break
                            if not poi_info['duration']:
                                for s in about_section.find_all(string=re.compile(r"Suggested duration:", re.I)):
                                    parent = s.parent
                                    if parent and parent.name not in ['script', 'style', 'head']:
                                        text = parent.text.strip()
                                        if len(text) < 100:
                                            poi_info['duration'] = text.replace("Suggested duration: ", "").replace("Suggested duration:", "").strip()
                                            break
                        
                        poi_info['duration'] = translate_duration(poi_info['duration'])
                except Exception as eng_e:
                    print("Lỗi khi cào dữ liệu bổ sung từ tên miền tiếng Anh:", eng_e)
                
                print("description:", poi_info['description'])
                print("duration:", poi_info['duration'])

                # Làm sạch ký tự xuống dòng (\n, \r) trong tất cả các chuỗi để tránh làm hỏng cấu trúc dòng của file CSV
                for key in poi_info:
                    if isinstance(poi_info[key], str):
                        poi_info[key] = poi_info[key].replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').strip()

                # Thêm vào danh sách kết quả tạm thời
                poi_info_list.append(poi_info)

                # Ghi/Thêm trực tiếp vào file CSV
                df_row = pd.DataFrame([poi_info])
                file_exists = os.path.exists(self.filename)
                df_row.to_csv(self.filename, mode='a', header=not file_exists, index=False)

                print("Đã cào thông tin POI thành công và lưu vào CSV!")

            except Exception as e:
                print("Lỗi khi cào thông tin POI từ URL:", url)
                failed_urls.append(url)
                print("Đã thêm URL vào danh sách lỗi (failed_urls).")
                print(e)

        print(f"\n{len(failed_urls)} URL bị lỗi: {failed_urls}")

        # Lưu danh sách URL POI bị lỗi vào file .txt để xử lý lại sau
        file_failed_urls = "output/poi_urls_failed.txt"
        with open(file_failed_urls, 'w') as file:
            for url in failed_urls:
                file.write(url + '\n')

        # Đóng trình duyệt khi hoàn thành
        try:
            poi_spider.browser.quit()
        except:
            pass

        # Đọc lại file CSV đầy đủ để trả về
        if os.path.exists(self.filename):
            self.poi_info_df = pd.read_csv(self.filename)

        return self.poi_info_df


# CHƯƠNG TRÌNH CHÍNH
if __name__ == '__main__':

    # Thu thập thông tin từ các URL POI
    start = time.time()

    scraper = PoiInfolScraper()
    poi_info_df = scraper.get_poi_info()

    end = time.time()

    # Hiển thị thời gian thực thi
    print('\nTổng thời gian chạy: %.2f s' % (end - start))