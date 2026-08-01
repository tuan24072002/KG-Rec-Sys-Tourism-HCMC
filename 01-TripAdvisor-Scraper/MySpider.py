import random
import requests
import time

# pyrefly: ignore [missing-import]
from fake_useragent import UserAgent

# pyrefly: ignore [missing-import]
import undetected_chromedriver as uc

# Lấy nội dung HTML của một URL

class Spider(object):
    def __init__(self):
        # Khởi tạo user agent ngẫu nhiên
        user_agent = UserAgent()
    
        # Thiết lập headers để lưu user agent ngẫu nhiên
        headers = {
            'UserAgent': user_agent.chrome
        }

        # Thiết lập tùy chọn Chrome với User-Agent tùy chỉnh
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument(f'user-agent={headers["UserAgent"]}')

        # Tự động tìm đường dẫn của trình duyệt Chrome for Testing trong cache Selenium (Windows)
        import glob
        import os
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "selenium")
        version_main = None
        if os.path.exists(cache_dir):
            matches = glob.glob(os.path.join(cache_dir, "**", "chrome.exe"), recursive=True)
            if matches:
                chrome_options.binary_location = matches[0]
                # Trích xuất số phiên bản chính (major version) từ đường dẫn (ví dụ: .../150.0.7871.24/chrome.exe)
                parts = matches[0].split(os.sep)
                for part in parts:
                    if part.replace('.', '').isdigit() and '.' in part:
                        try:
                            version_main = int(part.split('.')[0])
                            break
                        except ValueError:
                            pass

        # Khởi tạo trình duyệt bằng undetected_chromedriver
        if version_main:
            print(f"Đã phát hiện phiên bản Chrome chính: {version_main}")
            self.browser = uc.Chrome(options=chrome_options, version_main=version_main)
        else:
            self.browser = uc.Chrome(options=chrome_options)

        # Kiểm tra User-Agent thực tế từ các tùy chọn của Chrome
        actual_user_agent = self.browser.execute_script("return navigator.userAgent;")
        print("User-Agent thực tế:", actual_user_agent, '\n')

        # Khởi tạo user agent ngẫu nhiên trong headers cho các yêu cầu HTTP
        user_agent = UserAgent()

        self.headers = {
            'authority': 'tripadvisor.com',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Google Chrome";v="92"',
            'sec-ch-ua-mobile': '?0',
            'upgrade-insecure-requests': '1',
            'user-agent': user_agent.chrome,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'en-US,en;q=0.9',
        }

        self.url = 'https://www.tripadvisor.com.vn/Attractions-g293925-Activities-Ho_Chi_Minh_City.html'  # URL để chạy thử
        self.flag = 1

    def get_proxies(self):
        with open('proxies.txt', 'r') as f:
            result = f.readlines()                  # Đọc tất cả các proxy trong danh sách
        proxy_ip = random.choice(result)[:-1]       # Chọn ngẫu nhiên một proxy
        L = proxy_ip.split(':')
        proxy_ip = {
            'http': 'http://{}:{}'.format(L[0], L[1]),
            'https': 'https://{}:{}'.format(L[0], L[1])
        }
        return proxy_ip

    def get_html(self):
        if self.flag <= 3:
            try:
                self.browser.get(self.url)
                time.sleep(2)  # Đợi trang tải xong lần đầu

                # Vòng lặp phát hiện CAPTCHA và Khóa IP
                while True:
                    self.html = self.browser.page_source
                    
                    # 1. Kiểm tra CAPTCHA
                    if "captcha-delivery.com" in self.html or "geo.captcha-delivery.com" in self.html or "dd-captcha" in self.html:
                        print("\n[!] Phát hiện chặn CAPTCHA của TripAdvisor / DataDome!")
                        print("[!] Vui lòng giải CAPTCHA trực tiếp trên cửa sổ Chrome đang mở...")
                        time.sleep(4)
                        continue
                    
                    # 2. Kiểm tra chặn IP
                    html_lower = self.html.lower()
                    is_blocked = (
                        "access to this page has been denied" in html_lower or
                        "access is temporarily restricted" in html_lower or
                        "unusual activity from your device" in html_lower or
                        "access denied" in html_lower or
                        "<title>forbidden</title>" in html_lower or
                        "403 forbidden" in html_lower
                    )
                    if is_blocked:
                        print("\n" + "="*60)
                        print("[!] PHÁT HIỆN TRIPADVISOR KHÓA IP CỦA BẠN!")
                        print("[!] TripAdvisor đã chặn kết nối từ địa chỉ IP hiện tại.")
                        print("[!] Vui lòng thay đổi VPN, proxy hoặc kết nối mạng để lấy IP mới.")
                        print("="*60)
                        input("[!] Sau khi đã đổi IP, nhấn [Enter] trên terminal để tải lại trang...")
                        print("[*] Đang tải lại trang...")
                        self.browser.get(self.url)
                        time.sleep(4)
                        continue
                    
                    break

                # Kiểm tra nếu lấy được nội dung HTML thành công
                if ("<html" in self.html.lower()) and "captcha-delivery.com" not in self.html:
                    print(f"Spider đã lấy nội dung HTML thành công!")
                else:
                    print(f"Spider thất bại trong việc lấy nội dung HTML.")
                
                # Nghỉ ngẫu nhiên một vài giây sau mỗi yêu cầu
                time.sleep(random.randint(1, 3))
                return self.html

            except Exception as e:
                print(f"Thử lại ({self.flag}/3) do lỗi: {e}")
                self.flag += 1
                return self.get_html()
        else:
            print("\n" + "="*60)
            print("[!] PHÁT HIỆN LỖI TRÌNH DUYỆT HOẶC KẾT NỐI MẠNG!")
            print("[!] Chrome không thể tải trang sau 3 lần thử.")
            print("[!] Vui lòng kiểm tra lại kết nối mạng hoặc cửa sổ trình duyệt.")
            print("="*60)
            input("[!] Sau khi kiểm tra/khôi phục kết nối, nhấn [Enter] để thử lại...")
            self.flag = 1
            return self.get_html()
    
    # HÀM: Ghi nội dung HTML ra file để phục vụ cho việc gỡ lỗi
    def write_html(self):
        # Lấy phần đuôi của URL làm tên file HTML
        truncated_url = self.url[len("https://www.tripadvisor.com.vn/"):]
        
        # Ghi nội dung vào thư mục html/
        with open(f"html/{truncated_url}", "w", encoding="utf-8") as file:
            file.write(self.html)

        print("Đã ghi nội dung HTML ra file thành công.")


if __name__ == '__main__':
    spider = Spider()
    spider.get_html()
    spider.write_html()