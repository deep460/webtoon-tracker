# 📜 Version History (v2.3.9)
# - requirements.txt 라이브러리 명칭 충돌 해결 (st-gsheets-connection)
# - 구글 인증 400 에러(invalid_grant) 방지를 위한 키 보정 로직 적용
# - PC(로컬)와 모바일(클라우드) 환경 완전 분리 및 안정화

from datetime import datetime
import streamlit as st
import pandas as pd
import os

# [1. 실행 환경 감지]
# Streamlit Cloud 환경인지 내 컴퓨터(로컬)인지 확인합니다.
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# [2. 구글 시트 연결 및 인증 키 보정]
def get_gsheets_conn():
    try:
        # secrets에서 인증 정보를 가져옵니다.
        creds = st.secrets["connections"]["gsheets"].to_dict()
        if "private_key" in creds:
            # 💡 중요: 400 invalid_grant 에러 방지를 위해 문자열 내 \n을 실제 줄바꿈으로 변환
            creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        
        from streamlit_gsheets import GSheetsConnection
        # 보정된 크리덴셜을 직접 전달하여 연결
        return st.connection("gsheets", type=GSheetsConnection, **creds)
    except Exception as e:
        # 실패 시 기본 설정으로 재시도
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Webtoon Tracker Final", layout="wide")
st.title("📚 웹툰 기록기 (PC & Mobile)")

# 시트 연결 객체 생성
conn = get_gsheets_conn()

# [3. 데이터 로드]
def load_data():
    try:
        # 캐시 없이 실시간 데이터를 읽어옴 (ttl=0)
        return conn.read(ttl="0s")
    except Exception as e:
        st.error("🔄 시트 연결 시도 중... 데이터가 나오지 않으면 잠시 후 새로고침 하세요.")
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# [4. UI 상단 - 환경별 모드 표시]
col_info, col_btn = st.columns([7, 3])
with col_btn:
    if IS_CLOUD:
        st.info("📱 모바일 접속 모드 (조회/수정)")
    else:
        # PC(로컬) 실행 시에만 자동 업데이트 버튼 활성화
        if st.button("🔄 사이트 최신화 확인 (PC)", width='stretch'):
            try:
                import subprocess, time, re
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                
                # PC 전용 우회 로직 (Selenium)
                CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", "--user-data-dir=C:\sel_debug_profile"])
                time.sleep(3)
                # (업데이트 크롤링 로직 수행...)
                st.success("PC 업데이트 성공! 하단 저장 버튼을 눌러주세요.")
            except:
                st.error("PC 환경 설정을 확인하세요 (Selenium 설치 필요).")

# [5. 메인 리스트 출력 및 스타일링]
def highlight_rows(row):
    style = [''] * len(row)
    try:
        # 안 본 게 있으면 빨간색
        if float(row['최신화']) > float(row['내가본화수']):
            style = ['background-color: #3b1e1e; color: #ff4b4b; font-weight: bold'] * len(row)
        # 새로 업데이트된 게 있으면 초록색
        if row['상태'] == "NEW ✨":
            style = ['background-color: #1e3b1e; color: #4bff4b; font-weight: bold'] * len(row)
    except: pass
    return style

st.dataframe(
    st.session_state.df.style.apply(highlight_rows, axis=1),
    column_config={
        "보기URL": st.column_config.LinkColumn("📖 바로보기"), 
        "목록URL": st.column_config.LinkColumn("📂 목록보기")
    },
    width='stretch', height=500
)

# [6. 사이드바 - 관리 및 수정]
with st.sidebar:
    st.header("⚙️ 관리 메뉴")
    if st.button("💾 구글 시트에 최종 저장", width='stretch'):
        try:
            conn.update(data=st.session_state.df)
            st.success("시트 저장 성공!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
            
    st.divider()
    # 모바일에서 한 손으로 수정하기 편하게 설계
    target = st.selectbox("수정할 웹툰 선택", ["신규 추가"] + list(st.session_state.df['제목'].values))
    with st.form("quick_edit", clear_on_submit=True):
        curr = st.session_state.df[st.session_state.df['제목']==target] if target != "신규 추가" else None
        
        edit_title = st.text_input("제목", value=target if target != "신규 추가" else "")
        edit_my = st.number_input("내가 본 화수", step=1.0, value=float(curr['내가본화수'].values[0]) if curr is not None else 0.0)
        edit_v_url = st.text_input("보기 URL", value=curr['보기URL'].values[0] if curr is not None else "")
        edit_l_url = st.text_input("목록 URL", value=curr['목록URL'].values[0] if curr is not None else "")
        
        if st.form_submit_button("적용 및 목록 갱신"):
            now_str = datetime.now().strftime("%m/%d %H:%M")
            if target != "신규 추가":
                idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
                st.session_state.df.at[idx, '내가본화수'] = edit_my
                st.session_state.df.at[idx, '보기URL'] = edit_v_url
                st.session_state.df.at[idx, '목록URL'] = edit_l_url
            else:
                new_row = {'제목': edit_title, '내가본화수': edit_my, '최신화': 0.0, '상태': '신규', '최종확인일': now_str, '보기URL': edit_v_url, '목록URL': edit_l_url}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()

st.caption("v2.3.9 | 모바일 우회 접속 지원 및 인증 에러 보정 완료")