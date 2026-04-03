"""
Agent Controller - 메인 엔트리포인트

맥미니에서 이 스크립트를 실행하면:
1. FastAPI 서버 (REST API + 웹 대시보드) 기동
2. Telegram 봇 기동
3. auto_start 에이전트 자동 시작

사용법:
    python run.py

환경변수 (.env 파일):
    TELEGRAM_BOT_TOKEN  - 텔레그램 봇 토큰 (필수)
    TELEGRAM_USER_IDS   - 허용할 텔레그램 유저 ID (쉼표 구분, 선택)
    API_HOST            - API 서버 호스트 (기본: 0.0.0.0)
    API_PORT            - API 서버 포트 (기본: 8080)
    AGENTS_CONFIG       - 에이전트 설정 파일 경로 (기본: config/agents.yaml)
"""

import asyncio
import logging
import os
import threading

import uvicorn
from dotenv import load_dotenv

from controller.agent_manager import AgentManager
from controller.api import create_api
from controller.dashboard import setup_dashboard
from controller.telegram_bot import TelegramBot

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("controller")


def main():
    # 설정 로드
    config_path = os.getenv("AGENTS_CONFIG", "config/agents.yaml")
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8080"))
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_user_ids_raw = os.getenv("TELEGRAM_USER_IDS", "")
    telegram_user_ids = [
        int(uid.strip())
        for uid in telegram_user_ids_raw.split(",")
        if uid.strip()
    ]

    # Agent Manager 초기화
    manager = AgentManager(config_path)

    # FastAPI 앱 생성
    app = create_api(manager)

    # 웹 대시보드 마운트
    dashboard_router = setup_dashboard(manager)
    app.include_router(dashboard_router)

    # auto_start 에이전트 시작 (서버 시작 후 실행)
    @app.on_event("startup")
    async def on_startup():
        logger.info("Starting auto-start agents...")
        await manager.auto_start_agents()
        logger.info("Agent Controller is ready")

    # Telegram 봇 시작 (별도 스레드)
    if telegram_token:
        logger.info("Starting Telegram bot...")

        def run_telegram():
            bot = TelegramBot(telegram_token, manager, telegram_user_ids)
            tg_app = bot.build_app()
            tg_app.run_polling(drop_pending_updates=True)

        tg_thread = threading.Thread(target=run_telegram, daemon=True)
        tg_thread.start()
        logger.info("Telegram bot started")
    else:
        logger.warning(
            "TELEGRAM_BOT_TOKEN not set - Telegram bot disabled. "
            "Web dashboard still available."
        )

    # API 서버 시작
    logger.info(f"Starting API server on {api_host}:{api_port}")
    logger.info(f"Dashboard: http://localhost:{api_port}")
    uvicorn.run(app, host=api_host, port=api_port, log_level="info")


if __name__ == "__main__":
    main()
