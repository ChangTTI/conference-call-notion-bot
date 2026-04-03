"""
Agent Manager - 맥미니 에이전트 프로세스 생명주기 관리

기능:
- 에이전트 프로세스 시작/중지/재시작
- 상태 모니터링 (CPU, 메모리, 업타임)
- 로그 수집 및 조회
- 마스터/서브 에이전트 명령 전달
"""

import asyncio
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil
import yaml

logger = logging.getLogger(__name__)

LOG_DIR = Path.home() / ".agent_controller" / "logs"
COMMAND_DIR = Path.home() / ".agent_controller" / "commands"
RESPONSE_DIR = Path.home() / ".agent_controller" / "responses"


@dataclass
class AgentConfig:
    agent_id: str
    name: str
    description: str
    script: str
    working_dir: str
    python: str = "python3"
    auto_start: bool = False
    is_master: bool = False
    managed_by: Optional[str] = None
    env: dict = field(default_factory=dict)


@dataclass
class AgentStatus:
    agent_id: str
    name: str
    is_running: bool
    pid: Optional[int] = None
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    started_at: Optional[str] = None
    uptime_seconds: int = 0
    last_log_lines: list = field(default_factory=list)
    is_master: bool = False


class AgentManager:
    def __init__(self, config_path: str = "config/agents.yaml"):
        self.config_path = config_path
        self.agents: dict[str, AgentConfig] = {}
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.start_times: dict[str, datetime] = {}
        self._log_tasks: dict[str, asyncio.Task] = {}

        # 디렉토리 초기화
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        COMMAND_DIR.mkdir(parents=True, exist_ok=True)
        RESPONSE_DIR.mkdir(parents=True, exist_ok=True)

        self._load_config()

    def _load_config(self):
        """agents.yaml에서 에이전트 설정 로드"""
        config_path = Path(self.config_path)
        if not config_path.exists():
            logger.warning(f"Config not found: {config_path}")
            return

        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

        for agent_id, conf in raw.items():
            self.agents[agent_id] = AgentConfig(
                agent_id=agent_id,
                name=conf.get("name", agent_id),
                description=conf.get("description", ""),
                script=os.path.expanduser(conf["script"]),
                working_dir=os.path.expanduser(conf.get("working_dir", "~")),
                python=conf.get("python", "python3"),
                auto_start=conf.get("auto_start", False),
                is_master=conf.get("is_master", False),
                managed_by=conf.get("managed_by"),
                env=conf.get("env", {}),
            )
        logger.info(f"Loaded {len(self.agents)} agent configs")

    def reload_config(self):
        """설정 파일 리로드"""
        self.agents.clear()
        self._load_config()

    async def start_agent(self, agent_id: str) -> dict:
        """에이전트 프로세스 시작"""
        if agent_id not in self.agents:
            return {"success": False, "error": f"Unknown agent: {agent_id}"}

        if agent_id in self.processes and self.processes[agent_id].returncode is None:
            return {"success": False, "error": f"Agent '{agent_id}' is already running"}

        config = self.agents[agent_id]
        log_file = LOG_DIR / f"{agent_id}.log"

        # 환경변수 설정
        env = os.environ.copy()
        env.update(config.env)
        env["AGENT_ID"] = agent_id
        env["COMMAND_DIR"] = str(COMMAND_DIR)
        env["RESPONSE_DIR"] = str(RESPONSE_DIR)

        try:
            log_fh = open(log_file, "a")
            process = await asyncio.create_subprocess_exec(
                config.python, config.script,
                cwd=config.working_dir,
                env=env,
                stdout=log_fh,
                stderr=asyncio.subprocess.STDOUT,
                stdin=asyncio.subprocess.PIPE,
            )
            self.processes[agent_id] = process
            self.start_times[agent_id] = datetime.now()

            # 로그 감시 태스크
            self._log_tasks[agent_id] = asyncio.create_task(
                self._watch_process(agent_id, log_fh)
            )

            logger.info(f"Started agent '{agent_id}' (PID: {process.pid})")
            return {
                "success": True,
                "agent_id": agent_id,
                "pid": process.pid,
                "message": f"Agent '{config.name}' started",
            }
        except Exception as e:
            logger.error(f"Failed to start agent '{agent_id}': {e}")
            return {"success": False, "error": str(e)}

    async def _watch_process(self, agent_id: str, log_fh):
        """프로세스 종료 감시"""
        process = self.processes[agent_id]
        await process.wait()
        log_fh.close()
        logger.info(f"Agent '{agent_id}' exited with code {process.returncode}")

    async def stop_agent(self, agent_id: str, force: bool = False) -> dict:
        """에이전트 프로세스 중지"""
        if agent_id not in self.processes:
            return {"success": False, "error": f"Agent '{agent_id}' is not running"}

        process = self.processes[agent_id]
        if process.returncode is not None:
            del self.processes[agent_id]
            return {"success": False, "error": f"Agent '{agent_id}' already stopped"}

        try:
            if force:
                process.kill()
            else:
                process.terminate()

            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

            # 로그 태스크 정리
            if agent_id in self._log_tasks:
                self._log_tasks[agent_id].cancel()
                del self._log_tasks[agent_id]

            del self.processes[agent_id]
            if agent_id in self.start_times:
                del self.start_times[agent_id]

            logger.info(f"Stopped agent '{agent_id}'")
            return {
                "success": True,
                "agent_id": agent_id,
                "message": f"Agent '{self.agents[agent_id].name}' stopped",
            }
        except Exception as e:
            logger.error(f"Failed to stop agent '{agent_id}': {e}")
            return {"success": False, "error": str(e)}

    async def restart_agent(self, agent_id: str) -> dict:
        """에이전트 재시작"""
        stop_result = await self.stop_agent(agent_id)
        if not stop_result["success"] and "not running" not in stop_result.get("error", ""):
            return stop_result

        await asyncio.sleep(1)
        return await self.start_agent(agent_id)

    def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """에이전트 상태 조회"""
        if agent_id not in self.agents:
            return None

        config = self.agents[agent_id]
        is_running = (
            agent_id in self.processes
            and self.processes[agent_id].returncode is None
        )

        status = AgentStatus(
            agent_id=agent_id,
            name=config.name,
            is_running=is_running,
            is_master=config.is_master,
        )

        if is_running:
            pid = self.processes[agent_id].pid
            status.pid = pid
            try:
                proc = psutil.Process(pid)
                status.cpu_percent = proc.cpu_percent(interval=0.1)
                status.memory_mb = round(proc.memory_info().rss / 1024 / 1024, 1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            if agent_id in self.start_times:
                status.started_at = self.start_times[agent_id].isoformat()
                status.uptime_seconds = int(
                    (datetime.now() - self.start_times[agent_id]).total_seconds()
                )

        # 최근 로그
        status.last_log_lines = self._get_recent_logs(agent_id, lines=20)
        return status

    def get_all_statuses(self) -> list[AgentStatus]:
        """모든 에이전트 상태 조회"""
        return [self.get_agent_status(aid) for aid in self.agents]

    def _get_recent_logs(self, agent_id: str, lines: int = 20) -> list[str]:
        """최근 로그 라인 읽기"""
        log_file = LOG_DIR / f"{agent_id}.log"
        if not log_file.exists():
            return []
        try:
            with open(log_file) as f:
                all_lines = f.readlines()
            return [line.rstrip() for line in all_lines[-lines:]]
        except Exception:
            return []

    def get_full_logs(self, agent_id: str, lines: int = 100) -> str:
        """전체 로그 조회"""
        return "\n".join(self._get_recent_logs(agent_id, lines))

    async def send_command(
        self, agent_id: str, command: str, timeout: float = 30
    ) -> dict:
        """에이전트에게 명령 전달 (파일 기반 통신)

        명령 파일을 COMMAND_DIR에 생성하면 에이전트가 읽어감.
        에이전트가 RESPONSE_DIR에 응답 파일을 생성하면 읽어서 반환.
        """
        if agent_id not in self.agents:
            return {"success": False, "error": f"Unknown agent: {agent_id}"}

        if agent_id not in self.processes or self.processes[agent_id].returncode is not None:
            return {"success": False, "error": f"Agent '{agent_id}' is not running"}

        # 명령 파일 생성
        timestamp = int(time.time() * 1000)
        cmd_file = COMMAND_DIR / f"{agent_id}_{timestamp}.cmd"
        resp_file = RESPONSE_DIR / f"{agent_id}_{timestamp}.resp"

        cmd_data = {
            "agent_id": agent_id,
            "command": command,
            "timestamp": timestamp,
            "response_file": str(resp_file),
        }

        with open(cmd_file, "w") as f:
            yaml.dump(cmd_data, f)

        logger.info(f"Sent command to '{agent_id}': {command[:100]}")

        # 응답 대기
        start = time.time()
        while time.time() - start < timeout:
            if resp_file.exists():
                try:
                    with open(resp_file) as f:
                        response = f.read()
                    resp_file.unlink(missing_ok=True)
                    cmd_file.unlink(missing_ok=True)
                    return {"success": True, "response": response, "agent_id": agent_id}
                except Exception as e:
                    return {"success": False, "error": f"Failed to read response: {e}"}
            await asyncio.sleep(0.5)

        cmd_file.unlink(missing_ok=True)
        return {
            "success": True,
            "response": f"Command sent (no response within {timeout}s - agent may process it asynchronously)",
            "agent_id": agent_id,
        }

    async def send_command_to_master(self, command: str, timeout: float = 30) -> dict:
        """마스터 에이전트에게 명령 전달"""
        master_id = None
        for aid, config in self.agents.items():
            if config.is_master:
                master_id = aid
                break

        if not master_id:
            return {"success": False, "error": "No master agent configured"}

        return await self.send_command(master_id, command, timeout)

    async def auto_start_agents(self):
        """auto_start=true인 에이전트 자동 시작"""
        for agent_id, config in self.agents.items():
            if config.auto_start:
                logger.info(f"Auto-starting agent: {agent_id}")
                result = await self.start_agent(agent_id)
                if not result["success"]:
                    logger.error(f"Auto-start failed for '{agent_id}': {result['error']}")

    def get_system_info(self) -> dict:
        """시스템 정보 (맥미니 상태)"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / 1024**3, 1),
                "used_gb": round(psutil.virtual_memory().used / 1024**3, 1),
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total_gb": round(psutil.disk_usage("/").total / 1024**3, 1),
                "used_gb": round(psutil.disk_usage("/").used / 1024**3, 1),
                "percent": round(psutil.disk_usage("/").percent, 1),
            },
            "uptime_hours": round(
                (time.time() - psutil.boot_time()) / 3600, 1
            ),
        }
