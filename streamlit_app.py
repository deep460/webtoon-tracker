import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Webtoon Cloud Tracker", layout="wide")
st.title("📚 웹툰 클라우드 기록기")

# 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# 데이터 불러오기
# --- 기존 코드 ---
# df = conn.read(ttl="0") 

# --- 수정 코드 (이걸로 교체하세요) ---
# 본인의 구글 시트 주소를 아래 따옴표 안에 넣으세요
SHEET_URL = "https://docs.google.com/spreadsheets/d/14nRamWc2f6FF6KTLbpHly7oB095fllDZI6whoEKzq5c/edit"

# 주소를 직접 전달하여 데이터를 읽어옵니다.
df = conn.read(spreadsheet=SHEET_URL, ttl="0")

with st.expander("➕ 새 에피소드 기록하기"):
    with st.form("webtoon_form"):
        title = st.text_input("웹툰 제목")
        episode = st.number_input("현재 화수", min_value=1)
        url = st.text_input("URL")
        submit = st.form_submit_button("저장하기")

        if submit and title:
            # 기존 데이터에 추가
            new_row = pd.DataFrame([{"제목": title, "화수": episode, "URL": url}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("구글 시트에 저장되었습니다!")
            st.rerun()

# 목록 출력
st.subheader("📖 나의 정주행 목록")
for index, row in df.iterrows():
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        col1.markdown(f"**{row['제목']}**")
        col2.metric("진행", f"{row['화수']}화")
        if row['URL']:
            st.link_button("🚀 바로가기", row['URL'])