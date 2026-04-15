# LinkedIn Search MCP Server

An MCP (Model Context Protocol) server that lets Claude search LinkedIn for
people, companies, and job postings — and fetch rich profile data.

## Features

| Tool | Description |
|---|---|
| `search_linkedin_people` | Search professionals by name, title, company, school, or location |
| `search_linkedin_companies` | Search companies by name, industry, or location |
| `search_linkedin_jobs` | Search job postings by title, skills, location, and recency |
| `get_linkedin_profile` | Fetch detailed profile data for a given LinkedIn URL |

## Requirements

- Python 3.10+
- [SerpAPI](https://serpapi.com/) key (for people/company/job search — free tier available)
- [Proxycurl](https://nubela.co/proxycurl/) key *(optional — only for `get_linkedin_profile`)*

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and set SERPAPI_KEY (and optionally PROXYCURL_KEY)
```

### 3. Connect to Claude

Add the server to your Claude Desktop config
(`~/.claude/claude_desktop_config.json` on macOS/Linux,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "linkedin-search": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

Restart Claude Desktop. The LinkedIn search tools will appear automatically.

### 4. Use from Claude Code CLI

```bash
claude --mcp-config '{"mcpServers":{"linkedin-search":{"command":"python","args":["-m","src.server"],"cwd":"."}}}'
```

## Example Prompts

Once connected, you can ask Claude things like:

- *"Search LinkedIn for machine learning engineers in London at DeepMind"*
- *"Find fintech companies headquartered in Singapore on LinkedIn"*
- *"Search for senior product manager jobs posted this week in New York"*
- *"Get the LinkedIn profile details for https://www.linkedin.com/in/satyanadella/"*

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   └── server.py        # MCP server with all 4 tools
├── .env.example         # Template for API keys
├── .gitignore
├── requirements.txt
└── readme.md
```

## How It Works

- **People / company / job search** — sends a `site:linkedin.com/...` Google
  search via SerpAPI and returns the organic results.
- **Profile lookup** — calls the Proxycurl API with the LinkedIn URL and
  returns a structured summary (name, headline, experience, education, skills).

## API Key Notes

| Service | Free Tier | Docs |
|---|---|---|
| SerpAPI | 100 searches/month | https://serpapi.com/manage-api-key |
| Proxycurl | 10 credits free | https://nubela.co/proxycurl/dashboard |
