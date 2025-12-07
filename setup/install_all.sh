#!/bin/bash
# Cognitive Exocortex - Full Infrastructure Setup
# Run this on your Ubuntu VM to install everything

set -e

echo "============================================"
echo "  Cognitive Exocortex Infrastructure Setup"
echo "============================================"

# Update system
echo "[1/7] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "[2/7] Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Install PostgreSQL
echo "[3/7] Installing PostgreSQL..."
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Install TimescaleDB
echo "[4/7] Installing TimescaleDB extension..."
sudo apt install -y gnupg postgresql-common apt-transport-https lsb-release
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install -y timescaledb-2-postgresql-16 || sudo apt install -y timescaledb-2-postgresql-14

# Configure TimescaleDB
sudo timescaledb-tune --quiet --yes || true
sudo systemctl restart postgresql

# Install Docker for Qdrant
echo "[5/7] Installing Docker for Qdrant..."
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Qdrant (vector database)
echo "[6/7] Starting Qdrant container..."
sudo docker pull qdrant/qdrant
sudo docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
    -v ~/qdrant_storage:/qdrant/storage \
    --restart unless-stopped \
    qdrant/qdrant

# Create project directories
echo "[7/7] Setting up project structure..."
mkdir -p ~/cognitive-exocortex/{desktop,server,lambda,ios,data,logs,config}

echo ""
echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""
echo "Services running:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Qdrant:     localhost:6333 (HTTP), localhost:6334 (gRPC)"
echo ""
echo "Next: Run ./setup_databases.sh to create schemas"
echo ""
