#!/usr/bin/env python3
"""PDF → 한국어 번역 → Notion 저장 CLI 파이프라인"""

import argparse
import os
import sys
from pathlib import Path

import anthropic
import httpx
from dotenv import load_dotenv
from markitdown import MarkItDown


def extract_markdown(pdf_path: str) -> str:
    """PDF 파일을 마크다운으로 변환"""
    md = MarkItDown()
    result = md.convert(pdf_path)
    return result.text_content


def translate_to_korean(text: str) -> str:
    """Claude API로 마크다운을 한국어로 번역"""
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": (
                    "다음 마크다운 문서를 한국어로 번역해주세요. "
                    "마크다운 서식(제목, 목록, 표, 코드블록 등)은 그대로 유지하세요. "
                    "번역 결과만 출력하고, 설명이나 부가 텍스트는 넣지 마세요.\n\n"
                    f"{text}"
                ),
            }
        ],
    )
    return message.content[0].text


def create_notion_page(
    title: str, markdown_content: str, parent_page_id: str, token: str
) -> dict:
    """Notion에 마크다운 페이지 생성"""
    response = httpx.post(
        "https://api.notion.com/v1/pages",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        json={
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": [{"text": {"content": title}}],
            },
            "markdown": markdown_content,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="PDF → 한국어 번역 → Notion 저장 파이프라인"
    )
    parser.add_argument("pdf_path", help="변환할 PDF 파일 경로")
    parser.add_argument(
        "--title",
        default=None,
        help="노션 페이지 제목 (기본값: PDF 파일명)",
    )
    parser.add_argument(
        "--parent-page-id",
        default=os.getenv("NOTION_PARENT_PAGE_ID"),
        help="노션 부모 페이지 ID (환경변수 NOTION_PARENT_PAGE_ID로도 설정 가능)",
    )
    parser.add_argument(
        "--skip-translate",
        action="store_true",
        help="번역을 건너뛰고 원문 그대로 저장",
    )
    parser.add_argument(
        "--output-md",
        default=None,
        help="마크다운 파일로도 저장 (선택)",
    )
    args = parser.parse_args()

    # 유효성 검사
    if not Path(args.pdf_path).exists():
        print(f"오류: 파일을 찾을 수 없습니다: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    notion_token = os.getenv("NOTION_API_TOKEN")
    if not notion_token:
        print("오류: NOTION_API_TOKEN 환경변수를 설정해주세요.", file=sys.stderr)
        sys.exit(1)

    if not args.parent_page_id:
        print(
            "오류: --parent-page-id를 지정하거나 NOTION_PARENT_PAGE_ID 환경변수를 설정해주세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.skip_translate and not os.getenv("ANTHROPIC_API_KEY"):
        print("오류: ANTHROPIC_API_KEY 환경변수를 설정해주세요.", file=sys.stderr)
        sys.exit(1)

    title = args.title or Path(args.pdf_path).stem

    # Step 1: PDF → 마크다운
    print(f"[1/3] PDF 변환 중: {args.pdf_path}")
    markdown_text = extract_markdown(args.pdf_path)
    print(f"      변환 완료 ({len(markdown_text)} 글자)")

    # Step 2: 번역
    if args.skip_translate:
        print("[2/3] 번역 건너뜀")
        translated = markdown_text
    else:
        print("[2/3] 한국어 번역 중...")
        translated = translate_to_korean(markdown_text)
        print(f"      번역 완료 ({len(translated)} 글자)")

    # 마크다운 파일 저장 (선택)
    if args.output_md:
        Path(args.output_md).write_text(translated, encoding="utf-8")
        print(f"      마크다운 저장: {args.output_md}")

    # Step 3: Notion에 저장
    print(f"[3/3] Notion에 저장 중: '{title}'")
    result = create_notion_page(title, translated, args.parent_page_id, notion_token)
    page_url = result.get("url", "URL 없음")
    print(f"      완료! {page_url}")


if __name__ == "__main__":
    main()
