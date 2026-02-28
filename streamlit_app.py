import streamlit as st
import pandas as pd
import subprocess
import time
import re
import os
from datetime import datetime
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
        element = driver.find_element(By.CSS_SELECTOR, ".list-item .wr-subject a")
        match = re.search(r'(\d+(\.\d+)?)', element.text)
        if match: return float(match.group(1))
    except: return None
    return None

# ==========================================
# 2. 구글 시트 연결 및 데이터 로드
# ==========================================
st.set_page_config(page_title="Webtoon Tracker v2.2.7", layout="wide")
st.title("📚 웹툰 기록기 (v2.2.7 - 상태 업데이트 모드)")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        expected_cols = ['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL']
        if data.empty:
            return pd.DataFrame(columns=expected_cols)
        # 필요한 컬럼 자동 생성 및 누락 데이터 보정
        for col in expected_cols:
            if col not in data.columns:
                data[col] = ""
        return data[expected_cols]
    except:
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# ==========================================
# 3. 메인 로직 및 UI
# ==========================================

col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🔄 전체 최신화 자동 확인", width='stretch'):
        start_debug_chrome()
        total_count = len(st.session_state.df)
        if total_count > 0:
            progress_bar = st.progress(0.0)
            now_str = datetime.now().strftime("%m/%d %H:%M") # 현재 시간 (예: 03/01 14:30)
            
            for idx, (i, row) in enumerate(st.session_state.df.iterrows()):
                if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
                    old_latest = row['최신화']
                    new_latest = fetch_latest_from_url(row['목록URL'])
                    
                    if new_latest is not None:
                        st.session_state.df.at[i, '최신화'] = new_latest
                        st.session_state.df.at[i, '최종확인일'] = now_str
                        
                        # 💡 핵심 로직: 기존 최신화 정보보다 늘어났을 때만 'NEW' 표시
                        try:
                            if float(new_latest) > float(old_latest if old_latest else 0):
                                st.session_state.df.at[i, '상태'] = "NEW ✨"
                            else:
                                st.session_state.df.at[i, '상태'] = "확인완료"
                        except:
                            st.session_state.df.at[i, '상태'] = "확인완료"
                            
                progress_bar.progress(min((idx + 1) / total_count, 1.0))
            st.success(f"✅ 확인 완료 ({now_str})")
        else:
            st.warning("목록이 비어 있습니다.")

# 목록 표시 스타일 정의
def style_row(row):
    style = [''] * len(row)
    try:
        # 내가 본 것보다 최신화가 더 많으면 빨간색 강조
        if float(row['최신화']) > float(row['내가본화수']):
            style = ['background-color: #3b1e1e; color: #ff4b4b; font-weight: bold'] * len(row)
        # 상태가 NEW ✨ 이면 테두리나 글자색 추가 강조
        if row['상태'] == "NEW ✨":
            style = ['background-color: #1e3b1e; color: #4bff4b; font-weight: bold'] * len(row)
    except: pass
    return style

st.subheader("📋 내 웹툰 목록")
st.dataframe(
    st.session_state.df.style.apply(style_row, axis=1),
    column_config={
        "보기URL": st.column_config.LinkColumn("📖 바로보기"),
        "목록URL": st.column_config.LinkColumn("📂 목록보기"),
        "상태": st.column_config.TextColumn("상태", help="NEW: 마지막 확인보다 화수가 늘어남 / 확인완료: 변동 없음"),
        "최종확인일": st.column_config.TextColumn("마지막 체크"),
    },
    width='stretch',
    height=450
)

st.divider()

# 입력 및 수정 UI
st.subheader("➕ 웹툰 추가 및 정보 수정")
with st.form("add_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    new_title = c1.text_input("웹툰 제목")
    new_my = c2.number_input("내가 본 화수", min_value=0.0, step=0.1)
    new_latest = c3.number_input("현재 최신 화수", min_value=0.0, step=0.1)
    
    c4, c5 = st.columns(2)
    new_view_url = c4.text_input("보기 URL (현재 보던 페이지)")
    new_list_url = c5.text_input("목록 URL (전체 리스트)")
    
    submit = st.form_submit_button("목록에 추가 / 수정", width='stretch')
    
    if submit and new_title:
        now_str = datetime.now().strftime("%m/%d %H:%M")
        if new_title in st.session_state.df['제목'].values:
            idx = st.session_state.df[st.session_state.df['제목'] == new_title].index[0]
            st.session_state.df.at[idx, '내가본화수'] = new_my
            st.session_state.df.at[idx, '최신화'] = new_latest
            st.session_state.df.at[idx, '보기URL'] = new_view_url
            st.session_state.df.at[idx, '목록URL'] = new_list_url
            st.session_state.df.at[idx, '최종확인일'] = now_str
            st.session_state.df.at[idx, '상태'] = "수정됨"
        else:
            new_row = {
                '제목': new_title, '내가본화수': new_my, '최신화': new_latest,
                '상태': '신규', '최종확인일': now_str, '보기URL': new_view_url, '목록URL': new_list_url
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        st.rerun()

# 사이드바 관리
with st.sidebar:
    st.header("⚙️ 관리 도구")
    if st.button("💾 구글 시트에 최종 저장", width='stretch'):
        try:
            conn.update(data=st.session_state.df)
            st.success("구글 시트 저장 완료!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
            
    st.divider()
    delete_target = st.selectbox("삭제할 웹툰 선택", ["선택하세요"] + list(st.session_state.df['제목'].values))
    if st.button("🗑️ 선택 항목 삭제", width='stretch'):
        if delete_target != "선택하세요":
            st.session_state.df = st.session_state.df[st.session_state.df['제목'] != delete_target]
            st.rerun()

st.caption("v2.2.7 | NEW ✨: 화수 증가 감지 | 최종확인일 기록")