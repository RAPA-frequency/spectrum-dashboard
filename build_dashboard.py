import os
import json
import time
import re
from datetime import datetime

# 파일 경로 설정 (구조에 맞게 정확히 매핑)
FCC_JSON_PATH = 'FCC/fcc_data.json'
PT_JSON_PATH = 'PolicyTracker/policy_db.json'
HTML_FILE = 'index.html'

def load_json_safe(file_path):
    """JSON 파일을 안전하게 읽어오는 함수"""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"⚠️ '{file_path}' 파일이 올바른 JSON 형식이 아닙니다.")
                return []
    print(f"ℹ️ '{file_path}' 파일이 아직 존재하지 않아 빈 데이터로 처리합니다.")
    return []

def build_dashboard():
    print("🚀 각 폴더의 데이터를 취합하여 대시보드 빌드를 시작합니다...")

    if not os.path.exists(HTML_FILE):
        print(f"⚠️ 기준이 되는 '{HTML_FILE}' 파일이 존재하지 않습니다.")
        return

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # ----------------------------------------------------------------
    # 1. 상단 업데이트 기준일 최신화 (실행 당일 날짜로 세팅)
    # ----------------------------------------------------------------
    now = datetime.now()
    current_date_str = f" '{now.strftime('%y')}년 {now.month}월 {now.day}일 기준"
    html_content = re.sub(
        r"(<h5[^>]*>업데이트:).*?(</h5>)", 
        rf"\g<1>{current_date_str}\g<2>", 
        html_content, 
        count=1, 
        flags=re.IGNORECASE | re.DOTALL
    )

    # ----------------------------------------------------------------
    # 2. [파트 A] FCC 데이터 취합 및 HTML 주입 (히든 없음)
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
        if not tab_id: 
            continue
        
        fcc_trs[tab_id] += f"""
                    <tr class="item-row">
                        <td class="col-band"><span class="badge">{item.get('type', 'Notice')}</span></td>
                        <td class="col-title"><strong>{item.get('title_ko', '')}</strong><br><span class="en-title">{item.get('title_en', '')}</span></td>
                        <td class="col-summary">{item.get('summary', '')}<br><a href="{item.get('link', '#')}" target="_blank" class="link-btn" onclick="event.stopPropagation();">🔗 원문 링크 열기</a></td>
                        <td class="col-date">{item.get('date', '')}</td>
                    </tr>"""

    for b_name, b_id in fcc_html_ids.items():
        pattern = f'(id="{b_id}"[^>]*>.*?<tbody>)(.*?)(</tbody>)'
        safe_repl = r'\g<1>\n' + fcc_trs[b_id].replace('\\', '\\\\') + r'\n                    \g<3>'
        html_content = re.sub(pattern, safe_repl, html_content, count=1, flags=re.DOTALL)


    # ----------------------------------------------------------------
    # 3. [파트 B] PolicyTracker 데이터 취합 및 히든 레이아웃 새로 생성
    # ----------------------------------------------------------------
    pt_data = load_json_safe(PT_JSON_PATH)
    pt_html_ids = {
        '위성통신 및 D2D': 'pt_0',
        '차세대 이동통신(5G/6G) 및 시장 동향': 'pt_1',
        '공공·산업망 및 간섭 관리': 'pt_2',
        '글로벌 주파수 정책 및 법안': 'pt_3'
    }
    pt_trs = {b_id: "" for b_id in pt_html_ids.values()}
    hidden_divs_html = ""

    for i, item in enumerate(pt_data):
        tab_id = pt_html_ids.get(item.get('category', ''), 'pt_1')
        unique_article_id = f"pt-article-{i}" # 순서 기준 고유 고정 ID 생성

        # PolicyTracker 메인 화면용 테이블 tr 조립
        pt_trs[tab_id] += f"""
                    <tr class="item-row" onclick="openNewWindow('{unique_article_id}')">
                        <td class="col-band"><span class="badge">{item.get('band', '전 대역')}</span></td>
                        <td class="col-title"><strong>{item.get('title_ko', '')}</strong><br><span class="en-title">{item.get('title_en', '')}</span></td>
                        <td class="col-summary">{item.get('summary', '')}</td>
                        <td class="col-date">{item.get('date', '')}</td>
                    </tr>"""

        # 🌟 PolicyTracker 전용 팝업용 히든 div 상세 템플릿 생성
        full_ko_content = item.get('full_ko', '내용 없음').replace('\n', '<br>')
        full_en_content = item.get('full_en', '내용 없음').replace('\n', '<br>')

        hidden_divs_html += f"""
        <div id="{unique_article_id}" style="display: none;">
            <div style="max-width: 900px; margin: 0 auto; font-family: 'Malgun Gothic', sans-serif; color: #333; line-height: 1.7;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #34495e; padding-bottom: 10px; line-height: 1.4;">{item.get('title_ko', '')}</h2>
                <p style="color: #7f8c8d; font-size: 0.9em; margin-bottom: 10px;">발행일: {item.get('date', '')} | 카테고리: {item.get('category', '')}</p>
                <p style="color: #2980b9; font-weight: bold; margin-bottom: 30px;">주파수 대역: {item.get('band', '전 대역')}</p>
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

    # PolicyTracker 메인 테이블 주입
    for cat_name, b_id in pt_html_ids.items():
        pattern = f'(id="{b_id}"[^>]*>.*?<tbody>)(.*?)(</tbody>)'
        safe_repl = r'\g<1>\n' + pt_trs[b_id].replace('\\', '\\\\') + r'\n                    \g<3>'
        html_content = re.sub(pattern, safe_repl, html_content, count=1, flags=re.DOTALL)

    # ----------------------------------------------------------------
    # 4. 팝업용 hidden-data 구역 복구 및 데이터 주입 (예외 철저 방어)
    # ----------------------------------------------------------------
    hidden_div_wrapper = f'<div id="hidden-data">\n{hidden_divs_html}\n</div>'
    
    if 'id="hidden-data"' in html_content:
        # 기존에 태그 흔적이 있다면 내부 내용만 깔끔하게 교체
        hidden_pattern = r'(<div id="hidden-data"[^>]*>)(.*?)(</div>)'
        safe_hidden_repl = r'\g<1>\n' + hidden_divs_html.replace('\\', '\\\\') + r'\n</div>'
        html_content = re.sub(hidden_pattern, safe_hidden_repl, html_content, count=1, flags=re.DOTALL)
    else:
        # 🌟 중요: 히든 구역이 통째로 유실된 경우, </body> 태그 직전에 강제로 새로 만들어 넣음
        print("ℹ️ 기존 index.html에서 'hidden-data' 구역이 유실된 것을 감지하여 자동으로 재생성합니다.")
        html_content = html_content.replace('</body>', f'{hidden_div_wrapper}\n</body>')

    # ----------------------------------------------------------------
    # 5. 최종 파일 업데이트 완료
    # ----------------------------------------------------------------
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("\n📊 [완료] PolicyTracker의 번역 상세 본문(Hidden Data)이 성공적으로 복구 및 갱신되었습니다!")

if __name__ == "__main__":
    build_dashboard()
