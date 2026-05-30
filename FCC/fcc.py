import os
import json
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Selenium 관련 라이브러리
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# OpenAI 라이브러리
from openai import OpenAI

# ==========================================
# 🔑 OpenAI API 키 설정 (GitHub Secrets 연동)
# ==========================================
# GitHub Secrets에 등록한 OPENAI_API_KEY를 안전하게 불러옵니다.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
client = OpenAI(api_key=OPENAI_API_KEY)

# 파일 경로 설정
JSON_FILE = 'fcc_data.json'
HTML_FILE = 'fcc.html'

def normalize_url(url):
    return url.strip().rstrip('/').lower() if url else ""

def normalize_title(title):
    return re.sub(r'\s+', '', title.strip().lower()) if title else ""

def load_existing_data():
    target_file = JSON_FILE
    if not os.path.exists(JSON_FILE) and os.path.exists('fcc_data원본.json'):
        target_file = 'fcc_data원본.json'

    if os.path.exists(target_file):
        with open(target_file, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_data(data):
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def translate_title_with_gpt(title_en):
    if not title_en:
        return "제목 없음"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 미국 통신/전파 정책 전문 번역가입니다. 제공된 영어 제목을 문맥에 맞는 자연스럽고 전문적인 한국어 제목으로 번역하세요. 부연 설명 없이 번역된 결과(제목)만 출력하세요."},
                {"role": "user", "content": title_en}
            ],
            temperature=0.15
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return title_en

