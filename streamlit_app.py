# 📜 Version History (v2.4.8)
# - 리스트 삭제(Delete) 기능 추가 (사이드바 메뉴)
# - 삭제 시 즉각 반영 및 시트 저장 연동
# - PC Selenium 엔진 및 Mobile 인증 보정 유지

from datetime import datetime
import streamlit as st
import pandas as pd
import subprocess
import time
import re
import os

# [1. 실행 환경 감지]
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# [2. 구글 시트 연결 및 인증 보정]
def get_gsheets_conn():
    try:
        creds = st.secrets["connections"]["gsheets"].to_dict()
        if "private_key" in creds:
            key = creds["private_key"].replace("\\n", "\n").replace("\\r", "")
            creds["private_key"] = key.strip().strip('"')
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection, **creds)
    except:
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Webtoon Tracker Final", layout="wide")
st.title("📚 웹툰 기록기 (v2.4.8)")

conn = get_gsheets_conn()

def load_data():
    try:
        return conn.read(ttl="0s")
    except:
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# [3. PC 전용 크롬 제어 엔진]
def fetch_latest_from_pc(list_url):
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        driver = webdriver.Chrome(options=options)
        driver.get(list_url)
        time.sleep(3) 
        element = driver.find_element(By.CSS_SELECTOR, ".list-item .wr-subject a")
        match = re.search(r'(\d+(\.\d+)?)', element.text)
        return float(match.group(1)) if match else None
    except:
        return None

# [4. 상단 버튼부]
col_info, col_btn = st.columns([7, 3])
with col_btn:
    if not IS_CLOUD:
        if st.button("🔄 PC에서 최신화 자동 확인", width='stretch'):
            CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(CHROME_PATH):
                subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", "--user-data-dir=C:\\sel_debug_profile"])
                time.sleep(3)
                progress_bar = st.progress(0.0)
                now_str = datetime.now().strftime("%m/%d %H:%M")
                
                for idx, (i, row) in enumerate(st.session_state.df.iterrows()):
                    if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
                        new_val = fetch_latest_from_pc(row['목록URL'])
                        if new_val:
                            old_val = row['최신화']
                            st.session_state.df.at[i, '최신화'] = new_val
                            st.session_state.df.at[i, '최종확인일'] = now_str
                            st.session_state.df.at[i, '상태'] = "NEW ✨" if float(new_val) > float(old_val if old_val else 0) else "확인완료"
                    progress_bar.progress(min((idx + 1) / len(st.session_state.df), 1.0))
                st.success("✅ 업데이트 완료! 저장 버튼을 눌러주세요.")
                st.rerun()

# [5. 메인 리스트 출력]
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
    width='stretch', height=600
)

# [6. 사이드바 - 수정 및 삭제 관리]
with st.sidebar:
    st.header("⚙️ 관리 메뉴")
    if st.button("💾 구글 시트에 최종 저장", width='stretch', type="primary"):
        try:
            conn.update(data=st.session_state.df)
            st.success("시트 저장 성공!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
            
    st.divider()
    
    # 웹툰 선택
    titles = list(st.session_state.df['제목'].values)
    target = st.selectbox("수정/삭제할 웹툰 선택", ["+ 신규 추가"] + titles)
    
    if target != "+ 신규 추가":
        # 🗑️ 삭제 기능 추가
        if st.button(f"🗑️ '{target}' 삭제하기", width='stretch'):
            st.session_state.df = st.session_state.df[st.session_state.df['제목'] != target]
            st.warning(f"'{target}'이(가) 리스트에서 제거되었습니다. 저장 버튼을 눌러야 시트에 반영됩니다.")
            st.rerun()
        st.write("---")

    # 수정/추가 폼
    with st.form("edit_form", clear_on_submit=True):
        curr = st.session_state.df[st.session_state.df['제목']==target] if target != "+ 신규 추가" else None
        
        edit_title = st.text_input("제목", value=target if target != "+ 신규 추가" else "")
        edit_my = st.number_input("내가 본 화수", step=1.0, value=float(curr['내가본화수'].values[0]) if curr is not None else 0.0)
        edit_v_url = st.text_input("보기 URL (📖)", value=curr['보기URL'].values[0] if curr is not None else "")
        edit_l_url = st.text_input("목록 URL (📂)", value=curr['목록URL'].values[0] if curr is not None else "")
        
        submit_label = "변경사항 적용" if target != "+ 신규 추가" else "새 웹툰 추가"
        if st.form_submit_button(submit_label):
            if target != "+ 신규 추가":
                idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
                st.session_state.df.at[idx, '제목'] = edit_title
                st.session_state.df.at[idx, '내가본화수'] = edit_my
                st.session_state.df.at[idx, '보기URL'] = edit_v_url
                st.session_state.df.at[idx, '목록URL'] = edit_l_url
            else:
                new_row = {
                    '제목': edit_title, '내가본화수': edit_my, '최신화': 0.0, 
                    '상태': '신규', '최종확인일': datetime.now().strftime("%m/%d %H:%M"),
                    '보기URL': edit_v_url, '목록URL': edit_l_url
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()

st.caption("v2.4.8 | 삭제 기능 추가됨 | PC Selenium & Cloud Auth")