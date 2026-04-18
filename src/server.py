"""
LinkedIn Search MCP Server

Uses the linkedin-api package (unofficial LinkedIn internal API) to perform
authenticated searches for people, companies, and jobs — with full behind-login
data access.

Authentication — set ONE of these in your .env:
  LINKEDIN_COOKIE   li_at cookie value from your browser (recommended)
  LINKEDIN_EMAIL + LINKEDIN_PASSWORD   username/password (blocked on cloud IPs)

NOTE: LinkedIn blocks requests from cloud/datacenter IPs. Run this server on
your local machine where your home IP is not flagged.

Setup (local machine):
    pip install -r requirements.txt
    cp .env.example .env   # fill in LINKEDIN_COOKIE
    python -m src.server

Claude Desktop config (~/.claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "linkedin-search": {
          "command": "python",
          "args": ["-m", "src.server"],
          "cwd": "/absolute/path/to/this/repo"
        }
      }
    }
"""

import os

import requests as _requests
from dotenv import load_dotenv
from linkedin_api import Linkedin
from mcp.server.fastmcp import FastMCP

load_dotenv()

LINKEDIN_COOKIE = os.getenv("LINKEDIN_COOKIE", "")
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

mcp = FastMCP("LinkedIn Search")

_api: Linkedin | None = None


def _build_cookie_jar(li_at: str):
    """Return a RequestsCookieJar with li_at + JSESSIONID fetched from LinkedIn."""
    session = _requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    })
    session.cookies.set("li_at", li_at, domain=".linkedin.com")
    session.get("https://www.linkedin.com/feed/", allow_redirects=True)
    # Return the full RequestsCookieJar — linkedin-api sets session.cookies = cookies
    # directly (not .update()), so it must be a CookieJar, not a plain dict.
    return session.cookies


