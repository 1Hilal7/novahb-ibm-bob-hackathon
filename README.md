# novaHB — Developer Attention Router

> **Route attention, not notifications.**

novaHB is a developer attention-routing system built for the **IBM Bob 2.0 Hackathon**.

Software teams receive many notifications whenever code changes. But being technically related to a file, module, or dependency does not necessarily mean that a developer needs to take action.

novaHB asks a more useful question:

> **Who actually needs attention because of this change?**

For every developer, novaHB produces one of three routing decisions:

- **ACTION** — the developer needs to take action.
- **REVIEW_REQUIRED** — an expert review is required.
- **SILENT** — the developer is technically related, but no action is necessary.

**Silence is a feature.**

---

## Live Demo

**Application:**  
https://novahb.vercel.app

**Backend API:**  
https://novahb-api.onrender.com

> The backend is hosted on Render's free tier, so the first request after a period of inactivity may take longer while the service wakes up.

---

## The Problem

Modern development workflows generate notifications through:

- code ownership
- pull-request reviews
- shared modules
- dependency relationships
- team collaboration tools
- automated alerts

However:

```text
technically related != actually requires action
```

A developer may own or depend on a module while their code already handles the new behavior safely.

Notifying that developer anyway creates:

- notification fatigue
- unnecessary context switching
- review overload
- wasted developer attention

novaHB treats **developer attention as a limited resource**.

---

## The Solution

novaHB analyzes a code change and combines technical impact with developer context.

```text
Git Change
    ↓
Semantic Change Analysis
    ↓
Dependency Analysis
    ↓
Source-Code Safety Analysis
    ↓
Developer Ownership + Expertise + Current Task
    ↓
Attention Routing
```

The final result assigns every developer one of:

```text
ACTION
REVIEW_REQUIRED
SILENT
```

Each routing result explains:

- why the developer is affected or unaffected
- which technical area is involved
- what evidence supports the decision
- what action should be taken when necessary

novaHB also provides contextual questions for developers who inspect an impact decision.

---

## Demo Scenario

The controlled demo changes the shared user model from:

```python
email: str
```

to:

```python
email: str | None
```

The canonical demo commit is:

```text
fafa0ce0
feat: allow nullable user email
```

Although this appears to be a small schema change, its impact differs across the team.

| Developer | Decision | Reason |
|---|---|---|
| Batuhan | **ACTION** | Billing uses `User.email` without a null guard |
| Emre | **REVIEW_REQUIRED** | Responsible for schema migration and backward compatibility |
| Hilal | **SILENT** | Auth already handles nullable email safely |
| Ayşe | **SILENT** | Notifications already handle missing email safely |
| Selin | **SILENT** | No security action is required |
| Mert | **SILENT** | Platform work has no dependency on `User.email` |

### Demo Result

```text
6 developers evaluated
2 attention events
4 developers kept silent
```

Traditional ownership-oriented systems can identify who is related to changed code.

novaHB goes further by asking:

> **Who genuinely needs attention?**

---

## Routing Decisions

### ACTION

The change directly affects the developer's work.

novaHB provides:

- the reason
- technical evidence
- a recommended action

### REVIEW_REQUIRED

The change enters an expert's responsibility area.

The expert can:

- approve the change
- request changes

### SILENT

The developer may still be technically related to the project, but no action is required.

novaHB deliberately avoids creating another unnecessary notification.

---

## Product Views

### Project Focus

The main working interface displays:

- change summary
- affected domains
- affected and safe modules
- developer routing
- recommended actions
- expert-review controls
- contextual developer questions

### Full Network

Shows relationships between:

- the code change
- project modules
- developers
- routing decisions

It provides a wider view of how attention flows through the project.

### 3D Attention Network

The 3D view visualizes the live attention network with depth.

It highlights:

- ACTION developers
- REVIEW_REQUIRED developers
- affected modules
- important relationships

SILENT paths remain visually quieter.

The 3D visualization is used for high-level exploration, while Project Focus contains the detailed assistant and review workflow.

---

## Interactive Developer Assistant

Developers can inspect their routing decision and ask contextual questions.

### ACTION

- What changed in this commit?
- How does this affect me?
- What should I do?
- Is my current work blocked?

### REVIEW_REQUIRED

- What changed in this commit?
- How does this affect me?
- What should I review?
- What could break if this is merged?

### SILENT

- What changed in this commit?
- How does this affect me?
- Do I need to do anything?
- Who is handling this change?

The answers are generated from the current impact report and the developer's routing context.

---

## Architecture

```text
Git Commit / Production Demo Fixture
                │
                ▼
        Git Diff Extraction
         git_analyzer.py
                │
                ▼
      Semantic Change Detection
       semantic_detector.py
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
 Gemini enrichment   Deterministic fallback
        │                │
        └───────┬────────┘
                │
                ▼
       Dependency Analysis
      dependency_analyzer.py
                │
                ▼
      Source Safety Analysis
       relevance_analyzer.py
                │
                ▼
       Developer Context
 ownership + expertise + current task
                │
                ▼
    Deterministic Attention Router
              router.py
                │
      ┌─────────┼──────────────┐
      ▼         ▼              ▼
   ACTION   REVIEW_REQUIRED   SILENT
      │         │              │
      └─────────┴──────┬───────┘
                       │
                       ▼
                 Impact Report
                report_builder.py
                       │
            ┌──────────┼───────────┐
            ▼          ▼           ▼
          REST API   Review   Developer Assistant
                       │
                       ▼
                 React Frontend
```

---

## Deterministic Routing

The final routing decision is intentionally deterministic.

AI semantic enrichment can improve context, but an external LLM is **not allowed to arbitrarily decide who gets notified**.

Example logic:

