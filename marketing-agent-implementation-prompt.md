# Marketing Agent Workflow Engine — Implementation Prompt

## Mục đích
Prompt này dùng để feed vào AI coding assistant (Claude Code, Cursor, etc.) nhằm implement từ đầu một Marketing Agent Workflow Engine bằng Python + LangGraph + Anthropic Claude API.

---

## 1. Project Overview

Build một **Marketing Agent Workflow Engine** — hệ thống multi-step pipeline tạo social media campaign content. Hệ thống nhận input tự nhiên từ user, tự assemble context từ knowledge base, sinh ra "master message" platform-agnostic, rồi render thành content native cho từng platform (Facebook, Instagram, TikTok).

### Core Design Principles
1. **Workflow-first, agent-second** — phần lớn node là deterministic, chỉ vài node cần LLM reasoning
2. **Schema-first** — mọi node giao tiếp bằng Pydantic typed models, không truyền text tự do
3. **RAG with policy filters** — knowledge base có metadata, retrieve theo priority hierarchy
4. **Human approval cho risky steps** — CLI interrupt trước khi generate content
5. **Eval-driven** — có golden dataset, scoring 4 chiều
6. **Trace everything** — mỗi run có trace đầy đủ

### Tech Stack
- **Python 3.11+**
- **LangGraph** (StateGraph, nodes, conditional edges, checkpointing)
- **LangChain** (ChatAnthropic, tools)
- **Anthropic Claude API** (Sonnet cho generation, Haiku cho parsing/checking)
- **Pydantic v2** (typed contracts)
- **ChromaDB** (vector store cho RAG — Phase 2, Phase 1 dùng static files)
- **Rich** (CLI output formatting)
- **UV hoặc Poetry** (dependency management)

---

## 2. Repo Structure

```
marketing-agent/
├── pyproject.toml
├── .env.example                    # ANTHROPIC_API_KEY=sk-ant-...
├── README.md
│
├── src/
│   ├── __init__.py
│   │
│   ├── models/                     # Pydantic schemas — typed IO contracts
│   │   ├── __init__.py
│   │   ├── brief.py                # CampaignBrief, AudienceProfile, BrandContext
│   │   ├── message.py              # MasterMessage, ContentPillar, CTASpec
│   │   ├── content.py              # ChannelContent, FacebookPost, InstagramCarousel, TikTokScript
│   │   ├── review.py               # ReviewResult, ReviewScore, ReviewFeedback
│   │   └── trace.py                # RunTrace, NodeTrace
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py                # CampaignState (TypedDict) — shared state
│   │   ├── workflow.py             # build_workflow() → CompiledGraph
│   │   └── edges.py                # should_retry(), is_approved() — conditional edge functions
│   │
│   ├── nodes/                      # workflow nodes (NOT all are "agents")
│   │   ├── __init__.py
│   │   ├── brief_parser.py         # deterministic — extract structured brief
│   │   ├── context_builder.py      # deterministic + RAG — assemble context pack
│   │   ├── strategist.py           # agentic — campaign strategy + web search
│   │   ├── message_architect.py    # agentic — master message (platform-agnostic)
│   │   ├── channel_renderer.py     # agentic — render per platform
│   │   ├── reviewer.py             # semi-deterministic — score 4 dimensions
│   │   └── formatter.py            # deterministic — compile final output
│   │
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── loader.py               # load markdown files from knowledge_base/
│   │   ├── retriever.py            # retrieve relevant context with priority filtering
│   │   └── voice_analyzer.py       # analyze sample posts → voice profile JSON
│   │
│   ├── prompts/
│   │   └── v1/
│   │       ├── brief_parser.md
│   │       ├── strategist.md
│   │       ├── message_architect.md
│   │       ├── channel_renderer_facebook.md
│   │       ├── channel_renderer_instagram.md
│   │       ├── channel_renderer_tiktok.md
│   │       └── reviewer.md
│   │
│   └── config/
│       ├── __init__.py
│       ├── settings.py             # load .env, model configs
│       ├── models.yaml             # model assignment per node
│       └── platforms.yaml          # platform specs (char limits, formats, etc.)
│
├── knowledge_base/                 # raw knowledge data
│   ├── brand/
│   │   ├── brand_identity.md
│   │   ├── tone_of_voice.md
│   │   └── visual_guidelines.md
│   ├── products/
│   │   └── _template.md
│   ├── audience/
│   │   └── _template.md
│   ├── platforms/
│   │   ├── facebook.md
│   │   ├── instagram.md
│   │   └── tiktok.md
│   └── policies/
│       └── content_policy.md
│
├── voice_profiles/
│   └── default.json
│
├── datasets/
│   ├── golden/                     # golden briefs + approved outputs
│   └── failures/                   # intentional bad cases for eval
│
├── outputs/                        # generated campaign outputs
│
├── cli.py                          # main entry point
└── eval.py                         # evaluation runner
```

---

## 3. Pydantic Models (src/models/)

### 3.1 brief.py

