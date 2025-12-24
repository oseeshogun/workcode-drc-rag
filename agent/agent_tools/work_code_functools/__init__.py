import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from langchain.tools import tool

current_dir = Path(__file__).resolve().parent


def load_data(file_path: os.PathLike | str) -> Dict[str, Any]:
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def _first_key(d: Dict[str, Any]) -> str:
    # data.yaml stores items like: {"title_1": {...}} / {"chapter_1": {...}}
    return next(iter(d.keys()))


def _suffix_number(key: str) -> str:
    # "title_12" -> "12"
    return key.split("_")[-1]


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _format_article_numbers(article_numbers: List[Any]) -> str:
    """
    Format article numbers for LLM-friendly output.
    Example: [1,2,3] -> "1, 2, 3"
    """
    return ", ".join(str(x) for x in article_numbers)


def _collect_articles_from_sections(sections: List[Any]) -> List[Any]:
    articles: List[Any] = []
    for section_item in sections:
        if not isinstance(section_item, dict) or not section_item:
            continue
        section_key = _first_key(section_item)
        section_payload = section_item.get(section_key, {}) or {}
        articles.extend(_as_list(section_payload.get("articles")))
    return articles


@tool("work_code_structure", description="Get the structure of the work code")
def get_work_code_structure() -> List[str]:
    """
    Build a rich natural-language outline for an LLM based on `data.yaml`.

    Includes:
    - Titles (with chapter count or direct article count)
    - Chapters (with article count + explicit article numbers)
    - Sections when present (with article count + explicit article numbers)
    """
    data = load_data(current_dir / "data.yaml")
    titles = _as_list(data.get("titles"))

    outline: List[str] = []

    for title_item in titles:
        if not isinstance(title_item, dict) or not title_item:
            continue

        title_key = _first_key(title_item)
        title_payload = title_item.get(title_key, {}) or {}

        title_index = _suffix_number(title_key)
        title_name = title_payload.get("name", "").strip() or "(sans nom)"

        chapters = _as_list(title_payload.get("chapters"))
        direct_articles = _as_list(title_payload.get("articles"))

        if chapters:
            outline.append(
                f"Titre {title_index} : {title_name}. "
                f"Ce titre contient {len(chapters)} chapitre(s), qui sont :"
            )
        elif direct_articles:
            outline.append(
                f"Titre {title_index} : {title_name}. "
                f"Ce titre ne contient pas de chapitres et contient directement "
                f"{len(direct_articles)} article(s) : {_format_article_numbers(direct_articles)}."
            )
            outline.append("")
            continue
        else:
            outline.append(
                f"Titre {title_index} : {title_name}. "
                f"Ce titre ne contient ni chapitres ni articles listés."
            )
            outline.append("")
            continue

        for chapter_item in chapters:
            if not isinstance(chapter_item, dict) or not chapter_item:
                continue

            chapter_key = _first_key(chapter_item)
            chapter_payload = chapter_item.get(chapter_key, {}) or {}

            chapter_index = _suffix_number(chapter_key)
            chapter_name = chapter_payload.get("name", "").strip() or "(sans nom)"

            sections = _as_list(chapter_payload.get("sections"))
            chapter_articles = _as_list(chapter_payload.get("articles"))

            if sections:
                section_articles = _collect_articles_from_sections(sections)
                outline.append(
                    f"- Chapitre {chapter_index} : {chapter_name}. "
                    f"Ce chapitre contient {len(sections)} section(s). "
                    f"Au total, ces sections contiennent {len(section_articles)} article(s) : "
                    f"{_format_article_numbers(section_articles)}."
                )

                outline.append("  Les sections sont :")
                for section_item in sections:
                    if not isinstance(section_item, dict) or not section_item:
                        continue

                    section_key = _first_key(section_item)
                    section_payload = section_item.get(section_key, {}) or {}

                    section_index = _suffix_number(section_key)
                    section_name = (
                        section_payload.get("name", "").strip() or "(sans nom)"
                    )
                    section_articles_list = _as_list(section_payload.get("articles"))

                    outline.append(
                        f"  - Section {section_index} : {section_name}. "
                        f"Cette section contient {len(section_articles_list)} article(s) : "
                        f"{_format_article_numbers(section_articles_list)}."
                    )
            elif chapter_articles:
                outline.append(
                    f"- Chapitre {chapter_index} : {chapter_name}. "
                    f"Ce chapitre contient {len(chapter_articles)} article(s) : "
                    f"{_format_article_numbers(chapter_articles)}."
                )
            else:
                outline.append(
                    f"- Chapitre {chapter_index} : {chapter_name}. "
                    f"Ce chapitre ne contient ni sections ni articles listés."
                )

        outline.append("")

    return outline or ["(Aucune structure trouvée)"]


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _min_max_int(values: List[Any]) -> Tuple[Optional[int], Optional[int]]:
    ints = [v for v in (_as_int(x) for x in values) if v is not None]
    if not ints:
        return None, None
    return min(ints), max(ints)


