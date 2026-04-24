<!-- mcp-name: io.github.ABRANJAN07/btp-mcp-server -->

# SAP BTP Services Discovery — MCP Server

A production-ready MCP (Model Context Protocol) server that exposes SAP BTP platform
APIs as tools for any MCP-compatible AI agent — Claude Code, Cursor, Joule Studio,
LangGraph agents, or any other MCP client.

<img width="1382" height="854" alt="image" src="https://github.com/user-attachments/assets/84860cfa-d985-4701-9198-fdb31096aa10" />

> Connect any AI agent to your SAP BTP landscape via the Model Context Protocol.

[![PyPI version](https://img.shields.io/pypi/v/btp-mcp-server.svg)](https://pypi.org/project/btp-mcp-server/)
[![Python](https://img.shields.io/pypi/pyversions/btp-mcp-server.svg)](https://pypi.org/project/btp-mcp-server/)
[![MCP](https://img.shields.io/badge/MCP-compatible-blue.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is this?

The **BTP MCP Server** is an open-source [Model Context Protocol](https://modelcontextprotocol.io)
server that connects AI agents to the SAP Business Technology Platform (BTP) APIs.

Instead of switching to BTP Cockpit to answer common developer questions,
you can ask your AI agent directly:

- _"What BTP services are available in my account?"_
- _"Is HANA Cloud already running in my subaccount?"_
- _"I need async messaging in my CAP app — what should I use?"_
- _"What destinations are configured and what authentication do they use?"_

Works with **Claude Code**, **Cursor**, **Joule Studio**, **LangGraph agents**,
and any other MCP-compatible AI client.

---

## Tools

| Tool                    | What it answers                                  |
| ----------------------- | ------------------------------------------------ |
| `list_btp_services`     | What BTP services exist in the global catalog?   |
| `get_btp_service_plans` | What plans does service X have? Are any free?    |
| `list_btp_instances`    | What is running in my subaccount? Is it healthy? |
| `get_btp_destinations`  | What external connections are configured?        |
| `recommend_btp_service` | Given a use case, what service should I use?     |

---

## Installation

```bash
pip install btp-mcp-server
```

---

## Prerequisites

You need a **Service Manager** service key from your BTP subaccount.

**Steps to get one:**

1. Go to BTP Cockpit → your subaccount → **Services → Service Marketplace**
2. Search for **Service Manager** → Create instance with plan `subaccount-admin`
3. Create a **Service Key** on the instance
4. The key JSON contains your credentials — see Configuration below

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env`
and fill in the values from your Service Manager service key:

```bash
# From your Service Manager service key JSON
BTP_CLIENT_ID=your-client-id          # from "clientid"
BTP_CLIENT_SECRET=your-client-secret  # from "clientsecret"
BTP_TOKEN_URL=https://your-subdomain.authentication.us10.hana.ondemand.com/oauth/token
BTP_SM_URL=https://service-manager.cfapps.us10.hana.ondemand.com  # from "sm_url"

# From BTP Cockpit → your subaccount → Overview → "Subaccount ID"
BTP_SUBACCOUNT_ID=your-subaccount-guid

# Destination Service URL (region-specific — adjust region if needed)
BTP_DESTINATION_URL=https://destination.cfapps.us10.hana.ondemand.com

# Optional: cache TTL in seconds (default: 300)
# CACHE_TTL_SECONDS=300
```

> **Note:** Never commit your `.env` file to GitHub.
> Use `.env.example` (with no real values) as a reference template.

---

## Usage

### With Claude Desktop

Add to your `claude_desktop_config.json`:

**Mac:** `~/.claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sap-btp": {
      "command": "btp-mcp-server",
      "env": {
        "BTP_CLIENT_ID": "your-client-id",
        "BTP_CLIENT_SECRET": "your-client-secret",
        "BTP_TOKEN_URL": "https://your-subdomain.authentication.us10.hana.ondemand.com/oauth/token",
        "BTP_SM_URL": "https://service-manager.cfapps.us10.hana.ondemand.com",
        "BTP_SUBACCOUNT_ID": "your-subaccount-guid",
        "BTP_DESTINATION_URL": "https://destination.cfapps.us10.hana.ondemand.com"
      }
    }
  }
}
```

Restart Claude Desktop. Then ask:

- _"What BTP services do I have available?"_
- _"Are there any failed service instances?"_
- _"I need to connect to an on-premise SAP system — what BTP service handles that?"_

---

### With Claude Code / Cursor

```json
{
  "mcpServers": {
    "sap-btp": {
      "command": "btp-mcp-server",
      "env": {
        "BTP_CLIENT_ID": "...",
        "BTP_CLIENT_SECRET": "...",
        "BTP_TOKEN_URL": "...",
        "BTP_SM_URL": "...",
        "BTP_SUBACCOUNT_ID": "..."
      }
    }
  }
}
```

### With a LangGraph agent

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_anthropic import ChatAnthropic

async with MultiServerMCPClient({
    "btp": {
        "command": "btp-mcp-server",
        "transport": "stdio",
        "env": {
            "BTP_CLIENT_ID": "...",
            "BTP_CLIENT_SECRET": "...",
            "BTP_TOKEN_URL": "...",
            "BTP_SM_URL": "...",
            "BTP_SUBACCOUNT_ID": "...",
        }
    }
}) as client:
    tools = client.get_tools()
    agent = create_react_agent(
        ChatAnthropic(model="claude-sonnet-4-6"),
        tools
    )
    result = await agent.ainvoke({
        "messages": [{"role": "user", "content":
            "What BTP services do I have? Is there anything I should use for messaging?"
        }]
    })
```

### With Joule Studio (BTP)

Deploy in HTTP mode and register as a BTP Destination:

```bash
MCP_TRANSPORT=http btp-mcp-server
# Server starts at http://0.0.0.0:8080/mcp
```

Then in BTP Cockpit → Destinations → create a destination pointing to your server URL.
In Joule Studio Agent Builder → Tools → Add MCP Server → select the destination.

---

## Running locally from source

```bash
git clone https://github.com/ABRANJAN07/btp-mcp-server.git
cd btp-mcp-server

pip install -r requirements.txt
cp .env.example .env
# fill in .env with your BTP credentials

# Test BTP connectivity
python test_connection.py

# Start the MCP server
python server.py
```

---

## Running tests

Tests use mocked BTP responses — no real credentials needed.

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Expected output: **17 tests passed**

---

## Project structure

```
btp-mcp-server/
├── server.py              ← MCP server entry point (5 tools)
├── test_connection.py     ← Verify BTP connectivity
├── requirements.txt
├── .env.example           ← Configuration template
├── btp_mcp/
│   ├── config.py          ← Reads .env settings
│   ├── auth.py            ← OAuth2 token management
│   ├── btp_client.py      ← BTP API calls + caching
│   ├── cache.py           ← TTL cache
│   └── models.py          ← Pydantic response models
└── tests/
    └── test_tools.py      ← 17 tests with mocked responses
```

---

## How it works

```
AI Agent (Claude / Cursor / LangGraph)
    │
    │  MCP Protocol (stdio)
    ▼
BTP MCP Server (this package)
    │  OAuth2 client_credentials
    │  + TTL cache (5 min)
    ▼
SAP BTP APIs
  ├── Service Manager API  → service catalog, instances, plans
  └── Destination API      → configured connections
```

**Caching:** BTP API responses are cached for 5 minutes by default.
The service catalog and instance list change rarely — caching keeps
responses fast without sacrificing data freshness.

**Pagination:** All list endpoints fetch every page from BTP, not
just the first 50 results.

---

## Roadmap

This is **Phase 2** of a 6-phase project building toward a full
AI-powered BTP operations platform.

| Phase   | Status     | Description                                            |
| ------- | ---------- | ------------------------------------------------------ |
| Phase 1 | ✅ Done    | BTP auth + 2 tools + local MCP server                  |
| Phase 2 | ✅ Done    | 5 tools + caching + pagination + tests + PyPI          |
| Phase 3 | 🔜 Next    | LangGraph agent + FastAPI streaming + memory           |
| Phase 4 | 📋 Planned | Chainlit prototype → React + UI5 Web Components on BTP |
| Phase 5 | 📋 Planned | Multi-agent supervisor + RAG + proactive alerts        |
| Phase 6 | 📋 Planned | Production hardening + CI/CD + BTP marketplace         |

---

## Coming soon (Phase 3)

- LangGraph ReAct agent with multi-turn conversation memory
- FastAPI SSE streaming endpoint
- Code generation for recommended services
  (CAP binding config, CLI commands, YAML manifests)

---

## Entitlements API (temporarily disabled)

The `get_btp_entitlements` tool requires a separate
**Cloud Management Service** (CIS Central plan) service key.
The code is fully written and commented out — see
`ENTITLEMENTS_SETUP.md` to enable it when ready.

---

## Contributing

Contributions are welcome! Please open an issue first to discuss
what you'd like to change.

```bash
git clone https://github.com/ABRANJAN07/btp-mcp-server.git
cd btp-mcp-server
pip install -r requirements.txt
pytest tests/ -v   # make sure tests pass before submitting a PR
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Author

Built by [Abhijeet Ranjan](https://linkedin.com/in/abhijeet-ranjan-06b58b137/)
as part of a series on AI + SAP BTP integration.

Follow the journey on LinkedIn for Phase 3 updates.
