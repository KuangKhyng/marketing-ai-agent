# Marketing Agent — React + FastAPI Web UI Implementation Prompt

## Overview

Build một web UI đẹp cho Marketing Agent Workflow Engine, gồm:
- **FastAPI backend** — wrap pipeline hiện tại thành REST API
- **React frontend** — giao diện đẹp, modern, với multi-gate review flow

## Architecture

```
┌──────────────────┐         ┌──────────────────┐
│   React Frontend │ ←─API─→ │  FastAPI Backend  │
│   (Vite + React) │         │                   │
│   Port: 5173     │         │  ┌─────────────┐  │
│                  │         │  │  Pipeline    │  │
│  - Input Form    │         │  │  Runner      │  │
│  - Review Gates  │         │  │  (existing   │  │
│  - Content View  │         │  │   nodes)     │  │
│  - Export        │         │  └─────────────┘  │
│                  │         │   Port: 8000      │
└──────────────────┘         └──────────────────┘
```

---

## PART 1: FastAPI Backend

### File Structure

```
marketing-agent/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── campaign.py      # Campaign CRUD + pipeline endpoints
│   │   └── knowledge.py     # Knowledge base info endpoint
│   ├── schemas.py            # Request/Response Pydantic models
│   └── pipeline_runner.py    # Wrap existing nodes into callable pipeline
├── src/                      # (existing code — unchanged)
├── web/                      # React frontend (separate)
```

### api/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Marketing Agent API",
    description="AI-powered social media campaign generator",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from api.routes.campaign import router as campaign_router
from api.routes.knowledge import router as knowledge_router

app.include_router(campaign_router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["knowledge"])

@app.get("/api/health")
def health():
    return {"status": "ok"}
```

### api/schemas.py — Request/Response Models

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# === REQUEST SCHEMAS ===

class CampaignInput(BaseModel):
    """Input for starting a new campaign."""
    mode: str = "free_text"  # "free_text" | "structured"

    # Free text mode
    raw_input: Optional[str] = None

    # Structured mode
    goal: Optional[str] = None
    product: Optional[str] = None
    audience: Optional[str] = None
    channels: Optional[list[str]] = None
    key_message: Optional[str] = None
    cta: Optional[str] = None

    def to_raw_input(self) -> str:
        if self.mode == "free_text" and self.raw_input:
            return self.raw_input
        parts = []
        if self.goal: parts.append(f"Tạo campaign {self.goal}")
        if self.product: parts.append(f"cho {self.product}")
        if self.audience: parts.append(f"target {self.audience}")
        if self.channels: parts.append(f"Channels: {', '.join(self.channels)}")
        if self.key_message: parts.append(f"Key message: {self.key_message}")
        if self.cta: parts.append(f"CTA: {self.cta}")
        return ". ".join(parts)


class BriefEdit(BaseModel):
    """User edits to the parsed brief."""
    goal: Optional[str] = None
    product: Optional[str] = None
    audience: Optional[str] = None
    channels: Optional[list[str]] = None
    key_message: Optional[str] = None
    cta: Optional[str] = None


class StrategyFeedback(BaseModel):
    """User feedback on strategy."""
    approved: bool
    feedback_checks: list[str] = Field(default_factory=list)  # ["tone", "hook", "cta", ...]
    comment: Optional[str] = None


class ContentPieceFeedback(BaseModel):
    """User feedback on a single content piece."""
    piece_index: int
    approved: bool
    comment: Optional[str] = None
    edited_body: Optional[str] = None  # If user edited directly


class ContentFeedback(BaseModel):
    """User feedback on all content."""
    approved: bool
    piece_feedbacks: list[ContentPieceFeedback] = Field(default_factory=list)


# === RESPONSE SCHEMAS ===

class PipelineStatus(BaseModel):
    run_id: str
    phase: str  # "brief_review" | "strategy_review" | "content_review" | "final_review" | "completed" | "error"
    brief: Optional[dict] = None
    strategy: Optional[str] = None
    master_message: Optional[dict] = None
    content: Optional[dict] = None
    review_result: Optional[dict] = None
    error: Optional[str] = None
    revision_count: int = 0
    cost_estimate: float = 0.0
```

### api/routes/campaign.py — Main API Endpoints

