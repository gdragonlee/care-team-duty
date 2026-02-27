#!/bin/bash
# CARE팀 당직 앱 NAS 배포 스크립트
# 사용법: bash deploy.sh

NAS_USER="gdragonlee"
NAS_IP="192.168.0.2"
NAS_PORT="22"
NAS_DIR="/volume1/docker/care-team-duty"

echo "=== CARE팀 당직 앱 NAS 배포 시작 ==="
echo "대상: ${NAS_USER}@${NAS_IP}:${NAS_DIR}"
echo ""

# 1. NAS에 디렉토리 생성
echo "[1/3] NAS 디렉토리 준비..."
ssh -p ${NAS_PORT} ${NAS_USER}@${NAS_IP} "mkdir -p ${NAS_DIR}/data"

# 2. 파일 전송 (node_modules, .next, data 제외)
echo "[2/3] 파일 전송 중..."
rsync -avz --progress \
  --exclude='node_modules/' \
  --exclude='.next/' \
  --exclude='data/' \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='venv/' \
  --exclude='.env' \
  --exclude='.env.local' \
  -e "ssh -p ${NAS_PORT}" \
  /Users/gdragonlee/care-team-duty/ \
  ${NAS_USER}@${NAS_IP}:${NAS_DIR}/

# 3. NAS에서 Docker 빌드 & 실행
echo "[3/3] Docker 빌드 & 실행..."
ssh -p ${NAS_PORT} ${NAS_USER}@${NAS_IP} "
  cd ${NAS_DIR} && \
  docker compose down 2>/dev/null || true && \
  docker compose up --build -d && \
  echo '=== 배포 완료 ===' && \
  docker ps | grep care-team-duty
"

echo ""
echo "완료! 브라우저에서 http://${NAS_IP}:3000 으로 접속하세요."
