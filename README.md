# conference-call-notion-bot

PDF 문서를 한국어로 번역하여 Notion에 자동 저장하는 CLI 도구.

## 파이프라인

```
PDF → MarkItDown(마크다운 변환) → Claude API(한국어 번역) → Notion API(페이지 저장)
```

## 설치

```bash
pip install -r requirements.txt
```

## 환경변수 설정

`.env.example`을 `.env`로 복사하고 값을 채워주세요.

```bash
cp .env.example .env
```

| 변수 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `NOTION_API_TOKEN` | Notion Internal Integration 토큰 |
| `NOTION_PARENT_PAGE_ID` | 페이지를 저장할 부모 페이지 ID |

### Notion 부모 페이지 ID 찾기

Notion 페이지 URL에서 마지막 32자리 hex 문자열이 페이지 ID입니다:
```
https://notion.so/My-Page-1234567890abcdef1234567890abcdef
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
```

## 사용법

```bash
# 기본 사용
python main.py report.pdf

# 제목 지정
python main.py report.pdf --title "회의록 번역본"

# 부모 페이지 직접 지정
python main.py report.pdf --parent-page-id "1234567890abcdef..."

# 번역 없이 원문 저장
python main.py report.pdf --skip-translate

# 마크다운 파일로도 저장
python main.py report.pdf --output-md translated.md
```