```python
from fastapi import APIRouter, HTTPException
from typing import dict
import uuid

from api.schemas import (
    CampaignInput, BriefEdit, StrategyFeedback,
    ContentFeedback, PipelineStatus,
)
from api.pipeline_runner import PipelineRunner

router = APIRouter()

# In-memory store for active pipeline sessions
# Production: use Redis or database
sessions: dict[str, PipelineRunner] = {}


@router.post("/start", response_model=PipelineStatus)
def start_campaign(input: CampaignInput):
    """
    Start a new campaign pipeline.
    Runs Phase 1 (parse brief + build context).
    Returns brief for review.
    """
    runner = PipelineRunner()
    raw_input = input.to_raw_input()

    state = runner.phase_1_parse(raw_input)

    if state.get("error"):
        raise HTTPException(status_code=500, detail=state["error"])

    run_id = state["trace"].run_id
    sessions[run_id] = runner

    return PipelineStatus(
        run_id=run_id,
        phase="brief_review",
        brief=state["brief"].model_dump() if state.get("brief") else None,
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.post("/{run_id}/approve-brief", response_model=PipelineStatus)
def approve_brief(run_id: str, edit: BriefEdit = None):
    """
    Approve (or edit) the parsed brief, then generate strategy.
    Runs Phase 2 (strategist).
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    # Apply edits if any
    if edit:
        runner.update_brief_fields(edit)

    state = runner.phase_2_strategy()

    if state.get("error"):
        raise HTTPException(status_code=500, detail=state["error"])

    return PipelineStatus(
        run_id=run_id,
        phase="strategy_review",
        brief=state["brief"].model_dump(),
        strategy=state.get("strategy"),
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.post("/{run_id}/review-strategy", response_model=PipelineStatus)
def review_strategy(run_id: str, feedback: StrategyFeedback):
    """
    Review strategy — approve or request revision.
    If approved, runs Phase 3 (message architect + channel renderer).
    If revision requested, re-runs strategist with feedback.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    if not feedback.approved:
        # Compile feedback and re-run strategist
        feedback_text = _compile_strategy_feedback(feedback)
        state = runner.phase_2_strategy(feedback=feedback_text)

        return PipelineStatus(
            run_id=run_id,
            phase="strategy_review",  # Stay on strategy review
            strategy=state.get("strategy"),
            cost_estimate=state["trace"].total_cost_estimate,
        )

    # Approved — generate content
    state = runner.phase_3_content()

    if state.get("error"):
        raise HTTPException(status_code=500, detail=state["error"])

    return PipelineStatus(
        run_id=run_id,
        phase="content_review",
        master_message=state["master_message"].model_dump() if state.get("master_message") else None,
        content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.post("/{run_id}/review-content", response_model=PipelineStatus)
def review_content(run_id: str, feedback: ContentFeedback):
    """
    Review content — approve all or request revision on specific pieces.
    If approved, runs Phase 4 (reviewer).
    If revision requested, re-runs content generation with feedback.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    # Apply inline edits
    for pf in feedback.piece_feedbacks:
        if pf.edited_body:
            runner.update_content_piece(pf.piece_index, pf.edited_body)

    if not feedback.approved:
        feedback_text = _compile_content_feedback(feedback)
        state = runner.phase_3_content(feedback=feedback_text)

        return PipelineStatus(
            run_id=run_id,
            phase="content_review",
            content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
            revision_count=state.get("revision_count", 0),
            cost_estimate=state["trace"].total_cost_estimate,
        )

    # Approved — run automated review
    state = runner.phase_4_review()

    return PipelineStatus(
        run_id=run_id,
        phase="final_review",
        content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
        review_result=state["review_result"].model_dump() if state.get("review_result") else None,
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.post("/{run_id}/approve-final", response_model=PipelineStatus)
def approve_final(run_id: str):
    """
    Final approval — format and save output.
    """
    runner = sessions.get(run_id)
    if not runner:
        raise HTTPException(status_code=404, detail="Session not found")

    state = runner.phase_5_export()

    return PipelineStatus(
        run_id=run_id,
        phase="completed",
        content=state["campaign_content"].model_dump() if state.get("campaign_content") else None,
        review_result=state["review_result"].model_dump() if state.get("review_result") else None,
        cost_estimate=state["trace"].total_cost_estimate,
    )


@router.get("/{run_id}/download/{format}")
def download_output(run_id: str, format: str):
    """Download output in specified format (md, json)."""
    from fastapi.responses import FileResponse
    from src.config.settings import PROJECT_ROOT

    run_dir = PROJECT_ROOT / "outputs" / run_id
    if format == "md":
        path = run_dir / "content.md"
    elif format == "json":
        path = run_dir / "content.json"
    else:
        raise HTTPException(status_code=400, detail="Format must be 'md' or 'json'")

    if not path.exists():
        raise HTTPException(status_code=404, detail="Output not found")

    return FileResponse(path, filename=f"campaign-{run_id}.{format}")


@router.get("/history")
def list_campaigns():
    """List past campaign runs from outputs/ directory."""
    from src.config.settings import PROJECT_ROOT
    import json

    outputs_dir = PROJECT_ROOT / "outputs"
    runs = []
    if outputs_dir.exists():
        for run_dir in sorted(outputs_dir.iterdir(), reverse=True):
            if run_dir.is_dir():
                trace_path = run_dir / "trace.json"
                if trace_path.exists():
                    trace = json.loads(trace_path.read_text(encoding="utf-8"))
                    runs.append({
                        "run_id": run_dir.name,
                        "brief_summary": trace.get("brief_summary", ""),
                        "status": trace.get("final_status", "unknown"),
                        "cost": trace.get("total_cost_estimate", 0),
                        "timestamp": trace.get("started_at", ""),
                    })
    return runs


def _compile_strategy_feedback(feedback: StrategyFeedback) -> str:
    parts = []
    check_labels = {
        "tone": "Tone chưa phù hợp — cần điều chỉnh",
        "angle": "Góc tiếp cận chưa đúng",
        "audience": "Chưa hiểu đúng audience",
        "hook": "Hook chưa đủ mạnh",
        "cta": "CTA chưa rõ ràng",
        "platform": "Platform approach chưa đúng",
    }
    for check in feedback.feedback_checks:
        if check in check_labels:
            parts.append(check_labels[check])
    if feedback.comment:
        parts.append(f"User comment: {feedback.comment}")
    return "\n".join(f"- {p}" for p in parts)


def _compile_content_feedback(feedback: ContentFeedback) -> str:
    parts = ["User yêu cầu sửa các piece sau:"]
    for pf in feedback.piece_feedbacks:
        if not pf.approved:
            parts.append(f"- Piece #{pf.piece_index}: {pf.comment or 'Cần sửa'}")
    return "\n".join(parts)
```

