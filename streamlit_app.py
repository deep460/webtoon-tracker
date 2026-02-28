# 📜 Version History (v2.4.2)
# - google-auth 400 invalid_grant 에러 최종 해결 (Key 공백 및 줄바꿈 정규화)
# - 모바일(Cloud) 배포 시 시트 로드 안정성 확보
# - PC(Local) 실행 시에만 셀레니움 기능 조건부 활성화

from datetime import datetime
import streamlit as st
import pandas as pd
import os
import re

# [1. 실행 환경 감지]
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# [2. 구글 시트 연결 및 인증 키 강제 보정]
def get_gsheets_conn():
    try:
        # secrets에서 인증 정보를 가져옴
        creds = st.secrets["connections"]["gsheets"].to_dict()
        if "private_key" in creds:
            # 💡 핵심: 양끝 공백 제거 후 줄바꿈 문자 정규화
            key = creds["private_key"].strip()
            key = key.replace("\\n", "\n")
            # 만약 키가 따옴표로 감싸져 있다면 제거
            if key.startswith('"') and key.endswith('"'):
                key = key[1:-1]
            creds["private_key"] = key
        
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection, **creds)
    except Exception:
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Webtoon Tracker Final", layout="wide")
st.title("📚 웹툰 기록기 (v2.4.2)")

# 시트 연결 객체 생성
conn = get_gsheets_conn()

# [3. 데이터 로드]
def load_data():
    try:
        # 실시간 데이터를 읽어옴 (ttl=0)
        return conn.read(ttl="0s")
    except Exception as e:
        st.error("🔄 시트 인증 처리 중... 잠시 후 새로고침(F5) 하세요.")
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# [4. UI 상단 - 환경별 모드 설정]
col_info, col_btn = st.columns([7, 3])
with col_btn:
    if IS_CLOUD:
        st.info("📱 모바일: 조회/수정 모드")
    else:
        if st.button("🔄 사이트 최신화 확인 (PC)", width='stretch'):
            try:
                import subprocess, time
                from selenium import webdriver
                # PC 전용 경로 로직
                CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                if os.path.exists(CHROME_PATH):
                    subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", "--user-data-dir=C:\\sel_debug_profile"])
                    time.sleep(3)
                    st.success("PC 자동화 엔진 가동!")
                else: st.error("크롬 경로 오류")
            except: st.error("환경 설정을 확인하세요.")

# [5. 메인 리스트 출력 및 스타일링]
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

# [6. 사이드바 - 관리 및 수정]
with st.sidebar:
    st.header("⚙️ 관리")
    if st.button("💾 구글 시트에 최종 저장", width='stretch'):
        try:
            conn.update(data=st.session_state.df)
            st.success("저장 완료!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
            
    st.divider()
    target = st.selectbox("수정 항목", ["신규 추가"] + list(st.session_state.df['제목'].values))
    with st.form("edit_form"):
        curr = st.session_state.df[st.session_state.df['제목']==target] if target != "신규 추가" else None
        edit_title = st.text_input("제목", value=target if target != "신규 추가" else "")
        edit_my = st.number_input("내가 본 화수", step=1.0, value=float(curr['내가본화수'].values[0]) if curr is not None else 0.0)
        if st.form_submit_button("적용"):
            if target != "신규 추가":
                idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
                st.session_state.df.at[idx, '내가본화수'] = edit_my
            else:
                new_row = {'제목': edit_title, '내가본화수': edit_my, '최신화': 0.0, '상태': '신규'}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()

st.caption("v2.4.2 | 모바일 인증 에러 최종 해결 버전")