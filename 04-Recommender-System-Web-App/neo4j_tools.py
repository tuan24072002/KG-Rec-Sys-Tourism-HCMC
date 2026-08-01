# Nạp các thư viện cần thiết

import pandas as pd
import os
import configparser


# HÀM: Lấy thông tin xác thực kết nối Neo4j từ tệp cấu hình hoặc sử dụng giá trị mặc định
def get_credential():

    # Sử dụng tệp ini cho thông tin xác thực, ngược lại cung cấp các thông tin mặc định
    HOST = 'neo4j://localhost'
    USERNAME = 'neo4j'
    DATABASE = 'neo4j'
    PASSWORD = 'password'
    

    NEO4J_CONF_FILE = 'neo4j.ini'
    '''
    if os.path.exists(NEO4J_CONF_FILE):
        print("True")
    else:
        print("False")
    '''

    if NEO4J_CONF_FILE is not None and os.path.exists(NEO4J_CONF_FILE):
        config = configparser.RawConfigParser()
        config.read(NEO4J_CONF_FILE)
        HOST = config['NEO4J']['HOST']
        DATABASE = config['NEO4J'].get('DATABASE', 'neo4j')
        USERNAME = config['NEO4J'].get('USERNAME', DATABASE)
        PASSWORD = config['NEO4J']['PASSWORD']
        print('Đang sử dụng cấu hình cơ sở dữ liệu Neo4j tùy chỉnh')
    else:
        print('Không tìm thấy tệp thuộc tính cơ sở dữ liệu Neo4j, đang sử dụng giá trị mặc định')
    
    # Thiết lập định dạng hiển thị cho các giá trị thực (float), tránh ký hiệu khoa học cho số lớn
    pd.options.display.float_format = '{:.0f}'.format

    return HOST, USERNAME, DATABASE, PASSWORD


_cached_database = None

def get_database_name():
    global _cached_database
    if _cached_database is None:
        try:
            _, _, db, _ = get_credential()
            _cached_database = db
        except Exception:
            _cached_database = 'neo4j'
    return _cached_database


# HÀM: Hàm bổ trợ để chạy truy vấn bằng driver Python có hoặc không có tham số
def run(driver, query, params=None, database=None):
    if database is None:
        database = get_database_name()
    with driver.session(database=database) as session:
        if params is not None:
            return [r for r in session.run(query, params)]
        else:
            return [r for r in session.run(query)]

# Điểm khởi chạy (entry point)
if __name__ == '__main__':

    # Kết nối Neo4j

    # Lấy thông tin xác thực để kết nối Neo4j
    HOST, USERNAME, DATABASE, PASSWORD = get_credential()

    print(HOST)
    print(USERNAME)
    print(DATABASE)
    print(PASSWORD)