```text
IF a module is affected
AND the developer's active work overlaps that module
THEN ACTION

IF the change is high-criticality
AND the developer is responsible for the shared schema or migration
THEN REVIEW_REQUIRED

IF a dependent module already handles the changed behavior safely
THEN SILENT

IF the developer has no meaningful dependency, ownership,
task, or expertise relevance
THEN SILENT
```

This keeps the system reproducible even if an external AI service is temporarily unavailable.

---

## Semantic Analysis

novaHB uses a hybrid approach.

### Primary Path

When Gemini is available, the semantic analyzer examines the raw Git diff and identifies:

- the conceptual change
- technical domains
- criticality
- broken behavioral contracts

### Fallback Path

If the LLM is unavailable or times out, novaHB falls back to deterministic analysis based on:

- changed paths
- commit information
- diff signals
- dependency relationships
- source-code analysis

The core routing pipeline continues to work.

---

## IBM Bob Usage

IBM Bob was used as a meaningful development partner during the creation of novaHB.

Bob's planning and agent workflows were used to improve the semantic-analysis pipeline and integrate structured semantic information across the system.

A Bob-assisted development task included:

- planning the semantic-enrichment change
- adding structured `broken_contracts` support
- propagating semantic information through backend models
- integrating the new information into routing explanations
- exposing semantic context to developer questions
- validating the implementation against the test suite

Bob session evidence is stored in:

```text
bob_sessions/
```

The repository contains the actual code produced and refined through those Bob-assisted development sessions.

### Runtime AI vs. IBM Bob

IBM Bob and Gemini have different roles in novaHB:

```text
IBM Bob
→ development, planning, and implementation assistance

Google Gemini
→ optional runtime semantic enrichment

Deterministic novaHB engine
→ final routing logic and fallback behavior
```

This distinction keeps the deployed system reproducible while still using AI where it adds value.

---

## Tech Stack

### Frontend

- React 19
- Vite
- `@xyflow/react`
- Three.js
- `react-force-graph-3d`
- `three-spritetext`

### Backend

- Python
- FastAPI
- Pydantic v2
- Uvicorn
- Python AST
- Git CLI
- JSON-based persistence

### AI

- IBM Bob — development and implementation assistance
- Google Gemini — optional runtime semantic enrichment

### Testing

- pytest
- FastAPI TestClient
- frontend production build validation

### Deployment

- Vercel — frontend
- Render — backend

---

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Backend health check |
| `GET` | `/project` | Project dependency map |
| `GET` | `/developers` | Developer profiles and current tasks |
| `POST` | `/analyze` | Run the complete analysis pipeline |
| `GET` | `/impact/latest` | Retrieve the latest impact report |
| `POST` | `/review/{developer_id}` | Approve or request changes for expert review |
| `GET` | `/notify/{developer_id}` | Get developer-specific contextual questions |
| `POST` | `/notify/{developer_id}/ask` | Answer a selected contextual question |

---

## Impact Report

The frontend and backend communicate through a structured impact report.

Simplified example:

```json
{
  "commit": {
    "id": "fafa0ce0",
    "author": "Batuhan",
    "summary": "feat: allow nullable user email"
  },
  "semantic_change": {
    "summary": "User email changed from required to optional",
    "domains": ["shared-core", "user-model"],
    "criticality": "high",
    "broken_contracts": []
  },
  "affected_modules": [
    {
      "module": "billing",
      "status": "affected"
    },
    {
      "module": "notifications",
      "status": "safe"
    }
  ],
  "routing": [
    {
      "developer_id": "batuhan",
      "decision": "ACTION"
    },
    {
      "developer_id": "emre",
      "decision": "REVIEW_REQUIRED"
    },
    {
      "developer_id": "hilal",
      "decision": "SILENT"
    }
  ]
}
```

---

## Project Structure

```text
novahb-ibm-bob-hackathon/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── git_analyzer.py
│   │   ├── semantic_detector.py
│   │   ├── dependency_analyzer.py
│   │   ├── relevance_analyzer.py
│   │   ├── router.py
│   │   ├── report_builder.py
│   │   ├── question_engine.py
│   │   ├── llm.py
│   │   └── storage.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   └── package.json
│
├── sample_repo/
│   ├── shared/
│   ├── billing/
│   ├── notifications/
│   ├── auth/
│   └── platform/
│
├── config/
│   ├── developers.json
│   └── project_map.json
│
├── data/
│   └── demo_nullable_email.json
│
├── tests/
├── bob_sessions/
├── .env.example
└── README.md
```

---

## Running Locally

### Backend

From the repository root:

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Optional Gemini enrichment can be enabled with a local `.env` file:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.8-flash
```

The core application still works without Gemini through deterministic fallback behavior.

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

For local development, the frontend defaults to:

```text
http://localhost:8000
```

For production:

```env
VITE_API_BASE_URL=https://novahb-api.onrender.com
```

---

## Tests

Final verified backend test result:

```text
41 passed
1 skipped
1 warning
```

Run:

```bash
./backend/.venv/bin/python -m pytest -q
```

Frontend production build:

```bash
cd frontend
npm run build
```

The final production build completes successfully.

---

## Deployment

### Frontend

https://novahb.vercel.app

### Backend

https://novahb-api.onrender.com

---

## Team

### Hilal

- frontend development
- product experience
- visualization
- frontend/backend integration
- IBM Bob semantic-enrichment work
- final product and submission coordination

### Eşref Batuhan Simsar

- backend development
- analysis pipeline
- API implementation
- routing and notification systems
- testing and integration

---

## Product Principle

Most developer tools ask:

> **What is affected?**

novaHB asks:

> **Who actually needs attention — and what should they do?**

# novaHB

**Route attention, not notifications.**
