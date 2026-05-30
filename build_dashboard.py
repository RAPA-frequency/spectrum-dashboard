import os
import json
from datetime import datetime
from bs4 import BeautifulSoup

# 파일 경로 설정
FCC_JSON_PATH = 'FCC/fcc_data.json'
PT_JSON_PATH = 'PolicyTracker/policy_db.json'
HTML_FILE = 'index.html'

def load_json_safe(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def build_dashboard():
    print("🚀 [BeautifulSoup 엔진] 대시보드 취합 및 안전 빌드를 시작합니다...")

    if not os.path.exists(HTML_FILE):
        print(f"⚠️ 기준이 되는 '{HTML_FILE}' 파일이 존재하지 않습니다.")
        return

    # 1. 원본 HTML 읽기 및 BeautifulSoup 객체 변환 (구조 붕괴 절대 방지)
    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # 2. 상단 업데이트 날짜 실시간 최신화
    now = datetime.now()
    current_date_str = f"업데이트: '{now.strftime('%y')}년 {now.month}월 {now.day}일 기준"
    date_tag = soup.find(lambda tag: tag.name == 'h5' and '업데이트' in tag.text)
    if date_tag:
        date_tag.string = current_date_str

    # ----------------------------------------------------------------
    # 3. [FCC 파트] 데이터 처리 및 주입
    # ----------------------------------------------------------------
    fcc_data = load_json_safe(FCC_JSON_PATH)
    fcc_html_ids = {
        '무선통신국 (WTB)': 'fcc_541',
        '공학기술처 (OET)': 'fcc_526',
        '우주국 (Space)': 'fcc_13329'
    }
    fcc_trs = {b_id: "" for b_id in fcc_html_ids.values()}

    for item in fcc_data:
        tab_id = fcc_html_ids.get(item.get('bureau', ''))
        if not tab_id: continue
        fcc_trs[tab_id] += f"""
        <tr class="item-row">
            <td class="col-band"><span class="badge">{item.get('type', 'Notice')}</span></td>
            <td class="col-title"><strong>{item.get('title_ko', '')}</strong><br><span class="en-title">{item.get('title_en', '')}</span></td>
            <td class="col-summary">{item.get('summary', '')}<br><a href="{item.get('link', '#')}" target="_blank" class="link-btn" onclick="event.stopPropagation();">🔗 원문 링크 열기</a></td>
            <td class="col-date">{item.get('date', '')}</td>
        </tr>"""

    for b_id in fcc_html_ids.values():
        container = soup.find(id=b_id)
        if container:
            tbody = container.find('tbody')
            if tbody:
                tbody.clear()
                if fcc_trs[b_id].strip():
                    tbody.append(BeautifulSoup(fcc_trs[b_id], 'html.parser'))

    # ----------------------------------------------------------------
    # 4. [PolicyTracker 파트] 5개 카테고리 정밀 분류 및 주입
    # ----------------------------------------------------------------
    pt_data = load_json_safe(PT_JSON_PATH)
    pt_html_ids = ['pt_0', 'pt_1', 'pt_2', 'pt_3', 'pt_4']
    pt_trs = {b_id: "" for b_id in pt_html_ids}
    hidden_divs_html = ""

    for i, item in enumerate(pt_data):
        category_raw = item.get('category', '').strip()
        
        # 🌟 키워드 기반 5대 카테고리 정밀 분기 처리
        if '위성' in category_raw or 'D2D' in category_raw or '통신국' in category_raw:
            tab_id = 'pt_0'  # 위성통신 및 D2D
        elif '이동통신' in category_raw or '5G' in category_raw or '6G' in category_raw or '시장' in category_raw:
            tab_id = 'pt_1'  # 차세대 이동통신
        elif '공공' in category_raw or '산업망' in category_raw or '간섭' in category_raw or '관리' in category_raw:
            tab_id = 'pt_2'  # 공공·산업망 및 간섭
        elif '정책' in category_raw or '법안' in category_raw or '글로벌' in category_raw:
            tab_id = 'pt_3'  # 글로벌 정책 및 법안
        else:
            tab_id = 'pt_4'  # 기타 및 미분류 사단

        unique_article_id = f"pt-article-{i}"
        
        # 스크래퍼 변수명 매핑 보정 ('frequency_band', 'summary_ko')
        freq_band = item.get('frequency_band', '').strip()
        if not freq_band or freq_band == '-': freq_band = '전 대역'
        summary_ko = item.get('summary_ko', item.get('summary_en', '내용 없음'))

        # 테이블 테이블 행 생성
        pt_trs[tab_id] += f"""
        <tr class="item-row" onclick="openNewWindow('{unique_article_id}')">
            <td class="col-band"><span class="badge">{freq_band}</span></td>
            <td class="col-title"><strong>{item.get('title_ko', '')}</strong><br><span class="en-title">{item.get('title_en', '')}</span></td>
            <td class="col-summary">{summary_ko}</td>
            <td class="col-date">{item.get('date', '')}</td>
        </tr>"""

        # 🌟 숨김 팝업 상세 본문 생성 ('full_text_ko', 'full_text_en')
        full_ko_content = item.get('full_text_ko', '내용 없음').replace('\n', '<br>')
        full_en_content = item.get('full_text_en', '내용 없음').replace('\n', '<br>')

        hidden_divs_html += f"""
        <div id="{unique_article_id}" style="display: none;">
            <div style="max-width: 900px; margin: 0 auto; font-family: 'Malgun Gothic', sans-serif; color: #333; line-height: 1.7;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 10px; line-height: 1.4;">{item.get('title_ko', '')}</h2>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 10px;">발행일: {item.get('date', '')} | 카테고리: {category_raw}</p>
                <p style="color: #2980b9; font-weight: bold; margin-bottom: 30px;">주파수 대역: {freq_band}</p>
                <div style="background: #f8fafc; padding: 25px; border-radius: 8px; border: 1px solid #cbd5e1; margin-bottom: 30px;">
                    <span style="background-color: #2980b9; color: white; padding: 5px 12px; border-radius: 4px; font-weight: bold; font-size: 0.85em;">🇰🇷 한국어 번역 본문</span>
                    <div style="margin-top: 15px; font-size: 1.05em; color: #1a202c;">{full_ko_content}</div>
                </div>
                <div style="background: #ffffff; padding: 25px; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <span style="background-color: #7f8c8d; color: white; padding: 5px 12px; border-radius: 4px; font-weight: bold; font-size: 0.85em;">🇬🇧 영문 원본 본문</span>
                    <div style="margin-top: 15px; font-size: 0.95em; color: #4a5568;">{full_en_content}</div>
                </div>
            </div>
        </div>"""

    # 수집된 행들을 HTML 템플릿 내부에 안전하게 삽입
    for b_id in pt_html_ids:
        container = soup.find(id=b_id)
        if container:
            tbody = container.find('tbody')
            if tbody:
                tbody.clear()
                if pt_trs[b_id].strip():
                    tbody.append(BeautifulSoup(pt_trs[b_id], 'html.parser'))

    # 🌟 5. 지저분한 정규식 없이 hidden-data 구역 청소 후 재조립 (중복 헤더 버그 완벽 박멸)
    hidden_container = soup.find(id='hidden-data')
    if not hidden_container:
        hidden_container = soup.new_tag('div', id='hidden-data')
        soup.body.append(hidden_container)
    
    hidden_container.clear()
    if hidden_divs_html.strip():
        hidden_container.append(BeautifulSoup(hidden_divs_html, 'html.parser'))

    # 6. 최종 정렬된 깨끗한 HTML 파일로 저장
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))

    print("📊 [성공] 깨짐 현상 없이 대시보드 조립이 완벽하게 완료되었습니다!")

if __name__ == "__main__":
    build_dashboard()
