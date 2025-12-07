# Cognitive Exocortex

> An AI-powered cognitive enhancement system that extends your mind across devices

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)]()

**Cognitive Exocortex** is an open-source platform that learns your patterns, predicts your needs, and acts as an extension of your own cognitive function. It's the angel and devil on your shoulders - always there, always learning, always helping.

---

## 🧠 Vision

Build a cognitive enhancement system that:
- **Extends your mind** across desktop, server, and mobile
- **Learns your patterns** and predicts what you need before you ask
- **Always available** via iPhone app, desktop, and web
- **Open source and free** for everyone (MIT License)
- **Privacy-first** - your data stays yours

---

## ✨ Features

### **Tier 1: Core Intelligence** (In Development)

#### 1. **Predictive File Intelligence**
Learns your file access patterns and predicts what you'll need next
- Tracks every file operation (when, what, why)
- ML model predicts next 5 files you'll need
- Shows predictions with confidence scores
- Gets smarter over time

#### 2. **Semantic Search**
Understands meaning, not just keywords
- Natural language queries: "find documents about project planning from last month"
- Vector embeddings for deep understanding
- Search across code, docs, images
- Lightning-fast results

#### 3. **Infinite Undo**
Undo anything, anytime - full version control for your entire file system
- Every file operation creates a version
- Time-travel: "show me this folder from 3 days ago"
- Compressed storage (efficient)
- Query interface for exploring history

#### 4. **Natural Language Everything**
Control the entire system with plain English
- "Delete all PDFs over 10MB modified before January"
- "Organize screenshots by date"
- "Show me files I worked on during the Tesla project"
- Safety confirmations for destructive operations

### **Tier 2: Advanced Intelligence** (Planned)

5. **Focus Mode / Cognitive Load Manager** - Reduces mental overhead
6. **Knowledge Graph File System** - Files as nodes in a knowledge graph
7. **Temporal File Analysis** - Time-travel through your file system
8. **Crisis Prevention System** - Protects you from yourself

### **Tier 3: Experimental** (Future)

9. **Ambient Intelligence** - Silent AI always learning
10. **Parallel Universe File Management** - Experiment without consequences
11. **Hyperdimensional Search** - Multi-dimensional fuzzy search
12. **Memory Palace File System** - Spatial memory visualization
13. **Quantum File Operations** - Impossibly fast operations
14. **Biometric Integration** - Responds to your physical/mental state
15. **Subconscious File Sync** - Knows what you need before you do

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Desktop App (Python)                │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐      │
│  │ Predictive │ │  Semantic  │ │  Infinite  │      │
│  │Intelligence│ │   Search   │ │    Undo    │      │
│  └────────────┘ └────────────┘ └────────────┘      │
└─────────────────────────────────────────────────────┘
                         ↕ API
┌─────────────────────────────────────────────────────┐
│              Server Backend (FastAPI)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │PostgreSQL│ │  Qdrant  │ │SeaweedFS │           │
│  │TimescaleDB│ │ (Vector) │ │ Iceberg │           │
│  └──────────┘ └──────────┘ └──────────┘           │
└─────────────────────────────────────────────────────┘
                         ↕
┌─────────────────────────────────────────────────────┐
│              AWS Lambda GPU (Serverless)             │
│        ML Inference • Embeddings • Predictions       │
└─────────────────────────────────────────────────────┘
                         ↕
┌─────────────────────────────────────────────────────┐
│                iOS App (SwiftUI)                     │
│     File Browser • Predictions • Quick Actions       │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.8+
- Linux VM (Ubuntu 22.04 recommended)
- PostgreSQL, Qdrant, TimescaleDB, SeaweedFS
- AWS account (free tier)

### **Installation**

```bash
# Clone repository
git clone https://github.com/yourusername/cognitive-exocortex.git
cd cognitive-exocortex

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your VM IP, database credentials, AWS keys

# Run desktop app
python desktop/main.py
```

### **Server Setup (Linux VM)**

```bash
# SSH into your VM
ssh user@your-vm-ip

# Install server dependencies
cd cognitive-exocortex/server
pip install -r requirements.txt

# Run FastAPI server
uvicorn server:app --host 0.0.0.0 --port 8000
```

### **AWS Lambda Setup**

```bash
# Install AWS CLI
pip install awscli

# Configure AWS
aws configure

# Deploy Lambda functions
cd lambda
./deploy.sh
```

