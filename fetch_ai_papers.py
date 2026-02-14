#!/usr/bin/env python3
"""
Fetch recent AI research papers from OpenAlex.

1. Search OpenAlex Topics for 'artificial intelligence'
2. Collect topic IDs where the topic's field or subfield display_name is "Artificial intelligence"
3. Filter works on the API by primary_topic.id (only those topic IDs) + last 3 days + type=article
4. Save papers in a timestamped JSON file in temp/
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pyalex import Topics, Works

# Field/subfield display_name must be one of these (OpenAlex uses "Artificial Intelligence")
AI_FIELD_SUBFIELD_DISPLAY_NAMES = {"Artificial intelligence", "Artificial Intelligence"}

# Only fetch works of this type (article = journal articles; None = all types)
# Set to "article" to align with "research" and reduce count vs. preprints/books etc.
WORK_TYPE = "article"


def _short_id(oid: str) -> str:
    """Return short form id for OpenAlex (e.g. 1702 from https://openalex.org/subfields/1702)."""
    if not oid:
        return ""
    return oid.rstrip("/").split("/")[-1] if "/" in str(oid) else str(oid)


def get_ai_topic_ids() -> list[str]:
    """Search topics for AI and return topic IDs whose field or subfield display_name is 'Artificial intelligence' / 'Artificial Intelligence'."""
    topic_ids: list[str] = []
    seen: set[str] = set()
    max_pages = 10

    for i, page in enumerate(Topics().search("artificial intelligence").paginate(per_page=200)):
        if i >= max_pages:
            break
        for topic in page:
            field = topic.get("field") or {}
            subfield = topic.get("subfield") or {}
            fname = (field.get("display_name") or "").strip()
            sname = (subfield.get("display_name") or "").strip()
            if fname not in AI_FIELD_SUBFIELD_DISPLAY_NAMES and sname not in AI_FIELD_SUBFIELD_DISPLAY_NAMES:
                continue
            tid = _short_id(str(topic.get("id", "")))
            if tid and tid not in seen:
                seen.add(tid)
                topic_ids.append(tid)
    return topic_ids


def main() -> None:
    # 1. Get topic IDs whose field/subfield is "Artificial intelligence"
    print(f"Searching Topics for field/subfield display_name in {AI_FIELD_SUBFIELD_DISPLAY_NAMES}...")
    topic_ids = get_ai_topic_ids()
    if not topic_ids:
        raise RuntimeError(
            f"No topics with field/subfield display_name in {AI_FIELD_SUBFIELD_DISPLAY_NAMES} found. "
            "Try checking OpenAlex topic hierarchy."
        )
    print(f"  AI topic IDs: {len(topic_ids)} topics")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    three_days_ago = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
    print(f"Fetching works with primary_topic.id in AI topics, publication_date {three_days_ago} to {today} (last 3 days)")

    # 2. Single API filter: primary_topic.id in our AI topic list (no over-fetch, no post-filter)
    papers = []
    filter_extra = {"type": WORK_TYPE} if WORK_TYPE else {}
    query = (
        Works()
        .filter(
            primary_topic={"id": "|".join(topic_ids)},
            from_publication_date=three_days_ago,
            to_publication_date=today,
            **filter_extra,
        )
    )
    for page in query.paginate(per_page=200):
        papers.extend(page)
        print(f"  Fetched {len(papers)} papers so far...")

    # Optional: keep only AI topics in each work's topics array (smaller JSON)
    ai_topic_id_set = set(topic_ids)
    for p in papers:
        if "topics" in p and p["topics"]:
            p["topics"] = [t for t in p["topics"] if _short_id(str((t.get("id") or ""))) in ai_topic_id_set]

    print(f"Total papers: {len(papers)}")

    # 3. Save to timestamped JSON in temp/
    temp_dir = Path(__file__).resolve().parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = temp_dir / f"ai_papers_{timestamp}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)

    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
