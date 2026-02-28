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
# 1. 크롬 제어 엔진 (최신화 수집용)
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
        time.sleep(3) 
        # 뉴토끼 등 리스트 아이템 추출 규칙
        element = driver.find_element(By.CSS_SELECTOR, ".list-item .wr-subject a")
        match = re.search(r'(\d+(\.\d+)?)', element.text)
        if match: return float(match.group(1))
    except: return None
    return None

# ==========================================
# 2. 구글 시트 연결 설정
# ==========================================
st.set_page_config(page_title="Webtoon Tracker v2.2.5", layout="wide")
st.title("📚 웹툰 기록기 (v2.2.5 - 호환성 패치 완료)")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        expected_cols = ['제목', '내가본화수', '최신화', '보기URL', '목록URL']
        if data.empty:
            return pd.DataFrame(columns=expected_cols)
        # 필요한 컬럼이 시트에 없을 경우 자동 생성
        for col in expected_cols:
            if col not in data.columns:
                data[col] = 0.0 if '화수' in col or '최신화' in col else ""
        return data[expected_cols]
    except:
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# ==========================================
# 3. 메인 UI 및 컨트롤
# ==========================================

# (1) 업데이트 버튼
col1, col2 = st.columns([8, 2])
with col2:
    # variant="primary"를 제거하여 구버전 에러 해결
    if st.button("🔄 전체 최신화 자동 확인", use_container_width=True):
        start_debug_chrome()
        progress_bar = st.progress(0)
        for i, row in st.session_state.df.iterrows():
            if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
                latest = fetch_latest_from_url(row['목록URL'])
                if latest:
                    st.session_state.df.at[i, '최신화'] = latest
            progress_bar.progress((i + 1) / len(st.session_state.df))
        st.success("✅ 확인 완료!")

# (2) 목록 표시
def highlight_new(row):
    try:
        if float(row['최신화']) > float(row['내가본화수']):
            return ['background-color: #ff4b4b; color: white'] * len(row)
    except: pass
    return [''] * len(row)

st.subheader("📋 내 웹툰 목록")
st.dataframe(
    st.session_state.df.style.apply(highlight_new, axis=1),
    column_config={
        "보기URL": st.column_config.LinkColumn("📖 바로보기"),
        "목록URL": st.column_config.LinkColumn("📂 목록보기"),
    },
    use_container_width=True,
    height=400
)

st.divider()

# (3) 입력 및 수정 UI
st.subheader("➕ 웹툰 추가 및 정보 수정")
with st.form("add_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    new_title = c1.text_input("웹툰 제목")
    new_my = c2.number_input("내가 본 화수", min_value=0.0, step=0.1)
    new_latest = c3.number_input("최신 화수", min_value=0.0, step=0.1)
    
    c4, c5 = st.columns(2)
    new_view_url = c4.text_input("보기 URL (현재 보던 페이지)")
    new_list_url = c5.text_input("목록 URL (전체 리스트)")
    
    submit = st.form_submit_button("목록에 추가 / 수정")
    
    if submit and new_title:
        if new_title in st.session_state.df['제목'].values:
            idx = st.session_state.df[st.session_state.df['제목'] == new_title].index[0]
            st.session_state.df.at[idx, '내가본화수'] = new_my
            st.session_state.df.at[idx, '최신화'] = new_latest
            st.session_state.df.at[idx, '보기URL'] = new_view_url
            st.session_state.df.at[idx, '목록URL'] = new_list_url
        else:
            new_row = {
                '제목': new_title, '내가본화수': new_my, '최신화': new_latest,
                '보기URL': new_view_url, '목록URL': new_list_url
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        st.rerun()

# (4) 사이드바 관리
with st.sidebar:
    st.header("⚙️ 관리 도구")
    if st.button("💾 구글 시트에 최종 저장", use_container_width=True):
        try:
            conn.update(data=st.session_state.df)
            st.success("시트 저장 완료!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
            
    st.divider()
    delete_target = st.selectbox("삭제할 웹툰 선택", ["선택하세요"] + list(st.session_state.df['제목'].values))
    # 여기서도 variant를 제거했습니다.
    if st.button("🗑️ 선택 항목 삭제", use_container_width=True):
        if delete_target != "선택하세요":
            st.session_state.df = st.session_state.df[st.session_state.df['제목'] != delete_target]
            st.rerun()

st.caption("v2.2.5 | 'variant' 인자 제거로 안정성 확보")