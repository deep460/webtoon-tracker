# 📜 Version History (v2.3.6)
# - 모바일 접속 시 셀레니움 충돌 원천 차단 (Cloud 안정화)
# - PC 실행 시에만 셀레니움 로직 활성화 (로컬 우회 유지)

from datetime import datetime
import streamlit as st
import pandas as pd
import os

# [1. 환경 감지]
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# [2. 시트 연결]
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Webtoon Tracker Final", layout="wide")
st.title("📚 웹툰 기록기")

def load_data():
    try:
        return conn.read(ttl="0s")
    except:
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# [3. PC 전용 우회 업데이트 로직]
if not IS_CLOUD:
    st.sidebar.success("💻 PC 모드: 자동 업데이트 가능")
    if st.sidebar.button("🔄 사이트 최신화 확인 (우회 실행)", width='stretch'):
        import subprocess, time, re
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        
        # PC에서만 실행되는 우회 엔진
        CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", "--user-data-dir=C:\sel_debug_profile"])
        time.sleep(3)
        
        # ... (이전의 셀레니움 크롤링 로직 실행) ...
        st.success("✅ PC에서 업데이트 완료 후 시트에 저장하세요!")

else:
    st.sidebar.info("📱 모바일 모드: 조회 및 수동 수정")

# [4. 메인 테이블 표시]
st.dataframe(st.session_state.df, use_container_width=True, height=500)

# [5. 사이드바 저장 및 수정]
with st.sidebar:
    if st.button("💾 구글 시트에 최종 저장", width='stretch'):
        conn.update(data=st.session_state.df)
        st.success("시트 저장 성공!")
    
    st.divider()
    # 모바일에서도 간편하게 내가 본 화수 수정하기
    target = st.selectbox("웹툰 선택", ["선택"] + list(st.session_state.df['제목'].values))
    if target != "선택":
        new_ep = st.number_input("현재 본 화수", step=1.0)
        if st.button("화수 수정 완료"):
            idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
            st.session_state.df.at[idx, '내가본화수'] = new_ep
            st.rerun()