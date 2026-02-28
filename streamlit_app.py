import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="Webtoon Tracker", layout="wide")
st.title("📚 웹툰 실시간 기록기")

# 2. 구글 시트 연결 설정 (Secrets에 등록된 정보를 자동으로 사용)
conn = st.connection("gsheets", type=GSheetsConnection)

# [중요] Secrets에 등록된 시트 URL을 명시적으로 가져옵니다.
# 만약 에러가 발생한다면 이 부분에 직접 URL을 "https://..." 형태로 넣으셔도 됩니다.
try:
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("Secrets에 spreadsheet URL이 설정되지 않았습니다.")
    st.stop()

# 3. 데이터 불러오기 함수
def load_data():
    try:
        # 주소를 명시적으로 전달하여 데이터를 읽어옵니다.
        return conn.read(spreadsheet=SHEET_URL, ttl="0")
    except Exception as e:
        st.error(f"데이터 로딩 실패: {e}")
        # 에러 발생 시 빈 데이터프레임 반환 (헤더 기준 생성)
        return pd.DataFrame(columns=["제목", "화수", "URL"])

df = load_data()

# 4. 입력 섹션
with st.expander("📝 현재 화수 업데이트", expanded=True):
    with st.form("update_form"):
        title = st.text_input("웹툰 제목")
        episode = st.number_input("현재 몇 화인가요?", min_value=1, step=1)
        url = st.text_input("현재 페이지 링크(URL)")
        submit = st.form_submit_button("시트에 실시간 저장")

        if submit and title:
            # 기존 데이터가 있으면 업데이트, 없으면 추가하는 로직
            if not df.empty and title in df['제목'].values:
                df.loc[df['제목'] == title, ['화수', 'URL']] = [episode, url]
            else:
                new_row = pd.DataFrame([{"제목": title, "화수": episode, "URL": url}])
                df = pd.concat([df, new_row], ignore_index=True)
            
            try:
                # [핵심] 저장 시에도 반드시 spreadsheet 주소를 명시적으로 전달합니다.
                conn.update(spreadsheet=SHEET_URL, data=df)
                st.success(f"'{title}' 저장 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")

st.divider()

# 5. 목록 출력 섹션
st.subheader("📖 나의 정주행 리스트")
if not df.empty:
    # 최신 등록/수정 항목을 위로 보기 위해 역순 출력
    for index, row in df.iloc[::-1].iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"### {row['제목']}")
                if pd.notna(row['URL']) and str(row['URL']).strip():
                    st.link_button("🚀 이어서 보기", str(row['URL']))
            with c2:
                # 숫자 형식 에러 방지 (소수점 제거)
                try:
                    ep_display = int(row['화수'])
                except:
                    ep_display = row['화수']
                st.metric("진행", f"{ep_display}화")
else:
    st.info("시트에 데이터가 없습니다. 첫 기록을 남겨보세요!")

# --- 버전 히스토리 ---
# v1.8.0 (2026-02-28)
# * NoValidUrlKeyFound 에러 방지를 위해 모든 함수에 SHEET_URL 명시적 전달
# * RefreshError 방지를 위해 st.secrets 기반의 인증 구조 최적화
# * 데이터 타입 안정성(int 변환) 및 빈 시트 예외 처리 강화