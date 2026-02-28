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
        if not data.empty and '날짜' not in data.columns:
            data['날짜'] = ""
        return data
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        return pd.DataFrame(columns=["제목", "화수", "URL", "날짜"])

df = load_data()

# 4. 입력 및 업데이트 섹션 (새로 등록용)
with st.expander("➕ 새 웹툰 등록 / 직접 수정", expanded=False):
    with st.form("update_form"):
        title = st.text_input("웹툰 제목 (기존 제목 입력 시 내용이 수정됩니다)")
        episode = st.number_input("현재 몇 화인가요?", min_value=1, step=1)
        url = st.text_input("현재 페이지 링크(URL)")
        submit = st.form_submit_button("시트에 저장")

        if submit and title:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            if not df.empty and title in df['제목'].values:
                df.loc[df['제목'] == title, ['화수', 'URL', '날짜']] = [episode, url, current_time]
            else:
                new_row = pd.DataFrame([{"제목": title, "화수": episode, "URL": url, "날짜": current_time}])
                df = pd.concat([df, new_row], ignore_index=True)
            
            try:
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.success(f"'{title}' 처리 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

st.divider()

# 5. 나의 정주행 목록 출력 (수정/삭제 기능 포함)
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
                # --- 수정 기능 ---
                if st.button("✏️ 수정", key=f"edit_{index}"):
                    st.session_state[f"editing_{index}"] = True
                
                # --- 삭제 기능 ---
                if st.button("🗑️ 삭제", key=f"del_{index}"):
                    st.session_state[f"confirm_delete_{index}"] = True
            
            # 수정 모드 활성화 시 나타나는 입력창
            if st.session_state.get(f"editing_{index}", False):
                with st.form(key=f"edit_form_{index}"):
                    st.write(f"**[{row['제목']}]** 정보 수정")
                    new_ep = st.number_input("화수 변경", value=int(row['화수']) if str(row['화수']).isdigit() else 1)
                    new_url = st.text_input("URL 변경", value=row['URL'])
                    
                    col_save, col_cancel = st.columns(2)
                    if col_save.form_submit_button("✅ 적용"):
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                        df.loc[index, ['화수', 'URL', '날짜']] = [new_ep, new_url, current_time]
                        conn.update(spreadsheet=SHEET_URL, data=df)
                        del st.session_state[f"editing_{index}"]
                        st.rerun()
                    if col_cancel.form_submit_button("❌ 취소"):
                        del st.session_state[f"editing_{index}"]
                        st.rerun()

            # 삭제 확인 모드 (v1.9.0 로직)
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
# v2.1.0 (2026-02-28)
# * 리스트 개별 항목에 '✏️ 수정' 버튼 추가 및 즉시 수정 기능 구현
# * 수정 시에도 날짜와 시간이 자동으로 업데이트되도록 연동
# * 수정/삭제 버튼을 분리하여 모바일 가독성 향상