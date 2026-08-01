import re
from bs4 import BeautifulSoup
import time
import pandas as pd
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Thư viện tự định nghĩa
import MySpider
import PoiInfoScraper

class ReviewScraper(object):
    
    def __init__(self):
        # comment lại để crawl trước review của những poi hiện có, tối ưu thời gian
        self.poi_info_df = pd.read_csv("output/poi_info.csv").dropna(subset=['url', 'numReviews'])
        # poi_info_scraper = PoiInfoScraper.PoiInfolScraper()
        # self.poi_info_df = poi_info_scraper.get_poi_info()

        self.filename = "output/reviews.csv"
        self.review_df = pd.DataFrame()
        

    def get_review(self):
        # 1. Tải danh sách các trang đã được cào từ file output/scraped_pages.txt
        scraped_pages_file = "output/scraped_pages.txt"
        scraped_pages = set()
        if os.path.exists(scraped_pages_file):
            with open(scraped_pages_file, "r", encoding="utf-8") as f:
                scraped_pages = set(line.strip() for line in f if line.strip())
            print(f"\nĐã tải {len(scraped_pages)} trang đánh giá đã cào trước đó.")

        # 2. Kiểm tra xem những trang review nào đã được cào để bỏ qua khởi chạy Chrome nếu đã hoàn tất
        all_review_urls = []
        for index, row in self.poi_info_df.iterrows():
            poi_url = row["url"]
            num_reviews = row["numReviews"]
            num_page = int(num_reviews / 10) + 1
            review_urls_parts = poi_url.split('-Reviews-')
            for page in range(0, num_page):
                new_review_url = review_urls_parts[0]+'-Reviews-or{}-'.format(10 * page)+review_urls_parts[1]
                all_review_urls.append(new_review_url)

        remaining_urls = [u for u in all_review_urls if u not in scraped_pages]
        print(f"Tổng số trang review cần cào: {len(all_review_urls)}, còn lại: {len(remaining_urls)}")

        if not remaining_urls:
            print("\n[+] Tất cả các URL trang review đã được cào thành công!")
            if os.path.exists(self.filename):
                self.review_df = pd.read_csv(self.filename)
                print(f"Đã tải {len(self.review_df)} review từ file {self.filename}")
            return self.review_df

        # Khởi tạo một phiên bản spider để tái sử dụng cùng cửa sổ Chrome
        review_spider = MySpider.Spider()

        poi_counter = 0
        num_poi = self.poi_info_df.shape[0]

        # Với mỗi POI
        for index, row in self.poi_info_df.iterrows():
            poi_counter += 1

            poi_id = row["id"]
            poi_url = row["url"]
            num_reviews = row["numReviews"]
            num_page = int(num_reviews / 10) + 1

            # Lấy tất cả các URL trang review cho POI này
            review_urls = []
            review_urls_parts = poi_url.split('-Reviews-')
            for page in range(0, num_page):
                new_review_url = review_urls_parts[0]+'-Reviews-or{}-'.format(10 * page)+review_urls_parts[1]
                review_urls.append(new_review_url)

            total_num = len(review_urls)
            counter = 0

            # Duyệt qua từng URL review
            for url in review_urls:
                counter += 1

                # Nếu URL trang này đã được cào trước đó, bỏ qua nó
                if url in scraped_pages:
                    continue

                print(f"\nTiến trình: POI - {poi_counter}/{num_poi}; trang review - {counter}/{total_num}")

                try:
                    review_spider.url = url

                    # Lấy nội dung HTML
                    html = review_spider.get_html()

                    # Kiểm tra nếu lấy nội dung HTML thành công, nếu không thì bỏ qua
                    if not html or "<html" not in html.lower():
                        continue

                    soup = BeautifulSoup(html, 'html.parser')

                    # Thu thập các review
                    reviews = soup.find_all('div', class_='_c', attrs={'data-automation': 'reviewCard'})

                    if not reviews:
                        print(f"Không tìm thấy đánh giá nào trên trang này. Đã đạt đến trang cuối cùng cho POI {poi_id}.")
                        remaining_for_this_poi = review_urls[counter-1:]
                        with open(scraped_pages_file, "a", encoding="utf-8") as f:
                            for rem_url in remaining_for_this_poi:
                                f.write(rem_url + "\n")
                                scraped_pages.add(rem_url)
                        break

                    page_reviews = []
                    for review in reviews:
                        # Từ điển để lưu trữ thông tin cho một review đơn lẻ
                        review_info = {}

                        review_info['poiID'] = poi_id
                        print("\npoiID:", review_info['poiID'])

                        # 1. Tên người dùng (Username)
                        username_div = review.find('div', class_='tknvo ccudK Rb I o')
                        username = ''
                        if username_div and username_div.a and username_div.a.has_attr('href'):
                            username = username_div.a['href'].strip().replace('/Profile/', '')
                        else:
                            profile_a = review.find('a', href=lambda h: h and h.startswith('/Profile/'))
                            if profile_a:
                                username = profile_a['href'].strip().replace('/Profile/', '')
                        review_info['username'] = username
                        print("username:", review_info['username'])

                        # 2. Địa điểm (Location - lọc bỏ phần text đóng góp đóng vai trò là contribution)
                        vylts_div = review.find('div', class_='vYLts')
                        location = ''
                        if vylts_div:
                            spans = vylts_div.find_all('span')
                            for s in spans:
                                text = s.text.strip()
                                if "đóng góp" not in text.lower() and "contribution" not in text.lower():
                                    location = text
                                    break
                        review_info['location'] = location
                        print("location:", review_info['location'])

                        # 3. Liên kết / ID của Review
                        title_a = review.find('a', href=lambda h: h and h.startswith('/ShowUserReviews-'))
                        review_url = ''
                        review_id = ''
                        if title_a:
                            href = title_a['href']
                            review_url = "https://www.tripadvisor.com.vn" + href
                            match = re.search(r'-r(\d+)-', href)
                            if match:
                                review_id = match.group(1)
                        review_info['review_id'] = review_id
                        review_info['review_url'] = review_url
                        print("review_id:", review_info['review_id'])
                        print("review_url:", review_info['review_url'])

                        # 4. Tiêu đề và Nội dung qua class='yCeTE'
                        yCeTE_spans = review.find_all('span', class_='yCeTE')
                        title = ''
                        content = ''
                        if len(yCeTE_spans) >= 2:
                            title = yCeTE_spans[0].text.strip()
                            content = yCeTE_spans[1].text.strip()
                        elif len(yCeTE_spans) == 1:
                            content = yCeTE_spans[0].text.strip()
                        review_info['title'] = title
                        review_info['content'] = content
                        print("title:", review_info['title'])
                        print("content:", review_info['content'][:100] + "..." if len(content) > 100 else content)

                        # 5. Số điểm đánh giá (Rating)
                        rating_svg = review.find('svg', attrs={'data-automation': 'bubbleRatingImage'})
                        if not rating_svg:
                            rating_svg = review.find('svg', class_=lambda c: c and 'UctUV' in c)
                        
                        rating = ''
                        if rating_svg:
                            title_tag = rating_svg.find('title')
                            if title_tag:
                                match = re.search(r'\d+', title_tag.text)
                                if match:
                                    rating = match.group(0)
                            else:
                                aria = rating_svg.get('aria-label', '')
                                match = re.search(r'\d+', aria)
                                if match:
                                    rating = match.group(0)
                        review_info['rating'] = rating
                        print("rating:", review_info['rating'])

                        # 6. Ngày viết đánh giá (Date)
                        date_div = review.find(class_='BNelO')
                        date = ''
                        if date_div:
                            first_div = date_div.find('div')
                            if first_div:
                                date = first_div.text.strip().replace('Đã viết vào ', '').replace('Written ', '')
                        review_info['date'] = date
                        print("date:", review_info['date'])

                        # 7. Nhóm người dùng (User group)
                        user_group = ''
                        for tag in review.find_all(['div', 'span']):
                            if tag.text and '•' in tag.text and not tag.find_parent('div', class_='hcVjp'):
                                user_group = tag.text.split('•')[-1].strip()
                                break
                        review_info['user_group'] = user_group
                        print("user_group:", review_info['user_group'])

                        page_reviews.append(review_info)
                        print("Đã cào review thành công!")

                    # Nếu tìm thấy review trên trang, ghi chúng vào file CSV
                    if page_reviews:
                        df_row = pd.DataFrame(page_reviews)
                        file_exists = os.path.exists(self.filename)
                        df_row.to_csv(self.filename, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')

                    # Luôn lưu URL trang này vào danh sách đã cào thành công để tránh cào lại
                    with open(scraped_pages_file, "a", encoding="utf-8") as f:
                        f.write(url + "\n")
                    scraped_pages.add(url)

                except Exception as e:
                    print("Lỗi khi cào review từ URL:", url)
                    print(e)

        # Đóng trình duyệt khi hoàn thành
        try:
            review_spider.browser.quit()
        except:
            pass

        # Đọc lại file CSV cuối cùng để trả về DataFrame đầy đủ
        if os.path.exists(self.filename):
            self.review_df = pd.read_csv(self.filename)
        
        return self.review_df
    


# CHƯƠNG TRÌNH CHÍNH
if __name__ == '__main__':

    # Thu thập đánh giá cho từng URL
    start=time.time()

    scraper = ReviewScraper()
    review_df = scraper.get_review()

    end=time.time()

    # Hiển thị thời gian thực thi
    print('\nTổng thời gian chạy: %.2f s'%(end-start))
