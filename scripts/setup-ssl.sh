#!/bin/bash
# ===================================================
# InfraSmart - Let's Encrypt SSL 인증서 발급 스크립트
# 사전 조건:
#   - 도메인의 A 레코드가 이 서버 IP를 가리켜야 함
#   - 80 포트가 열려 있어야 함
#   - docker compose prod가 실행 중이어야 함
# ===================================================

set -e

# ── 설정값 입력 ───────────────────────────────────
read -p "도메인 입력 (예: api.yourdomain.com): " DOMAIN
read -p "이메일 입력 (인증서 만료 알림용): " EMAIL

echo "🔐 Let's Encrypt SSL 인증서 발급 중..."
echo "도메인: $DOMAIN"
echo "이메일: $EMAIL"

# certbot으로 인증서 발급 (webroot 방식)
docker compose -f docker-compose.prod.yml run --rm certbot \
  certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

echo "✅ SSL 인증서 발급 완료!"
echo ""
echo "📝 다음 단계: nginx/conf.d/default.conf 수정"
echo "  1. server_name을 $DOMAIN 으로 변경"
echo "  2. HTTP → HTTPS 리다이렉트 블록 활성화"
echo "  3. HTTPS 서버 블록 주석 해제"
echo "  4. 도메인 이름 $DOMAIN 으로 변경"
echo ""
echo "  수정 후 nginx 재로드:"
echo "  docker compose -f docker-compose.prod.yml exec nginx nginx -s reload"
