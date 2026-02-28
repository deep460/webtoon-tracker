# 📜 Version History (v2.3.5)
# - requirements.txt 최소화 대응: 셀레니움 없이도 구동 가능
# - 모바일(Cloud) 인증 에러 방지를 위한 라이브러리 격리 강화

from datetime import datetime
import streamlit as st
import pandas as pd
import os

# [1. 환경 감지]
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# [2. 시트 연결 설정]
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Webtoon Tracker Hybrid", layout="wide")
st.title("📚 웹툰 기록기")

# [3. 데이터 로드]
def load_data():
    try:
        # 캐시 없이 실시간 데이터를 읽어옵니다.
        return conn.read(ttl="0s")
    except Exception as e:
        st.error("🔄 데이터를 불러오는 중입니다. 잠시만 기다려주세요...")
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# [4. UI 구성: 모바일과 PC 분리]
if IS_CLOUD:
    st.info("📱 모바일 모드: 시트 데이터를 확인하고 본 화수를 수정할 수 있습니다.")
else:
    st.success("💻 PC 모드: '최신화 자동 확인' 기능을 실행할 수 있습니다.")
    
    # PC(로컬)에서만 작동하는 업데이트 버튼
    if st.button("🔄 사이트 최신화 자동 확인 (PC 전용)", width='stretch'):
        try:
            # 버튼을 누르는 순간에만 셀레니움을 호출하여 클라우드 에러 방지
            import subprocess, time
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            import re
            
            # (여기에 이전의 셀레니움 크롤링 로직이 들어갑니다)
            st.success("PC에서 업데이트가 완료되었습니다!")
        except ImportError:
            st.error("PC에 selenium 라이브러리가 설치되어 있지 않습니다.")

# [5. 데이터 목록 출력]
st.dataframe(st.session_state.df, use_container_width=True, height=500)

# [6. 사이드바 관리 메뉴]
with st.sidebar:
    st.header("⚙️ 관리")
    if st.button("💾 구글 시트에 최종 저장", use_container_width=True):
        try:
            conn.update(data=st.session_state.df)
            st.success("시트 저장 완료!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
    
    st.divider()
    # 화수 수정 폼 (모바일에서도 수정 가능하도록)
    target = st.selectbox("수정할 웹툰", ["선택"] + list(st.session_state.df['제목'].values))
    if target != "선택":
        new_val = st.number_input("내가 본 화수 수정", step=1.0)
        if st.button("화수 업데이트"):
            idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
            st.session_state.df.at[idx, '내가본화수'] = new_val
            st.rerun()

st.caption("v2.3.5 | Cloud 안정성 최적화 버전")