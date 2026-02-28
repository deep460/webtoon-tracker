# 📜 Version History (v2.3.4)
# - requirements.txt 최소화 대응 및 무중단 배포 로직
# - 모바일(Cloud)과 PC(Local) 실행 환경 완전 분리

from datetime import datetime
import streamlit as st
import pandas as pd
import os

# [1. 환경 감지]
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# [2. 시트 연결 설정]
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Webtoon Tracker", layout="wide")
st.title("📚 웹툰 기록기")

# [3. 데이터 로드]
def load_data():
    try:
        # 주소나 키가 잘못되었을 때를 대비해 예외 처리 강화
        return conn.read(ttl="0s")
    except Exception as e:
        st.error(f"데이터를 불러올 수 없습니다. secrets 설정을 확인하세요.")
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# [4. UI 구성]
if IS_CLOUD:
    st.info("📱 모바일(Cloud) 모드: 리스트 확인 및 수동 수정이 가능합니다.")
else:
    st.success("💻 PC(Local) 모드: '자동 최신화' 기능을 사용할 수 있습니다.")
    # PC에서만 셀레니움 기능을 시도하도록 버튼 배치 (코드 생략)

# [5. 리스트 출력]
st.dataframe(st.session_state.df, use_container_width=True)

# [6. 사이드바 관리]
with st.sidebar:
    if st.button("💾 구글 시트에 저장", use_container_width=True):
        conn.update(data=st.session_state.df)
        st.success("저장 완료!")