def _get_api() -> Linkedin:
    """Return a cached Linkedin API instance, authenticating on first call."""
    global _api
    if _api is not None:
        return _api

    if LINKEDIN_COOKIE:
        jar = _build_cookie_jar(LINKEDIN_COOKIE)
        _api = Linkedin("", "", cookies=jar)
    elif LINKEDIN_EMAIL and LINKEDIN_PASSWORD:
        _api = Linkedin(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
    else:
        raise ValueError(
            "Set LINKEDIN_COOKIE (preferred) or LINKEDIN_EMAIL + LINKEDIN_PASSWORD in .env"
        )
    return _api


# ---------------------------------------------------------------------------
# Tool: search_linkedin_people
# ---------------------------------------------------------------------------

@mcp.tool()
def search_linkedin_people(
    query: str,
    current_company: str = "",
    title: str = "",
    school: str = "",
    limit: int = 10,
) -> str:
    """
    Search for people / professionals on LinkedIn.

    Args:
        query: Name, skill, or role keywords (e.g. "machine learning engineer").
        current_company: Filter by current employer (e.g. "Google").
        title: Filter by job title keyword (e.g. "VP Engineering").
        school: Filter by school/university (e.g. "IIT Bombay").
        limit: Max results to return (default 10).

    Returns:
        Numbered list of matching profiles with name, headline, and URL.
    """
    api = _get_api()

    kwargs: dict = {"limit": limit}
    if current_company:
        kwargs["keyword_company"] = current_company
    if title:
        kwargs["keyword_title"] = title
    if school:
        kwargs["keyword_school"] = school

    results = api.search_people(keywords=query, **kwargs)
    if not results:
        return "No results found."

    lines = []
    for i, p in enumerate(results[:limit], 1):
        name = p.get("name", "")
        jobtitle = p.get("jobtitle", "")
        location = p.get("location", "")
        urn_id = p.get("urn_id", "")
        distance = p.get("distance", "").replace("DISTANCE_", "") + "nd degree" if p.get("distance") else ""
        lines.append(f"{i}. {name}\n   {jobtitle}\n   {location}  ·  {distance}\n   urn:{urn_id}")

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_linkedin_profile
# ---------------------------------------------------------------------------

@mcp.tool()
def get_linkedin_profile(linkedin_id: str) -> str:
    """
    Fetch full details of a LinkedIn profile.

    Args:
        linkedin_id: The public ID from the profile URL
                     (e.g. "satyanadella" from linkedin.com/in/satyanadella).

    Returns:
        Full profile: name, headline, summary, experience, education, skills.
    """
    api = _get_api()
    p = api.get_profile(linkedin_id)
    if not p:
        return f"No profile found for '{linkedin_id}'."

    lines = []
    name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
    if name:
        lines.append(f"Name: {name}")
    if p.get("headline"):
        lines.append(f"Headline: {p['headline']}")
    loc = p.get("geoLocationName") or p.get("locationName", "")
    if loc:
        lines.append(f"Location: {loc}")
    if p.get("summary"):
        lines.append(f"\nSummary:\n{p['summary']}")

    for exp in p.get("experience", [])[:6]:
        if not lines or lines[-1] != "\nExperience:":
            lines.append("\nExperience:")
        tp = exp.get("timePeriod", {})
        start = str(tp.get("startDate", {}).get("year", ""))
        end = str(tp.get("endDate", {}).get("year", "")) if tp.get("endDate") else "Present"
        lines.append(f"  - {exp.get('title','')} at {exp.get('companyName','')} ({start}–{end})")

    for edu in p.get("education", [])[:3]:
        if not lines or lines[-1] != "\nEducation:":
            lines.append("\nEducation:")
        lines.append(f"  - {edu.get('schoolName','')}: {edu.get('degreeName','')} {edu.get('fieldOfStudy','')}".strip())

    skills = [s.get("name", "") for s in p.get("skills", [])[:15] if s.get("name")]
    if skills:
        lines.append(f"\nSkills: {', '.join(skills)}")

    lines.append(f"\nProfile URL: https://www.linkedin.com/in/{linkedin_id}/")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: search_linkedin_jobs
# ---------------------------------------------------------------------------

@mcp.tool()
def search_linkedin_jobs(
    query: str,
    location: str = "",
    date_posted_hours: int = 24 * 7,
    limit: int = 10,
) -> str:
    """
    Search for job postings on LinkedIn.

    Args:
        query: Job title or keywords (e.g. "senior python engineer").
        location: City or region (e.g. "London", "Remote").
        date_posted_hours: Jobs posted within this many hours (default 168 = 1 week).
        limit: Max results (default 10).

    Returns:
        Numbered list of job postings with title, company, location, and URL.
    """
    api = _get_api()
    results = api.search_jobs(
        keywords=query,
        location_name=location or None,
        listed_at=date_posted_hours * 3600,
        limit=limit,
    )
    if not results:
        return "No jobs found."

    lines = []
    for i, job in enumerate(results[:limit], 1):
        job_id = (job.get("entityUrn") or "").split(":")[-1]
        title = job.get("title", "")
        company_block = job.get("companyDetails") or {}
        company_name = (
            company_block
            .get("com.linkedin.voyager.jobs.JobPostingCompany", {})
            .get("companyResolutionResult", {})
            .get("name", "")
        )
        loc = job.get("formattedLocation", "")
        url = f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else ""
        lines.append(f"{i}. {title}\n   Company: {company_name}\n   Location: {loc}\n   {url}")

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: search_linkedin_companies
# ---------------------------------------------------------------------------

@mcp.tool()
def search_linkedin_companies(query: str, limit: int = 10) -> str:
    """
    Search for companies on LinkedIn.

    Args:
        query: Company name or keyword (e.g. "fintech startup India").
        limit: Max results (default 10).

    Returns:
        Numbered list of company pages with name, industry, size, and URL.
    """
    api = _get_api()
    results = api.search_companies(keywords=query, limit=limit)
    if not results:
        return "No companies found."

    lines = []
    for i, c in enumerate(results[:limit], 1):
        name = c.get("name", "")
        industry = c.get("industryName") or c.get("industry", "")
        staff = c.get("staffCount", "")
        pub_id = c.get("universalName") or c.get("public_id", "")
        url = f"https://www.linkedin.com/company/{pub_id}/" if pub_id else ""
        lines.append(f"{i}. {name}\n   Industry: {industry}\n   Staff: {staff}\n   {url}")

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
