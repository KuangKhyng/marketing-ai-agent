# ✦ Công chúa Trang — Marketing Campaign Engine

Multi-brand marketing operating system, powered by LangGraph + Anthropic Claude API.

> Tự động tạo social media campaigns cho nhiều brands, với knowledge base quản lý riêng cho từng thương hiệu.

## ✨ Features

### Campaign Pipeline
- **Workflow-first**: Deterministic pipeline with LLM nodes only where needed
- **Schema-first**: Pydantic typed contracts between all nodes
- **Multi-platform**: Facebook, Instagram, TikTok native content
- **Human-in-the-loop**: Strategy approval + content review gates
- **4-dimension review**: Brand fit, factuality, channel fit, business fit scoring
- **Full trace**: Every run tracked with token usage and cost estimates

### Multi-Brand Knowledge System
- **Brand Management**: CRUD brands with completeness scoring
- **Knowledge Base UI**: Markdown editor with live preview
- **Brand-aware Pipeline**: Context automatically loaded based on selected brand
- **Voice Profiles**: Tone, vocabulary, anti-AI rules per brand
- **Document Templates**: Identity, products, audience, policies

### Content Tools
- **Quick Regenerate**: Viết lại / Đổi hook / Ngắn hơn / Đổi tone (Haiku ~3s)
- **Smart Copy**: One-click copy per platform, formatted for FB/IG/TikTok
- **Parallel Rendering**: All channel content rendered concurrently

## 🛠 Tech Stack

| Layer | Tech |
|-------|------|
| **Backend** | Python 3.11, FastAPI, LangGraph, LangChain |
| **LLM** | Anthropic Claude (Sonnet for generation, Haiku for parsing/rendering) |
| **Frontend** | React 18, Vite, Tailwind CSS v4, Framer Motion |
| **Data** | File-based knowledge base (Markdown + JSON) |
| **Deploy** | Railway (with persistent volumes) |

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/KuangKhyng/marketing-ai-agent.git
cd marketing-ai-agent

# Backend
pip install -r requirements.txt
cp .env.example .env  # Add ANTHROPIC_API_KEY

# Frontend
cd web && npm install && npm run build && cd ..

# Run
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` to access the web UI.

## 📊 Pipeline Flow

```
Input → brief_parser → context_builder → strategist → [HUMAN APPROVE]
                                                            │
                                                       (approved?)
                                                       /         \
                                                     Yes          No → END
                                                      │
                                              message_architect
                                                      │
                                          channel_renderer (parallel)
                                                      │
                                                 reviewer
                                                      │
                                                (passed?)
                                               /         \
                                             Yes          No → retry
                                              │
                                         formatter → Export
```

## 📁 Project Structure

```
├── api/                    # FastAPI backend
│   ├── main.py             # App entry + static serving
│   ├── routes/
│   │   ├── campaign.py     # Campaign pipeline endpoints
│   │   └── brands.py       # Brand CRUD + docs + voice
│   ├── pipeline_runner.py  # Pipeline orchestration
│   └── schemas.py          # API request/response models
├── src/
│   ├── models/             # Pydantic schemas (brief, content, review)
│   ├── graph/              # LangGraph workflow + edges
│   ├── nodes/              # Pipeline nodes (6 nodes)
│   ├── knowledge/          # BrandManager + retriever
│   ├── prompts/v1/         # Prompt templates per node
│   └── config/             # Settings, model configs, platforms
├── knowledge_base/
│   ├── _global/            # Shared platform rules + policies
│   └── brands/             # Per-brand knowledge
│       └── {brand_id}/
│           ├── brand.json
│           ├── identity.md
│           ├── tone_of_voice.md
│           ├── products/
│           ├── audience/
│           └── voice_profile.json
├── web/                    # React frontend (Vite)
│   └── src/
│       ├── pages/          # InputPage, BrandsPage, etc.
│       ├── components/     # Layout, Sidebar
│       └── api/            # Axios client
├── railway.toml            # Railway deploy config + volumes
└── requirements.txt
```

## 🌐 Deploy (Railway)

1. Push to GitHub
2. Connect repo in Railway Dashboard
3. Add env var: `ANTHROPIC_API_KEY`
4. Add volumes:
   - `/app/knowledge_base` → `knowledge-data`
   - `/app/outputs` → `campaign-outputs`
5. Deploy!

## 📝 License

MIT