```python
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class CampaignGoal(str, Enum):
    AWARENESS = "awareness"
    ENGAGEMENT = "engagement"
    LEAD_GENERATION = "lead_generation"
    CONVERSION = "conversion"
    RETENTION = "retention"


class AwarenessStage(str, Enum):
    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    MOST_AWARE = "most_aware"


class Channel(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class Deliverable(str, Enum):
    POST = "post"
    CAROUSEL = "carousel"
    REELS_SCRIPT = "reels_script"
    SHORT_VIDEO_SCRIPT = "short_video_script"
    STORY = "story"


class AudienceSpec(BaseModel):
    persona_description: str = Field(description="Mô tả ngắn gọn target audience")
    age_range: Optional[str] = None
    pain_points: list[str] = Field(default_factory=list)
    awareness_stage: AwarenessStage = AwarenessStage.PROBLEM_AWARE


class BrandSpec(BaseModel):
    name: str
    voice_profile_id: str = "default"
    forbidden_claims: list[str] = Field(default_factory=list, description="Những claim KHÔNG được đưa vào content")
    mandatory_terms: list[str] = Field(default_factory=list, description="Từ/cụm từ BẮT BUỘC phải có")


class OfferSpec(BaseModel):
    product_or_service: str = Field(description="Tên sản phẩm/dịch vụ")
    key_message: str = Field(description="Thông điệp chính muốn truyền tải")
    cta: str = Field(description="Call-to-action mong muốn")
    unique_selling_points: list[str] = Field(default_factory=list)


class ContentConstraints(BaseModel):
    word_limit: Optional[int] = None
    must_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    hashtag_count: Optional[int] = None


class SuccessCriteria(BaseModel):
    tone_match_min: float = Field(default=0.7, ge=0, le=1, description="Minimum tone match score")
    factuality_required: bool = True
    brand_safety_required: bool = True


class CampaignBrief(BaseModel):
    """Canonical brief schema — single source of truth cho toàn pipeline."""
    goal: CampaignGoal
    brand: BrandSpec
    audience: AudienceSpec
    offer: OfferSpec
    channels: list[Channel]
    deliverables: list[Deliverable]
    constraints: ContentConstraints = Field(default_factory=ContentConstraints)
    success_criteria: SuccessCriteria = Field(default_factory=SuccessCriteria)
    additional_context: Optional[str] = None
```

### 3.2 message.py

```python
from pydantic import BaseModel, Field


class MasterMessage(BaseModel):
    """Platform-agnostic message architecture — bộ xương cho tất cả content."""
    core_promise: str = Field(description="Lời hứa cốt lõi — 1 câu duy nhất")
    key_points: list[str] = Field(description="3-5 điểm chính hỗ trợ core promise", min_length=1, max_length=5)
    emotional_angle: str = Field(description="Góc cảm xúc muốn chạm — ví dụ: tò mò, an tâm, FOMO")
    proof_angle: str = Field(description="Bằng chứng/social proof hỗ trợ — ví dụ: số liệu, testimonial")
    cta_primary: str = Field(description="CTA chính")
    cta_secondary: Optional[str] = Field(default=None, description="CTA phụ (nếu có)")
    taboo_points: list[str] = Field(default_factory=list, description="Những điều TUYỆT ĐỐI KHÔNG đề cập")
    tone_direction: str = Field(description="Hướng dẫn tone cụ thể cho content này")


from typing import Optional
```

### 3.3 content.py

```python
from pydantic import BaseModel, Field
from typing import Optional
from .brief import Channel, Deliverable


class ContentPiece(BaseModel):
    """Một piece content cho một platform cụ thể."""
    channel: Channel
    deliverable: Deliverable
    headline: Optional[str] = None
    body: str = Field(description="Nội dung chính")
    hashtags: list[str] = Field(default_factory=list)
    visual_direction: Optional[str] = Field(default=None, description="Gợi ý hình ảnh/video")
    hook: Optional[str] = Field(default=None, description="Opening hook (đặc biệt quan trọng cho TikTok/Reels)")
    cta_text: str = ""
    notes: Optional[str] = Field(default=None, description="Ghi chú thêm cho content creator")
    word_count: int = 0


class CampaignContent(BaseModel):
    """Tập hợp tất cả content pieces cho một campaign."""
    pieces: list[ContentPiece]
    master_message_summary: str = Field(description="Tóm tắt message architecture để reference")
```

### 3.4 review.py

```python
from pydantic import BaseModel, Field
from enum import Enum


class ReviewDimension(str, Enum):
    BRAND_FIT = "brand_fit"
    FACTUALITY = "factuality"
    CHANNEL_FIT = "channel_fit"
    BUSINESS_FIT = "business_fit"


class DimensionScore(BaseModel):
    dimension: ReviewDimension
    score: float = Field(ge=0, le=1, description="0.0 = hoàn toàn sai, 1.0 = hoàn hảo")
    passed: bool
    feedback: str = Field(description="Lý do cụ thể nếu không pass")


class ReviewResult(BaseModel):
    overall_passed: bool
    dimension_scores: list[DimensionScore]
    critical_issues: list[str] = Field(default_factory=list, description="Vấn đề nghiêm trọng cần sửa ngay")
    suggestions: list[str] = Field(default_factory=list, description="Đề xuất cải thiện (không bắt buộc)")
    revision_instructions: Optional[str] = Field(default=None, description="Hướng dẫn sửa cụ thể nếu fail")


from typing import Optional
```

### 3.5 trace.py

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Optional
import uuid


class NodeTrace(BaseModel):
    node_name: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    model_used: Optional[str] = None
    input_summary: str = ""
    output_summary: str = ""
    retrieved_context_ids: list[str] = Field(default_factory=list)
    token_usage: dict[str, int] = Field(default_factory=dict)  # {"input": N, "output": M}
    error: Optional[str] = None


