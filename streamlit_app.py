import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# 데이터 저장 파일
DB_FILE = "webtoon_history.json"

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- UI 설정 ---
st.set_page_config(page_title="My Webtoon Tracker", layout="wide")
st.title("📚 웹툰 감상 기록기")

data = load_data()

# 1. 새로운 웹툰 등록/업데이트 섹션
with st.expander("➕ 새 에피소드 기록하기", expanded=True):
    col1, col2, col3 = st.columns([3, 1, 4])
    with col1:
        title = st.text_input("웹툰 제목", placeholder="예: 나 혼자만 레벨업")
    with col2:
        episode = st.number_input("현재 화수", min_value=1, step=1)
    with col3:
        url = st.text_input("현재 페이지 URL")
    
    if st.button("기록 저장하기"):
        if title:
            data[title] = {
                "episode": episode,
                "url": url,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_data(data)
            st.success(f"'{title}' {episode}화 기록 완료!")
            st.rerun()

st.divider()

# 2. 웹툰 리스트 출력
st.subheader("📖 현재 정주행 목록")
if data:
    # 표 형식으로 변환하여 보기 좋게 출력
    df_list = []
    for t, info in data.items():
        df_list.append({
            "제목": t,
            "최근 화수": f"{info['episode']}화",
            "업데이트일": info['updated_at'],
            "바로가기": info['url']
        })
    
    df = pd.DataFrame(df_list)
    
    # 리스트를 카드 형태로 출력 (모바일 가독성 최적화)
    for index, row in df.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.markdown(f"**{row['제목']}** ({row['최근 화수']})")
            c2.write(f"🕒 {row['업데이트일']}")
            if row['바로가기']:
                c3.link_button("🚀 이어서 보기", row['바로가기'], use_container_width=True)
else:
    st.info("아직 기록된 웹툰이 없습니다. 위에서 등록해 보세요!")

# 버전 관리 정보 (요청하신 히스토리 추가)
# v1.0.0: 초기 웹툰 트래커 구현 (저장/불러오기/링크 이동)
# v1.1.0: UI 레이아웃 모바일 최적화 및 카드 뷰 적용