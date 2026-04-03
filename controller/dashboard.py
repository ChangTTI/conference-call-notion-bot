"""
Web Dashboard - FastAPI에 마운트되는 웹 UI 라우터
"""

import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter()

# agent_manager는 setup에서 주입
_manager = None


def setup_dashboard(agent_manager):
    global _manager
    _manager = agent_manager
    return router


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    statuses = _manager.get_all_statuses()
    system = _manager.get_system_info()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "agents": [asdict(s) for s in statuses],
            "system": system,
        },
    )
