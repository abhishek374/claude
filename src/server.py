"""
LinkedIn Search MCP Server

Uses the linkedin-api package (unofficial LinkedIn internal API) to perform
authenticated searches for people, companies, and jobs — with full behind-login
data access.

Requires LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env.

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

from dotenv import load_dotenv
from linkedin_api import Linkedin
from mcp.server.fastmcp import FastMCP

load_dotenv()

LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

mcp = FastMCP("LinkedIn Search")

# Lazy singleton — created on first tool call so the server starts even if
# credentials are missing (error surfaces at call time, not import time).
_api: Linkedin | None = None


def _get_api() -> Linkedin:
    global _api
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        raise ValueError(
            "LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in your .env file."
        )
    if _api is None:
        _api = Linkedin(LINKEDIN_EMAIL, LINKEDIN_PASSWORD)
    return _api


# ---------------------------------------------------------------------------
# Tool: search_linkedin_people
# ---------------------------------------------------------------------------

@mcp.tool()
def search_linkedin_people(
    query: str,
    current_company: str = "",
    location: str = "",
    title: str = "",
    school: str = "",
    limit: int = 10,
) -> str:
    """
    Search for people / professionals on LinkedIn using authenticated access.

    Args:
        query: Keywords — name, skill, or role (e.g. "machine learning engineer").
        current_company: Filter by current employer (e.g. "Google").
        location: City or region (e.g. "San Francisco").
        title: Filter by job title keyword (e.g. "VP Engineering").
        school: Filter by school/university (e.g. "IIT Bombay").
        limit: Max results to return (default 10).

    Returns:
        Formatted list of matching LinkedIn profiles.
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
        name = f"{p.get('firstName', '')} {p.get('lastName', '')}".strip()
        headline = p.get("headline") or p.get("occupation", "")
        location_str = p.get("subline", {})
        if isinstance(location_str, dict):
            location_str = location_str.get("text", "")
        pub_id = p.get("public_id") or p.get("publicIdentifier", "")
        profile_url = f"https://www.linkedin.com/in/{pub_id}/" if pub_id else ""

        lines.append(
            f"{i}. {name}\n"
            f"   {headline}\n"
            f"   {location_str}\n"
            f"   {profile_url}"
        )

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_linkedin_profile
# ---------------------------------------------------------------------------

@mcp.tool()
def get_linkedin_profile(linkedin_id: str) -> str:
    """
    Fetch full details of a LinkedIn profile.

    Args:
        linkedin_id: LinkedIn public ID from the profile URL
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

    experiences = p.get("experience", [])
    if experiences:
        lines.append("\nExperience:")
        for exp in experiences[:6]:
            company = exp.get("companyName", "")
            title = exp.get("title", "")
            time_period = exp.get("timePeriod", {})
            start = time_period.get("startDate", {})
            end = time_period.get("endDate", {})
            start_str = str(start.get("year", "")) if start else ""
            end_str = str(end.get("year", "")) if end else "Present"
            lines.append(f"  - {title} at {company} ({start_str}–{end_str})")

    educations = p.get("education", [])
    if educations:
        lines.append("\nEducation:")
        for edu in educations[:3]:
            school = edu.get("schoolName", "")
            degree = edu.get("degreeName", "")
            field = edu.get("fieldOfStudy", "")
            lines.append(f"  - {school}: {degree} {field}".strip())

    skills = p.get("skills", [])
    if skills:
        skill_names = [s.get("name", "") for s in skills[:15] if s.get("name")]
        if skill_names:
            lines.append(f"\nSkills: {', '.join(skill_names)}")

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
        date_posted_hours: Only return jobs posted within this many hours
                           (default 168 = 1 week). Use 86400 for last 24h.
        limit: Max results to return (default 10).

    Returns:
        Formatted list of job postings with title, company, location and URL.
    """
    api = _get_api()

    results = api.search_jobs(
        keywords=query,
        location_name=location if location else None,
        listed_at=date_posted_hours * 3600,
        limit=limit,
    )

    if not results:
        return "No jobs found."

    lines = []
    for i, job in enumerate(results[:limit], 1):
        entity = job.get("entityUrn", "")
        job_id = entity.split(":")[-1] if entity else ""

        title = job.get("title", "")
        company = (job.get("companyDetails") or {})
        company_name = ""
        if isinstance(company, dict):
            company_name = (
                company.get("com.linkedin.voyager.jobs.JobPostingCompany", {})
                .get("companyResolutionResult", {})
                .get("name", "")
            )

        loc = job.get("formattedLocation", "")
        job_url = f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id else ""

        lines.append(
            f"{i}. {title}\n"
            f"   Company: {company_name}\n"
            f"   Location: {loc}\n"
            f"   {job_url}"
        )

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
        limit: Max results to return (default 10).

    Returns:
        Formatted list of matching LinkedIn company pages.
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

        lines.append(
            f"{i}. {name}\n"
            f"   Industry: {industry}\n"
            f"   Staff: {staff}\n"
            f"   {url}"
        )

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