### api/pipeline_runner.py

```python
"""
Pipeline Runner — wraps existing nodes into callable phases.
Used by FastAPI endpoints. Does NOT use LangGraph interrupt().
"""
from src.nodes.brief_parser import brief_parser_node
from src.nodes.context_builder import context_builder_node
from src.nodes.strategist import strategist_node
from src.nodes.message_architect import message_architect_node
from src.nodes.channel_renderer import channel_renderer_node
from src.nodes.reviewer import reviewer_node
from src.nodes.formatter import formatter_node
from src.models.trace import RunTrace
from src.models.brief import CampaignBrief, CampaignGoal, BrandSpec, AudienceSpec, OfferSpec, Channel, Deliverable
from src.models.review import ReviewResult, DimensionScore, ReviewDimension


class PipelineRunner:
    def __init__(self):
        self.state = None

    def phase_1_parse(self, raw_input: str) -> dict:
        self.state = self._init_state(raw_input)

        self.state.update(brief_parser_node(self.state))
        if self.state.get("error"):
            return self.state

        self.state.update(context_builder_node(self.state))
        return self.state

    def phase_2_strategy(self, feedback: str = None) -> dict:
        if feedback:
            self.state["strategy_feedback"] = feedback
        self.state.update(strategist_node(self.state))
        return self.state

    def phase_3_content(self, feedback: str = None) -> dict:
        if feedback:
            self.state["review_result"] = ReviewResult(
                overall_passed=False,
                dimension_scores=[
                    DimensionScore(dimension=d, score=0.5, passed=False, feedback="User revision")
                    for d in ReviewDimension
                ],
                revision_instructions=feedback,
                critical_issues=[],
            )
        self.state["human_approved"] = True
        self.state.update(message_architect_node(self.state))
        if self.state.get("error"):
            return self.state
        self.state.update(channel_renderer_node(self.state))
        return self.state

    def phase_4_review(self) -> dict:
        self.state.update(reviewer_node(self.state))
        return self.state

    def phase_5_export(self) -> dict:
        self.state.update(formatter_node(self.state))
        return self.state

    def update_brief_fields(self, edit) -> None:
        brief = self.state["brief"]
        if edit.goal:
            brief.goal = CampaignGoal(edit.goal)
        if edit.product:
            brief.offer.product_or_service = edit.product
        if edit.audience:
            brief.audience.persona_description = edit.audience
        if edit.channels:
            brief.channels = [Channel(c) for c in edit.channels]
        if edit.key_message:
            brief.offer.key_message = edit.key_message
        if edit.cta:
            brief.offer.cta = edit.cta
        # Re-build context with updated brief
        self.state.update(context_builder_node(self.state))

    def update_content_piece(self, index: int, new_body: str) -> None:
        pieces = self.state["campaign_content"].pieces
        if 0 <= index < len(pieces):
            pieces[index].body = new_body
            pieces[index].word_count = len(new_body.split())

    def _init_state(self, raw_input: str) -> dict:
        return {
            "raw_input": raw_input,
            "brief": None,
            "context_pack": None,
            "strategy": None,
            "strategy_feedback": None,
            "human_approved": False,
            "master_message": None,
            "campaign_content": None,
            "review_result": None,
            "revision_count": 0,
            "max_revisions": 2,
            "trace": RunTrace(),
            "current_node": "",
            "error": None,
        }
```

