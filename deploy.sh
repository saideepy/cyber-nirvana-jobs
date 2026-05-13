#!/usr/bin/env bash
# Deploy to EC2 — builds frontend locally, SCPs everything, rebuilds Python image only.
set -e

KEY=$HOME/.ssh/id_ed25519
HOST=ec2-user@54.173.25.115

echo "==> Building frontend locally..."
cd frontend && npm run build && cd ..

echo "==> Uploading to EC2..."
scp -i "$KEY" -o StrictHostKeyChecking=no \
  backend/scrapers.py backend/main.py backend/database.py backend/utils.py backend/resume.py backend/requirements.txt \
  Dockerfile .dockerignore \
  "$HOST":/tmp/

ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" "rm -rf /tmp/frontend-dist && mkdir -p /tmp/frontend-dist"
tar -czf /tmp/frontend-dist.tar.gz -C frontend dist
scp -i "$KEY" -o StrictHostKeyChecking=no /tmp/frontend-dist.tar.gz "$HOST":/tmp/frontend-dist.tar.gz

echo "==> Deploying on EC2..."
ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" bash -s << 'REMOTE'
  set -e
  sudo cp /tmp/scrapers.py      /app/backend/scrapers.py
  sudo cp /tmp/main.py          /app/backend/main.py
  sudo cp /tmp/database.py      /app/backend/database.py
  sudo cp /tmp/utils.py         /app/backend/utils.py
  sudo cp /tmp/resume.py        /app/backend/resume.py
  sudo cp /tmp/requirements.txt /app/backend/requirements.txt
  sudo cp /tmp/Dockerfile       /app/Dockerfile
  sudo cp /tmp/.dockerignore    /app/.dockerignore
  sudo rm -rf /app/frontend/dist
  sudo mkdir -p /app/frontend
  cd /app/frontend && sudo tar -xzf /tmp/frontend-dist.tar.gz

  echo "Rebuilding Docker image (Python only, no Node)..."
  cd /app
  # Build only the python stage — skip node stage since dist/ is already on host
  sudo docker build -t cyber-nirvana .

  echo "Restarting container..."
  sudo docker stop cyber-nirvana 2>/dev/null || true
  sudo docker rm   cyber-nirvana 2>/dev/null || true
  sudo docker run -d --name cyber-nirvana \
    -p 127.0.0.1:8000:8000 \
    -v /data:/data \
    --env-file /data/env.conf \
    --restart unless-stopped \
    cyber-nirvana

  until curl -s http://localhost:8000/api/health | grep -q ok; do sleep 2; done
  echo "DONE — site is live."
REMOTE
