# Marketing Agent — Deploy lên Railway (Step-by-step)

## Tổng quan

Deploy cả FastAPI backend + React frontend lên Railway.
Kết quả: 1 link cố định dạng `https://marketing-agent-xxx.up.railway.app` gửi cho bạn bè test.

Railway free tier: $5 credit/tháng — đủ cho 2-3 người dùng nhẹ.

---

## Chuẩn bị trước

### 1. Tạo tài khoản Railway
- Vào https://railway.com
- Đăng ký bằng GitHub (recommend — sẽ auto-connect repo)

### 2. Push code lên GitHub
Nếu chưa có repo trên GitHub:
```bash
cd marketing-agent
git init
git add .
git commit -m "Initial commit"

# Tạo repo trên GitHub, rồi:
git remote add origin https://github.com/<your-username>/marketing-agent.git
git branch -M main
git push -u origin main
```

**QUAN TRỌNG:** Đảm bảo `.env` nằm trong `.gitignore` — KHÔNG push API key lên GitHub.

### 3. Restructure project cho deployment

Hiện tại project có thể đang tách `web/` (React) riêng. Cần đảm bảo structure như sau:

```
marketing-agent/
├── api/                    # FastAPI backend
│   ├── main.py
│   ├── routes/
│   ├── schemas.py
│   └── pipeline_runner.py
├── web/                    # React frontend
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   └── dist/               # build output (sau npm run build)
├── src/                    # Existing pipeline code
├── knowledge_base/
├── voice_profiles/
├── requirements.txt        # NEW — cho Railway
├── Procfile                # NEW — cho Railway
├── Dockerfile              # NEW (optional) — nếu muốn Docker deploy
├── pyproject.toml
└── .gitignore
```

---

## Option A: Deploy đơn giản — Serve tất cả từ FastAPI (RECOMMEND)

Cách đơn giản nhất: build React thành static files, serve từ FastAPI. Chỉ cần deploy 1 service.

### Step 1: Build React frontend

```bash
cd web
npm run build
# Output vào web/dist/
```

### Step 2: Thêm static file serving vào FastAPI

Sửa `api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Marketing Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
from api.routes.campaign import router as campaign_router
from api.routes.knowledge import router as knowledge_router

app.include_router(campaign_router, prefix="/api/campaigns", tags=["campaigns"])
app.include_router(knowledge_router, prefix="/api/knowledge", tags=["knowledge"])

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Serve React static files
DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"

if DIST_DIR.exists():
    # Serve static assets (js, css, images)
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    # Catch-all: serve index.html for any non-API route (SPA routing)
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = DIST_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DIST_DIR / "index.html")
```

### Step 3: Update React API client cho production

Sửa `web/src/api/client.js`:

```javascript
import axios from 'axios';

// In production, API is on same domain (served by FastAPI)
// In development, API is on localhost:8000
const baseURL = import.meta.env.DEV
  ? 'http://localhost:8000/api'
  : '/api';

const api = axios.create({
  baseURL,
  timeout: 120000,
});

// ... rest of file unchanged
```

### Step 4: Tạo requirements.txt

```bash
cd marketing-agent

# Generate từ pyproject.toml
pip freeze > requirements.txt

# Hoặc tạo manual — chỉ cần những packages thực sự dùng:
```

Nội dung `requirements.txt`:
```
fastapi>=0.110
uvicorn>=0.27
langgraph>=0.4
langchain-anthropic>=0.3
langchain-core>=0.3
pydantic>=2.0
pyyaml>=6.0
rich>=13.0
python-dotenv>=1.0
```

### Step 5: Tạo Procfile

File `Procfile` (không có extension, đặt ở root):
```
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

### Step 6: Tạo railway.toml (optional nhưng recommended)

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/health"
healthcheckTimeout = 300
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3

[service]
internalPort = 8000
```

### Step 7: Tạo nixpacks.toml (cho Railway build)

```toml
[phases.setup]
nixPkgs = ["python311", "nodejs_20"]

[phases.build]
cmds = [
    "cd web && npm install && npm run build",
    "pip install -r requirements.txt",
]
```

### Step 8: Commit và push

```bash
# Build React trước
cd web && npm run build && cd ..

# Commit
git add .
git commit -m "Add deployment config"
git push origin main
```

### Step 9: Deploy trên Railway

1. Vào https://railway.com/dashboard
2. Click **"New Project"**
3. Chọn **"Deploy from GitHub repo"**
4. Chọn repo `marketing-agent`
5. Railway sẽ auto-detect và bắt đầu build

### Step 10: Set Environment Variables

Trong Railway dashboard, vào service vừa tạo:

1. Click tab **"Variables"**
2. Click **"+ New Variable"**
3. Thêm:
   ```
   ANTHROPIC_API_KEY = sk-ant-api03-your-actual-key-here
   PORT = 8000
   PYTHON_VERSION = 3.11
   ```

### Step 11: Generate Domain

1. Trong Railway dashboard, vào tab **"Settings"**
2. Scroll xuống **"Networking"** → **"Generate Domain"**
3. Railway sẽ tạo URL dạng: `https://marketing-agent-production-xxxx.up.railway.app`
4. Gửi link này cho bạn bè

### Step 12: Verify

Mở browser:
- `https://your-app.up.railway.app` → React UI
- `https://your-app.up.railway.app/api/health` → `{"status": "ok"}`
- `https://your-app.up.railway.app/api/docs` → Swagger UI

---

## Troubleshooting

### Build fail — "Module not found"
- Check `requirements.txt` có đủ packages
- Check path imports đúng (Railway chạy từ root folder)

### API timeout
- LLM calls mất 10-30 giây mỗi node, full pipeline có thể mất 2-3 phút
- Railway free tier có timeout 5 phút — đủ
- Nếu timeout, tăng `healthcheckTimeout` trong `railway.toml`

### CORS error
- Đảm bảo `allow_origins=["*"]` trong FastAPI CORS middleware
- Với Option A (serve tất cả từ FastAPI), CORS không phải vấn đề vì same-origin

### Không tìm thấy knowledge_base
- Railway copy toàn bộ repo lên, bao gồm `knowledge_base/` và `voice_profiles/`
- Check path trong `settings.py` dùng relative path từ `__file__`, không hardcode

### outputs/ folder không writable
- Railway filesystem là ephemeral — mỗi lần redeploy sẽ mất outputs cũ
- Với mục đích test thì OK
- Nếu cần persist, dùng Railway Volume hoặc external storage (Phase 2)

---

## Chi phí

- **Railway**: $5 free credit/tháng. Với 2-3 người dùng nhẹ, đủ ~500 giờ uptime hoặc ~100 builds.
- **Anthropic API**: ~$0.05-0.15 mỗi lần chạy pipeline. 50 lần chạy ≈ $5-7.
- **Tổng/tháng**: $5-12 cho test nhẹ.

## Lưu ý bảo mật

- API key chỉ nằm trong Railway Variables — KHÔNG trong code
- Bất kỳ ai có link đều có thể dùng → tốn API credit của bạn
- Nếu muốn giới hạn, thêm basic auth vào FastAPI:

```python
# Simple password protection
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os

security = HTTPBasic()

def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = os.getenv("APP_PASSWORD", "test123")
    if credentials.password != correct_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.username

# Apply to all campaign routes:
# router = APIRouter(dependencies=[Depends(verify_password)])
```

Thêm `APP_PASSWORD=your-secret` vào Railway Variables. Khi bạn bè mở link sẽ phải nhập username + password.
