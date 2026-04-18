# Marketing Agent Workflow Engine

Multi-step pipeline tạo social media campaign content, powered by LangGraph + Anthropic Claude API.

## Features

- **Workflow-first**: Deterministic pipeline with LLM nodes only where needed
- **Schema-first**: Pydantic typed contracts between all nodes
- **Multi-platform**: Facebook, Instagram, TikTok native content
- **Human-in-the-loop**: Strategy approval gate before content generation
- **4-dimension review**: Brand fit, factuality, channel fit, business fit scoring
- **Full trace**: Every run tracked with token usage and cost estimates

## Tech Stack

- Python 3.11+
- LangGraph (StateGraph, conditional edges, checkpointing)
- LangChain + Anthropic Claude API (Sonnet for generation, Haiku for parsing)
- Pydantic v2 (typed contracts)
- Rich (CLI formatting)

## Setup

```bash
# Clone and enter project
cd marketing-agent

# Install dependencies with uv
uv sync

# Copy env file and add your API key
cp .env.example .env
# Edit .env → add ANTHROPIC_API_KEY

# Run
python cli.py run "Tạo campaign cho dịch vụ tử vi online target Gen Z"
```

## Usage

```bash
# Run with natural language input
python cli.py run "Viết campaign awareness cho app thiền định, target millennials"

# Interactive mode
python cli.py run --interactive

# Evaluate on golden dataset
python cli.py eval

# Analyze sample posts → create voice profile
python cli.py analyze-voice
```

## Pipeline Flow

```
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
                                      Yes          No → retry (max 2x)
                                       │
                                  formatter → END
```

## Project Structure

```
├── src/
│   ├── models/         # Pydantic schemas
│   ├── graph/          # LangGraph workflow
│   ├── nodes/          # Pipeline nodes
│   ├── knowledge/      # Knowledge base loading
│   ├── prompts/v1/     # Prompt templates
│   └── config/         # Settings, model configs
├── knowledge_base/     # Brand, product, audience data
├── voice_profiles/     # Voice profile JSONs
├── datasets/           # Golden & failure test cases
├── outputs/            # Generated campaign outputs
└── cli.py              # Entry point
```
