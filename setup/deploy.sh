#!/bin/bash
# Cognitive Exocortex - Deployment Script
# Deploys the server to the VM

set -e

echo "============================================"
echo "  Deploying Cognitive Exocortex Server"
echo "============================================"

# Configuration
PROJECT_DIR=~/cognitive-exocortex

# Create directories
mkdir -p $PROJECT_DIR/{server,desktop,data,logs,config}

# Create Python virtual environment
echo "[1/4] Setting up Python environment..."
cd $PROJECT_DIR
python3 -m venv venv
source venv/bin/activate

# Install server dependencies
echo "[2/4] Installing dependencies..."
pip install --upgrade pip
pip install \
    fastapi \
    uvicorn[standard] \
    pydantic \
    pydantic-settings \
    asyncpg \
    qdrant-client \
    sentence-transformers \
    anthropic \
    aiofiles \
    httpx \
    python-dotenv

# Create .env file
echo "[3/4] Creating configuration..."
cat > $PROJECT_DIR/server/.env << 'EOF'
# Cognitive Exocortex Configuration
DEBUG=false

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=cognitive_exocortex
POSTGRES_USER=exocortex
POSTGRES_PASSWORD=exocortex_secure_2025

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# API
API_HOST=0.0.0.0
API_PORT=8000
EOF

# Create systemd service
echo "[4/4] Creating systemd service..."
sudo tee /etc/systemd/system/exocortex.service << EOF
[Unit]
Description=Cognitive Exocortex Server
After=network.target postgresql.service docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR/server
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable exocortex

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
echo ""
echo "To start the server:"
echo "  sudo systemctl start exocortex"
echo ""
echo "To check status:"
echo "  sudo systemctl status exocortex"
echo ""
echo "To view logs:"
echo "  journalctl -u exocortex -f"
echo ""
echo "API available at: http://YOUR_TAILSCALE_IP:8000"
echo "API docs at: http://YOUR_TAILSCALE_IP:8000/docs"
echo ""