def _article_text_by_number(data: Dict[str, Any], article_number: int) -> Optional[str]:
    """
    data.yaml stores the full article texts under `articles` as a list of dicts:
    - article_1: "..."
    - article_2: "..."
    """
    for item in _as_list(data.get("articles")):
        if not isinstance(item, dict) or not item:
            continue
        key = _first_key(item)  # e.g. "article_12"
        if _as_int(_suffix_number(key)) == article_number:
            value = item.get(key)
            return value.strip() if isinstance(value, str) else str(value)
    return None


def _find_article_location(data: Dict[str, Any], article_number: int) -> Dict[str, Any]:
    """
    Returns structural context for the given article number:
    - title / chapter / section names (when applicable)
    - lists of articles in that container
    - useful counts and ranges
    """
    titles = _as_list(data.get("titles"))

    for title_item in titles:
        if not isinstance(title_item, dict) or not title_item:
            continue

        title_key = _first_key(title_item)
        title_payload = title_item.get(title_key, {}) or {}

        title_index = _suffix_number(title_key)
        title_name = (title_payload.get("name", "") or "").strip() or "(sans nom)"

        # Some titles have direct articles
        direct_articles = _as_list(title_payload.get("articles"))
        if article_number in {
            x for x in (_as_int(a) for a in direct_articles) if x is not None
        }:
            tmin, tmax = _min_max_int(direct_articles)
            return {
                "title": {"index": title_index, "name": title_name},
                "chapter": None,
                "section": None,
                "container_articles": direct_articles,
                "container_counts": {
                    "articles_count": len(direct_articles),
                    "articles_range": [tmin, tmax],
                },
            }

        chapters = _as_list(title_payload.get("chapters"))
        for chapter_item in chapters:
            if not isinstance(chapter_item, dict) or not chapter_item:
                continue

            chapter_key = _first_key(chapter_item)
            chapter_payload = chapter_item.get(chapter_key, {}) or {}

            chapter_index = _suffix_number(chapter_key)
            chapter_name = (
                chapter_payload.get("name", "") or ""
            ).strip() or "(sans nom)"

            # Chapter can have direct articles
            chapter_articles = _as_list(chapter_payload.get("articles"))
            if article_number in {
                x for x in (_as_int(a) for a in chapter_articles) if x is not None
            }:
                cmin, cmax = _min_max_int(chapter_articles)
                return {
                    "title": {"index": title_index, "name": title_name},
                    "chapter": {"index": chapter_index, "name": chapter_name},
                    "section": None,
                    "container_articles": chapter_articles,
                    "container_counts": {
                        "articles_count": len(chapter_articles),
                        "articles_range": [cmin, cmax],
                    },
                }

            # Or via sections
            sections = _as_list(chapter_payload.get("sections"))
            for section_item in sections:
                if not isinstance(section_item, dict) or not section_item:
                    continue

                section_key = _first_key(section_item)
                section_payload = section_item.get(section_key, {}) or {}

                section_index = _suffix_number(section_key)
                section_name = (
                    section_payload.get("name", "") or ""
                ).strip() or "(sans nom)"

                section_articles = _as_list(section_payload.get("articles"))
                if article_number in {
                    x for x in (_as_int(a) for a in section_articles) if x is not None
                }:
                    smin, smax = _min_max_int(section_articles)
                    return {
                        "title": {"index": title_index, "name": title_name},
                        "chapter": {"index": chapter_index, "name": chapter_name},
                        "section": {"index": section_index, "name": section_name},
                        "container_articles": section_articles,
                        "container_counts": {
                            "articles_count": len(section_articles),
                            "articles_range": [smin, smax],
                        },
                    }

    return {
        "title": None,
        "chapter": None,
        "section": None,
        "container_articles": [],
        "container_counts": {"articles_count": 0, "articles_range": [None, None]},
    }


@tool(
    "get_article_by_number",
    description=(
        "Retrieve a Code du Travail article by its number, including its full text and "
        "structural context (title/chapter/section) from data.yaml."
    ),
)
def get_article_by_number(article_number: int) -> str:
    data = load_data(current_dir / "data.yaml")

    n = _as_int(article_number)
    if n is None or n <= 0:
        return "Invalid article_number: expected a positive integer."

    text = _article_text_by_number(data, n)
    if not text:
        return f"Article {n} not found in data.yaml."

    location = _find_article_location(data, n)

    # Build an LLM-friendly response
    parts: List[str] = []
    parts.append(f"Article {n}")
    parts.append("")
    parts.append("Texte :")
    parts.append(text)
    parts.append("")

    title = location.get("title")
    chapter = location.get("chapter")
    section = location.get("section")

    parts.append("Contexte (structure) :")
    if title:
        parts.append(f"- Titre {title['index']} : {title['name']}")
    if chapter:
        parts.append(f"- Chapitre {chapter['index']} : {chapter['name']}")
    if section:
        parts.append(f"- Section {section['index']} : {section['name']}")

    container_articles = location.get("container_articles") or []
    counts = location.get("container_counts") or {}
    rng = counts.get("articles_range") or [None, None]

    if container_articles:
        parts.append(
            f"- Le même bloc contient {counts.get('articles_count', len(container_articles))} article(s) "
            f"(plage {rng[0]} à {rng[1]}) : {_format_article_numbers(container_articles)}."
        )

    return "\n".join(parts)
