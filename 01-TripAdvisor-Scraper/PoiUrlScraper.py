import os
import json
from bs4 import BeautifulSoup

# Thư viện tự định nghĩa
import MySpider


# Lấy tất cả các URL trang chi tiết địa điểm du lịch (POI) của khu vực từ các trang danh sách
class PoiUrlScraper(object):
    def __init__(self):

        # Trang danh sách tất cả các POI tại Thành phố Hồ Chí Minh
        self.listing_url = 'https://www.tripadvisor.com.vn/Attractions-g293925-Activities-Ho_Chi_Minh_City.html'

        # Lưu kết quả vào các file này
        self.filename = "output/poi_urls.txt"
        self.categories_filename = "output/poi_categories.json"

        # Tổng số trang danh sách cần quét (mỗi trang hiển thị 30 địa điểm)
        # Đối với TP.HCM, ước tính khoảng 158 trang (~4700+ địa điểm thực tế)
        self.num_page = 158

        # Khởi tạo các danh sách và từ điển rỗng
        self.poi_url_list = []
        self.poi_categories = {}


    # HÀM: Lấy URL và Thể loại của các POI từ trang danh sách
    def get_poi_urls(self):
        
        # Tải bản đồ ánh xạ danh mục thể loại nếu file đã tồn tại
        if os.path.exists(self.categories_filename):
            try:
                with open(self.categories_filename, 'r', encoding='utf-8') as file:
                    self.poi_categories = json.load(file)
            except Exception as e:
                print(f"Cảnh báo: Không thể tải file thể loại đã lưu trước đó: {e}")

        # Nếu file .txt lưu trữ URL POI đã tồn tại, đọc trực tiếp danh sách URL từ file đó
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as file:
                self.poi_url_list = [line.strip() for line in file]

            # Trả về danh sách URL tải từ file ngoài
            print(f"\nĐã tải {len(self.poi_url_list)} URL từ file {self.filename}")
            return self.poi_url_list

        # Ngược lại, nếu chưa có file, sinh danh sách các trang danh sách của TP.HCM dựa trên num_page
        listing_urls = []
        listing_url_parts = self.listing_url.split('-Activities-')
        for page in range(0, self.num_page):
            new_listing_url = listing_url_parts[0]+'-Activities-oa{}-'.format(30 * page)+listing_url_parts[1]
            listing_urls.append(new_listing_url)

        # Khởi tạo một phiên bản spider để tái sử dụng cùng một cửa sổ Chrome
        listing_spider = MySpider.Spider()

        counter = 0
        for listing_url in listing_urls:
            counter += 1
            print(f"\nTiến trình: {counter}/{self.num_page}")

            # Thử mở từng trang danh sách trong danh sách URL
            try:
                listing_spider.url = listing_url

                # Lấy nội dung HTML và lưu vào thư mục html để debug
                html = listing_spider.get_html()
                listing_spider.write_html()

                # Phân tích cú pháp HTML
                soup = BeautifulSoup(html, 'html.parser')

            except Exception as e:
                print(f"Không thể lấy nội dung HTML từ URL: {listing_url}, lỗi: {e}")
                continue

            # Phân tích cú pháp các thẻ card cấp cao đại diện cho địa điểm trên trang danh sách
            for a in soup.find_all('a', href=True):
                href = a['href']
                if "Attraction_Review-" in href and "-g293925-" in href and a.text.strip() and not a.text.strip().isdigit():
                    # Loại bỏ định danh neo/hạt (fragment) để tránh trùng lặp liên kết (ví dụ: #REVIEWS)
                    clean_href = href.split('#')[0]
                    poi_url = 'https://www.tripadvisor.com.vn' + clean_href
                    if poi_url not in self.poi_url_list:
                        self.poi_url_list.append(poi_url)

                    # Tìm thẻ div container bên ngoài bao quanh toàn bộ card
                    p = a.parent
                    card_container = None
                    while p and p.name != 'html':
                        if p.name == 'div' and 'hZuqH' in p.get('class', []):
                            card_container = p
                        p = p.parent

                    if card_container:
                        cat_div = card_container.find('div', class_=lambda c: c and 'yzLvM' in c)
                        category = cat_div.text.strip() if cat_div else ""

                        # Làm sạch các chuỗi trạng thái hoạt động (như "Đang mở cửa", "Đóng cửa")
                        for status in ["Đang mở cửa", "Đóng cửa", "Mở cửa"]:
                            if status in category:
                                category = category.replace(status, "").strip()
                        category = category.replace("•", " • ").replace("  ", " ").strip()

                        self.poi_categories[poi_url] = category

        # Đóng trình duyệt sau khi hoàn thành
        try:
            listing_spider.browser.quit()
        except:
            pass

        # Lưu danh sách URL POI vào file .txt
        with open(self.filename, 'w', encoding='utf-8') as file:
            for url in self.poi_url_list:
                file.write(url + '\n')

        # Lưu từ điển thể loại địa điểm vào file JSON
        try:
            with open(self.categories_filename, 'w', encoding='utf-8') as file:
                json.dump(self.poi_categories, file, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Lỗi khi lưu thể loại vào file JSON: {e}")

        # Trả về danh sách URL địa điểm
        print(f"\nĐã thu thập và lưu trữ {len(self.poi_url_list)} URL địa điểm (POI).")
        return self.poi_url_list
    

    # HÀM: In danh sách URL ra màn hình
    def print_poi_urls(self):
        for poi_url in self.poi_url_list:
            print(poi_url)



# CHƯƠNG TRÌNH CHÍNH
if __name__ == '__main__':

    # Thu thập tất cả URL địa điểm từ các trang danh sách của Thành phố Hồ Chí Minh
    scraper = PoiUrlScraper()
    poi_urls = scraper.get_poi_urls()

    # In tất cả các URL
    #scraper.print_poi_urls()
