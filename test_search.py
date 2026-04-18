#!/usr/bin/env python3
"""
Quick smoke-test for the LinkedIn Search MCP server.
Run this to confirm your li_at cookie works before connecting Claude Desktop.

Usage:
    python test_search.py
    python test_search.py "data scientist"          # custom query
    python test_search.py "engineer" --company Google
"""

import argparse
import os
import sys
from pathlib import Path


def load_env():
    """Load .env without requiring python-dotenv."""
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("ERROR: .env not found. Run: python setup.py")
        sys.exit(1)
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    parser = argparse.ArgumentParser(description="Test LinkedIn search")
    parser.add_argument("query", nargs="?", default="machine learning engineer")
    parser.add_argument("--company", default="", help="Filter by company")
    parser.add_argument("--title",   default="", help="Filter by title")
    parser.add_argument("--jobs",    action="store_true", help="Search jobs instead")
    parser.add_argument("--limit",   type=int, default=5)
    args = parser.parse_args()

    load_env()
    cookie = os.environ.get("LINKEDIN_COOKIE", "")
    if not cookie:
        print("ERROR: LINKEDIN_COOKIE not set in .env")
        sys.exit(1)

    print(f"Connecting to LinkedIn …  (cookie: {cookie[:20]}…)")
    try:
        import requests
        from linkedin_api import Linkedin

        # Build a proper RequestsCookieJar with li_at + JSESSIONID.
        # linkedin-api does session.cookies = cookies (not .update()), so it
        # must be a CookieJar — a plain dict causes AttributeError downstream.
        s = requests.Session()
        s.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
        s.cookies.set("li_at", cookie, domain=".linkedin.com")
        s.get("https://www.linkedin.com/feed/", allow_redirects=True)
        jsessionid = s.cookies.get("JSESSIONID", "")
        if jsessionid:
            print(f"  JSESSIONID obtained: {jsessionid[:20]}…")

        api = Linkedin("", "", cookies=s.cookies)
        print("Connected.\n")
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    if args.jobs:
        print(f"Searching jobs: '{args.query}'\n{'─'*50}")
        results = api.search_jobs(keywords=args.query, limit=args.limit)
        if not results:
            print("No jobs found.")
            return
        for i, job in enumerate(results, 1):
            job_id = (job.get("entityUrn") or "").split(":")[-1]
            title = job.get("title", "")
            loc = job.get("formattedLocation", "")
            url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            print(f"{i}. {title}  —  {loc}\n   {url}\n")
    else:
        print(f"Searching people: '{args.query}'"
              + (f"  @ {args.company}" if args.company else "")
              + f"\n{'─'*50}")
        kwargs = {"limit": args.limit}
        if args.company:
            kwargs["keyword_company"] = args.company
        if args.title:
            kwargs["keyword_title"] = args.title

        results = api.search_people(keywords=args.query, **kwargs)
        if not results:
            print("No results found.")
            return

        for i, p in enumerate(results, 1):
            name     = p.get("name", "")
            jobtitle = p.get("jobtitle", "")
            location = p.get("location", "")
            distance = p.get("distance", "").replace("DISTANCE_", "") + "nd degree" if p.get("distance") else ""
            print(f"{i}. {name}\n   {jobtitle}\n   {location}  ·  {distance}\n")


if __name__ == "__main__":
    main()
