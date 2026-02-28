# 📜 Version History (v2.3.2)
# - SpreadsheetNotFound 및 API 인증 에러 방어 강화
# - 시트 아이디 추출 로직 최적화 및 환경 감지 로직 고도화

from datetime import datetime
import streamlit as st
import pandas as pd
import re
import os

# [환경 감지] Streamlit Cloud 여부 확인
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# 라이브러리 조건부 로드
try:
    from streamlit_gsheets import GSheetsConnection
    if not IS_CLOUD:
        import subprocess
        import time
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
except ImportError:
    pass

# ==========================================
# 1. 크롬 엔진 (로컬 전용)
# ==========================================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_PATH = r"C:\sel_debug_profile"

def start_debug_chrome():
    if IS_CLOUD: return False
    if not os.path.exists(CHROME_PATH): return False
    import subprocess, time
    if not os.path.exists(USER_DATA_PATH): os.makedirs(USER_DATA_PATH)
    subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", f"--user-data-dir={USER_DATA_PATH}"])
    time.sleep(3)
    return True

def fetch_latest_from_url(list_url):
    if IS_CLOUD: return None
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(list_url)
        time.sleep(3) 
        element = driver.find_element(By.CSS_SELECTOR, ".list-item .wr-subject a")
        match = re.search(r'(\d+(\.\d+)?)', element.text)
        return float(match.group(1)) if match else None
    except: return None

# ==========================================
# 2. UI 및 데이터 연동
# ==========================================
st.set_page_config(page_title="Webtoon Tracker Hybrid", layout="wide")
st.title("📚 웹툰 기록기 (PC & Mobile)")

# 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 캐시 없이 데이터 로드
        data = conn.read(ttl="0s")
        expected_cols = ['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL']
        if data is None or data.empty: return pd.DataFrame(columns=expected_cols)
        # 컬럼 누락 시 자동 생성
        for col in expected_cols:
            if col not in data.columns: data[col] = ""
        return data[expected_cols]
    except Exception as e:
        st.error(f"⚠️ 연결 오류: {e}")
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 상단 레이아웃 ---
col_info, col_btn = st.columns([7, 3])
with col_btn:
    if IS_CLOUD:
        st.info("📱 모바일 모드: 조회/수정 전용")
    else:
        if st.button("🔄 사이트 최신화 자동 확인", width='stretch'):
            if start_debug_chrome():
                progress_bar = st.progress(0.0)
                now_str = datetime.now().strftime("%m/%d %H:%M")
                df_curr = st.session_state.df
                for idx, (i, row) in enumerate(df_curr.iterrows()):
                    if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
                        old_v = row['최신화']
                        new_v = fetch_latest_from_url(row['목록URL'])
                        if new_v is not None:
                            df_curr.at[i, '최신화'] = new_v
                            df_curr.at[i, '최종확인일'] = now_str
                            df_curr.at[i, '상태'] = "NEW ✨" if float(new_v) > float(old_val if (old_val:=row['최신화']) else 0) else "확인완료"
                    progress_bar.progress(min((idx + 1) / len(df_curr), 1.0))
                st.session_state.df = df_curr
                st.success("✅ 확인 완료!")

# --- 데이터 목록 ---
def style_row(row):
    style = [''] * len(row)
    try:
        if float(row['최신화']) > float(row['내가본화수']):
            style = ['background-color: #3b1e1e; color: #ff4b4b; font-weight: bold'] * len(row)
        if row['상태'] == "NEW ✨":
            style = ['background-color: #1e3b1e; color: #4bff4b; font-weight: bold'] * len(row)
    except: pass
    return style

st.dataframe(
    st.session_state.df.style.apply(style_row, axis=1),
    column_config={"보기URL": st.column_config.LinkColumn("📖"), "목록URL": st.column_config.LinkColumn("📂")},
    width='stretch', height=450
)

# --- 사이드바 관리 ---
with st.sidebar:
    st.header("⚙️ 관리 메뉴")
    if st.button("💾 구글 시트에 저장", width='stretch'):
        try:
            conn.update(data=st.session_state.df)
            st.success("시트 저장 성공!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
            
    st.divider()
    target = st.selectbox("수정/삭제 선택", ["신규 추가"] + list(st.session_state.df['제목'].values))
    
    with st.form("edit_form"):
        curr_row = st.session_state.df[st.session_state.df['제목']==target] if target != "신규 추가" else None
        title = st.text_input("제목", value=target if target!="신규 추가" else "")
        my_ep = st.number_input("내가 본 화수", step=1.0, value=float(curr_row['내가본화수'].values[0]) if curr_row is not None else 0.0)
        v_url = st.text_input("보기 URL", value=curr_row['보기URL'].values[0] if curr_row is not None else "")
        l_url = st.text_input("목록 URL", value=curr_row['목록URL'].values[0] if curr_row is not None else "")
        
        c1, c2 = st.columns(2)
        if c1.form_submit_button("적용"):
            now_str = datetime.now().strftime("%m/%d %H:%M")
            if target != "신규 추가":
                idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
                st.session_state.df.at[idx, '내가본화수'] = my_ep
                st.session_state.df.at[idx, '보기URL'] = v_url
                st.session_state.df.at[idx, '목록URL'] = l_url
            else:
                new_row = {'제목': title, '내가본화수': my_ep, '최신화': 0.0, '상태': '신규', '최종확인일': now_str, '보기URL': v_url, '목록URL': l_url}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()
        if target != "신규 추가":
            if c2.form_submit_button("🗑️ 삭제"):
                st.session_state.df = st.session_state.df[st.session_state.df['제목'] != target]
                st.rerun()

st.caption("v2.3.2 | PC에서 업데이트하고 밖(모바일)에서 확인하세요!")