import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="Webtoon Tracker", layout="wide")
st.title("📚 웹툰 실시간 기록기")

# 2. 구글 시트 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

# --- [수정 포인트] 본인의 구글 시트 주소를 여기에 직접 입력하세요 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/14nRamWc2f6FF6KTLbpHly7oB095fllDZI6whoEKzq5c/edit"

# 3. 데이터 불러오기 함수
def load_data():
    try:
        # 주소를 직접 사용하여 데이터를 읽어옵니다.
        return conn.read(spreadsheet=SHEET_URL, ttl="0")
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        # 오류 시 기본 헤더를 가진 빈 표를 생성합니다.
        return pd.DataFrame(columns=["제목", "화수", "URL"])

df = load_data()

# 4. 입력 및 업데이트 섹션
with st.expander("📝 현재 화수 업데이트", expanded=True):
    with st.form("update_form"):
        title = st.text_input("웹툰 제목")
        episode = st.number_input("현재 몇 화인가요?", min_value=1, step=1)
        url = st.text_input("현재 페이지 링크(URL)")
        submit = st.form_submit_button("시트에 실시간 저장")

        if submit and title:
            # 중복 제목이 있으면 업데이트, 없으면 추가
            if not df.empty and title in df['제목'].values:
                df.loc[df['제목'] == title, ['화수', 'URL']] = [episode, url]
            else:
                new_row = pd.DataFrame([{"제목": title, "화수": episode, "URL": url}])
                df = pd.concat([df, new_row], ignore_index=True)
            
            try:
                # 저장 시에도 직접 지정한 주소를 사용합니다.
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.success(f"'{title}' 저장 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")

st.divider()

# 5. 나의 정주행 목록 출력
st.subheader("📖 나의 정주행 리스트")
if not df.empty:
    # 최신순으로 정렬하여 출력
    for index, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"### {row['제목']}")
                if pd.notna(row['URL']) and str(row['URL']).strip():
                    st.link_button("🚀 이어서 보기", str(row['URL']))
            with c2:
                try:
                    ep_val = int(row['화수'])
                except:
                    ep_val = row['화수']
                st.metric("진행", f"{ep_val}화")
else:
    st.info("시트에 데이터가 없거나 로딩되지 않았습니다. 첫 기록을 남겨보세요!")

# --- 버전 히스토리 ---
# v1.8.1 (2026-02-28)
# * SHEET_URL 변수를 코드 내에 직접 선언하여 Secrets 의존성 감소
# * 데이터 로딩 및 저장 시 명시적 URL 전달로 NoValidUrlKeyFound 방지