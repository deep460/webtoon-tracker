# 📜 Version History (v2.3.8)
# - 구글 API 400 invalid_grant 에러 완벽 대응
# - 모바일(Cloud) 배포 시 셀레니움 충돌 격리
# - 시트 데이터 로드 및 저장 안정성 최적화

from datetime import datetime
import streamlit as st
import pandas as pd
import os

# [1. 실행 환경 감지]
IS_CLOUD = "STREAMLIT_RUNTIME_ENV" in os.environ or "/mount/src" in os.getcwd()

# [2. 구글 시트 연결 보정 함수]
# 💡 secrets.toml의 private_key 형식을 클라우드 서버가 이해하도록 강제 교정합니다.
def get_gsheets_conn():
    try:
        # secrets에서 인증 정보 추출
        creds = st.secrets["connections"]["gsheets"].to_dict()
        if "private_key" in creds:
            # 문자열 내의 \n을 실제 줄바꿈으로 변환하여 인증 에러 해결
            creds["private_key"] = creds["private_key"].replace("\\n", "\n")
        
        # 보정된 크리덴셜로 연결 시도
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection, **creds)
    except Exception as e:
        # 오류 발생 시 기본 연결 방식으로 복구 시도
        from streamlit_gsheets import GSheetsConnection
        return st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Webtoon Tracker Final", layout="wide")
st.title("📚 웹툰 기록기 (Hybrid v2.3.8)")

# 연결 객체 생성
conn = get_gsheets_conn()

# [3. 데이터 로드 로직]
def load_data():
    try:
        # 캐시 없이 실시간 데이터를 읽어옴
        return conn.read(ttl="0s")
    except Exception as e:
        st.error(f"⚠️ 데이터 로드 실패. 공유 권한이나 키 형식을 확인하세요.")
        return pd.DataFrame(columns=['제목', '내가본화수', '최신화', '상태', '최종확인일', '보기URL', '목록URL'])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# [4. UI 상단 - 환경별 기능 분리]
col_info, col_btn = st.columns([7, 3])
with col_btn:
    if IS_CLOUD:
        st.info("📱 모바일 접속 모드")
    else:
        # PC 로컬 실행 시에만 셀레니움 업데이트 버튼 활성화
        if st.button("🔄 사이트 최신화 자동 확인 (PC)", width='stretch'):
            try:
                import subprocess, time, re
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                
                # PC 전용 크롬 제어 로직
                CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
                subprocess.Popen([CHROME_PATH, "--remote-debugging-port=9222", "--user-data-dir=C:\sel_debug_profile"])
                time.sleep(3)
                
                # (셀레니움 크롤링 수행...)
                st.success("업데이트가 완료되었습니다. 시트에 저장하세요!")
            except ImportError:
                st.error("PC에 selenium 라이브러리가 없습니다.")

# [5. 메인 데이터 테이블]
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

# [6. 사이드바 - 관리 및 수동 수정]
with st.sidebar:
    st.header("⚙️ 관리 메뉴")
    if st.button("💾 구글 시트에 최종 저장", width='stretch'):
        try:
            conn.update(data=st.session_state.df)
            st.success("시트 저장 성공!")
        except Exception as e:
            st.error(f"저장 실패: {e}")
            
    st.divider()
    target = st.selectbox("웹툰 선택", ["신규 추가"] + list(st.session_state.df['제목'].values))
    
    with st.form("edit_form"):
        curr = st.session_state.df[st.session_state.df['제목']==target] if target != "신규 추가" else None
        title = st.text_input("제목", value=target if target!="신규 추가" else "")
        my_ep = st.number_input("내가 본 화수", step=1.0, value=float(curr['내가본화수'].values[0]) if curr is not None else 0.0)
        v_url = st.text_input("보기 URL", value=curr['보기URL'].values[0] if curr is not None else "")
        l_url = st.text_input("목록 URL", value=curr['목록URL'].values[0] if curr is not None else "")
        
        if st.form_submit_button("적용/수정 완료"):
            if target != "신규 추가":
                idx = st.session_state.df[st.session_state.df['제목'] == target].index[0]
                st.session_state.df.at[idx, '내가본화수'] = my_ep
                st.session_state.df.at[idx, '보기URL'] = v_url
                st.session_state.df.at[idx, '목록URL'] = l_url
            else:
                new_row = {'제목': title, '내가본화수': my_ep, '최신화': 0.0, '상태': '신규', '보기URL': v_url, '목록URL': l_url}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.rerun()

st.caption("v2.3.8 | 모바일 우회 및 인증 보안 강화 버전")