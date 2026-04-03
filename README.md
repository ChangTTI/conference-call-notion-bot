# Agent Controller

맥미니에서 구동되는 에이전트들을 외부에서 원격 제어하는 시스템.

## 기능

- **Telegram 봇**: 외부에서 메시지로 에이전트 제어
- **웹 대시보드**: 브라우저에서 상태 확인 및 제어
- **REST API**: 프로그래밍 방식 제어
- **프로세스 관리**: 에이전트 시작/중지/재시작
- **상태 모니터링**: CPU, 메모리, 업타임, 로그
- **명령 전달**: 마스터/개별 에이전트에 명령 전달

## 아키텍처

```
외부 (폰/노트북)
    │
    ├── Telegram Bot ──┐
    │                  │
    └── Web Dashboard ─┼── Agent Controller (맥미니)
                       │        │
                       │   ┌────┴────┐
                       │   │ Master  │──── Sub Agent 1
                       │   │ Agent   │──── Sub Agent 2
                       │   └─────────┘──── Sub Agent N
```

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env
# .env 파일을 수정하여 TELEGRAM_BOT_TOKEN 등 설정
```

## 설정

### 1. Telegram 봇 생성
1. Telegram에서 @BotFather에게 `/newbot` 명령
2. 봇 토큰을 `.env`의 `TELEGRAM_BOT_TOKEN`에 입력
3. @userinfobot에게 메시지를 보내 본인 user ID 확인
4. `.env`의 `TELEGRAM_USER_IDS`에 입력

### 2. 에이전트 등록
`config/agents.yaml`에 관리할 에이전트를 등록:

```yaml
master:
  name: "Master Agent"
  script: "~/agents/master_agent.py"
  working_dir: "~/agents"
  auto_start: true
  is_master: true

sub_agent_1:
  name: "Data Collector"
  script: "~/agents/data_collector.py"
  working_dir: "~/agents"
  managed_by: "master"
```

## 실행

```bash
python run.py
```

- 웹 대시보드: `http://맥미니IP:8080`
- API: `http://맥미니IP:8080/api/agents`

## Telegram 명령어

| 명령 | 설명 |
|------|------|
| `/status` | 전체 에이전트 상태 |
| `/status <id>` | 특정 에이전트 상태 |
| `/start <id>` | 에이전트 시작 |
| `/stop <id>` | 에이전트 중지 |
| `/restart <id>` | 에이전트 재시작 |
| `/logs <id>` | 로그 조회 |
| `/cmd <명령>` | 마스터에게 명령 |
| `/cmdto <id> <명령>` | 특정 에이전트에 명령 |
| `/system` | 맥미니 시스템 정보 |
| 일반 텍스트 | 마스터에게 바로 전달 |

## 외부 접속 (포트포워딩 없이)

맥미니에 외부에서 접속하려면:
- **Tailscale** (권장): VPN 설치 후 Tailscale IP로 접속
- **Cloudflare Tunnel**: `cloudflared tunnel` 설정
- **ngrok**: `ngrok http 8080`
