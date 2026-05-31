"""LangGraph StateGraph orchestrating all recon sources in parallel."""
from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agent.recon.sources.company import scrape_company
from agent.recon.sources.github import scrape_github
from agent.recon.sources.instagram import scrape_instagram
from agent.recon.sources.linkedin import scrape_linkedin
from agent.recon.sources.reddit import scrape_reddit
from agent.recon.sources.twitter import scrape_twitter
from agent.recon.sources.web import scrape_web
from agent.synthesizer.document_agent import build_person_profile
from agent.synthesizer.synthesizer import synthesize

logger = logging.getLogger(__name__)

_FRESHNESS_DAYS = 7


class ReconState(TypedDict):
    name: str
    company: str
    role: str
    event_name: str
    linkedin_url: str | None
    twitter_handle: str | None
    github_handle: str | None
    instagram_handle: str | None
    existing_recon: dict[str, Any]
    raw_sources: dict[str, Any]
    synthesis: dict[str, Any]
    profile: dict[str, Any]


def _is_fresh(existing_recon: dict[str, Any], source: str) -> bool:
    src = existing_recon.get(source, {})
    if not src:
        return False
    scraped_at = src.get("scraped_at")
    if not scraped_at:
        return False
    try:
        ts = datetime.datetime.fromisoformat(scraped_at)
        return (datetime.datetime.utcnow() - ts).days < _FRESHNESS_DAYS
    except Exception:
        return False


async def _node_web(state: ReconState) -> dict:
    if _is_fresh(state["existing_recon"], "web"):
        logger.info("web: fresh, skipping")
        return {"raw_sources": {**state["raw_sources"], "web": state["existing_recon"]["web"]["data"]}}

    data = await scrape_web(state["name"], state["company"])
    return {"raw_sources": {**state["raw_sources"], "web": data}}


async def _node_parallel_scrapers(state: ReconState) -> dict:
    sources = state["raw_sources"]
    web = sources.get("web", {})

    li_url = state["linkedin_url"] or web.get("linkedin_url")
    tw = state["twitter_handle"] or web.get("twitter_handle")
    gh = state["github_handle"] or web.get("github_handle")
    ig = state["instagram_handle"]

    logger.info(f"handles — linkedin={li_url} twitter={tw} github={gh}")

    tasks = {
        "linkedin": scrape_linkedin(li_url, state["name"]),
        "twitter": scrape_twitter(tw),
        "github": scrape_github(gh, state["name"]),
        "instagram": scrape_instagram(ig, state["name"]),
        "reddit": scrape_reddit(state["name"], state["company"]),
        "company": scrape_company(state["company"]),
    }

    skip: dict[str, Any] = {}
    run: dict[str, Any] = {}
    for key, coro in tasks.items():
        if _is_fresh(state["existing_recon"], key):
            logger.info(f"{key}: fresh, skipping")
            skip[key] = state["existing_recon"][key]["data"]
        else:
            run[key] = coro

    results = {}
    if run:
        gathered = await asyncio.gather(*run.values(), return_exceptions=True)
        for key, res in zip(run.keys(), gathered):
            if isinstance(res, Exception):
                logger.warning(f"{key} scraper raised: {res}")
                results[key] = {}
            else:
                results[key] = res

    return {"raw_sources": {**sources, **skip, **results}}


async def _node_synthesize(state: ReconState) -> dict:
    synthesis = await synthesize(
        name=state["name"],
        company=state["company"],
        role=state["role"],
        raw_data=state["raw_sources"],
    )
    return {"synthesis": synthesis}


def _node_build_profile(state: ReconState) -> dict:
    profile = build_person_profile(
        name=state["name"],
        company=state["company"],
        role=state["role"],
        event_name=state["event_name"],
        raw_sources=state["raw_sources"],
        synthesis=state["synthesis"],
    )
    return {"profile": profile}


def _build_graph() -> Any:
    g = StateGraph(ReconState)

    g.add_node("web", _node_web)
    g.add_node("scrapers", _node_parallel_scrapers)
    g.add_node("synthesize", _node_synthesize)
    g.add_node("build_profile", _node_build_profile)

    g.set_entry_point("web")
    g.add_edge("web", "scrapers")
    g.add_edge("scrapers", "synthesize")
    g.add_edge("synthesize", "build_profile")
    g.add_edge("build_profile", END)

    return g.compile()


_graph = _build_graph()


async def run_recon(
    *,
    name: str,
    company: str,
    role: str = "",
    event_name: str = "",
    linkedin_url: str | None = None,
    twitter_handle: str | None = None,
    github_handle: str | None = None,
    instagram_handle: str | None = None,
    existing_recon: dict[str, Any] | None = None,
) -> dict[str, Any]:
    initial: ReconState = {
        "name": name,
        "company": company,
        "role": role,
        "event_name": event_name,
        "linkedin_url": linkedin_url,
        "twitter_handle": twitter_handle,
        "github_handle": github_handle,
        "instagram_handle": instagram_handle,
        "existing_recon": existing_recon or {},
        "raw_sources": {},
        "synthesis": {},
        "profile": {},
    }

    final_state = await _graph.ainvoke(initial)
    return final_state["profile"]
