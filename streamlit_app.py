import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="Webtoon Tracker", layout="wide")
st.title("📚 웹툰 실시간 기록기")

# 2. 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# --- [수정 포인트] 본인의 구글 시트 주소를 입력하세요 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/14nRamWc2f6FF6KTLbpHly7oB095fllDZI6whoEKzq5c/edit"

# 3. 데이터 불러오기 함수
@st.cache_data(ttl=0)
def load_data():
    try:
        data = conn.read(spreadsheet=SHEET_URL, ttl="0")
        # '날짜' 컬럼이 없으면 새로 생성
        if not data.empty and '날짜' not in data.columns:
            data['날짜'] = ""
        return data
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        return pd.DataFrame(columns=["제목", "화수", "URL", "날짜"])

df = load_data()

# 4. 입력 및 업데이트 섹션
with st.expander("📝 현재 화수 업데이트", expanded=False):
    with st.form("update_form"):
        title = st.text_input("웹툰 제목")
        episode = st.number_input("현재 몇 화인가요?", min_value=1, step=1)
        url = st.text_input("현재 페이지 링크(URL)")
        submit = st.form_submit_button("시트에 실시간 저장")

        if submit and title:
            # 현재 시간을 'YYYY-MM-DD HH:MM' 형식으로 생성
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            if not df.empty and title in df['제목'].values:
                # 기존 데이터 업데이트 시 날짜도 갱신
                df.loc[df['제목'] == title, ['화수', 'URL', '날짜']] = [episode, url, current_time]
            else:
                # 새 데이터 추가
                new_row = pd.DataFrame([{"제목": title, "화수": episode, "URL": url, "날짜": current_time}])
                df = pd.concat([df, new_row], ignore_index=True)
            
            try:
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.success(f"'{title}' 저장 완료! (기록: {current_time})")
                st.rerun()
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")

st.divider()

# 5. 나의 정주행 목록 출력 (날짜 표시 추가)
st.subheader("📖 나의 정주행 리스트")

if not df.empty:
    for index, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            
            with c1:
                st.markdown(f"### {row['제목']}")
                # 날짜 정보 표시
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
                # 삭제 기능 (v1.9.0 로직 유지)
                if st.button("🗑️ 삭제", key=f"del_{index}"):
                    st.session_state[f"confirm_delete_{index}"] = True
                
                if st.session_state.get(f"confirm_delete_{index}", False):
                    st.warning("정말 삭제할까요?")
                    col_yes, col_no = st.columns(2)
                    if col_yes.button("✅ 예", key=f"yes_{index}"):
                        df = df.drop(index)
                        conn.update(spreadsheet=SHEET_URL, data=df)
                        del st.session_state[f"confirm_delete_{index}"]
                        st.rerun()
                    if col_no.button("❌ 아니오", key=f"no_{index}"):
                        del st.session_state[f"confirm_delete_{index}"]
                        st.rerun()
else:
    st.info("리스트가 비어있습니다.")

# --- 버전 히스토리 ---
# v2.0.0 (2026-02-28)
# * 저장 시 현재 시간(YYYY-MM-DD HH:MM) 자동 기록 기능 추가
# * 목록 화면에서 마지막 기록 일시 시각화
# * 기존 삭제 기능 및 URL 링크 기능 유지