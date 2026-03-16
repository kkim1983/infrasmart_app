#!/bin/bash
# ===================================================
# InfraSmart - AWS EC2 최초 서버 세팅 스크립트
# Ubuntu 22.04 LTS 기준
# 사용법: chmod +x setup-ec2.sh && ./setup-ec2.sh
# ===================================================

set -e  # 에러 발생 시 중단

echo "🚀 InfraSmart 서버 세팅 시작..."

# ── 1. 시스템 업데이트 ────────────────────────────
echo "📦 시스템 업데이트..."
sudo apt-get update && sudo apt-get upgrade -y

# ── 2. Docker 설치 ────────────────────────────────
echo "🐳 Docker 설치..."
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Docker를 sudo 없이 사용 (재로그인 필요)
sudo usermod -aG docker $USER
echo "✅ Docker 설치 완료"

# ── 3. 프로젝트 클론 ──────────────────────────────
echo "📂 프로젝트 클론..."
# GitHub에 올린 경우:
# git clone https://github.com/YOUR_USERNAME/infrasmart.git /opt/infrasmart
#
# 현재는 수동으로 파일 복사 필요:
echo "⚠️  GitHub에 코드를 올린 후 아래 명령으로 클론하세요:"
echo "    git clone https://github.com/YOUR_USERNAME/infrasmart.git /opt/infrasmart"
echo "    cd /opt/infrasmart"

# ── 4. 환경변수 설정 가이드 ───────────────────────
echo ""
echo "📝 환경변수 설정:"
echo "    cp .env.prod.example .env.prod"
echo "    nano .env.prod  # 실제 값으로 수정"
echo ""
echo "🔑 JWT Secret Key 생성:"
echo "    openssl rand -hex 32"
echo ""

# ── 5. 방화벽 설정 ────────────────────────────────
echo "🔒 방화벽 설정..."
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw --force enable
echo "✅ 방화벽 설정 완료 (22, 80, 443)"

echo ""
echo "✅ 기본 세팅 완료!"
echo ""
echo "📋 다음 단계:"
echo "  1. newgrp docker  (또는 재로그인으로 Docker 그룹 적용)"
echo "  2. 코드 클론 및 .env.prod 설정"
echo "  3. docker compose -f docker-compose.prod.yml up -d"
echo "  4. docker compose -f docker-compose.prod.yml exec api alembic upgrade head"
echo "  5. SSL 인증서 발급 (setup-ssl.sh 실행)"
