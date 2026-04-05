"""
외부 접속 터널 설정 스크립트

맥미니의 웹 대시보드를 외부(아이폰 등)에서 접속할 수 있게 해줍니다.

사용법:
    # ngrok 방식 (가장 간단)
    python tunnel.py ngrok

    # Cloudflare Tunnel 방식
    python tunnel.py cloudflare

    # Tailscale 방식 (이미 설치되어 있다면)
    python tunnel.py tailscale
"""

import os
import subprocess
import sys

PORT = int(os.getenv("API_PORT", "8080"))


def setup_ngrok():
    """ngrok으로 외부 URL 생성"""
    print("🔗 ngrok 터널 시작 중...")
    print(f"   로컬 포트: {PORT}")
    print()

    # ngrok 설치 확인
    result = subprocess.run(["which", "ngrok"], capture_output=True)
    if result.returncode != 0:
        print("ngrok이 설치되어 있지 않습니다.")
        print()
        print("설치 방법 (macOS):")
        print("  brew install ngrok")
        print()
        print("또는 https://ngrok.com/download 에서 다운로드")
        print()
        print("설치 후 인증:")
        print("  ngrok config add-authtoken <your-token>")
        return

    print("ngrok 시작...")
    print("Ctrl+C로 종료")
    print()
    os.execvp("ngrok", ["ngrok", "http", str(PORT)])


def setup_cloudflare():
    """Cloudflare Tunnel로 외부 접속"""
    print("🔗 Cloudflare Tunnel 시작 중...")

    result = subprocess.run(["which", "cloudflared"], capture_output=True)
    if result.returncode != 0:
        print("cloudflared가 설치되어 있지 않습니다.")
        print()
        print("설치 방법 (macOS):")
        print("  brew install cloudflared")
        return

    print(f"포트 {PORT}에 대한 임시 터널 생성...")
    print("Ctrl+C로 종료")
    print()
    os.execvp(
        "cloudflared",
        ["cloudflared", "tunnel", "--url", f"http://localhost:{PORT}"],
    )


def show_tailscale():
    """Tailscale 접속 정보 표시"""
    print("🔗 Tailscale 접속 정보")
    print()

    result = subprocess.run(["which", "tailscale"], capture_output=True)
    if result.returncode != 0:
        print("Tailscale이 설치되어 있지 않습니다.")
        print()
        print("설치: https://tailscale.com/download/mac")
        print()
        print("설치 후:")
        print("1. 맥미니에서 Tailscale 로그인")
        print("2. 아이폰에서도 Tailscale 앱 설치 후 같은 계정 로그인")
        print(f"3. 아이폰 Safari에서 http://<맥미니-tailscale-ip>:{PORT}")
        return

    result = subprocess.run(
        ["tailscale", "ip", "-4"], capture_output=True, text=True
    )
    if result.returncode == 0:
        ip = result.stdout.strip()
        print(f"맥미니 Tailscale IP: {ip}")
        print()
        print(f"아이폰에서 접속:")
        print(f"  대시보드: http://{ip}:{PORT}")
        print(f"  API:      http://{ip}:{PORT}/api/agents")
    else:
        print("Tailscale이 연결되어 있지 않습니다.")
        print("  tailscale up 으로 연결하세요.")


def main():
    if len(sys.argv) < 2:
        print("사용법: python tunnel.py [ngrok|cloudflare|tailscale]")
        print()
        print("  ngrok       - 가장 간단. 즉시 외부 URL 생성")
        print("  cloudflare  - 안정적. 무료 임시 터널")
        print("  tailscale   - 가장 안전. VPN 기반")
        return

    method = sys.argv[1].lower()
    if method == "ngrok":
        setup_ngrok()
    elif method == "cloudflare":
        setup_cloudflare()
    elif method == "tailscale":
        show_tailscale()
    else:
        print(f"알 수 없는 방법: {method}")
        print("ngrok, cloudflare, tailscale 중 선택하세요.")


if __name__ == "__main__":
    main()
