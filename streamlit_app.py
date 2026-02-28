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

# ==========================================
# 1. 크롬 제어 엔진 (목록 URL에서 최신화 추출)
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
        # 목록 페이지에서 최상단 회차 제목 태그 추출
        element = driver.find_element(By.CSS_SELECTOR, ".list-item .wr-subject a")
        match = re.search(r'(\d+(\.\d+)?)', element.text)
        if match: return float(match.group(1))
    except: return None
    return None

# ==========================================
# 2. Streamlit UI 및 데이터 연동
# ==========================================
st.set_page_config(page_title="나만의 웹툰 기록기 v2.0", layout="wide")
st.title("📚 웹툰 기록기 (URL 이원화 버전)")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheet_data():
    data = conn.read(ttl="0s")
    # 필수 컬럼 정의 (URL 분리)
    required_cols = ['제목', '내가본화수', '최신화', '보기URL', '목록URL']
    for col in required_cols:
        if col not in data.columns:
            data[col] = 0.0 if '화수' in col or '최신화' in col else ""
    return data[required_cols] # 컬럼 순서 고정

if 'df' not in st.session_state:
    try:
        st.session_state.df = load_gsheet_data()
    except:
        st.session_state.df = pd.DataFrame(columns=['제목', '내가본화수', '최신화', '보기URL', '목록URL'])

df = st.session_state.df

# --- 최신화 확인 버튼 ---
if st.button("🔄 전체 웹툰 최신화 자동 업데이트", width='stretch'):
    st.info("🚀 목록 URL에 접속하여 최신화를 수집합니다...")
    start_debug_chrome()
    
    progress_bar = st.progress(0)
    for i, row in df.iterrows():
        if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
            latest = fetch_latest_from_url(row['목록URL'])
            if latest:
                df.at[i, '최신화'] = latest
        progress_bar.progress((i + 1) / len(df))
    
    st.session_state.df = df
    st.success("✅ 모든 리스트의 최신 상태를 확인했습니다!")

# --- 리스트 강조 및 출력 ---
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

# --- 사이드바: 데이터 관리 및 신규 등록 ---
with st.sidebar:
    st.header("➕ 웹툰 추가/수정")
    with st.form("add_form", clear_on_submit=True):
        title = st.text_input("제목")
        my_ep = st.number_input("본 화수", min_value=0.0, step=1.0)
        view_url = st.text_input("바로보기 URL (현재 읽는 회차)")
        list_url = st.text_input("목록보기 URL (전체 회차 리스트)")
        submit = st.form_submit_state = st.form_submit_button("리스트에 추가")
        
        if submit and title:
            new_row = pd.DataFrame([[title, my_ep, 0.0, view_url, list_url]], 
                                   columns=['제목', '내가본화수', '최신화', '보기URL', '목록URL'])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.success("추가되었습니다. '구글 시트에 저장'을 눌러주세요.")

    st.divider()
    if st.button("💾 변경사항 구글 시트에 저장", width='stretch'):
        conn.update(data=st.session_state.df)
        st.success("시트 저장 완료!")

    if st.button("🔃 새로고침", width='stretch'):
        st.session_state.df = load_gsheet_data()
        st.rerun()