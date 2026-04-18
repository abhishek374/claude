# LinkedIn Search MCP Server

Connects Claude Desktop to LinkedIn so you can search for people, companies,
and jobs — with full behind-login access — directly from Claude.

> **Important:** LinkedIn blocks requests from cloud/datacenter IPs.
> Run this server on your **local machine** (laptop/desktop).

---

## Quick Setup (3 steps)

### 1. Clone & run the setup script

```bash
git clone https://github.com/abhishek374/claude.git
cd claude
python setup.py
```

The script will:
- Create a virtual environment (`.venv/`)
- Install all dependencies
- Ask for your `li_at` cookie and save it to `.env`
- Auto-write the MCP server entry into your Claude Desktop config

### 2. Get your `li_at` cookie

1. Open **Chrome** and log into [linkedin.com](https://www.linkedin.com)
2. Press **F12** → **Application** tab → **Cookies** → `https://www.linkedin.com`
3. Find the cookie named **`li_at`** and copy its **Value**
4. Paste it when `setup.py` asks

### 3. Test & restart Claude Desktop

```bash
# Verify LinkedIn access works
python test_search.py

# Custom searches
python test_search.py "data scientist" --company Google
python test_search.py "product manager" --title "VP"
python test_search.py "python developer" --jobs
```

Then **quit and reopen Claude Desktop**. The `linkedin-search` server loads automatically.

---

## Using it in Claude

Once connected, just ask Claude naturally:

| Ask Claude | Tool used |
|---|---|
| "Search LinkedIn for ML engineers at Anthropic in London" | `search_linkedin_people` |
| "Find fintech startups headquartered in Singapore" | `search_linkedin_companies` |
| "Search for senior PM jobs posted this week" | `search_linkedin_jobs` |
| "Get the LinkedIn profile for satyanadella" | `get_linkedin_profile` |

---

## Tools

| Tool | Parameters |
|---|---|
| `search_linkedin_people` | `query`, `current_company`, `title`, `school`, `limit` |
| `search_linkedin_companies` | `query`, `limit` |
| `search_linkedin_jobs` | `query`, `location`, `date_posted_hours`, `limit` |
| `get_linkedin_profile` | `linkedin_id` (e.g. `"satyanadella"`) |

---

## Manual Claude Desktop config

If you prefer to configure manually instead of running `setup.py`, add this
to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "linkedin-search": {
      "command": "/absolute/path/to/claude/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/claude"
    }
  }
}
```

---

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   └── server.py       ← MCP server (4 LinkedIn search tools)
├── setup.py            ← one-command local setup
├── test_search.py      ← quick CLI test
├── .env.example        ← template for LINKEDIN_COOKIE
├── requirements.txt
└── readme.md
```

---

## Cookie security note

The `li_at` cookie is your LinkedIn session token — treat it like a password.
It is stored only in your local `.env` file (which is gitignored).
Refresh it by repeating step 2 if it expires (usually after ~1 year).