### Run Backend

```bash
# Install
pip install fastapi uvicorn

# Run
uvicorn api.main:app --reload --port 8000

# API docs auto-generated at http://localhost:8000/docs
```

---

## PART 2: React Frontend

### Setup

```bash
# Trong thư mục marketing-agent/
npm create vite@latest web -- --template react
cd web
npm install
npm install axios react-router-dom lucide-react framer-motion
npm install -D tailwindcss @tailwindcss/vite
```

### File Structure

```
web/
├── index.html
├── vite.config.js
├── tailwind.config.js
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── index.css               # Tailwind + custom styles
│   ├── api/
│   │   └── client.js           # Axios instance + API functions
│   ├── store/
│   │   └── campaignStore.js    # State management (zustand or context)
│   ├── components/
│   │   ├── Layout.jsx          # Sidebar + Main layout
│   │   ├── Sidebar.jsx         # Phase progress + history
│   │   ├── PhaseIndicator.jsx  # Step indicator component
│   │   └── ContentCard.jsx     # Reusable content display card
│   ├── pages/
│   │   ├── InputPage.jsx       # Campaign input form
│   │   ├── BriefReviewPage.jsx # Gate 1: review brief
│   │   ├── StrategyReviewPage.jsx  # Gate 2: review strategy
│   │   ├── ContentReviewPage.jsx   # Gate 3: review content
│   │   ├── FinalReviewPage.jsx     # Gate 4: review scores
│   │   └── ExportPage.jsx      # Download/export
│   └── hooks/
│       └── useCampaign.js      # Custom hook for campaign state
```

### Design System

```
Color Palette (matching tử vi brand):
- Primary:       #6c5ce7 (purple — accent, buttons)
- Primary Dark:  #4a3db5
- Background:    #0f0f1a (dark navy — main bg)
- Surface:       #1a1a2e (dark card bg)
- Surface Light: #252540 (lighter card)
- Text Primary:  #e8e6f0 (light text)
- Text Secondary:#8b89a6 (muted text)
- Gold Accent:   #f5c842 (gold — highlights)
- Success:       #00d68f
- Error:         #ff4757
- Border:        #2d2d4a

Typography:
- Headings: Inter or Space Grotesk (modern, clean)
- Body: Inter
- Mono: JetBrains Mono (for JSON/code)

Vibe: Dark mode, modern spiritual, premium feel.
Không giống Streamlit — giống một SaaS product thật.
```

### src/index.css

```css
@import "tailwindcss";

:root {
  --primary: #6c5ce7;
  --primary-dark: #4a3db5;
  --bg: #0f0f1a;
  --surface: #1a1a2e;
  --surface-light: #252540;
  --text: #e8e6f0;
  --text-muted: #8b89a6;
  --gold: #f5c842;
  --success: #00d68f;
  --error: #ff4757;
  --border: #2d2d4a;
}

body {
  background-color: var(--bg);
  color: var(--text);
  font-family: 'Inter', system-ui, sans-serif;
}
```

### src/api/client.js

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 120000, // 2 min — LLM calls can be slow
});

export const campaignAPI = {
  start: (input) => api.post('/campaigns/start', input),
  approveBrief: (runId, edit) => api.post(`/campaigns/${runId}/approve-brief`, edit),
  reviewStrategy: (runId, feedback) => api.post(`/campaigns/${runId}/review-strategy`, feedback),
  reviewContent: (runId, feedback) => api.post(`/campaigns/${runId}/review-content`, feedback),
  approveFinal: (runId) => api.post(`/campaigns/${runId}/approve-final`),
  download: (runId, format) => api.get(`/campaigns/${runId}/download/${format}`, { responseType: 'blob' }),
  history: () => api.get('/campaigns/history'),
};

export default api;
```

### src/App.jsx — Main App

```jsx
import { useState } from 'react';
import Layout from './components/Layout';
import InputPage from './pages/InputPage';
import BriefReviewPage from './pages/BriefReviewPage';
import StrategyReviewPage from './pages/StrategyReviewPage';
import ContentReviewPage from './pages/ContentReviewPage';
import FinalReviewPage from './pages/FinalReviewPage';
import ExportPage from './pages/ExportPage';

const PHASES = ['input', 'brief_review', 'strategy_review', 'content_review', 'final_review', 'export'];

