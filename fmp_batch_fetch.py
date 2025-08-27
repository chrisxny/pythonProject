import csv
import requests
import sqlite3
import time

# -------------------- 配置 --------------------
API_KEY = '7djxP4qVYLIpvVLlJAquBpK58kMBPMxD'   # 🔑 替换成你的 FMP API Key
BATCH_SIZE = 5                  # 每批查询的 ticker 数量
LIMIT = 1                       # 每个 ticker 查几期财报
API_URL = 'https://financialmodelingprep.com/api/v3/income-statement/{}?limit={}&period=quarter&apikey={}'

# -------------------- 读取 CSV --------------------
def read_tickers(csv_file):
    with open(csv_file, 'r') as file:
        reader = csv.reader(file)
        tickers = [row[1].strip() for row in reader if row]
    return tickers

# -------------------- 初始化 SQLite --------------------
def init_db():
    conn = sqlite3.connect('financials.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income_statements (
            symbol TEXT,
            date TEXT,
            revenue INTEGER,
            netIncome INTEGER,
            eps REAL,
            operatingIncome INTEGER,
            totalRevenue INTEGER,
            costOfRevenue INTEGER,
            grossProfit INTEGER,
            ebit INTEGER,
            weightedAverageShsOut INTEGER,
            PRIMARY KEY (symbol, date)
        )
    ''')
    conn.commit()
    return conn

# -------------------- 保存数据到 SQLite --------------------
def save_to_db(conn, statements):
    cursor = conn.cursor()
    for item in statements:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO income_statements
                (symbol, date, revenue, netIncome, eps, operatingIncome, totalRevenue,
                costOfRevenue, grossProfit, ebit, weightedAverageShsOut)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('symbol'),
                item.get('date'),
                item.get('revenue'),
                item.get('netIncome'),
                item.get('eps'),
                item.get('operatingIncome'),
                item.get('totalRevenue'),
                item.get('costOfRevenue'),
                item.get('grossProfit'),
                item.get('ebit'),
                item.get('weightedAverageShsOut'),
            ))
        except Exception as e:
            print(f"Error saving record for {item.get('symbol')} on {item.get('date')}: {e}")
    conn.commit()

# -------------------- 批量请求 API --------------------
def fetch_income_statements(tickers):
    url = API_URL.format(','.join(tickers), LIMIT, API_KEY)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} {response.text}")
            return []
    except Exception as e:
        print(f"Request failed: {e}")
        return []

# -------------------- 主流程 --------------------
def main():
    tickers = read_tickers('stocks.csv')
    conn = init_db()

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        print(f"Fetching batch: {batch}")
        data = fetch_income_statements(batch)

        # API 返回的数据可能是列表或嵌套列表（多个 ticker）
        if isinstance(data, list):
            all_statements = []
            for item in data:
                if isinstance(item, dict) and 'symbol' in item:
                    all_statements.append(item)
                elif isinstance(item, list):
                    all_statements.extend(item)
            save_to_db(conn, all_statements)

        time.sleep(1)  # 避免触发速率限制

    conn.close()
    print("✅ 数据获取并保存完成。")

if __name__ == '__main__':
    main()
