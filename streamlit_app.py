import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import sys
import io

# [필수] 한글 인코딩 에러 방지 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# 1. 페이지 설정
st.set_page_config(page_title="Webtoon Tracker", layout="wide")
st.title("📚 웹툰 실시간 기록기")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# --- [수정 포인트] 본인의 구글 시트 주소를 입력하세요 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/14nRamWc2f6FF6KTLbpHly7oB095fllDZI6whoEKzq5c/edit"

# 한국 시간(KST) 계산 함수
def get_kst_now():
    return (datetime.now() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")

# 3. 데이터 불러오기 함수
@st.cache_data(ttl=0)
def load_data():
    try:
        # 주소를 직접 사용하여 데이터를 읽어옴
        data = conn.read(spreadsheet=SHEET_URL, ttl="0")
        
        # '날짜' 컬럼이 없는 경우를 대비한 자동 생성
        if not data.empty and '날짜' not in data.columns:
            data['날짜'] = ""
        return data
    except Exception as e:
        st.error(f"데이터 로딩 실패: {str(e)}")
        # 에러 발생 시 기본 헤더를 가진 빈 데이터프레임 반환
        return pd.DataFrame(columns=["제목", "화수", "URL", "날짜"])

# 데이터 로드
df = load_data()

# 4. 입력 및 업데이트 섹션
with st.expander("➕ 새 웹툰 등록 / 제목으로 수정", expanded=False):
    with st.form("update_form", clear_on_submit=True):
        title = st.text_input("웹툰 제목")
        episode = st.number_input("현재 몇 화인가요?", min_value=1, step=1)
        url = st.text_input("현재 페이지 링크(URL)")
        submit = st.form_submit_button("시트에 저장")

        if submit and title:
            current_time = get_kst_now()
            title_clean = title.strip()
            
            # 기존 목록에 제목이 있으면 업데이트, 없으면 추가
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

# 5. 나의 정주행 목록 출력 (수정/삭제 기능 포함)
st.subheader("📖 나의 정주행 리스트")

if not df.empty:
    # 최신 기록이 위로 오도록 역순 출력
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
                # 수정 버튼
                if st.button("✏️ 수정", key=f"edit_{index}"):
                    st.session_state[f"editing_{index}"] = True
                
                # 삭제 버튼
                if st.button("🗑️ 삭제", key=f"del_{index}"):
                    st.session_state[f"confirm_delete_{index}"] = True

            # --- 수정 폼 ---
            if st.session_state.get(f"editing_{index}", False):
                with st.form(key=f"edit_form_{index}"):
                    st.write(f"**[{row['제목']}]** 정보 수정")
                    # 기존 화수 숫자로 변환 시도
                    try:
                        current_ep = int(row['화수'])
                    except:
                        current_ep = 1
                    
                    new_ep = st.number_input("화수 변경", value=current_ep)
                    new_url = st.text_input("URL 변경", value=row['URL'])
                    
                    col_save, col_cancel = st.columns(2)
                    if col_save.form_submit_button("✅ 적용"):
                        current_time = get_kst_now()
                        df.loc[index, ['화수', 'URL', '날짜']] = [new_ep, new_url, current_time]
                        conn.update(spreadsheet=SHEET_URL, data=df)
                        del st.session_state[f"editing_{index}"]
                        st.rerun()
                    if col_cancel.form_submit_button("❌ 취소"):
                        del st.session_state[f"editing_{index}"]
                        st.rerun()

            # --- 삭제 확인 폼 ---
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
    st.info("리스트가 비어있습니다. 첫 웹툰을 등록해 보세요!")

# --- 버전 히스토리 ---
# v2.2.2 (2026-02-28)
# * 'ascii' 인코딩 에러 해결을 위한 UTF-8 강제 설정 추가
# * 한국 시간(KST) 보정 및 개별 항목 수정/삭제 기능 통합
# * 제목 공백 제거(strip)로 데이터 매칭 정확도 향상