export default function App() {
  const [phase, setPhase] = useState('input');
  const [campaignData, setCampaignData] = useState(null);
  const [loading, setLoading] = useState(false);

  const pageProps = { campaignData, setCampaignData, setPhase, loading, setLoading };

  return (
    <Layout phase={phase} phases={PHASES} onReset={() => { setPhase('input'); setCampaignData(null); }}>
      {phase === 'input' && <InputPage {...pageProps} />}
      {phase === 'brief_review' && <BriefReviewPage {...pageProps} />}
      {phase === 'strategy_review' && <StrategyReviewPage {...pageProps} />}
      {phase === 'content_review' && <ContentReviewPage {...pageProps} />}
      {phase === 'final_review' && <FinalReviewPage {...pageProps} />}
      {phase === 'export' && <ExportPage {...pageProps} />}
    </Layout>
  );
}
```

### src/components/Layout.jsx

```jsx
import Sidebar from './Sidebar';

export default function Layout({ children, phase, phases, onReset }) {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r flex flex-col"
             style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)' }}>
        <div className="p-6">
          <h1 className="text-xl font-bold" style={{ color: 'var(--primary)' }}>
            ✦ Marketing Agent
          </h1>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            AI-powered campaign generator
          </p>
        </div>
        <Sidebar phase={phase} phases={phases} />
        <div className="mt-auto p-4">
          <button onClick={onReset}
                  className="w-full py-2 rounded-lg text-sm font-medium transition-colors"
                  style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text-muted)' }}>
            + New Campaign
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-4xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
```

### src/components/Sidebar.jsx

```jsx
import { Check, Circle, Loader2 } from 'lucide-react';

const PHASE_CONFIG = {
  input:           { label: 'Campaign Brief',   icon: '📝' },
  brief_review:    { label: 'Brief Review',     icon: '📋' },
  strategy_review: { label: 'Strategy Review',  icon: '🎯' },
  content_review:  { label: 'Content Review',   icon: '✍️' },
  final_review:    { label: 'Final Review',     icon: '📊' },
  export:          { label: 'Export',            icon: '📦' },
};

export default function Sidebar({ phase, phases }) {
  const currentIdx = phases.indexOf(phase);

  return (
    <nav className="flex-1 px-4">
      {phases.map((p, i) => {
        const config = PHASE_CONFIG[p];
        const isActive = p === phase;
        const isDone = i < currentIdx;

        return (
          <div key={p} className="flex items-center gap-3 py-2.5 px-3 rounded-lg mb-1 transition-all"
               style={{
                 backgroundColor: isActive ? 'var(--surface-light)' : 'transparent',
                 color: isDone ? 'var(--success)' : isActive ? 'var(--text)' : 'var(--text-muted)',
               }}>
            <span className="text-sm w-5 text-center">
              {isDone ? '✓' : config.icon}
            </span>
            <span className="text-sm font-medium">{config.label}</span>
          </div>
        );
      })}
    </nav>
  );
}
```

### src/pages/InputPage.jsx

```jsx
import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Loader2, Sparkles } from 'lucide-react';

