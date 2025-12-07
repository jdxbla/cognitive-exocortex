#!/bin/bash
# Cognitive Exocortex - Quick Start
# Run this on your VM to set up everything automatically

set -e

echo "🧠 Cognitive Exocortex - Quick Start"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please run as regular user (not root)"
    exit 1
fi

# Step 1: System setup
echo "Step 1/5: Installing system packages..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl wget \
    postgresql postgresql-contrib docker.io

# Step 2: Start services
echo "Step 2/5: Starting services..."
sudo systemctl start postgresql
sudo systemctl enable postgresql
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Step 3: Setup PostgreSQL
echo "Step 3/5: Setting up PostgreSQL..."
sudo -u postgres psql -c "CREATE USER exocortex WITH PASSWORD 'exocortex_secure_2025';" || true
sudo -u postgres psql -c "CREATE DATABASE cognitive_exocortex OWNER exocortex;" || true
sudo -u postgres psql -d cognitive_exocortex -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" || true

# Step 4: Start Qdrant
echo "Step 4/5: Starting Qdrant..."
sudo docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
    -v ~/qdrant_storage:/qdrant/storage \
    --restart unless-stopped \
    qdrant/qdrant || true

# Step 5: Setup project
echo "Step 5/5: Setting up project..."
mkdir -p ~/cognitive-exocortex/{server,desktop,data,logs}
cd ~/cognitive-exocortex

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install deps
pip install --upgrade pip
pip install fastapi uvicorn[standard] pydantic pydantic-settings \
    asyncpg qdrant-client sentence-transformers anthropic \
    aiofiles httpx python-dotenv

echo ""
echo "============================================"
echo "  Quick Start Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Copy server files to ~/cognitive-exocortex/server/"
echo "2. Run: cd ~/cognitive-exocortex && source venv/bin/activate"
echo "3. Run: cd server && python main.py"
echo ""
echo "Or use SCP to copy files:"
echo "  scp -r server/* ubuntu@YOUR_TAILSCALE_IP:~/cognitive-exocortex/server/"
echo ""
