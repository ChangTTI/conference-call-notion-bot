"""
REST API - FastAPI 기반 에이전트 제어 API

엔드포인트:
- GET  /api/agents          - 모든 에이전트 상태
- GET  /api/agents/{id}     - 특정 에이전트 상태
- POST /api/agents/{id}/start   - 에이전트 시작
- POST /api/agents/{id}/stop    - 에이전트 중지
- POST /api/agents/{id}/restart - 에이전트 재시작
- GET  /api/agents/{id}/logs    - 에이전트 로그
- POST /api/agents/{id}/command - 에이전트에 명령 전달
- POST /api/command             - 마스터 에이전트에 명령 전달
- GET  /api/system              - 시스템 정보
- POST /api/config/reload       - 설정 리로드
"""

import logging
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CommandRequest(BaseModel):
    command: str
    timeout: float = 30


class StopRequest(BaseModel):
    force: bool = False


def create_api(agent_manager) -> FastAPI:
    api = FastAPI(title="Agent Controller API", version="1.0.0")

    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @api.get("/api/agents")
    async def list_agents():
        statuses = agent_manager.get_all_statuses()
        return {"agents": [asdict(s) for s in statuses]}

    @api.get("/api/agents/{agent_id}")
    async def get_agent(agent_id: str):
        status = agent_manager.get_agent_status(agent_id)
        if not status:
            raise HTTPException(404, f"Agent '{agent_id}' not found")
        return asdict(status)

    @api.post("/api/agents/{agent_id}/start")
    async def start_agent(agent_id: str):
        result = await agent_manager.start_agent(agent_id)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @api.post("/api/agents/{agent_id}/stop")
    async def stop_agent(agent_id: str, req: StopRequest = StopRequest()):
        result = await agent_manager.stop_agent(agent_id, force=req.force)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @api.post("/api/agents/{agent_id}/restart")
    async def restart_agent(agent_id: str):
        result = await agent_manager.restart_agent(agent_id)
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @api.get("/api/agents/{agent_id}/logs")
    async def get_logs(agent_id: str, lines: int = 100):
        if agent_id not in agent_manager.agents:
            raise HTTPException(404, f"Agent '{agent_id}' not found")
        logs = agent_manager.get_full_logs(agent_id, lines)
        return {"agent_id": agent_id, "logs": logs}

    @api.post("/api/agents/{agent_id}/command")
    async def send_command(agent_id: str, req: CommandRequest):
        result = await agent_manager.send_command(
            agent_id, req.command, req.timeout
        )
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @api.post("/api/command")
    async def send_master_command(req: CommandRequest):
        result = await agent_manager.send_command_to_master(
            req.command, req.timeout
        )
        if not result["success"]:
            raise HTTPException(400, result["error"])
        return result

    @api.get("/api/system")
    async def system_info():
        return agent_manager.get_system_info()

    @api.post("/api/config/reload")
    async def reload_config():
        agent_manager.reload_config()
        return {
            "success": True,
            "agents_count": len(agent_manager.agents),
            "message": "Config reloaded",
        }

    return api