export default function InputPage({ setCampaignData, setPhase, loading, setLoading }) {
  const [mode, setMode] = useState('structured');
  const [freeText, setFreeText] = useState('');
  const [form, setForm] = useState({
    goal: 'awareness',
    product: '',
    audience: '',
    channels: ['facebook', 'instagram'],
    key_message: '',
    cta: '',
  });

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const input = mode === 'free_text'
        ? { mode: 'free_text', raw_input: freeText }
        : { mode: 'structured', ...form };

      const { data } = await campaignAPI.start(input);
      setCampaignData(data);
      setPhase('brief_review');
    } catch (err) {
      alert('Error: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">Campaign Brief</h2>
      <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
        Nhập yêu cầu campaign — AI sẽ phân tích và tạo content cho bạn.
      </p>

      {/* Mode toggle */}
      <div className="flex gap-2 mb-6">
        {['free_text', 'structured'].map(m => (
          <button key={m} onClick={() => setMode(m)}
                  className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                  style={{
                    backgroundColor: mode === m ? 'var(--primary)' : 'var(--surface)',
                    color: mode === m ? '#fff' : 'var(--text-muted)',
                  }}>
            {m === 'free_text' ? 'Free Text' : 'Structured Form'}
          </button>
        ))}
      </div>

      {mode === 'free_text' ? (
        <textarea value={freeText} onChange={e => setFreeText(e.target.value)}
                  placeholder="Ví dụ: Tạo campaign awareness cho dịch vụ tử vi online, target Gen Z quan tâm tâm linh..."
                  rows={4}
                  className="w-full p-4 rounded-xl text-sm resize-none focus:outline-none focus:ring-2"
                  style={{ backgroundColor: 'var(--surface)', borderColor: 'var(--border)',
                           color: 'var(--text)', focusRingColor: 'var(--primary)' }}
        />
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {/* Goal */}
          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-muted)' }}>Mục tiêu</label>
            <select value={form.goal} onChange={e => setForm({...form, goal: e.target.value})}
                    className="w-full p-3 rounded-xl text-sm"
                    style={{ backgroundColor: 'var(--surface)', color: 'var(--text)', border: '1px solid var(--border)' }}>
              <option value="awareness">Awareness</option>
              <option value="engagement">Engagement</option>
              <option value="lead_generation">Lead Generation</option>
              <option value="conversion">Conversion</option>
            </select>
          </div>

          {/* Channels */}
          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-muted)' }}>Channels</label>
            <div className="flex gap-2">
              {['facebook', 'instagram', 'tiktok'].map(ch => (
                <button key={ch} onClick={() => {
                  const channels = form.channels.includes(ch)
                    ? form.channels.filter(c => c !== ch)
                    : [...form.channels, ch];
                  setForm({...form, channels});
                }}
                className="px-3 py-2 rounded-lg text-xs font-medium transition-all"
                style={{
                  backgroundColor: form.channels.includes(ch) ? 'var(--primary)' : 'var(--surface-light)',
                  color: form.channels.includes(ch) ? '#fff' : 'var(--text-muted)',
                }}>
                  {ch}
                </button>
              ))}
            </div>
          </div>

          {/* Product */}
          <InputField label="Sản phẩm/Dịch vụ" value={form.product}
                      onChange={v => setForm({...form, product: v})}
                      placeholder="Dịch vụ xem tử vi online" />

          {/* Key Message */}
          <InputField label="Thông điệp chính" value={form.key_message}
                      onChange={v => setForm({...form, key_message: v})}
                      placeholder="Khám phá bản thân qua lá số tử vi" />

          {/* Audience */}
          <InputField label="Đối tượng" value={form.audience}
                      onChange={v => setForm({...form, audience: v})}
                      placeholder="Gen Z quan tâm tâm linh" />

          {/* CTA */}
          <InputField label="CTA" value={form.cta}
                      onChange={v => setForm({...form, cta: v})}
                      placeholder="Đặt lịch xem tử vi" />
        </div>
      )}

      {/* Generate button */}
      <button onClick={handleSubmit} disabled={loading}
              className="w-full mt-6 py-3.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all hover:brightness-110 disabled:opacity-50"
              style={{ backgroundColor: 'var(--primary)', color: '#fff' }}>
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
        {loading ? 'Đang xử lý...' : 'Generate Campaign'}
      </button>
    </div>
  );
}

function InputField({ label, value, onChange, placeholder }) {
  return (
    <div>
      <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--text-muted)' }}>{label}</label>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
             className="w-full p-3 rounded-xl text-sm focus:outline-none focus:ring-2"
             style={{ backgroundColor: 'var(--surface)', color: 'var(--text)',
                      border: '1px solid var(--border)' }} />
    </div>
  );
}
```

### src/pages/StrategyReviewPage.jsx

```jsx
import { useState } from 'react';
import { campaignAPI } from '../api/client';
import { Check, RotateCcw, Loader2 } from 'lucide-react';

const FEEDBACK_OPTIONS = [
  { key: 'tone', label: 'Tone chưa phù hợp' },
  { key: 'angle', label: 'Góc tiếp cận chưa đúng' },
  { key: 'audience', label: 'Chưa hiểu đúng audience' },
  { key: 'hook', label: 'Hook chưa đủ mạnh' },
  { key: 'cta', label: 'CTA chưa rõ ràng' },
  { key: 'platform', label: 'Platform approach chưa đúng' },
];

