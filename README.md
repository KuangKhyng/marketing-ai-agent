# ✦ Marketing Campaign Engine

Multi-brand marketing operating system chạy trên Anthropic Claude API.

> Tự động tạo social media campaigns cho nhiều brands, với knowledge base quản lý riêng cho từng thương hiệu.

Hai entrypoint: web app (FastAPI + React) và CLI. Cùng một chuỗi node, hai cách
điều phối — xem [Pipeline Flow](#-pipeline-flow). LangGraph chỉ nằm ở nhánh CLI.

## ✨ Features

### Campaign Pipeline
- **Workflow-first**: Deterministic pipeline with LLM nodes only where needed
- **Schema-first**: Pydantic typed contracts between all nodes
- **Multi-platform**: Facebook, Instagram, TikTok native content
- **Human-in-the-loop**: 4 cửa duyệt — brief, chiến lược, nội dung, và chấm
  chất lượng cuối. Mỗi cửa đều sửa được rồi chạy lại bước đó.
- **5-dimension review**: Brand fit, factuality, channel fit, business fit,
  content depth. Vi phạm quy tắc cứng (word limit, mandatory term, forbidden
  claim) làm chiều tương ứng trượt bất kể điểm LLM.
- **Fail-closed**: Reviewer lỗi ⇒ "chưa chấm được", không bao giờ hiện ra như
  "đã đạt"
- **Full trace**: Every run tracked with token usage and cost estimates
- **Mở lại phiên dở**: `run_id` nằm trên URL, F5 hay gửi link đều dựng lại được
  (server giữ state 120 phút)

### Multi-Brand Knowledge System
- **Brand Management**: CRUD brands with completeness scoring
- **Knowledge Base UI**: Markdown editor with live preview
- **Brand-aware Pipeline**: Context automatically loaded based on selected brand
- **Voice Profiles**: Tone, vocabulary, anti-AI rules per brand
- **Document Templates**: Identity, products, audience, policies

### Content Tools
- **Quick Regenerate**: Viết lại / Đổi hook / Ngắn hơn / Đổi tone
  (dùng model của `channel_renderer` trong `src/config/models.yaml`)
- **Smart Copy**: One-click copy per platform, formatted for FB/IG/TikTok
- **Parallel Rendering**: All channel content rendered concurrently

## 🛠 Tech Stack

| Layer | Tech |
|-------|------|
| **Backend** | Python 3.11, FastAPI, LangChain (LangGraph: chỉ nhánh CLI) |
| **LLM** | Claude Sonnet cho strategist / message_architect / channel_renderer, Haiku cho brief_parser / reviewer — xem `src/config/models.yaml` |
| **Frontend** | React 18, Vite, Tailwind CSS v4, Framer Motion |
| **Data** | File-based knowledge base (Markdown + JSON) |
| **Tests** | pytest (offline, LLM nodes mocked) + GitHub Actions CI |
| **Deploy** | Railway (with persistent volumes) |

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/KuangKhyng/marketing-ai-agent.git
cd marketing-ai-agent

# Backend
pip install -r requirements.txt        # hoặc: uv sync
cp .env.example .env

# Frontend
cd web && npm ci --include=dev && npm run build && cd ..

# Run
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Trong `.env` cần sửa hai dòng để chạy local:

```env
ANTHROPIC_API_KEY=sk-ant-...
ENV=dev          # mặc định là production, và ở production mà thiếu APP_API_KEY
                 # thì MỌI endpoint /api trả 503 (xem api/security.py)
```

Mở `http://localhost:8000`.

### CLI

```bash
python cli.py run "Tạo campaign awareness cho dịch vụ tử vi online, target Gen Z"
python cli.py run --interactive
```

Nhánh CLI chạy qua LangGraph và **tự** vòng lại khi review trượt, khác với web
(xem Pipeline Flow). Kết quả ghi vào `outputs/{run_id}/` gồm `content.md`,
`content.json` và `trace.json`.

### Dependency

Ba nơi khai báo, mỗi nơi một mục đích:

| File | Dùng để |
|------|---------|
| `requirements.txt` | nixpacks **cài thật** trên Railway. Có chặn trên theo major. |
| `pyproject.toml` | metadata package + extra `dev` |
| `uv.lock` | pin chính xác cho môi trường dev local (`uv sync`) |

`tests/test_dependency_consistency.py` canh cho ba file không nói ngược nhau —
trước đây requirements ghi `langgraph>=0.2` trong khi lock là 1.1.8, tức là đã
trôi qua một major mà không ai biết.

**Sinh lại `web/package-lock.json` phải dùng npm ≥ 11:**

```bash
cd web && npx npm@11 install --package-lock-only --include=dev
```

npm 10 trên Windows chỉ ghi binary của win32 vào lock, nên `npm ci` trên CI và
Railway vỡ với thông báo rất khó hiểu (`Cannot find module
@rollup/rollup-linux-x64-gnu`) — ảnh hưởng cả rollup, esbuild, tailwind oxide và
lightningcss. Lock do npm 11 sinh thì npm 10 vẫn đọc được, nên CI không cần đổi
gì. `tests/test_dependency_consistency.py` kiểm luôn điều này.

### Tests

```bash
pip install -e ".[dev]"
pytest                              # không gọi Anthropic API, chạy offline
python scripts/smoke_real_api.py all   # gọi API THẬT, có tốn tiền
```

## 📊 Pipeline Flow

Cùng một chuỗi node, hai đường thực thi:

| Đường | Chạy bởi | Điều phối |
|-------|----------|-----------|
| Web (mặc định) | `api/routes/campaign.py` | `api/pipeline_runner.py` — từng phase là một HTTP request |
| CLI | `cli.py` | `src/graph/workflow.py` — LangGraph + `interrupt()` |

```
Input → brief_parser → context_builder → strategist → [NGƯỜI DUYỆT]
                                                            │
                                                       (approved?)
                                                       /         \
                                                     Yes          No → END
                                                      │
                                              message_architect
                                                      │
                                          channel_renderer (song song)
                                                      │
                                                 reviewer
                                                      │
                                       route_after_review (src/graph/edges.py)
                                          /           |            \
                                    passed         retry        max_retries
                                        │             │              │
                                        │      message_architect     │
                                        └──────────► formatter ◄─────┘
                                                      │
                                                   Export
```

Khác biệt duy nhất giữa hai đường, và là khác biệt **có chủ ý**: ở nhánh
`retry`, LangGraph tự vòng lại `message_architect`; nhánh web trả route ra UI
để người dùng bấm "Hệ thống sửa lại" — mỗi vòng là một lượt gọi API tốn tiền.

Cả hai dùng chung `route_after_review`, và `tests/test_parity.py` chạy cùng một
brief qua cả hai đường rồi so thứ tự node để phát hiện lệch.

## 📁 Project Structure

```
├── cli.py                  # Entrypoint CLI (chạy qua LangGraph)
├── api/                    # FastAPI backend
│   ├── main.py             # App entry, static serving, seed knowledge base
│   ├── security.py         # API key auth, fail-closed ở production
│   ├── routes/
│   │   ├── campaign.py     # Pipeline endpoints + SessionStore
│   │   ├── brands.py       # Brand CRUD + docs + voice
│   │   └── templates.py    # Lưu/nạp brief mẫu
│   ├── pipeline_runner.py  # Điều phối pipeline cho nhánh web
│   ├── events.py           # ProgressBus (SSE tiến trình)
│   ├── cache.py            # Cache strategy/content, key gồm brief + strategy
│   └── schemas.py          # API request/response models
├── src/
│   ├── models/             # Pydantic schemas (brief, content, review)
│   ├── graph/              # LangGraph workflow + edges (routing dùng chung)
│   ├── nodes/              # Pipeline nodes (7 nodes)
│   ├── knowledge/          # BrandManager, retriever, seed volume
│   ├── prompts/v1/         # Prompt templates per node
│   ├── utils/              # paths (chống traversal), trace, callbacks, logging
│   └── config/             # settings.py, models.yaml, platforms.yaml
├── tests/                  # pytest — không gọi API thật
├── scripts/
│   ├── smoke_real_api.py   # smoke test thủ công, GỌI API THẬT
│   └── shot.sh             # chụp ảnh UI để review
├── knowledge_base/
│   ├── _global/            # Shared platform rules + policies
│   └── brands/             # Per-brand knowledge
│       └── {brand_id}/
│           ├── brand.json          # meta + forbidden_claims, mandatory_terms
│           ├── identity.md
│           ├── tone_of_voice.md
│           ├── visual_guidelines.md
│           ├── voice_profile.json
│           ├── products/
│           ├── audience/
│           └── policies/
├── web/                    # React frontend (Vite)
│   └── src/
│       ├── pages/          # 9 trang: Input -> ... -> Export, Brands, Editor
│       ├── components/     # Layout, Sidebar, AuthGate, LoadingOverlay, Scene, Toast
│       ├── hooks/          # useProgress (đọc luồng SSE)
│       └── api/            # Axios client
├── .github/workflows/ci.yml # pytest + import smoke + lint + build
├── nixpacks.toml           # Build: npm ci -> vite build -> pip -> copy seed
├── railway.toml            # Volumes + healthcheck + start command
└── requirements.txt        # bản nixpacks thật sự cài (có chặn major)
```

## 🌐 Deploy (Railway)

1. Push to GitHub
2. Connect repo in Railway Dashboard
3. Env vars:
   - `ANTHROPIC_API_KEY` — bắt buộc
   - `APP_API_KEY` — **bắt buộc**, một hoặc nhiều access key cách nhau bằng dấu
     phẩy. Thiếu biến này thì mọi endpoint `/api` trả 503 (fail-closed có chủ ý:
     thà app không chạy còn hơn mở API cho người lạ đốt token).
   - `ALLOWED_ORIGINS`, `LOG_LEVEL` — tuỳ chọn
4. Volumes — `railway.toml` đã khai sẵn, chỉ cần xác nhận trên dashboard:
   - `/app/knowledge_base` → `knowledge-data`
   - `/app/outputs` → `campaign-outputs`
5. Deploy!

Healthcheck là `/api/health` (public, không cần key). `/api/auth/status` trả
`misconfigured: true` nếu đang chạy production mà thiếu `APP_API_KEY` — frontend
hiện cảnh báo cho admin thay vì để user đoán.

**Về volume và knowledge base:** volume mount vào `/app/knowledge_base` sẽ che
nội dung đã commit ở đó. Lúc build, nixpacks copy `knowledge_base/` sang
`seed_knowledge/` (nằm ngoài mount point); lúc khởi động,
`src/knowledge/seed.py` nạp những file còn thiếu vào volume và không bao giờ ghi
đè file người dùng đã sửa.

## 📝 License

MIT