---

## 💻 Tech Stack

### **Desktop App**
- Python 3.8+
- scikit-learn (ML)
- sentence-transformers (embeddings)
- networkx (graphs)
- psycopg2 (PostgreSQL)
- qdrant-client (vector DB)

### **Server Backend**
- FastAPI (Python)
- PostgreSQL (patterns, metadata)
- TimescaleDB (time-series)
- Qdrant (vector embeddings)
- DuckDB (analytics)
- Apache Iceberg (data lakehouse)
- SeaweedFS (file storage)
- Apache Airflow (orchestration)

### **Cloud**
- AWS Lambda (GPU for ML)
- AWS S3 (backups)

### **iOS App**
- Swift 5.9+
- SwiftUI
- HealthKit (biometrics)
- CoreLocation (context)

---

## 📊 Infrastructure Mapping

| Feature | Infrastructure |
|---------|---------------|
| Predictive Intelligence | PostgreSQL + AWS Lambda |
| Semantic Search | Qdrant + AWS Lambda |
| Infinite Undo | SeaweedFS + Iceberg |
| Natural Language | Claude API |
| Focus Mode | PostgreSQL |
| Knowledge Graph | PostgreSQL |
| Temporal Analysis | TimescaleDB |
| Crisis Prevention | PostgreSQL |
| Ambient Intelligence | Airflow |
| Subconscious Sync | SeaweedFS + Airflow |

---

## 💰 Cost

**Self-Hosted (Free Tier):**
- Oracle Cloud VM: $0 (24GB RAM, 4 vCPU, 200GB storage)
- AWS Lambda GPU: $0-5/month (1M requests free)
- **Total: $0-5/month**

**Paid Hosting:**
- Hetzner CPX31: €15.30/month (8GB RAM, 4 vCPU)
- AWS Lambda GPU: $0-5/month
- **Total: ~$20/month**

---

## 🗺️ Roadmap

### **Week 1-2: Tier 1 Features**
- [x] Project setup
- [ ] Predictive Intelligence
- [ ] Semantic Search
- [ ] Infinite Undo
- [ ] Natural Language

### **Week 3-4: Tier 2 Features**
- [ ] Focus Mode
- [ ] Knowledge Graph
- [ ] Temporal Analysis
- [ ] Crisis Prevention

### **Week 5-6: Server Backend**
- [ ] FastAPI server
- [ ] Database integrations
- [ ] AWS Lambda deployment

### **Week 7-8: iOS App**
- [ ] SwiftUI app
- [ ] Server integration
- [ ] Biometric features

### **Week 9-10: Integration & Launch**
- [ ] Cross-device sync
- [ ] Beta testing
- [ ] Documentation
- [ ] Public release

---

## 🤝 Contributing

We welcome contributions! This project is open source and free forever.

### **How to Contribute**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### **Development Setup**
```bash
# Clone your fork
git clone https://github.com/yourusername/cognitive-exocortex.git

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linter
black . && flake8
```

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**What this means:**
- ✅ Free to use, modify, distribute
- ✅ Commercial use allowed
- ✅ Private use allowed
- ✅ No warranty provided
- ⚠️ Must include copyright notice

---

## 🙏 Acknowledgments

- **File Commander** - Original CLI file manager that inspired this project
- **Anthropic Claude** - AI assistance for natural language features
- **Open Source Community** - For the amazing tools that made this possible

---

## 📬 Contact

- **GitHub Issues:** [Report bugs or request features](https://github.com/yourusername/cognitive-exocortex/issues)
- **Discussions:** [Join the conversation](https://github.com/yourusername/cognitive-exocortex/discussions)
- **Discord:** [Community server](https://discord.gg/your-invite-link)

---

## 🌟 Star History

If this project helps you, please consider giving it a star ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/cognitive-exocortex&type=Date)](https://star-history.com/#yourusername/cognitive-exocortex&Date)

---

## 🎯 Project Goals

### **3 Months**
- 100 GitHub stars
- 10 contributors
- Tier 1 & 2 features complete

### **6 Months**
- 1,000 users
- iOS App Store launch
- Server infrastructure stable

### **1 Year**
- 10,000 users
- "Cognitive exocortex" becomes a movement
- Full feature set complete

---

**Built with 🧠 by the Cognitive Exocortex Team**

*"Extending human cognition, one file at a time."*
