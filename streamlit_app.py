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

# 📜 Version History (v1.9.2)
# - KeyError: '최신화' 방어 로직 추가
# - Streamlit 최신 문법(width='stretch') 반영 및 경고 해결

# ==========================================
# 1. 디버깅 크롬 및 추출 엔진 설정
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

def fetch_latest_from_url(url):
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(4) 
        element = driver.find_element(By.CSS_SELECTOR, ".list-item .wr-subject a")
        match = re.search(r'(\d+(\.\d+)?)', element.text)
        if match: return float(match.group(1))
    except: return None
    return None

# ==========================================
# 2. Streamlit UI 및 구글 시트 연동
# ==========================================
st.set_page_config(page_title="나만의 웹툰 기록기", layout="wide")
st.title("📚 웹툰 기록기 (v1.9.2)")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheet_data():
    data = conn.read(ttl="0s")
    # [방어 로직] 필수 컬럼이 없으면 빈 값으로 생성
    for col in ['제목', '내가본화수', '최신화', 'URL']:
        if col not in data.columns:
            data[col] = 0.0 if '화수' in col or '최신화' in col else ""
    return data

if 'df' not in st.session_state:
    try:
        st.session_state.df = load_gsheet_data()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        st.session_state.df = pd.DataFrame(columns=['제목', '내가본화수', '최신화', 'URL'])

df = st.session_state.df

# --- 상단 컨트롤 ---
col1, col2 = st.columns([8, 2])
with col2:
    # width='stretch'로 경고 해결
    if st.button("🔄 사이트 최신화 자동 확인", width='stretch'):
        st.info("🚀 크롬 엔진 가동 중...")
        start_debug_chrome()
        
        progress_bar = st.progress(0)
        for i, row in df.iterrows():
            if pd.notna(row['URL']) and str(row['URL']).startswith('http'):
                latest = fetch_latest_from_url(row['URL'])
                if latest:
                    df.at[i, '최신화'] = latest
            progress_bar.progress((i + 1) / len(df))
        
        st.session_state.df = df
        st.success("✅ 업데이트 확인 완료!")

# --- 리스트 출력 (KeyError 방지) ---
def highlight_new(row):
    try:
        # 컬럼 존재 여부 재확인 후 비교
        if '최신화' in row and '내가본화수' in row:
            if row['최신화'] > row['내가본화수']:
                return ['background-color: #ff4b4b; color: white'] * len(row)
    except:
        pass
    return [''] * len(row)

st.subheader("📋 내 웹툰 목록")
st.dataframe(
    df.style.apply(highlight_new, axis=1),
    column_config={"URL": st.column_config.LinkColumn("링크")},
    width='stretch' # use_container_width 대신 stretch 사용
)

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 데이터 관리")
    if st.button("💾 구글 시트에 저장"):
        try:
            conn.update(data=st.session_state.df)
            st.success("저장 완료!")
        except Exception as e:
            st.error(f"저장 실패: {e}")

    if st.button("🔃 새로고침"):
        st.session_state.df = load_gsheet_data()
        st.rerun()

st.divider()
st.caption("v1.9.2 | KeyError 방지 및 최신 문법 적용 버전")