class RunTrace(BaseModel):
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    brief_summary: str = ""
    node_traces: list[NodeTrace] = Field(default_factory=list)
    total_cost_estimate: float = 0.0
    revision_count: int = 0
    final_status: str = "running"  # running, completed, failed, human_rejected
```

---

## 4. Graph State (src/graph/state.py)

```python
from typing import TypedDict, Optional, Annotated
from src.models.brief import CampaignBrief
from src.models.message import MasterMessage
from src.models.content import CampaignContent
from src.models.review import ReviewResult
from src.models.trace import RunTrace


class CampaignState(TypedDict):
    # Input
    raw_input: str                              # user's natural language input

    # Parsed
    brief: Optional[CampaignBrief]              # structured brief from Brief Parser

    # Context
    context_pack: Optional[dict]                # assembled context from knowledge base
                                                 # {"brand": str, "product": str, "audience": str,
                                                 #  "platform_rules": dict[str, str], "policies": str}

    # Strategy
    strategy: Optional[str]                     # campaign strategy from Strategist (text)
    human_approved: bool                        # whether human approved the strategy

    # Content
    master_message: Optional[MasterMessage]     # platform-agnostic message architecture
    campaign_content: Optional[CampaignContent] # rendered content per platform

    # Review
    review_result: Optional[ReviewResult]       # review scores and feedback
    revision_count: int                         # number of revision loops done
    max_revisions: int                          # max allowed (default 2)

    # Trace
    trace: Optional[RunTrace]                   # full run trace

    # Control
    current_node: str                           # which node is currently active
    error: Optional[str]                        # error message if any
