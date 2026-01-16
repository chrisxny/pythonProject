import os
import glob
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import re

# --- 配置区 ---
DESKTOP_PATH = os.path.join(os.environ['USERPROFILE'], 'Desktop')
CREDENTIALS_FILE = "credentials.json"
SPREADSHEET_NAME = "股票计划"
TARGET_SHEET = "Test Sheet"
FILE_PATTERN = "Portfolio_Positions_*.csv" 

# 锁定区域：G8:T17
START_ROW = 8
END_ROW = 17
START_COL_STR = 'G'
END_COL_STR = 'T'
SEARCH_RANGE = f"{START_COL_STR}{START_ROW}:{END_COL_STR}{END_ROW}"

MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}

def extract_date_from_filename(filename):
    match = re.search(r'([A-Za-z]{3})[-_](\d{1,2})[-_](\d{4})', filename)
    if match:
        month_str, day, year = match.groups()
        month = MONTH_MAP.get(month_str.capitalize(), 1)
        return datetime.datetime(int(year), month, int(day))
    return datetime.datetime(1970, 1, 1)

def get_latest_csv_by_filename_date():
    search_path = os.path.join(DESKTOP_PATH, FILE_PATTERN)
    files = glob.glob(search_path)
    if not files: return None
    return max(files, key=lambda f: extract_date_from_filename(os.path.basename(f)))

def convert_currency(val):
    if pd.isna(val) or str(val).strip() == "": return 0.0
    val_str = str(val).replace('$', '').replace(',', '').strip()
    if val_str.startswith('(') and val_str.endswith(')'):
        val_str = "-" + val_str[1:-1]
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def run_precision_sync():
    csv_path = get_latest_csv_by_filename_date()
    if not csv_path:
        print("❌ 错误：在桌面上没找到符合格式的 CSV 文件。")
        return

    print(f"📂 正在处理最新日期文件: {os.path.basename(csv_path)}")

    try:
        # 【重要修正】：增加 index_col=False 防止列偏移
        # 即使 CSV 末尾有多余逗号，这样也能保证 Symbol 在 'Symbol' 列
        df_raw = pd.read_csv(csv_path, index_col=False)
        
        # 如果依然担心名称对不上，我们直接用列索引（Symbol是第3列, index=2; Current Value是第8列, index=7）
        symbol_col = 'Symbol' if 'Symbol' in df_raw.columns else df_raw.columns[2]
        value_col = 'Current Value' if 'Current Value' in df_raw.columns else df_raw.columns[7]
        
        print(f"🔎 正在读取列: [{symbol_col}] 作为代码, [{value_col}] 作为市值")

        # 清理并转换
        df_clean = df_raw[df_raw[symbol_col].notna()].copy()
        df_clean[value_col] = df_clean[value_col].apply(convert_currency)
        
        summary = {}
        for _, row in df_clean.iterrows():
            raw_sym = str(row[symbol_col]).replace("**", "").strip()
            # 过滤掉末尾的说明文字行（Fidelity CSV 末尾通常有长串免责声明）
            if len(raw_sym) > 30: continue 
            
            target = "cash" if raw_sym.upper() == "SPAXX" else raw_sym
            summary[target] = summary.get(target, 0) + row[value_col]

        csv_symbols = set(summary.keys())

        # 2. 连接 Google Sheets
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)
        worksheet = client.open(SPREADSHEET_NAME).worksheet(TARGET_SHEET)

        # 3. 读取限定区域
        matrix = worksheet.get(SEARCH_RANGE, value_render_option='FORMULA')
        num_rows, num_cols = END_ROW - START_ROW + 1, 14
        full_matrix = [row + [""] * (num_cols - len(row)) for row in matrix]
        while len(full_matrix) < num_rows: full_matrix.append([""] * num_cols)

        updates = []
        start_col_idx = 7 # G列索引

        # 4. 更新/新增逻辑
        for symbol, value in summary.items():
            found = False
            for r_idx, row in enumerate(full_matrix):
                for c_idx, cell_value in enumerate(row):
                    cell_str = str(cell_value).strip()
                    is_match = (cell_str.lower() == "cash") if symbol == "cash" else (cell_str == symbol)
                    
                    if is_match:
                        if c_idx + 1 < num_cols:
                            right_val = str(row[c_idx + 1]).strip()
                            if not right_val.startswith('='):
                                actual_row, actual_col = r_idx + START_ROW, c_idx + start_col_idx + 1
                                updates.append({'range': gspread.utils.rowcol_to_a1(actual_row, actual_col), 'values': [[value]]})
                                print(f"✅ 更新: {symbol} -> {value}")
                            found = True
                        break
                if found: break
            
            if not found: # 第 14 行追加
                row_14_idx = 14 - START_ROW
                for c_idx in range(0, num_cols - 1, 2):
                    if not str(full_matrix[row_14_idx][c_idx]).strip():
                        actual_col_sym, actual_col_val = c_idx + start_col_idx, c_idx + start_col_idx + 1
                        updates.append({'range': gspread.utils.rowcol_to_a1(14, actual_col_sym), 'values': [[symbol]]})
                        updates.append({'range': gspread.utils.rowcol_to_a1(14, actual_col_val), 'values': [[value]]})
                        full_matrix[row_14_idx][c_idx], full_matrix[row_14_idx][c_idx+1] = symbol, value
                        print(f"✨ 新增: {symbol}")
                        break

        # 5. 清理已卖出逻辑
        ignore_labels = {"symbol", "ticker", "value", "price", "cash", "代码", "市值", "现价", "持仓", "账户"}
        for r_idx, row in enumerate(full_matrix):
            for c_idx, cell_value in enumerate(row):
                cell_str = str(cell_value).strip()
                if cell_str and not cell_str.startswith('=') and not cell_str.replace('.','').replace('-','').isdigit():
                    is_present = (cell_str.lower() == "cash" and "cash" in csv_symbols) or (cell_str in csv_symbols)
                    if not is_present and cell_str.lower() not in ignore_labels:
                        actual_row, actual_col = r_idx + START_ROW, c_idx + start_col_idx
                        updates.append({'range': gspread.utils.rowcol_to_a1(actual_row, actual_col), 'values': [['']]})
                        print(f"🧹 清理已卖出: {cell_str}")
                        if c_idx + 1 < num_cols:
                            if not str(row[c_idx + 1]).strip().startswith('='):
                                updates.append({'range': gspread.utils.rowcol_to_a1(actual_row, actual_col + 1), 'values': [['']]})

        # 6. A7 时间戳
        current_time = datetime.datetime.now().strftime("%m/%d/%Y")
        updates.append({'range': 'A7', 'values': [[f"Updated on {current_time}"]]})

        # 7. 提交
        if updates:
            worksheet.batch_update(updates)
            print(f"🎉 同步成功！")
        else:
            print("☕ 无需改动。")

    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    run_precision_sync()