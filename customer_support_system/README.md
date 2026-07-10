# AI-Powered Customer Support Automation System
### ABC Technologies | Built with LangGraph

---

## Project Overview

This project implements an AI-powered customer support automation system for ABC Technologies using **LangGraph**, **Anthropic Claude**, and **SQLite memory**. The system automatically classifies customer queries, routes them to specialised support agents, retrieves relevant knowledge base context via RAG, maintains conversation history, and escalates high-risk requests to human supervisors.

---

## Architecture

```
Customer Query
      │
      ▼
┌─────────────────┐
│  load_memory    │  ← SQLite: fetch past conversations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ classify_intent │  ← Claude: Sales / Technical / Billing / Account / Memory
└────────┬────────┘
         │
    (conditional routing)
    ┌────┴────────────────────────────────────┐
    ▼        ▼           ▼          ▼         ▼
 [Sales] [Technical] [Billing] [Account] [Memory]
    └────┬────────────────────────────────────┘
         │
    (high-risk check)
    ┌────┴─────────┐
    ▼              ▼
[Human         [Supervisor
 Approval]      Agent]
    │              │
    └──────┬───────┘
           ▼
    [save_memory]  ← SQLite: persist interaction
           │
           ▼
      Final Response
```

---

## Task Completion Summary

| Task | Description | Status |
|------|-------------|--------|
| Task 1 | LangGraph Workflow Design | ✅ `main.py` |
| Task 2 | State Structure | ✅ `state.py` |
| Task 3 | Intent Classification Node | ✅ `agents/department_agents.py` |
| Task 4 | Conditional Routing | ✅ `agents/department_agents.py` |
| Task 5 | Specialized Department Agents (Sales, Technical, Billing, Account) | ✅ `agents/department_agents.py` |
| Task 6 | RAG Pipeline with Knowledge Base Documents | ✅ `rag/retriever.py` |
| Task 7 | SQLite Memory (store & retrieve history) | ✅ `memory/sqlite_memory.py` |
| Task 8 | Human-in-the-Loop Approval | ✅ `agents/supervisor.py` |
| Task 9 | Supervisor Agent (validate & improve responses) | ✅ `agents/supervisor.py` |
| Task 10 | 5 Sample Query Demonstration | ✅ `main.py` (run as `__main__`) |

---

## Project Structure

```
customer_support_system/
├── main.py                     # Task 1: Workflow + Task 10: Demo
├── state.py                    # Task 2: State structure
├── memory.db                   # SQLite database (auto-created)
├── agents/
│   ├── department_agents.py    # Tasks 3, 4, 5
│   └── supervisor.py           # Tasks 8, 9
├── rag/
│   └── retriever.py            # Task 6: RAG pipeline
├── memory/
│   └── sqlite_memory.py        # Task 7: SQLite memory
└── docs/
    ├── company_policy.txt
    ├── pricing_guide.txt
    ├── technical_manual.txt
    └── faq.txt
```

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- An Anthropic API key

### 1. Clone / Unzip the project
```bash
unzip customer_support_system.zip
cd customer_support_system
```

### 2. Create a virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set your Anthropic API key
```bash
export ANTHROPIC_API_KEY="your_api_key_here"   # Linux/Mac
set ANTHROPIC_API_KEY=your_api_key_here         # Windows
```

### 5. Run the demonstration
```bash
python main.py
```

When **Query 4** (refund request) runs, you will be prompted in the terminal to approve or reject it as the human supervisor.

---

## Dependencies

```
langgraph>=0.2
langchain>=0.3
langchain-anthropic>=0.3
langchain-community>=0.3
anthropic>=0.40
```

---

## Knowledge Base Documents

The RAG system uses four documents stored in `/docs`:

| Document | Coverage |
|----------|----------|
| `company_policy.txt` | Refund, cancellation, closure, compensation, escalation, SLA policies |
| `pricing_guide.txt` | Starter, Professional, Business, Enterprise plans and add-ons |
| `technical_manual.txt` | Installation, login, errors, file upload issues, API docs |
| `faq.txt` | Common questions across all departments |

---

## High-Risk Requests (Human-in-the-Loop)

The following request types are automatically flagged and **require human supervisor approval** before a response is sent:

- Refund requests
- Subscription cancellation
- Account closure requests
- Compensation requests
- Escalation to management

---

## Memory System

Customer conversation history is stored in `memory.db` (SQLite). Each interaction is recorded with:
- `customer_id` — unique identifier per customer
- `customer_name` — extracted from conversation
- `role` — `user` or `assistant`
- `message` — full message text
- `intent` — classified intent
- `timestamp` — ISO format timestamp

---

## Sample Output (Query 5 — Memory Recall)

```
Customer: "What was my previous support issue?"
System:   Memory Agent retrieves past interaction from SQLite.
Response: "Based on your conversation history, you previously contacted us about
           a refund request for your annual subscription (Billing department)."
```

---

## Author Notes

- The RAG pipeline uses keyword-based retrieval (TF-IDF scoring) — no external vector database required.
- The human-in-the-loop node simulates supervisor approval via terminal prompt. In production, replace with a webhook/email notification + approval dashboard.
- All LLM calls use `claude-sonnet-4-6` via the Anthropic API.
