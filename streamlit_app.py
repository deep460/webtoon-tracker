# 📜 Version History (v2.3.0)
# - 모바일(Streamlit Cloud) 배포 호환성 완성
# - 환경 감지 로직 추가 (Cloud vs Local)
# - 모바일에서 '자동 확인' 버튼 숨김 처리

from datetime import datetime
import streamlit as st
import pandas as pd
import re
import os

# [환경 감지] Streamlit Cloud 환경인지 확인
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# 💡 클라우드 환경이면 Selenium 관련 라이브러리 로드를 시도하지 않거나 예외처리함
try:
    from streamlit_gsheets import GSheetsConnection
    if not IS_CLOUD:
        import subprocess
        import time
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
except ImportError:
    st.error("필수 라이브러리가 설치되지 않았습니다. requirements.txt를 확인하세요.")

# ==========================================
# 1. 크롬 엔진 (로컬 PC에서만 작동)
# ==========================================
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_PATH = r"C:\sel_debug_profile"

def start_debug_chrome():
    if IS_CLOUD: return False
    if not os.path.exists(CHROME_PATH): return False
    
    import subprocess
    import time
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
        if match: return float(match.group(1))
    except: return None
    return None

# ==========================================
# 2. UI 및 데이터 로드
# ==========================================
st.set_page_config(page_title="Webtoon Tracker v2.3.0", layout="wide")
st.title("📚 웹툰 기록기 (Mobile & PC)")

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(ttl="0s")
        expected_cols = ['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL']
        if data is None or data.empty: return pd.DataFrame(columns=expected_cols)
        for col in expected_cols:
            if col not in data.columns: data[col] = ""
        return data[expected_cols]
    except:
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 업데이트 버튼 (PC에서만 활성화) ---
col1, col2 = st.columns([7, 3])
with col2:
    if IS_CLOUD:
        st.info("📱 모바일 모드: 조회 및 수정 가능")
    else:
        if st.button("🔄 사이트 최신화 자동 확인", width='stretch'):
            if start_debug_chrome():
                progress_bar = st.progress(0.0)
                now_str = datetime.now().strftime("%m/%d %H:%M")
                total = len(st.session_state.df)
                for idx, (i, row) in enumerate(st.session_state.df.iterrows()):
                    if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
                        old_v = row['최신화']; new_v = fetch_latest_from_url(row['목록URL'])
                        if new_v:
                            st.session_state.df.at[i, '최신화'] = new_v
                            st.session_state.df.at[i, '최종확인일'] = now_str
                            st.session_state.df.at[i, '상태'] = "NEW ✨" if float(new_v) > float(old_v if old_v else 0) else "확인완료"
                    progress_bar.progress(min((idx + 1) / total, 1.0))
                st.success("✅ 확인 완료!")

# --- 리스트 출력 ---
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

# --- 사이드바 및 수정 UI ---
with st.sidebar:
    st.header("⚙️ 관리")
    if st.button("💾 구글 시트에 저장", width='stretch'):
        conn.update(data=st.session_state.df)
        st.success("저장 완료!")
    
    st.divider()
    # 모바일에서도 수정하기 편하게 제목 선택 후 화수 수정 기능
    target = st.selectbox("수정할 웹툰 선택", ["신규 추가"] + list(st.session_state.df['제목'].values))
    with st.form("edit_form"):
        title = st.text_input("제목", value="" if target=="신규 추가" else target)
        my_ep = st.number_input("내가 본 화수", step=1.0)
        view_url = st.text_input("보기 URL")
        list_url = st.text_input("목록 URL")
        if st.form_submit_button("적용"):
            now_str = datetime.now().strftime("%m/%d %H:%M")
            if target != "신규 추가":
                idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
                st.session_state.df.at[idx, '제목'] = title
                st.session_state.df.at[idx, '내가본화수'] = my_ep
                st.session_state.df.at[idx, '보기URL'] = view_url
                st.session_state.df.at[idx, '목록URL'] = list_url
            else:
                new_row = {'제목': title, '내가본화수': my_ep, '최신화': 0.0, '상태': '신규', '최종확인일': now_str, '보기URL': view_url, '목록URL': list_url}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()

st.caption("v2.3.0 | Cloud & Mobile Compatible")