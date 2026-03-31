#!/usr/bin/env python3
"""
네이버 금융에서 4종목(메지온, 삼성전자, 월덱스, SK하이닉스)의
일별 시세 + 기관/외국인 순매수를 스크래핑하고,
수급 오실레이터 이중축 차트를 PNG로 저장하는 스크립트.

사용법:
    pip install requests beautifulsoup4 lxml openpyxl pandas numpy scipy matplotlib
    python scrape_and_chart.py
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from scipy.stats import linregress
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import sys
import time
from datetime import datetime, date

# ────────────────────────────────────────
# 한글 폰트 설정
# ────────────────────────────────────────
def setup_korean_font():
    candidates = [
        # macOS
        '/System/Library/Fonts/AppleSDGothicNeo.ttc',
        '/Library/Fonts/AppleGothic.ttf',
        '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
        # Linux
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        # Windows
        'C:/Windows/Fonts/malgun.ttf',
    ]
    for fp in candidates:
        if os.path.exists(fp):
            fm.fontManager.addfont(fp)
            prop = fm.FontProperties(fname=fp)
            plt.rcParams['font.family'] = prop.get_name()
            plt.rcParams['axes.unicode_minus'] = False
            print(f"  Font: {prop.get_name()}")
            return
    # fallback search
    for f in fm.fontManager.ttflist:
        if any(k in f.name.lower() for k in ['apple sd', 'nanum', 'noto', 'cjk', 'gothic', 'malgun']):
            plt.rcParams['font.family'] = f.name
            plt.rcParams['axes.unicode_minus'] = False
            print(f"  Font (fallback): {f.name}")
            return
    print("  WARNING: Korean font not found. Text may not render correctly.")

# ────────────────────────────────────────
# 종목 설정
# ────────────────────────────────────────
STOCKS = {
    '메지온':     '241310',
    '삼성전자':   '005930',
    '월덱스':     '101160',
    'SK하이닉스': '000660',
}
START_DATE = date(2025, 11, 1)
TODAY = date.today()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
XLSX_PATH = os.path.expanduser('~/raw_data.xlsx')

# ────────────────────────────────────────
# 스크래핑: 일별 시세
# ────────────────────────────────────────
def scrape_daily_price(code, start_date, end_date):
    """네이버 금융 sise_day 페이지에서 일별 시세를 가져온다."""
    rows = []
    page = 1
    while True:
        url = f'https://finance.naver.com/item/sise_day.naver?code={code}&page={page}'
        resp = requests.get(url, headers=HEADERS)
        resp.encoding = 'euc-kr'
        soup = BeautifulSoup(resp.text, 'lxml')
        table = soup.find('table', class_='type2')
        if not table:
            break

        trs = table.find_all('tr', attrs={'onmouseover': True})
        if not trs:
            break

        stop = False
        for tr in trs:
            tds = tr.find_all('td')
            if len(tds) < 7:
                continue
            date_str = tds[0].text.strip()
            try:
                dt = datetime.strptime(date_str, '%Y.%m.%d').date()
            except ValueError:
                continue
            if dt < start_date:
                stop = True
                break
            if dt > end_date:
                continue
            close = int(tds[1].text.strip().replace(',', ''))
            change = tds[2].text.strip().replace(',', '')
            open_p = int(tds[3].text.strip().replace(',', ''))
            high = int(tds[4].text.strip().replace(',', ''))
            low = int(tds[5].text.strip().replace(',', ''))
            volume = int(tds[6].text.strip().replace(',', ''))
            rows.append({
                '날짜': dt, '종가': close, '전일비': change,
                '시가': open_p, '고가': high, '저가': low, '거래량': volume,
            })
        if stop:
            break

        # 마지막 페이지 확인
        pgrr = soup.find('td', class_='pgRR')
        if pgrr:
            last_page = int(pgrr.a['href'].split('=')[-1])
            if page >= last_page:
                break
        else:
            break
        page += 1
        time.sleep(0.25)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values('날짜').reset_index(drop=True)
    return df

# ────────────────────────────────────────
# 스크래핑: 기관/외국인 순매매
# ────────────────────────────────────────
def scrape_investor_trading(code, start_date, end_date):
    """네이버 금융 frgn 페이지에서 기관/외국인 순매매를 가져온다."""
    rows = []
    page = 1
    while True:
        url = f'https://finance.naver.com/item/frgn.naver?code={code}&page={page}'
        resp = requests.get(url, headers=HEADERS)
        resp.encoding = 'euc-kr'
        soup = BeautifulSoup(resp.text, 'lxml')
        table = soup.find('table', class_='type2')
        if not table:
            break

        trs = table.find_all('tr', attrs={'onmouseover': True})
        if not trs:
            break

        stop = False
        for tr in trs:
            tds = tr.find_all('td')
            if len(tds) < 6:
                continue
            date_str = tds[0].text.strip()
            try:
                dt = datetime.strptime(date_str, '%Y.%m.%d').date()
            except ValueError:
                continue
            if dt < start_date:
                stop = True
                break
            if dt > end_date:
                continue

            def parse_signed(td):
                text = td.text.strip().replace(',', '').replace('+', '')
                try:
                    return int(text)
                except ValueError:
                    return 0

            institutional = parse_signed(tds[4])
            foreign = parse_signed(tds[5])
            rows.append({
                '날짜': dt,
                '기관순매매': institutional,
                '외국인순매매': foreign,
            })
        if stop:
            break

        pgrr = soup.find('td', class_='pgRR')
        if pgrr:
            last_page = int(pgrr.a['href'].split('=')[-1])
            if page >= last_page:
                break
        else:
            break
        page += 1
        time.sleep(0.25)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values('날짜').reset_index(drop=True)
    return df

# ────────────────────────────────────────
# 수급 오실레이터 계산
# ────────────────────────────────────────
def compute_oscillator(close_series, window=10, multiplier=5):
    """
    오실레이터 = (종가 / 첫날 종가) 비율의 10일 선형회귀 기울기 × 5
    """
    first_close = close_series.iloc[0]
    ratio = close_series / first_close
    osc = pd.Series(np.nan, index=close_series.index)
    for i in range(window - 1, len(ratio)):
        y = ratio.iloc[i - window + 1 : i + 1].values
        x = np.arange(window)
        slope, _, _, _, _ = linregress(x, y)
        osc.iloc[i] = slope * multiplier
    return osc

# ────────────────────────────────────────
# 차트 그리기
# ────────────────────────────────────────
def draw_chart(dates, close, oscillator, name, save_path):
    fig, ax1 = plt.subplots(figsize=(14, 6))

    # 종가 (검은선)
    ax1.plot(dates, close, color='black', linewidth=1.2, label='종가')
    ax1.set_ylabel('종가 (원)', color='black', fontsize=11)
    ax1.tick_params(axis='y', labelcolor='black')
    ax1.set_xlabel('날짜', fontsize=11)

    # 오실레이터 (빨간선, 이중축)
    ax2 = ax1.twinx()
    ax2.plot(dates, oscillator, color='red', linewidth=1.0, label='수급 오실레이터')
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.7)
    ax2.set_ylabel('수급 오실레이터', color='red', fontsize=11)
    ax2.tick_params(axis='y', labelcolor='red')

    fig.suptitle(f'{name} — 종가 & 수급 오실레이터 (2025.11~현재)', fontsize=14, fontweight='bold')
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  -> 차트 저장: {save_path}")

# ────────────────────────────────────────
# 메인
# ────────────────────────────────────────
def main():
    print("=" * 50)
    print(" 주식 데이터 수집 & 수급 오실레이터 차트 생성")
    print("=" * 50)
    print(f"  기간: {START_DATE} ~ {TODAY}")
    print(f"  종목: {', '.join(STOCKS.keys())}")
    setup_korean_font()
    print()

    all_data = {}

    for name, code in STOCKS.items():
        print(f"[{name} ({code})]")

        print(f"  일별 시세 스크래핑...")
        price_df = scrape_daily_price(code, START_DATE, TODAY)
        print(f"  -> {len(price_df)}건")

        print(f"  기관/외국인 순매매 스크래핑...")
        investor_df = scrape_investor_trading(code, START_DATE, TODAY)
        print(f"  -> {len(investor_df)}건")

        if not price_df.empty and not investor_df.empty:
            merged = pd.merge(price_df, investor_df, on='날짜', how='left')
        elif not price_df.empty:
            merged = price_df.copy()
            merged['기관순매매'] = 0
            merged['외국인순매매'] = 0
        else:
            print(f"  !! 데이터 없음, 건너뜀")
            continue

        merged['종목명'] = name
        merged['종목코드'] = code
        all_data[name] = merged
        print()

    if not all_data:
        print("ERROR: 수집된 데이터가 없습니다. 네트워크 연결을 확인하세요.")
        sys.exit(1)

    # ── Excel 저장 ──
    # 기존 파일이 있으면 기존 시트 유지하면서 추가/업데이트
    print(f"Excel 저장: {XLSX_PATH}")
    if os.path.exists(XLSX_PATH):
        existing = pd.read_excel(XLSX_PATH, sheet_name=None, engine='openpyxl')
        # 기존 시트 중 이번에 업데이트하지 않는 것은 유지
        for sheet_name, df in existing.items():
            if sheet_name not in all_data:
                all_data[sheet_name] = df
        print(f"  (기존 파일에 데이터 병합)")

    with pd.ExcelWriter(XLSX_PATH, engine='openpyxl') as writer:
        for name, df in all_data.items():
            sheet_name = name[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    print(f"  -> 저장 완료\n")

    # ── 차트 생성 ──
    print("차트 생성 중...")
    for name in STOCKS.keys():
        if name not in all_data:
            continue
        df = all_data[name]
        if len(df) < 10:
            print(f"  [{name}] 데이터 부족 ({len(df)}건), 건너뜀")
            continue
        osc = compute_oscillator(df['종가'])
        save_path = os.path.join(SCRIPT_DIR, f'{name}_oscillator.png')
        draw_chart(df['날짜'], df['종가'], osc, name, save_path)

    print("\n완료!")


if __name__ == '__main__':
    main()
