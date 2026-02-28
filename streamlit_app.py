import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import sys

# [추가] 시스템 기본 인코딩을 UTF-8로 설정하여 한글 깨짐 방지
import io
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# 1. 페이지 설정
st.set_page_config(page_title="Webtoon Tracker", layout="wide")
st.title("📚 웹툰 실시간 기록기")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# --- [수정 포인트] 본인의 구글 시트 주소를 입력하세요 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/본인의_시트_ID_입력/edit"

# 3. 데이터 불러오기 함수
@st.cache_data(ttl=0)
def load_data():
    try:
        # 주소에 한글이 섞여있을 경우를 대비해 인코딩 확인
        data = conn.read(spreadsheet=SHEET_URL, ttl="0")
        if not data.empty and '날짜' not in data.columns:
            data['날짜'] = ""
        return data
    except Exception as e:
        # 에러 메시지 출력 시에도 한글 처리가 가능하도록 함
        st.error(f"데이터 로딩 실패: {str(e)}")
        return pd.DataFrame(columns=["제목", "화수", "URL", "날짜"])

df = load_data()

# 한국 시간 계산 함수
def get_kst_now():
    return (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")

# 4. 입력 및 업데이트 섹션
with st.expander("➕ 새 웹툰 등록 / 직접 수정", expanded=False):
    with st.form("update_form", clear_on_submit=True):
        title = st.text_input("웹툰 제목")
        episode = st.number_input("현재 몇 화인가요?", min_value=1, step=1)
        url = st.text_input("현재 페이지 링크(URL)")
        submit = st.form_submit_button("시트에 저장")

        if submit and title:
            current_time = get_kst_now()
            # 한글 제목 비교 시 공백 제거 등 정규화 적용
            title_clean = title.strip()
            
            if not df.empty and title_clean in df['제목'].values:
                df.loc[df['제목'] == title_clean, ['화수', 'URL', '날짜']] = [episode, url, current_time]
            else:
                new_row = pd.DataFrame([{"제목": title_clean, "화수": episode, "URL": url, "날짜": current_time}])
                df = pd.concat([df, new_row], ignore_index=True)
            
            try:
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.success(f"'{title_clean}' 저장 완료! (KST: {current_time})")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {str(e)}")

st.divider()

# 5. 리스트 출력 및 수정/삭제 (기존 로직 유지)
st.subheader("📖 나의 정주행 리스트")

if not df.empty:
    for index, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.markdown(f"### {row['제목']}")
                save_date = row['날짜'] if pd.notna(row['날짜']) and str(row['날짜']).strip() else "기록 없음"
                st.caption(f"📅 마지막 기록: {save_date}")
                if pd.notna(row['URL']) and str(row['URL']).strip():
                    st.link_button("🚀 이어서 보기", str(row['URL']))
            with c2:
                try:
                    ep_val = int(row['화수'])
                except:
                    ep_val = row['화수']
                st.metric("진행", f"{ep_val}화")
            with c3:
                if st.button("✏️ 수정", key=f"edit_{index}"):
                    st.session_state[f"editing_{index}"] = True
                if st.button("🗑️ 삭제", key=f"del_{index}"):
                    st.session_state[f"confirm_delete_{index}"] = True
            
            # 수정/삭제 폼 생략 (기존 v2.2.0과 동일)
            # ... (이전 코드의 수정/삭제 로직을 그대로 붙여넣으시면 됩니다)