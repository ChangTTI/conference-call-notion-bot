"""
Telegram Bot - 외부에서 에이전트 제어

명령어:
/status           - 모든 에이전트 상태 조회
/status <id>      - 특정 에이전트 상태 조회
/start <id>       - 에이전트 시작
/stop <id>        - 에이전트 중지
/restart <id>     - 에이전트 재시작
/logs <id>        - 에이전트 로그 조회
/cmd <command>    - 마스터 에이전트에 명령 전달
/cmdto <id> <cmd> - 특정 에이전트에 명령 전달
/system           - 맥미니 시스템 정보
/agents           - 등록된 에이전트 목록
/help             - 도움말
"""

import logging
from dataclasses import asdict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, agent_manager, allowed_user_ids: list[int] = None):
        self.token = token
        self.manager = agent_manager
        self.allowed_user_ids = allowed_user_ids or []
        self.app: Application = None

    def _is_authorized(self, user_id: int) -> bool:
        if not self.allowed_user_ids:
            return True  # 제한 없음
        return user_id in self.allowed_user_ids

    async def _check_auth(self, update: Update) -> bool:
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ 권한이 없습니다.")
            logger.warning(f"Unauthorized access attempt: {update.effective_user.id}")
            return False
        return True

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update):
            return

        text = (
            "🤖 *Agent Controller*\n\n"
            "📋 *상태 조회*\n"
            "/status - 전체 에이전트 상태\n"
            "/status `<id>` - 특정 에이전트 상태\n"
            "/agents - 등록된 에이전트 목록\n"
            "/system - 맥미니 시스템 정보\n\n"
            "🎮 *제어*\n"
            "/start `<id>` - 에이전트 시작\n"
            "/stop `<id>` - 에이전트 중지\n"
            "/restart `<id>` - 에이전트 재시작\n\n"
            "💬 *명령 전달*\n"
            "/cmd `<명령>` - 마스터에게 명령\n"
            "/cmdto `<id>` `<명령>` - 특정 에이전트에 명령\n\n"
            "📜 *로그*\n"
            "/logs `<id>` - 최근 로그 조회\n"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update):
            return

        args = context.args
        if args:
            # 특정 에이전트 상태
            agent_id = args[0]
            status = self.manager.get_agent_status(agent_id)
            if not status:
                await update.message.reply_text(f"❌ 에이전트 '{agent_id}'를 찾을 수 없습니다.")
                return

            icon = "🟢" if status.is_running else "🔴"
            master_tag = " 👑" if status.is_master else ""
            text = (
                f"{icon} *{status.name}*{master_tag}\n"
                f"ID: `{status.agent_id}`\n"
                f"상태: {'실행 중' if status.is_running else '중지됨'}\n"
            )
            if status.is_running:
                text += (
                    f"PID: {status.pid}\n"
                    f"CPU: {status.cpu_percent}%\n"
                    f"메모리: {status.memory_mb} MB\n"
                    f"업타임: {_format_uptime(status.uptime_seconds)}\n"
                )
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            # 전체 에이전트 상태
            statuses = self.manager.get_all_statuses()
            if not statuses:
                await update.message.reply_text("등록된 에이전트가 없습니다.")
                return

            lines = ["📊 *에이전트 상태*\n"]
            for s in statuses:
                icon = "🟢" if s.is_running else "🔴"
                master_tag = " 👑" if s.is_master else ""
                uptime = _format_uptime(s.uptime_seconds) if s.is_running else "-"
                lines.append(
                    f"{icon} *{s.name}*{master_tag}\n"
                    f"   ID: `{s.agent_id}` | "
                    f"{'PID ' + str(s.pid) if s.is_running else '중지'} | "
                    f"업타임: {uptime}"
                )

            await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")

    async def cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update):
            return

        if not self.manager.agents:
            await update.message.reply_text("등록된 에이전트가 없습니다.")
            return

        lines = ["📋 *등록된 에이전트*\n"]
        for aid, config in self.manager.agents.items():
            master_tag = " 👑" if config.is_master else ""
            lines.append(
                f"• `{aid}`{master_tag} - {config.name}\n"
                f"  {config.description}\n"
                f"  스크립트: `{config.script}`"
            )
        await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update):
            return

        if not context.args:
            await update.message.reply_text("사용법: /start <agent_id>")
            return

        agent_id = context.args[0]
        await update.message.reply_text(f"⏳ '{agent_id}' 시작 중...")
        result = await self.manager.start_agent(agent_id)

        if result["success"]:
            await update.message.reply_text(
                f"✅ {result['message']} (PID: {result['pid']})"
            )
        else:
            await update.message.reply_text(f"❌ 실패: {result['error']}")

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update):
            return

        if not context.args:
            await update.message.reply_text("사용법: /stop <agent_id>")
            return

        agent_id = context.args[0]
        await update.message.reply_text(f"⏳ '{agent_id}' 중지 중...")
        result = await self.manager.stop_agent(agent_id)

        if result["success"]:
            await update.message.reply_text(f"✅ {result['message']}")
        else:
            await update.message.reply_text(f"❌ 실패: {result['error']}")

    async def cmd_restart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update):
            return

        if not context.args:
            await update.message.reply_text("사용법: /restart <agent_id>")
            return

        agent_id = context.args[0]
        await update.message.reply_text(f"⏳ '{agent_id}' 재시작 중...")
        result = await self.manager.restart_agent(agent_id)

        if result["success"]:
            await update.message.reply_text(f"✅ {result['message']}")
        else:
            await update.message.reply_text(f"❌ 실패: {result['error']}")

    async def cmd_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update):
            return

        if not context.args:
            await update.message.reply_text("사용법: /logs <agent_id>")
            return

        agent_id = context.args[0]
        logs = self.manager.get_full_logs(agent_id, lines=30)

        if not logs:
            await update.message.reply_text(f"📜 '{agent_id}' 로그가 없습니다.")
            return

        # 텔레그램 메시지 길이 제한 (4096자)
        if len(logs) > 3900:
            logs = "...\n" + logs[-3900:]

        await update.message.reply_text(
            f"📜 *{agent_id} 로그*\n```\n{logs}\n```",
            parse_mode="Markdown",
        )

    async def cmd_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """마스터 에이전트에게 명령 전달"""
        if not await self._check_auth(update):
            return

        if not context.args:
            await update.message.reply_text("사용법: /cmd <명령>")
            return

        command = " ".join(context.args)
        await update.message.reply_text(f"⏳ 마스터에게 명령 전달 중...\n`{command}`", parse_mode="Markdown")
        result = await self.manager.send_command_to_master(command)

        if result["success"]:
            response = result.get("response", "응답 없음")
            if len(response) > 3900:
                response = response[:3900] + "..."
            await update.message.reply_text(f"✅ 응답:\n```\n{response}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ 실패: {result['error']}")

    async def cmd_command_to(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """특정 에이전트에게 명령 전달"""
        if not await self._check_auth(update):
            return

        if len(context.args) < 2:
            await update.message.reply_text("사용법: /cmdto <agent_id> <명령>")
            return

        agent_id = context.args[0]
        command = " ".join(context.args[1:])
        await update.message.reply_text(
            f"⏳ '{agent_id}'에게 명령 전달 중...\n`{command}`", parse_mode="Markdown"
        )
        result = await self.manager.send_command(agent_id, command)

        if result["success"]:
            response = result.get("response", "응답 없음")
            if len(response) > 3900:
                response = response[:3900] + "..."
            await update.message.reply_text(f"✅ 응답:\n```\n{response}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ 실패: {result['error']}")

    async def cmd_system(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self._check_auth(update):
            return

        info = self.manager.get_system_info()
        text = (
            "🖥 *맥미니 시스템 정보*\n\n"
            f"CPU: {info['cpu_percent']}%\n"
            f"메모리: {info['memory']['used_gb']}/{info['memory']['total_gb']} GB "
            f"({info['memory']['percent']}%)\n"
            f"디스크: {info['disk']['used_gb']}/{info['disk']['total_gb']} GB "
            f"({info['disk']['percent']}%)\n"
            f"가동시간: {info['uptime_hours']}시간"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_unknown_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """일반 텍스트를 마스터 에이전트에게 전달"""
        if not await self._check_auth(update):
            return

        command = update.message.text
        await update.message.reply_text(f"⏳ 마스터에게 전달 중...", parse_mode="Markdown")
        result = await self.manager.send_command_to_master(command)

        if result["success"]:
            response = result.get("response", "응답 없음")
            if len(response) > 3900:
                response = response[:3900] + "..."
            await update.message.reply_text(f"💬 {response}")
        else:
            await update.message.reply_text(f"❌ {result['error']}")

    def build_app(self) -> Application:
        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("stop", self.cmd_stop))
        self.app.add_handler(CommandHandler("restart", self.cmd_restart))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("agents", self.cmd_agents))
        self.app.add_handler(CommandHandler("logs", self.cmd_logs))
        self.app.add_handler(CommandHandler("cmd", self.cmd_command))
        self.app.add_handler(CommandHandler("cmdto", self.cmd_command_to))
        self.app.add_handler(CommandHandler("system", self.cmd_system))
        # 일반 텍스트 → 마스터 에이전트에 전달
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.cmd_unknown_text)
        )

        return self.app


def _format_uptime(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}초"
    if seconds < 3600:
        return f"{seconds // 60}분"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours < 24:
        return f"{hours}시간 {minutes}분"
    days = hours // 24
    hours = hours % 24
    return f"{days}일 {hours}시간"
