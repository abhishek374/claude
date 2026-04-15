"""
LinkedIn Search MCP Server

Exposes LinkedIn search capabilities (people, companies, jobs, profile lookup)
to Claude via the Model Context Protocol (MCP).

Search is powered by SerpAPI (Google-based) and optionally Proxycurl for
rich profile data.

Usage:
    python -m src.server

Claude Desktop config (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "linkedin-search": {
          "command": "python",
          "args": ["-m", "src.server"],
          "cwd": "/path/to/this/repo"
        }
      }
    }
"""

import json
import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
PROXYCURL_KEY = os.getenv("PROXYCURL_KEY", "")
SERPAPI_BASE = "https://serpapi.com/search"
PROXYCURL_BASE = "https://nubela.co/proxycurl/api"

mcp = FastMCP("LinkedIn Search")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_serpapi() -> None:
    if not SERPAPI_KEY:
        raise ValueError(
            "SERPAPI_KEY is not set. Add it to your .env file. "
            "Get a key at https://serpapi.com/"
        )


def _require_proxycurl() -> None:
    if not PROXYCURL_KEY:
        raise ValueError(
            "PROXYCURL_KEY is not set. Add it to your .env file. "
            "Get a key at https://nubela.co/proxycurl/"
        )


def _format_organic_results(data: dict, max_results: int = 10) -> str:
    """Extract and format organic Google search results."""
    results = data.get("organic_results", [])[:max_results]
    if not results:
        return "No results found."

    lines = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "No title")
        link = r.get("link", "")
        snippet = r.get("snippet", "")
        lines.append(f"{i}. {title}\n   {link}\n   {snippet}\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: search_linkedin_people
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_linkedin_people(
    query: str,
    location: str = "",
    current_company: str = "",
    school: str = "",
    limit: int = 10,
) -> str:
    """
    Search for people / professionals on LinkedIn.

    Args:
        query: Name, job title, skill, or any keyword (e.g. "machine learning engineer").
        location: City, region, or country to narrow results (e.g. "San Francisco").
        current_company: Filter by current employer (e.g. "Google").
        school: Filter by school/university attended (e.g. "MIT").
        limit: Maximum number of results to return (1-20, default 10).

    Returns:
        Numbered list of LinkedIn profiles with name, URL, and snippet.
    """
    _require_serpapi()

    limit = max(1, min(limit, 20))

    # Build a targeted Google query restricted to LinkedIn profiles
    parts = [f'site:linkedin.com/in/ {query}']
    if current_company:
        parts.append(f'"{current_company}"')
    if school:
        parts.append(f'"{school}"')
    if location:
        parts.append(location)

    search_q = " ".join(parts)

    params = {
        "engine": "google",
        "q": search_q,
        "num": limit,
        "api_key": SERPAPI_KEY,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(SERPAPI_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    return _format_organic_results(data, limit)


# ---------------------------------------------------------------------------
# Tool: search_linkedin_companies
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_linkedin_companies(
    query: str,
    industry: str = "",
    location: str = "",
    limit: int = 10,
) -> str:
    """
    Search for companies on LinkedIn.

    Args:
        query: Company name or keyword (e.g. "electric vehicles startup").
        industry: Industry vertical to narrow results (e.g. "fintech", "healthcare").
        location: Headquarters location (e.g. "New York").
        limit: Maximum number of results to return (1-20, default 10).

    Returns:
        Numbered list of LinkedIn company pages with name, URL, and snippet.
    """
    _require_serpapi()

    limit = max(1, min(limit, 20))

    parts = [f'site:linkedin.com/company/ {query}']
    if industry:
        parts.append(industry)
    if location:
        parts.append(location)

    search_q = " ".join(parts)

    params = {
        "engine": "google",
        "q": search_q,
        "num": limit,
        "api_key": SERPAPI_KEY,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(SERPAPI_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    return _format_organic_results(data, limit)


# ---------------------------------------------------------------------------
# Tool: search_linkedin_jobs
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_linkedin_jobs(
    query: str,
    location: str = "",
    date_posted: str = "month",
    limit: int = 10,
) -> str:
    """
    Search for job postings on LinkedIn.

    Args:
        query: Job title or skills (e.g. "senior backend engineer python").
        location: City, region, or country (e.g. "Remote", "London").
        date_posted: Recency filter — "day", "week", "month", or "any" (default "month").
        limit: Maximum number of results to return (1-20, default 10).

    Returns:
        Numbered list of LinkedIn job postings with title, company, URL, and snippet.
    """
    _require_serpapi()

    limit = max(1, min(limit, 20))

    parts = [f'site:linkedin.com/jobs/ {query}']
    if location:
        parts.append(location)

    search_q = " ".join(parts)

    # Map date_posted to Google's tbs parameter
    tbs_map = {"day": "qdr:d", "week": "qdr:w", "month": "qdr:m"}
    tbs = tbs_map.get(date_posted, "")

    params: dict = {
        "engine": "google",
        "q": search_q,
        "num": limit,
        "api_key": SERPAPI_KEY,
    }
    if tbs:
        params["tbs"] = tbs

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(SERPAPI_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

    return _format_organic_results(data, limit)


# ---------------------------------------------------------------------------
# Tool: get_linkedin_profile
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_linkedin_profile(linkedin_url: str) -> str:
    """
    Fetch detailed information about a LinkedIn profile.

    Requires PROXYCURL_KEY to be set in .env.

    Args:
        linkedin_url: Full LinkedIn profile URL
                      (e.g. "https://www.linkedin.com/in/satyanadella/").

    Returns:
        Structured profile data including name, headline, summary, experience,
        education, and skills.
    """
    _require_proxycurl()

    params = {
        "url": linkedin_url,
        "fallback_to_cache": "on-error",
        "use_cache": "if-present",
        "skills": "include",
        "inferred_salary": "include",
    }
    headers = {"Authorization": f"Bearer {PROXYCURL_KEY}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{PROXYCURL_BASE}/v2/linkedin",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    # Format the profile into readable text
    lines: list[str] = []

    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    if name:
        lines.append(f"Name: {name}")
    if data.get("headline"):
        lines.append(f"Headline: {data['headline']}")
    if data.get("city") or data.get("country_full_name"):
        location_parts = [data.get("city", ""), data.get("country_full_name", "")]
        lines.append(f"Location: {', '.join(p for p in location_parts if p)}")
    if data.get("summary"):
        lines.append(f"\nSummary:\n{data['summary']}")

    experiences = data.get("experiences", [])
    if experiences:
        lines.append("\nExperience:")
        for exp in experiences[:5]:
            company = exp.get("company", "")
            title = exp.get("title", "")
            starts = exp.get("starts_at", {})
            ends = exp.get("ends_at", {})
            start_str = f"{starts.get('year', '')}" if starts else ""
            end_str = f"{ends.get('year', '')}" if ends else "Present"
            lines.append(f"  - {title} at {company} ({start_str}–{end_str})")

    educations = data.get("education", [])
    if educations:
        lines.append("\nEducation:")
        for edu in educations[:3]:
            school = edu.get("school", "")
            degree = edu.get("degree_name", "")
            field = edu.get("field_of_study", "")
            lines.append(f"  - {school}: {degree} {field}".strip())

    skills = data.get("skills", [])
    if skills:
        lines.append(f"\nSkills: {', '.join(skills[:15])}")

    if data.get("public_identifier"):
        lines.append(
            f"\nProfile URL: https://www.linkedin.com/in/{data['public_identifier']}/"
        )

    return "\n".join(lines) if lines else json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