def summarize_and_translate_with_gpt(text):
    if not text or "본문(TXT 파일)을 찾을 수 없습니다" in text or "내용 추출 실패" in text:
        return "원문 내용을 확인할 수 없어 요약을 제공하지 못했습니다."
    
    try:
        short_text = text[:15000] 
        
        system_prompt = """
        당신은 미국 연방통신위원회(FCC) 및 전파/통신 정책을 분석하는 최고 수준의 수석 애널리스트입니다. 
        제공된 영문 공문서를 읽고, 핵심 정책 내용만 추출하여 한국어 정책 브리핑 스타일로 3~4문장 분량으로 요약하세요.
        
        [절대 지켜야 할 번역 및 요약 규칙 - 위반 시 감점]
        1. 어투 및 종결어미: 반드시 정중하고 전문적인 경어체('~했습니다', '~합니다', '~조치입니다', '~예정입니다')를 사용하세요. 뉴스 기사처럼 '~했다', '~한다' 식의 평어체는 절대 사용하지 마세요.
        2. 주어 명시: 첫 문장은 반드시 "FCC(미국 연방통신위원회)의 [해당 부서명(예: 무선통신국(WTB), 공학기술처(OET) 등)]은(는)..." 형식으로 주체를 명확히 밝히며 시작하세요.
        3. 세부 정보와 전문성: 단순 요약에 그치지 말고, 이 정책/결정이 왜 이루어졌는지(배경), 시장이나 업계에 어떤 영향을 미치는지 구체적인 내용을 포함하여 유려하게 의역하세요. 
        4. 단순 절차 정보 배제: 공고일, 문서 번호(DA/FCC 등), 우편 주소 등은 철저히 제외하세요. (단, 주제 자체가 '기한 연장'인 경우에만 날짜 포함)
        
        [필수 고정 용어집]
        - FCC = FCC(미국 연방통신위원회)
        - OET = 공학기술처
        - WTB = 무선통신국
        - Space Bureau = 우주국
        - TCB = 통신인증기관
        - Post-Market Surveillance = 사후 시장 감시
        - Waiver = 면제 (또는 유예)
        - Covered List = 규제 대상 목록
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"다음 공문서를 위 가이드라인에 맞춰 최고 수준의 한국어 정책 브리핑으로 요약 및 번역해 주세요:\n\n{short_text}"}
            ],
            temperature=0.15 
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠️ 본문 요약/번역 오류: {e}")
        return "요약 및 번역 실패"

def get_detail_page_info(driver, article_url):
    """상세 페이지에 접속하여 '본문 내용(TXT)'과 '발행일(Date)'을 동시에 추출합니다."""
    raw_text = "본문(TXT 파일)을 찾을 수 없습니다."
    release_date = ""

    try:
        driver.get(article_url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 1. 상세 페이지에서 날짜 추출
        date_tag = soup.select_one('.edoc_release-dt time')
        if not date_tag:
            date_tag = soup.find('time')
        
        if date_tag and date_tag.text.strip():
            release_date = date_tag.text.strip()
        else:
            date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}', soup.text, re.IGNORECASE)
            if date_match:
                release_date = date_match.group(0).strip()

        # 2. 본문(TXT) 링크 찾아서 내용 긁어오기
        txt_link_tag = soup.find('a', string=lambda text: text and 'txt' in text.lower())
        if not txt_link_tag:
            txt_link_tag = soup.find('a', href=lambda href: href and href.lower().endswith('.txt'))
            
        if txt_link_tag and txt_link_tag.get('href'):
            txt_url = txt_link_tag['href']
            if txt_url.startswith('/'):
                txt_url = f"https://www.fcc.gov{txt_url}"
                
            driver.get(txt_url)
            time.sleep(2)
            raw_text = driver.find_element(By.TAG_NAME, "body").text.strip()
            
    except Exception as e:
        print(f"  ⚠️ 상세 페이지 파싱 오류: {e}")

    return raw_text, release_date

def fetch_new_fcc_data(driver, bureau_name, main_url, existing_links, existing_titles):
    print(f"\n[{bureau_name}] 데이터 수집 시작...")
    try:
        driver.get(main_url)
        time.sleep(5) 
    except Exception as e:
        print(f"⚠️ [{bureau_name}] 접속 오류: {e}")
        return []

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    new_data = []

    articles = soup.select('.views-row') 
    if not articles:
        articles = soup.select('.item-list ul li') or soup.select('article')

    for article in articles:
        try:
            title_tag = article.select_one('h3 a') or article.select_one('.field-title a') or article.select_one('a')
            if not title_tag:
                continue
                
            article_link = title_tag['href']
            if article_link.startswith('/'):
                article_link = f"https://www.fcc.gov{article_link}"
            
            title_en = title_tag.text.strip()
            title_en = " ".join(title_en.split())
            
            article_link_norm = normalize_url(article_link)
            title_en_norm = normalize_title(title_en)
            
            if (article_link_norm in existing_links) or (title_en_norm in existing_titles):
                print(" 🛑 이미 수집된 최신 기사를 확인했습니다. 해당 부서 수집을 중단합니다.")
                break
            
            if len(title_en) < 5 or "read more" in title_en.lower():
                continue
                
            print(f" 🌟 신규 기사 발견: {title_en[:30]}... (GPT 요약 중 ⏳)")
            
            type_tag = article.select_one('.document-type') or article.select_one('.views-field-document-type .field-content')
            doc_type = type_tag.text.strip() if type_tag else "Notice"
            
            raw_text, detail_date = get_detail_page_info(driver, article_link)
            
            if detail_date:
                date_str = detail_date
            else:
                date_str = "날짜 미상"
            
            title_ko = translate_title_with_gpt(title_en)
            summary_ko = summarize_and_translate_with_gpt(raw_text)

            new_data.append({
                'bureau': bureau_name,
                'type': doc_type,
                'title_ko': title_ko,
                'title_en': title_en,
                'summary': summary_ko,
                'date': date_str,
                'link': article_link
            })
            
            time.sleep(2)
            
        except Exception as e:
            continue

    return new_data

def update_index_html(new_data_total):
    if not os.path.exists(HTML_FILE):
        print(f"⚠️ '{HTML_FILE}' 파일을 찾을 수 없어 HTML 업데이트를 건너뜁니다.")
        return

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 대시보드 상단 업데이트 날짜를 오늘 날짜로 자동 변경
    now = datetime.now()
    current_date_str = f" '{now.strftime('%y')}년 {now.month}월 {now.day}일 기준"
    html_content = re.sub(
        r"(<h5[^>]*>업데이트:).*?(</h5>)", 
        rf"\g<1>{current_date_str}\g<2>", 
        html_content, 
        count=1, 
        flags=re.IGNORECASE | re.DOTALL
    )

    bureau_html_ids = {
        '무선통신국 (WTB)': 'fcc_541',
        '공학기술처 (OET)': 'fcc_526',
        '우주국 (Space)': 'fcc_13329'
    }

    new_html_by_bureau = {b_id: "" for b_id in bureau_html_ids.values()}

    for item in reversed(new_data_total):
        tab_id = bureau_html_ids.get(item['bureau'])
        if not tab_id:
            continue
            
        tr_html = f"""
                    <tr class="item-row">
                        <td class="col-band"><span class="badge">{item['type']}</span></td>
                        <td class="col-title"><strong>{item['title_ko']}</strong><br><span class="en-title">{item['title_en']}</span></td>
                        <td class="col-summary">{item['summary']}<br><a href="{item['link']}" target="_blank" class="link-btn" onclick="event.stopPropagation();">🔗 원문 링크 열기</a></td>
                        <td class="col-date">{item['date']}</td>
                    </tr>"""
        new_html_by_bureau[tab_id] = tr_html + new_html_by_bureau[tab_id]

    for b_name, b_id in bureau_html_ids.items():
        if new_html_by_bureau[b_id]:
            pattern = f'(id="{b_id}"[^>]*>.*?<tbody>)'
            safe_replacement = r'\g<1>' + new_html_by_bureau[b_id].replace('\\', '\\\\')
            
            html_content = re.sub(
                pattern, 
                safe_replacement, 
                html_content, 
                count=1, 
                flags=re.DOTALL
            )

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"\n✅ '{HTML_FILE}' 파일에 원본 손상 없이 기사 및 날짜 업데이트가 완료되었습니다!")

def main():
    targets = {
        '무선통신국 (WTB)': 'https://www.fcc.gov/news-events/headlines/541', 
        '공학기술처 (OET)': 'https://www.fcc.gov/news-events/headlines/526',
        '우주국 (Space)': 'https://www.fcc.gov/news-events/headlines/13329'
    }
    
    existing_data = load_existing_data()
    existing_links = {normalize_url(item['link']) for item in existing_data if 'link' in item}
    existing_titles = {normalize_title(item['title_en']) for item in existing_data if 'title_en' in item}
    
    print(f"📄 기존 저장된 기사 수: {len(existing_data)}개")

    chrome_options = Options()
    # GitHub Actions 환경을 위한 필수 헤드리스 옵션
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    print("🚀 크롬 브라우저를 구동하여 신규 기사를 탐색합니다...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    new_data_total = []
    
    try:
        for bureau, url in targets.items():
            new_data = fetch_new_fcc_data(driver, bureau, url, existing_links, existing_titles)
            new_data_total.extend(new_data)
    finally:
        driver.quit()
        
    # 4. 결과 처리
    if new_data_total:
        print(f"\n✅ 총 {len(new_data_total)}건의 신규 기사를 추가합니다.")
        final_data = new_data_total + existing_data
        save_data(final_data)
        update_index_html(new_data_total) 
    else:
        print("\n✅ 새롭게 추가된 기사는 없지만, 대시보드 기준일(날짜)은 최신으로 갱신합니다.")
        update_index_html([]) 

if __name__ == "__main__":
    main()
