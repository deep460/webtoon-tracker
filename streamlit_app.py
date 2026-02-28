# 📜 Version History (v2.4.7)
# - PC 전용 '최신화 자동 확인' 크롤링 로직 완벽 복구
# - 모바일(Cloud) 환경 인증 에러(400) 방지 로직 유지
# - PC와 모바일 환경 자동 감지 및 기능 최적화

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
            # Secrets의 \n 문자를 실제 줄바꿈으로 복구 (인증 성공의 핵심)
            creds["private_key"] = creds["private_key"].replace("\\n", "\n").replace("\\r", "")
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection, **creds)
    except:
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Webtoon Tracker Final", layout="wide")
st.title("📚 웹툰 기록기 (PC & Mobile)")

conn = get_gsheets_conn()

def load_data():
    try:
        return conn.read(ttl="0s")
    except:
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# ==========================================
# 3. PC 전용 크롬 제어 엔진 (Selenium)
# ==========================================
def fetch_latest_from_pc(list_url):
    # PC 환경에서만 셀레니움 임포트 (모바일 충돌 방지)
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(list_url)
        time.sleep(3) 
        # 사이트 구조에 따른 최신화 추출 (뉴토끼 등 기준)
        element = driver.find_element(By.CSS_SELECTOR, ".list-item .wr-subject a")
        match = re.search(r'(\d+(\.\d+)?)', element.text)
        return float(match.group(1)) if match else None
    except:
        return None

# ==========================================
# 4. 메인 UI 및 컨트롤
# ==========================================

col_info, col_btn = st.columns([7, 3])
with col_btn:
    if IS_CLOUD:
        st.info("📱 모바일: 조회/수정 모드")
    else:
        # PC(로컬)에서만 버튼이 보이고 작동함
        if st.button("🔄 PC에서 최신화 자동 확인", width='stretch'):
            CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(CHROME_PATH):
                # 디버깅 모드 크롬 실행
                subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", "--user-data-dir=C:\\sel_debug_profile"])
                time.sleep(3)
                
                progress_bar = st.progress(0.0)
                now_str = datetime.now().strftime("%m/%d %H:%M")
                df_curr = st.session_state.df
                
                for idx, (i, row) in enumerate(df_curr.iterrows()):
                    if pd.notna(row['목록URL']) and str(row['목록URL']).startswith('http'):
                        new_val = fetch_latest_from_pc(row['목록URL'])
                        if new_val:
                            # 기존 값보다 클 때만 NEW 표시
                            old_val = row['최신화']
                            df_curr.at[i, '최신화'] = new_val
                            df_curr.at[i, '최종확인일'] = now_str
                            df_curr.at[i, '상태'] = "NEW ✨" if float(new_val) > float(old_val if old_val else 0) else "확인완료"
                    progress_bar.progress(min((idx + 1) / len(df_curr), 1.0))
                
                st.session_state.df = df_curr
                st.success("✅ PC 업데이트 완료! 시트에 저장하세요.")
            else:
                st.error("크롬 경로를 찾을 수 없습니다.")

# 목록 표시 스타일
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
    width='stretch', height=500
)

# 사이드바 관리
with st.sidebar:
    st.header("⚙️ 관리")
    if st.button("💾 구글 시트에 최종 저장", width='stretch'):
        try:
            conn.update(data=st.session_state.df)
            st.success("저장 완료!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
            
    st.divider()
    target = st.selectbox("수정할 웹툰", ["신규 추가"] + list(st.session_state.df['제목'].values))
    with st.form("edit_form"):
        curr = st.session_state.df[st.session_state.df['제목']==target] if target != "신규 추가" else None
        edit_title = st.text_input("제목", value=target if target != "신규 추가" else "")
        edit_my = st.number_input("내가 본 화수", step=1.0, value=float(curr['내가본화수'].values[0]) if curr is not None else 0.0)
        edit_v_url = st.text_input("보기 URL", value=curr['보기URL'].values[0] if curr is not None else "")
        edit_l_url = st.text_input("목록 URL", value=curr['목록URL'].values[0] if curr is not None else "")
        
        if st.form_submit_button("적용"):
            if target != "신규 추가":
                idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
                st.session_state.df.at[idx, '내가본화수'] = edit_my
                st.session_state.df.at[idx, '보기URL'] = edit_v_url
                st.session_state.df.at[idx, '목록URL'] = edit_l_url
            else:
                new_row = {'제목': edit_title, '내가본화수': edit_my, '최신화': 0.0, '상태': '신규', '보기URL': edit_v_url, '목록URL': edit_l_url}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()

st.caption("v2.4.7 | PC: Selenium 확인 가능 | Mobile: 인증 성공 모드")