export default function StrategyReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const [checks, setChecks] = useState([]);
  const [comment, setComment] = useState('');

  const handleApprove = async () => {
    setLoading(true);
    try {
      const { data } = await campaignAPI.reviewStrategy(campaignData.run_id, {
        approved: true,
        feedback_checks: [],
        comment: null,
      });
      setCampaignData(data);
      setPhase('content_review');
    } finally {
      setLoading(false);
    }
  };

  const handleRevise = async () => {
    if (checks.length === 0 && !comment) {
      alert('Vui lòng chọn ít nhất 1 vấn đề hoặc viết comment.');
      return;
    }
    setLoading(true);
    try {
      const { data } = await campaignAPI.reviewStrategy(campaignData.run_id, {
        approved: false,
        feedback_checks: checks,
        comment,
      });
      setCampaignData(data);
      // Stay on same page with new strategy
      setComment('');
      setChecks([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">Strategy Review</h2>
      <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
        Xem lại chiến lược campaign trước khi tạo content.
      </p>

      {/* Strategy content */}
      <div className="rounded-xl p-6 mb-6 whitespace-pre-wrap leading-relaxed text-sm"
           style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}>
        {campaignData?.strategy}
      </div>

      {/* Feedback section */}
      <div className="rounded-xl p-6 mb-6" style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}>
        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--gold)' }}>
          💬 Feedback (nếu cần sửa)
        </h3>

        <div className="grid grid-cols-2 gap-2 mb-4">
          {FEEDBACK_OPTIONS.map(opt => (
            <label key={opt.key}
                   className="flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-all"
                   style={{
                     backgroundColor: checks.includes(opt.key) ? 'rgba(108, 92, 231, 0.2)' : 'var(--surface-light)',
                     color: checks.includes(opt.key) ? 'var(--primary)' : 'var(--text-muted)',
                   }}>
              <input type="checkbox" checked={checks.includes(opt.key)}
                     onChange={e => {
                       if (e.target.checked) setChecks([...checks, opt.key]);
                       else setChecks(checks.filter(c => c !== opt.key));
                     }}
                     className="accent-purple-500" />
              {opt.label}
            </label>
          ))}
        </div>

        <textarea value={comment} onChange={e => setComment(e.target.value)}
                  placeholder="Ghi chú thêm..."
                  rows={3}
                  className="w-full p-3 rounded-xl text-sm resize-none"
                  style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text)', border: 'none' }} />
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button onClick={handleApprove} disabled={loading}
                className="flex-1 py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
                style={{ backgroundColor: 'var(--success)', color: '#fff' }}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
          Approve — Tiếp tục
        </button>
        <button onClick={handleRevise} disabled={loading || (checks.length === 0 && !comment)}
                className="flex-1 py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
                style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text)' }}>
          <RotateCcw className="w-4 h-4" />
          Yêu cầu sửa
        </button>
      </div>
    </div>
  );
}
```

### src/pages/ContentReviewPage.jsx

```jsx
import { useState } from 'react';
import { campaignAPI } from '../api/client';