```

---

## 5. Node Implementations (src/nodes/)

### 5.1 brief_parser.py — Deterministic, Claude Haiku

```python
"""
Brief Parser Node
- Input: raw_input (natural language)
- Output: CampaignBrief (Pydantic model)
- Model: Claude Haiku (fast, cheap — parsing task)
- Type: Deterministic

Logic:
1. Load prompt template from prompts/v1/brief_parser.md
2. Send raw_input + prompt to Claude Haiku
3. Parse response as CampaignBrief JSON
4. Validate with Pydantic
5. Return updated state with brief

Error handling:
- If parsing fails, retry once with more explicit instructions
- If still fails, set error in state and stop workflow

QUAN TRỌNG: dùng Claude API với tool_use / structured output
để ép model trả đúng CampaignBrief schema.
"""
```

### 5.2 context_builder.py — Deterministic + Knowledge Base

```python
"""
Context Builder Node
- Input: CampaignBrief
- Output: context_pack (dict)
- Model: None (Phase 1) — pure file loading + filtering
- Type: Deterministic

Logic:
1. Đọc brief.brand.voice_profile_id → load voice profile từ voice_profiles/
2. Đọc brief.offer.product_or_service → tìm matching file trong knowledge_base/products/
3. Đọc brief.audience → load relevant persona từ knowledge_base/audience/
4. Đọc brief.channels → load platform rules cho từng channel từ knowledge_base/platforms/
5. Load brand guidelines từ knowledge_base/brand/
6. Load content policies từ knowledge_base/policies/
7. Assemble thành context_pack dict

Source-of-truth hierarchy (priority cao → thấp):
1. User input (brief.additional_context)
2. Brand policies (knowledge_base/policies/)
3. Brand identity (knowledge_base/brand/)
4. Product facts (knowledge_base/products/)
5. Audience personas (knowledge_base/audience/)
6. Platform rules (knowledge_base/platforms/)

Phase 2: thay file loading bằng ChromaDB RAG retrieval với metadata filtering.
"""
```

### 5.3 strategist.py — Agentic, Claude Sonnet

```python
"""
Strategist Node
- Input: CampaignBrief + context_pack
- Output: strategy (string — campaign strategy)
- Model: Claude Sonnet (needs reasoning + creativity)
- Type: Agentic (có thể gọi web search tool)

Logic:
1. Load prompt template from prompts/v1/strategist.md
2. Inject brief + context_pack vào prompt
3. Call Claude Sonnet
4. Output: chiến lược campaign bao gồm:
   - Content pillars (2-3 trụ cột nội dung)
   - Posting approach per platform
   - Tone/angle cho campaign này
   - Suggested content hooks
   - Timing/frequency recommendations
5. Return strategy string

Note: sau node này có HUMAN APPROVAL gate.
LangGraph interrupt() sẽ pause workflow ở đây.
User review strategy qua CLI, approve hoặc reject + feedback.
"""
```

### 5.4 message_architect.py — Agentic, Claude Sonnet

```python
"""
Message Architect Node
- Input: CampaignBrief + context_pack + strategy (approved)
- Output: MasterMessage (Pydantic model)
- Model: Claude Sonnet (needs creativity + structured output)
- Type: Agentic

Logic:
1. Load prompt template from prompts/v1/message_architect.md
2. Inject brief + context + strategy
3. Instruct model to generate MasterMessage (JSON)
4. Parse + validate with Pydantic
5. Return master_message in state

MasterMessage là PLATFORM-AGNOSTIC — không viết cho platform cụ thể nào.
Nó là "bộ xương" mà Channel Renderer sẽ dùng để render native content.

Nội dung MasterMessage:
- core_promise: 1 câu duy nhất — lời hứa cốt lõi
- key_points: 3-5 điểm chính
- emotional_angle: góc cảm xúc
- proof_angle: bằng chứng/social proof
- cta_primary: CTA chính
- taboo_points: điều không được đề cập
- tone_direction: tone cụ thể cho campaign này
"""
```

### 5.5 channel_renderer.py — Agentic, Claude Sonnet

```python
"""
Channel Renderer Node
- Input: CampaignBrief + MasterMessage + context_pack (platform rules + voice profile)
- Output: CampaignContent (list of ContentPiece)
- Model: Claude Sonnet
- Type: Agentic

Logic:
1. Lặp qua brief.channels (hoặc chạy parallel nếu có)
2. Cho mỗi channel:
   a. Load prompt template channel-specific: prompts/v1/channel_renderer_{channel}.md
   b. Inject: MasterMessage + platform rules + voice profile + brief constraints
   c. Call Claude Sonnet
   d. Parse output thành ContentPiece
3. Aggregate thành CampaignContent

ĐẶC BIỆT QUAN TRỌNG — Channel Renderer PHẢI:
- Render content NATIVE cho platform (không phải cắt từ platform khác)
- Apply voice profile (tone, vocabulary, sentence length)
- Loại bỏ AI patterns phổ biến (đừng mở bài "Bạn đã bao giờ...", đừng liệt kê quá đều)
- Tuân thủ platform constraints (character limits, format)

Platform-specific rules (load từ knowledge_base/platforms/):
- Facebook: copy 150-300 từ, narrative style, question CTA, 3-5 hashtags
- Instagram carousel: 5-7 slides, mỗi slide 1 key point, CTA slide cuối, 15-25 hashtags
- Instagram Reels script: 15-30s, hook trong 3s đầu, visual cues
- TikTok script: 15-60s, hook cực mạnh, trending format, text overlay cues

Note: Tích hợp humanize logic VÀO node này, không tách thành node riêng.
"""
```

### 5.6 reviewer.py — Semi-deterministic, Claude Haiku + Rules

```python
"""
Reviewer Node
- Input: CampaignContent + CampaignBrief + context_pack + MasterMessage
- Output: ReviewResult (Pydantic model)
- Model: Claude Haiku (checking task) + rule-based checks
- Type: Semi-deterministic

Logic:
1. Rule-based checks (TRƯỚC KHI gọi LLM):
   - Word count within constraints?
   - Required terms present?
   - Forbidden terms absent?
   - Hashtag count correct?
   - Channel format specs met?

2. LLM-based checks (Claude Haiku):
   - Brand fit: content có đúng giọng thương hiệu? (so sánh với voice profile)
   - Factuality: có bịa product facts? (cross-check với product docs trong context_pack)
   - Channel fit: tone/format có native cho platform? hay giống "AI viết rồi paste"?
   - Business fit: CTA rõ ràng? đúng objective? đúng awareness stage?

3. Scoring:
   - Mỗi dimension: 0.0 → 1.0
   - Pass threshold: brand_fit >= 0.7, factuality >= 0.9, channel_fit >= 0.6, business_fit >= 0.7
   - overall_passed = tất cả dimensions pass

4. Nếu fail:
   - Set revision_instructions cụ thể
   - Workflow loops lại Message Architect (max 2 lần)
   - Revision instructions kèm theo context: dimension nào fail, vì sao, sửa gì
"""
```

### 5.7 formatter.py — Deterministic

```python
"""
Formatter Node
- Input: CampaignContent (reviewed & passed) + RunTrace
- Output: final formatted output
- Model: None
- Type: Deterministic

Logic:
1. Compile mỗi ContentPiece thành readable format
2. Group by channel
3. Thêm metadata: run_id, timestamp, brief summary
4. Output formats:
   - Console: Rich formatted output (tables, panels)
   - JSON: structured output for downstream tools
   - Markdown: human-readable file saved to outputs/
5. Save trace to outputs/{run_id}/trace.json
6. Save content to outputs/{run_id}/content.md
"""
```

---

## 6. Graph Definition (src/graph/workflow.py)

```python
"""
Workflow Definition

Build LangGraph StateGraph:

    brief_parser → context_builder → strategist → [HUMAN APPROVE]
                                                        │
                                                   (approved?)
                                                   /         \
                                                 Yes          No → END
                                                  │
                                          message_architect
                                                  │
                                          channel_renderer
                                                  │
                                             reviewer
                                                  │
                                            (passed?)
                                           /         \
                                         Yes          No → (revision_count < max?)
                                          │                    /          \
                                     formatter              Yes           No → formatter (with warnings)
                                          │                   │
                                        END          message_architect (with feedback)


Key implementation details:
- Dùng StateGraph(CampaignState)
- Human approval: dùng LangGraph interrupt() mechanism
  Khi đến node strategist, sau khi output strategy,
  workflow interrupt để user review qua CLI.
  User input "approve" → set human_approved = True, continue
  User input "reject" hoặc feedback → set human_approved = False, END hoặc re-strategize
- Conditional edges:
  - after strategist: check human_approved
  - after reviewer: check review_result.overall_passed AND revision_count < max_revisions
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver  # in-memory checkpoint for dev

def build_workflow():
    graph = StateGraph(CampaignState)

    # Add nodes
    graph.add_node("brief_parser", brief_parser_node)
    graph.add_node("context_builder", context_builder_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("human_approval", human_approval_node)  # interrupt point
    graph.add_node("message_architect", message_architect_node)
    graph.add_node("channel_renderer", channel_renderer_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("formatter", formatter_node)

    # Set entry point
    graph.set_entry_point("brief_parser")

    # Add edges
    graph.add_edge("brief_parser", "context_builder")
    graph.add_edge("context_builder", "strategist")
    graph.add_edge("strategist", "human_approval")

    # Conditional: human approved?
    graph.add_conditional_edges(
        "human_approval",
        lambda state: "continue" if state["human_approved"] else "end",
        {"continue": "message_architect", "end": END}
    )

    graph.add_edge("message_architect", "channel_renderer")
    graph.add_edge("channel_renderer", "reviewer")

    # Conditional: review passed?
    graph.add_conditional_edges(
        "reviewer",
        route_after_review,  # defined in edges.py
        {
            "passed": "formatter",
            "retry": "message_architect",
            "max_retries": "formatter"  # output anyway with warnings
        }
    )

    graph.add_edge("formatter", END)

    # Compile
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)
```

---

## 7. Prompt Templates (src/prompts/v1/)

### 7.1 brief_parser.md

```markdown
# System Prompt — Brief Parser

Bạn là một Marketing Brief Analyst. Nhiệm vụ: phân tích input tự nhiên từ user
và extract thành structured campaign brief.

## Rules
- Extract MỌI thông tin có trong input
- Nếu thiếu thông tin, dùng giá trị mặc định hợp lý
- Không bịa thông tin không có trong input
- Output PHẢI là JSON hợp lệ theo schema CampaignBrief

## Default Values (khi user không chỉ định)
- goal: "awareness"
- channels: ["facebook", "instagram"]
- deliverables: tùy channels — facebook→["post"], instagram→["carousel","reels_script"]
- awareness_stage: "problem_aware"
- word_limit: null (không giới hạn)
- hashtag_count: null

## Ví dụ
Input: "Viết campaign cho dịch vụ xem tử vi online, target Gen Z quan tâm tâm linh"
Output:
{
  "goal": "awareness",
  "brand": {"name": "", "voice_profile_id": "default", "forbidden_claims": [], "mandatory_terms": []},
  "audience": {
    "persona_description": "Gen Z (18-25) quan tâm tâm linh, tử vi, huyền học",
    "age_range": "18-25",
    "pain_points": ["muốn hiểu bản thân", "tìm định hướng cuộc sống"],
    "awareness_stage": "problem_aware"
  },
  "offer": {
    "product_or_service": "Dịch vụ xem tử vi online",
    "key_message": "Khám phá bản thân qua lá số tử vi",
    "cta": "Đặt lịch xem tử vi",
    "unique_selling_points": []
  },
  "channels": ["facebook", "instagram"],
  "deliverables": ["post", "carousel", "reels_script"],
  "constraints": {},
  "success_criteria": {"tone_match_min": 0.7, "factuality_required": true, "brand_safety_required": true},
  "additional_context": null
}
```

### 7.2 strategist.md

```markdown
# System Prompt — Strategist

Bạn là một Social Media Campaign Strategist chuyên nghiệp.
Nhiệm vụ: dựa trên brief và context, đề xuất chiến lược campaign.

## Input bạn sẽ nhận
- Campaign Brief (JSON)
- Brand Context (guidelines, tone, policies)
- Product/Service Information
- Audience Persona
- Platform Rules

## Output yêu cầu
Viết chiến lược campaign bao gồm:

1. **Campaign Angle**: góc tiếp cận chính — tại sao audience nên quan tâm?
2. **Content Pillars** (2-3 trụ cột): mỗi pillar = 1 góc nội dung khác nhau
3. **Platform Approach**:
   - Mỗi platform: format nào, tone nào, frequency nào
   - Tại sao format đó phù hợp platform đó
4. **Hook Strategy**: 3-5 opening hooks gợi ý (đặc biệt quan trọng cho Reels/TikTok)
5. **CTA Strategy**: CTA chính + CTA biến thể cho từng platform
6. **Tone Direction**: tone cụ thể cho campaign này (không phải tone chung của brand)
7. **Cảnh báo**: những điều cần tránh dựa trên audience + platform

## Rules
- Chiến lược phải SPECIFIC cho brief này, không generic
- Luôn tham chiếu brand guidelines khi đề xuất tone
- Luôn tham chiếu audience pain points khi đề xuất angle
- Nếu có conflict giữa brand policy và trend, ưu tiên brand policy
```

### 7.3 message_architect.md

```markdown
# System Prompt — Message Architect

Bạn là một Marketing Message Architect.
Nhiệm vụ: tạo ra bộ khung message PLATFORM-AGNOSTIC từ strategy đã approved.

## QUAN TRỌNG
- Output KHÔNG phải content cho platform cụ thể nào
- Output là "bộ xương" mà sẽ được render thành content native cho từng platform sau
- Nghĩ như một Creative Director đang brief cho team content

## Output JSON — MasterMessage schema:
{
  "core_promise": "1 câu duy nhất — lời hứa cốt lõi",
  "key_points": ["Điểm 1", "Điểm 2", "Điểm 3"],
  "emotional_angle": "Góc cảm xúc muốn chạm",
  "proof_angle": "Bằng chứng/social proof",
  "cta_primary": "CTA chính",
  "cta_secondary": "CTA phụ (hoặc null)",
  "taboo_points": ["Không đề cập X", "Tránh nói Y"],
  "tone_direction": "Tone cụ thể: ví dụ 'nhẹ nhàng, empathetic, không quá sale-sy'"
}

## Rules
- core_promise phải CỤ THỂ, không generic ("Giải pháp tốt nhất" = BAD)
- key_points tối đa 5, mỗi point phải có substance
- emotional_angle phải match audience awareness stage
- taboo_points phải bao gồm brand forbidden_claims
- KHÔNG viết content, chỉ viết KHUNG
```

### 7.4 channel_renderer_facebook.md

```markdown
# System Prompt — Channel Renderer: Facebook

Bạn là một Facebook Content Creator chuyên nghiệp.
Nhiệm vụ: từ Message Architecture, tạo ra Facebook post native.

## Input
- MasterMessage (JSON)
- Voice Profile (JSON)
- Facebook Platform Rules
- Campaign Brief

## Output — ContentPiece schema

## Facebook Content Rules (2026)
- Độ dài tối ưu: 150-300 từ
- Format: narrative/storytelling, KHÔNG liệt kê bullet points
- Hook: 2 dòng đầu phải gây tò mò (trước nút "Xem thêm")
- CTA: soft, mời gọi chứ không ép
- Hashtags: 3-5, đặt cuối bài
- Emoji: vừa phải, đúng ngữ cảnh, KHÔNG spam

## Voice Profile Integration
- Đọc voice profile và PHẢI tuân thủ:
  - Tone (casual/formal)
  - Sentence length trung bình
  - Từ vựng ưa thích vs từ vựng tránh
  - Cách mở bài đặc trưng
  - Cách CTA đặc trưng

## Anti-AI Patterns — BẮT BUỘC TRÁNH
- KHÔNG mở bài bằng "Bạn đã bao giờ..." hoặc "Trong thế giới hiện đại..."
- KHÔNG dùng "hãy cùng khám phá" quá 1 lần
- KHÔNG liệt kê đều đặn kiểu "Thứ nhất... Thứ hai... Thứ ba..."
- KHÔNG dùng transition quá mượt ("Không chỉ vậy", "Hơn thế nữa", "Đặc biệt hơn")
- KHÔNG kết bài bằng "Hãy bắt đầu hành trình..."
- Viết như NGƯỜI THẬT đang chia sẻ, không như AI đang thuyết trình
```

### 7.5 channel_renderer_instagram.md

```markdown
# System Prompt — Channel Renderer: Instagram Carousel

## Instagram Carousel Rules (2026)
- 5-7 slides (tối ưu engagement)
- Slide 1: HOOK — gây tò mò, có thể dùng câu hỏi hoặc stat gây shock
- Slide 2-5/6: mỗi slide = 1 key point, ngắn gọn, visual-first
- Slide cuối: CTA rõ ràng + save/share prompt
- Mỗi slide: tối đa 30-40 từ
- Caption: 100-150 từ, bổ sung context
- Hashtags: 15-25, mix giữa popular + niche + branded
- Format output:
  [SLIDE 1]
  Text: ...
  Visual direction: ...
  [SLIDE 2]
  ...
  [CAPTION]
  ...
  [HASHTAGS]
  ...

## Voice & Anti-AI: (same rules as Facebook renderer)
```

### 7.6 channel_renderer_tiktok.md

```markdown
# System Prompt — Channel Renderer: TikTok Script

## TikTok Script Rules (2026)
- Độ dài: 15-60 giây
- HOOK trong 3 giây đầu — quyết định sống chết
- Format: conversational, talking-head hoặc text-on-screen
- Ngôn ngữ: casual, đời thường, dùng slang nếu phù hợp audience
- CTA: nhẹ nhàng, thường là "follow để xem thêm" hoặc "comment cho mình biết"
- Trending format: áp dụng nếu phù hợp (storytime, POV, "things I wish I knew")

## Script Format Output:
```
[HOOK - 3s]
(visual cue)
Text/voiceover: ...

[BODY - 20-50s]
(visual cue)
Text/voiceover: ...

[CTA - 5s]
(visual cue)
Text/voiceover: ...

[TEXT OVERLAYS]
- ...

[SUGGESTED SOUND/MUSIC DIRECTION]
- ...

[HASHTAGS]
- ...
```

## ĐẶC BIỆT CHO TIKTOK
- Hook PHẢI gây conflict/curiosity/shock nhẹ
- Ví dụ hooks tốt: "Điều này sẽ thay đổi cách bạn nhìn...", "POV: bạn vừa phát hiện..."
- KHÔNG giảng dạy, KHÔNG thuyết trình — chia sẻ như bạn bè
- Pace nhanh, chuyển ý mỗi 5-10 giây
```

### 7.7 reviewer.md

```markdown
# System Prompt — Reviewer

Bạn là một Marketing Content Reviewer nghiêm khắc.
Nhiệm vụ: đánh giá content theo 4 chiều và cho điểm cụ thể.

## Input
- Content pieces (list)
- Original CampaignBrief
- MasterMessage
- Voice Profile
- Brand/Product Context

## 4 Dimensions — cho điểm từ 0.0 đến 1.0

### 1. Brand Fit (threshold: 0.7)
- Tone có đúng voice profile?
- Từ vựng có đúng brand vocabulary?
- Có vi phạm forbidden_claims?
- Có thiếu mandatory_terms?

### 2. Factuality (threshold: 0.9)
- Có thông tin nào KHÔNG CÓ trong product docs?
- Có số liệu bịa đặt?
- Có claim quá mức?
- Cross-check MỌI claim với context_pack

### 3. Channel Fit (threshold: 0.6)
- Format có đúng platform specs?
- Độ dài có trong phạm vi tối ưu?
- Tone có native cho platform?
- Hook có đủ mạnh (đặc biệt TikTok/Reels)?

### 4. Business Fit (threshold: 0.7)
- CTA có rõ ràng và actionable?
- Có đúng campaign objective (awareness vs conversion)?
- Có match audience awareness stage?
- Key message có được truyền tải?

## Output JSON — ReviewResult schema
Nếu overall fail, PHẢI viết revision_instructions CỤ THỂ:
- Dimension nào fail
- Vì sao fail
- Sửa gì, ở content piece nào
```

---

## 8. CLI Entry Point (cli.py)

```python
"""
CLI Interface
- Dùng Rich library cho formatted output
- Interactive flow:
  1. User nhập campaign request (natural language)
  2. System chạy pipeline
  3. Pause tại human_approval → show strategy → user approve/reject
  4. Continue pipeline
  5. Show final output with review scores
  6. Save to outputs/

