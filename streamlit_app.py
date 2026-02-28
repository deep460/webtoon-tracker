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

# 📜 Version History (v2.2.3)
# - 'multiple values for keyword argument type' 에러 해결
# - secrets 인증 정보와 connection 객체 생성 로직 최적화

# ==========================================
# 1. 크롬 제어 엔진 (Remote Debugging)
# ==========================================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_PATH = r"C:\sel_debug_profile"

def start_debug_chrome():
    if not os.path.exists(USER_DATA_PATH):
        os.makedirs(USER_DATA_PATH)
    subprocess.Popen([
        CHROME_PATH, 
        "--remote-debugging-port=9222", 
        f"--user-data-dir={USER_DATA_PATH}"
    ])
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
# 2. 구글 시트 연결 및 데이터 로드 (v2.2.3)
# ==========================================
st.set_page_config(page_title="Webtoon Tracker v2.2.3", layout="wide")
st.title("📚 웹툰 기록기 (v2.2.3 - 연결 성공 모드)")

# 💡 [핵심 해결책] 
# secrets.toml의 정보를 별도로 가공하지 않고 st.connection이 직접 읽게 합니다.
# 단, private_key의 \n 에러를 방지하기 위해 환경 변수를 직접 건드리지 않고 
# 아래와 같이 연결을 설정합니다.
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 정상적으로 시트 읽기 시도
        return conn.read(ttl="0s")
    except Exception as e:
        # 만약 여기서 Invalid Private Key 에러가 다시 나면 상세 로그 출력
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '보기URL', '목록URL'])

# 데이터 초기 로드
if 'df' not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# ==========================================
# 3. 메인 UI 로직
# ==========================================

col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🔄 전체 최신화 자동 확인", width='stretch'):
        if df.empty:
            st.warning("데이터가 없습니다.")
        else:
            st.info("🚀 최신화를 수집 중입니다...")
            start_debug_chrome()
            progress_bar = st.progress(0)
            for i, row in df.iterrows():
                if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
                    latest = fetch_latest_from_url(row['목록URL'])
                    if latest:
                        df.at[i, '최신화'] = latest
                progress_bar.progress((i + 1) / len(df))
            st.session_state.df = df
            st.success("✅ 확인 완료!")

# 리스트 출력
def highlight_new(row):
    try:
        if row['최신화'] > row['내가본화수']:
            return ['background-color: #ff4b4b; color: white'] * len(row)
    except: pass
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

with st.sidebar:
    st.header("⚙️ 데이터 관리")
    if st.button("💾 변경사항 구글 시트에 저장", width='stretch'):
        try:
            conn.update(data=st.session_state.df)
            st.success("시트 저장 성공!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
    
    if st.button("🔃 시트 데이터 새로고침", width='stretch'):
        st.session_state.df = load_data()
        st.rerun()