export default function ContentReviewPage({ campaignData, setCampaignData, setPhase, loading, setLoading }) {
  const pieces = campaignData?.content?.pieces || [];
  const [activeTab, setActiveTab] = useState(0);
  const [editMode, setEditMode] = useState({});
  const [edits, setEdits] = useState({});
  const [feedback, setFeedback] = useState({});

  const handleApprove = async () => {
    setLoading(true);
    try {
      const pieceFeedbacks = pieces.map((_, i) => ({
        piece_index: i,
        approved: !feedback[i]?.needsChange,
        comment: feedback[i]?.comment || null,
        edited_body: edits[i] || null,
      }));

      const { data } = await campaignAPI.reviewContent(campaignData.run_id, {
        approved: true,
        piece_feedbacks: pieceFeedbacks,
      });
      setCampaignData(data);
      setPhase('final_review');
    } finally {
      setLoading(false);
    }
  };

  const handleRevise = async () => {
    setLoading(true);
    try {
      const pieceFeedbacks = Object.entries(feedback)
        .filter(([_, fb]) => fb.needsChange)
        .map(([i, fb]) => ({
          piece_index: parseInt(i),
          approved: false,
          comment: fb.comment,
          edited_body: edits[i] || null,
        }));

      const { data } = await campaignAPI.reviewContent(campaignData.run_id, {
        approved: false,
        piece_feedbacks: pieceFeedbacks,
      });
      setCampaignData(data);
      setFeedback({});
      setEdits({});
    } finally {
      setLoading(false);
    }
  };

  const activePiece = pieces[activeTab];
  const needsChangeCount = Object.values(feedback).filter(f => f.needsChange).length;

  return (
    <div>
      <h2 className="text-2xl font-bold mb-2">Content Review</h2>
      <p className="mb-6" style={{ color: 'var(--text-muted)' }}>
        Review từng piece content. Chỉnh sửa trực tiếp hoặc yêu cầu AI sửa.
      </p>

      {/* Channel tabs */}
      <div className="flex gap-2 mb-4">
        {pieces.map((piece, i) => (
          <button key={i} onClick={() => setActiveTab(i)}
                  className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                  style={{
                    backgroundColor: activeTab === i ? 'var(--primary)' : 'var(--surface)',
                    color: activeTab === i ? '#fff' : 'var(--text-muted)',
                  }}>
            {piece.channel.toUpperCase()} — {piece.deliverable}
            {feedback[i]?.needsChange && ' ⚠️'}
          </button>
        ))}
      </div>

      {/* Active piece content */}
      {activePiece && (
        <div className="rounded-xl p-6 mb-4" style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}>
          {/* Hook */}
          {activePiece.hook && (
            <div className="mb-4">
              <span className="text-xs font-semibold px-2 py-1 rounded" style={{ backgroundColor: 'var(--gold)', color: '#000' }}>HOOK</span>
              <p className="mt-2 text-sm">{activePiece.hook}</p>
            </div>
          )}

          {/* Body — editable */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>CONTENT</span>
              <button onClick={() => setEditMode({...editMode, [activeTab]: !editMode[activeTab]})}
                      className="text-xs px-3 py-1 rounded-lg"
                      style={{ backgroundColor: 'var(--surface-light)', color: 'var(--primary)' }}>
                {editMode[activeTab] ? 'Preview' : '✏️ Edit'}
              </button>
            </div>

            {editMode[activeTab] ? (
              <textarea value={edits[activeTab] || activePiece.body}
                        onChange={e => setEdits({...edits, [activeTab]: e.target.value})}
                        rows={12}
                        className="w-full p-4 rounded-xl text-sm resize-none"
                        style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text)', border: 'none' }} />
            ) : (
              <div className="whitespace-pre-wrap text-sm leading-relaxed p-4 rounded-xl"
                   style={{ backgroundColor: 'var(--surface-light)' }}>
                {edits[activeTab] || activePiece.body}
              </div>
            )}
          </div>

          {/* CTA */}
          {activePiece.cta_text && (
            <div className="p-3 rounded-lg mb-4" style={{ backgroundColor: 'rgba(0, 214, 143, 0.1)', border: '1px solid var(--success)' }}>
              <span className="text-xs font-semibold" style={{ color: 'var(--success)' }}>CTA: </span>
              <span className="text-sm">{activePiece.cta_text}</span>
            </div>
          )}

          {/* Hashtags */}
          {activePiece.hashtags?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {activePiece.hashtags.map((h, i) => (
                <span key={i} className="text-xs px-2 py-1 rounded-full" style={{ backgroundColor: 'var(--surface-light)', color: 'var(--primary)' }}>
                  {h}
                </span>
              ))}
            </div>
          )}

          {/* Word count */}
          <p className="text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
            {activePiece.word_count} words
          </p>
        </div>
      )}

      {/* Per-piece feedback */}
      <div className="rounded-xl p-4 mb-6" style={{ backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }}>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox"
                 checked={feedback[activeTab]?.needsChange || false}
                 onChange={e => setFeedback({
                   ...feedback,
                   [activeTab]: { ...feedback[activeTab], needsChange: e.target.checked }
                 })}
                 className="accent-red-500" />
          <span className="text-sm">🔄 Piece này cần sửa</span>
        </label>

        {feedback[activeTab]?.needsChange && (
          <textarea placeholder="Cần sửa gì? (ví dụ: hook yếu, tone quá formal...)"
                    value={feedback[activeTab]?.comment || ''}
                    onChange={e => setFeedback({
                      ...feedback,
                      [activeTab]: { ...feedback[activeTab], comment: e.target.value }
                    })}
                    rows={2}
                    className="w-full mt-3 p-3 rounded-xl text-sm resize-none"
                    style={{ backgroundColor: 'var(--surface-light)', color: 'var(--text)', border: 'none' }} />
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        <button onClick={handleApprove} disabled={loading || needsChangeCount > 0}
                className="flex-1 py-3 rounded-xl text-sm font-semibold disabled:opacity-40"
                style={{ backgroundColor: 'var(--success)', color: '#fff' }}>
          ✅ Approve tất cả
        </button>
        {needsChangeCount > 0 && (
          <button onClick={handleRevise} disabled={loading}
                  className="flex-1 py-3 rounded-xl text-sm font-semibold"
                  style={{ backgroundColor: 'var(--primary)', color: '#fff' }}>
            🔄 Yêu cầu sửa ({needsChangeCount} pieces)
          </button>
        )}
      </div>
    </div>
  );
}
```

### Các pages còn lại (BriefReviewPage, FinalReviewPage, ExportPage)

Implement tương tự pattern trên:
- **BriefReviewPage**: Hiện brief fields dạng cards, có nút "Edit" để chỉnh từng field, nút "Approve → Generate Strategy"
- **FinalReviewPage**: Hiện 4 score cards với progress bars, overall status, nút "Approve & Export" / "← Back to Content"
- **ExportPage**: Hiện preview content + download buttons (MD, JSON), link tới output directory

---

## Run Commands

```bash
# Terminal 1 — Backend
cd marketing-agent
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Frontend
cd marketing-agent/web
npm run dev
# → http://localhost:5173
```

## Dependencies to add

```bash
# Backend
pip install fastapi uvicorn

# Frontend (already set up by Vite)
cd web && npm install
```

## Implementation Order

1. **Backend first** — tạo `api/` folder, implement endpoints, test với Swagger UI (`/docs`)
2. **Frontend skeleton** — Layout, Sidebar, routing giữa pages
3. **InputPage** — form + call `/start`
4. **BriefReviewPage** — display brief + call `/approve-brief`
5. **StrategyReviewPage** — display strategy + feedback + call `/review-strategy`
6. **ContentReviewPage** — tabs + inline edit + call `/review-content`
7. **FinalReviewPage** — scores + call `/approve-final`
8. **ExportPage** — download buttons
9. **History** — sidebar list from `/history`
10. **Polish** — animations, loading states, error handling