Commands:
  python cli.py run "Tạo campaign cho dịch vụ tử vi online target Gen Z"
  python cli.py run --interactive  (interactive mode, hỏi từng bước)
  python cli.py eval              (chạy evaluation trên golden dataset)
  python cli.py analyze-voice     (phân tích sample posts tạo voice profile)

Human approval flow (trong CLI):
  - Print strategy
  - Prompt: "[A]pprove / [R]eject / [F]eedback: "
  - If approve → continue
  - If reject → end
  - If feedback → re-run strategist with feedback
"""
```

---

## 9. Config Files

### 9.1 models.yaml

```yaml
nodes:
  brief_parser:
    model: "claude-haiku-4-5-20251001"
    temperature: 0.1          # low — parsing, deterministic
    max_tokens: 2000

  context_builder:
    model: null                # no LLM call — pure data loading

  strategist:
    model: "claude-sonnet-4-6"
    temperature: 0.7           # moderate — creative but controlled
    max_tokens: 3000

  message_architect:
    model: "claude-sonnet-4-6"
    temperature: 0.6
    max_tokens: 2000

  channel_renderer:
    model: "claude-sonnet-4-6"
    temperature: 0.7           # creative
    max_tokens: 3000

  reviewer:
    model: "claude-haiku-4-5-20251001"
    temperature: 0.1           # strict — evaluation
    max_tokens: 2000
```

### 9.2 platforms.yaml

```yaml
facebook:
  post:
    min_words: 100
    max_words: 400
    optimal_words: 200
    hashtag_count: "3-5"
    format: "narrative"
    hook_position: "first 2 lines (before See More)"
    emoji: "moderate"
    cta_style: "soft invite"
    media: "1 image or video recommended"

instagram:
  carousel:
    slides: "5-7"
    words_per_slide: "20-40"
    caption_words: "100-150"
    hashtag_count: "15-25"
    first_slide: "hook — question or stat"
    last_slide: "CTA + save prompt"
    format: "visual-first, text overlay"

  reels_script:
    duration: "15-30 seconds"
    hook_duration: "3 seconds"
    format: "vertical 9:16"
    caption_words: "50-100"
    hashtag_count: "10-15"
    hook_style: "pattern interrupt, curiosity gap"

tiktok:
  short_video_script:
    duration: "15-60 seconds"
    hook_duration: "3 seconds"
    format: "vertical 9:16"
    tone: "casual, conversational"
    hashtag_count: "3-5"
    text_overlays: true
    pace: "fast, change every 5-10s"
    trending_formats: ["storytime", "POV", "things I wish I knew", "unpopular opinion"]
```

---

## 10. Knowledge Base Templates

### 10.1 knowledge_base/brand/brand_identity.md

```markdown
# Brand Identity

## Brand Name
[Tên thương hiệu của bạn]

## Mission
[Sứ mệnh — 1-2 câu]

## Vision
[Tầm nhìn]

## Unique Selling Proposition (USP)
[Điều gì khiến bạn khác biệt]

## Brand Values
- [Giá trị 1]
- [Giá trị 2]
- [Giá trị 3]

## Brand Personality
[Thương hiệu giống ai? Đặc điểm tính cách]
```

### 10.2 knowledge_base/brand/tone_of_voice.md

```markdown
# Tone of Voice Guidelines

## Overall Tone
[casual/formal/friendly/authoritative/spiritual/...]

## Do's
- [Nên viết kiểu gì]
- [Nên dùng từ gì]

## Don'ts
- [Không viết kiểu gì]
- [Không dùng từ gì]

## Vocabulary Preferences
### Preferred Words/Phrases
- [Từ ưa thích 1]
- [Từ ưa thích 2]

### Avoided Words/Phrases
- [Từ tránh 1]
- [Từ tránh 2]

## Sentence Style
- Average length: [ngắn/trung bình/dài]
- Complexity: [đơn giản/phức tạp]
- Perspective: [ngôi thứ nhất/thứ hai/thứ ba]

## Emoji Usage
[Nhiều/vừa/ít/không dùng]

## Example Posts (Good)
[Paste 3-5 bài post mẫu thể hiện đúng tone]
```

### 10.3 knowledge_base/products/_template.md

```markdown
# [Tên sản phẩm/dịch vụ]

## Mô tả ngắn
[1-2 câu]

## Chi tiết
[Mô tả đầy đủ]

## Đối tượng
[Ai nên dùng]

## Lợi ích chính
- [Lợi ích 1]
- [Lợi ích 2]
- [Lợi ích 3]

## Giá
[Thông tin giá nếu có]

## FAQ
- Q: [Câu hỏi 1]
  A: [Trả lời 1]

## Claims được phép
- [Claim 1]

## Claims KHÔNG được phép
- [Claim cấm 1]
```

---

## 11. Voice Profile Format (voice_profiles/default.json)

```json
{
  "profile_id": "default",
  "created_at": "2026-01-01",
  "analyzed_from": "10 sample posts",
  "tone": {
    "primary": "casual-spiritual",
    "secondary": "empathetic",
    "formality": 0.3
  },
  "writing_style": {
    "avg_sentence_length": 15,
    "avg_paragraph_length": 3,
    "perspective": "first_person_plural",
    "uses_questions": true,
    "question_frequency": "every 3-4 paragraphs"
  },
  "vocabulary": {
    "preferred": ["khám phá", "hành trình", "bản mệnh", "năng lượng"],
    "avoided": ["click ngay", "mua liền", "ưu đãi sốc", "chỉ còn X ngày"],
    "emoji_style": "moderate_meaningful",
    "common_emojis": ["✨", "🌙", "💫"]
  },
  "content_patterns": {
    "opening_hook_style": "question_or_insight",
    "cta_style": "soft_invite",
    "closing_style": "reflective_or_question",
    "storytelling_frequency": "high"
  },
  "anti_ai_rules": [
    "Never start with 'Bạn đã bao giờ'",
    "Never use 'Trong thế giới hiện đại'",
    "Avoid listing more than 3 items with numbers",
    "Avoid smooth transitions like 'Không chỉ vậy', 'Hơn thế nữa'",
    "Never end with 'Hãy bắt đầu hành trình'"
  ]
}
```

---

## 12. Implementation Order

### Phase 1 — Working MVP (target: 2 tuần)

Thứ tự implement:

```
1. Setup project
   - pyproject.toml (dependencies: langgraph, langchain-anthropic, pydantic, rich, pyyaml)
   - .env + config loading
   - Folder structure

2. Pydantic models (src/models/)
   - brief.py → message.py → content.py → review.py → trace.py
   - Test: instantiate mỗi model với sample data

3. Knowledge base
   - Tạo content thật cho knowledge_base/ (brand, 1 product, audience, platforms)
   - Implement knowledge/loader.py (đọc markdown files)

4. Prompt templates
   - Viết tất cả prompts trong prompts/v1/
   - Test: copy prompt + sample input vào Claude chat, xem output có đúng schema

5. Node implementations (từng node một, test riêng trước)
   - brief_parser.py → test với 5 sample inputs
   - context_builder.py → test với sample brief
   - strategist.py → test với sample brief + context
   - message_architect.py → test với sample strategy
   - channel_renderer.py → test với sample MasterMessage (FB + IG)
   - reviewer.py → test với sample content
   - formatter.py → test với sample reviewed content

6. Graph assembly
   - state.py → workflow.py → edges.py
   - Wire up all nodes
   - Test full pipeline end-to-end

7. CLI
   - Basic cli.py với "run" command
   - Human approval prompt
   - Rich formatted output

8. Golden dataset
   - 10 sample briefs
   - Run pipeline, manually review + approve best outputs
   - Save as golden/
```

### Phase 2 — Intelligence Layer (target: 2 tuần thêm)
- ChromaDB RAG thay static file loading
- Voice Analyzer (phân tích sample posts → profile JSON)
- Web search tool cho Strategist
- TikTok channel renderer
- Multi-model optimization

### Phase 3 — Quality & Scale (ongoing)
- Evaluation runner (eval.py)
- Learning memory (track reviewer feedback)
- Streamlit UI
- Content calendar batch generation
- A/B variant generation

---

## 13. Dependencies (pyproject.toml)

```toml
[project]
name = "marketing-agent"
version = "0.1.0"
description = "Marketing Agent Workflow Engine"
requires-python = ">=3.11"

dependencies = [
    "langgraph>=0.4",
    "langchain-anthropic>=0.3",
    "langchain-core>=0.3",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "rich>=13.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
rag = [
    "chromadb>=0.5",
    "langchain-chroma>=0.2",
]
eval = [
    "pandas>=2.0",
]
ui = [
    "streamlit>=1.35",
]

[project.scripts]
marketing-agent = "cli:main"
```

---

## 14. Lưu ý quan trọng khi implement

1. **Mỗi node test riêng trước khi wire vào graph.** Đừng build graph trước rồi test cả pipeline. Test node → test node → test chain 2 node → ... → test full pipeline.

2. **Prompt là thứ quan trọng nhất.** Dành 60% effort vào prompt engineering, 40% code. Code chỉ là plumbing — quality phụ thuộc vào prompt.

3. **Structured output.** Khi gọi Claude API, dùng `tool_use` pattern để ép model trả đúng JSON schema. Không dùng text parsing + regex.

4. **Error handling.** Mỗi node PHẢI có try/except. Nếu LLM trả sai format, retry 1 lần với prompt rõ hơn. Nếu vẫn sai, ghi vào trace và stop.

5. **Cost tracking.** Log token usage cho mỗi LLM call. Tính cost estimate: Haiku ~$0.25/1M input, Sonnet ~$3/1M input.

6. **Knowledge base phải có content thật.** Đừng để placeholder — brand guidelines, product info, audience personas phải là data thật của bạn. Pipeline tốt nhưng data giả = output giả.

7. **Git commit thường xuyên.** Commit sau mỗi node hoạt động. Branch strategy: main (stable) + dev (working).
