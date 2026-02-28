import streamlit as st
import pandas as pd
import subprocess
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from streamlit_gsheets import GSheetsConnection

# 📜 Version History (v2.2.0)
# - 구글 시트 쓰기 권한(Service Account) 복구
# - v2.1.0의 로컬 저장 방식을 다시 GSheets API 방식으로 전환

# ==========================================
# 1. 크롬 제어 엔진 (Remote Debugging)
# ==========================================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_PATH = r"C:\sel_debug_profile"

def start_debug_chrome():
    if not os.path.exists(USER_DATA_PATH):
        os.makedirs(USER_DATA_PATH)
    subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", f"--user-data-dir={USER_DATA_PATH}"])
    time.sleep(3)

def fetch_latest_from_url(list_url):
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(list_url)
        time.sleep(4) 
        element = driver.find_element(By.CSS_SELECTOR, ".list-item .wr-subject a")
        match = re.search(r'(\d+(\.\d+)?)', element.text)
        if match: return float(match.group(1))
    except: return None
    return None

# ==========================================
# 2. UI 및 구글 시트 API 연동
# ==========================================
st.set_page_config(page_title="Webtoon Tracker API", layout="wide")
st.title("📚 웹툰 기록기 (구글 시트 API 연동)")

# [핵심] 서비스 계정(API)을 사용하여 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheet_data():
    # ttl=0으로 설정하여 항상 최신 데이터를 읽어옵니다.
    return conn.read(ttl="0s")

if 'df' not in st.session_state:
    try:
        st.session_state.df = load_gsheet_data()
    except Exception as e:
        st.error(f"API 인증 실패: {e}")
        st.session_state.df = pd.DataFrame(columns=['제목', '내가본화수', '최신화', '보기URL', '목록URL'])

df = st.session_state.df

# --- 상단 업데이트 버튼 ---
if st.button("🔄 사이트 최신화 자동 업데이트", width='stretch'):
    st.info("🚀 API 권한을 사용하여 데이터를 갱신 중...")
    start_debug_chrome()
    
    progress_bar = st.progress(0)
    for i, row in df.iterrows():
        if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
            latest = fetch_latest_from_url(row['목록URL'])
            if latest:
                df.at[i, '최신화'] = latest
        progress_bar.progress((i + 1) / len(df))
    
    st.session_state.df = df
    st.success("✅ 확인 완료! 시트에 저장하려면 왼쪽 버튼을 누르세요.")

# --- 리스트 출력 ---
def highlight_new(row):
    if row['최신화'] > row['내가본화수']:
        return ['background-color: #ff4b4b; color: white'] * len(row)
    return [''] * len(row)

st.subheader("📋 내 웹툰 목록")
st.dataframe(
    df.style.apply(highlight_new, axis=1),
    column_config={
        "보기URL": st.column_config.LinkColumn("📖 바로보기"),
        "목록URL": st.column_config.LinkColumn("📂 목록보기"),
    },
    width='stretch'
)

# --- 사이드바 관리 ---
with st.sidebar:
    st.header("⚙️ 데이터 관리")
    if st.button("💾 변경사항 구글 시트에 저장", width='stretch'):
        try:
            # API 권한이 있으면 정상 작동합니다.
            conn.update(data=st.session_state.df)
            st.success("성공적으로 시트에 저장되었습니다!")
        except Exception as e:
            st.error(f"저장 실패 (권한 문제 가능성): {e}")

    if st.button("🔃 새로고침", width='stretch'):
        st.session_state.df = load_gsheet_data()
        st.rerun()

st.divider()
st.caption("v2.2.0 | Service Account API 연동 모드")