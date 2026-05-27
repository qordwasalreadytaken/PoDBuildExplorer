"""Build classification summary and HTML generation.

This module builds a page-oriented view on top of the rule-based build classifier.
It does not modify any existing site pages.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

if __package__ in (None, ""):
    current_dir = Path(__file__).resolve().parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    from build_classifier import BuildMatch, classify_character, default_build_definitions
else:
    from .build_classifier import BuildMatch, classify_character, default_build_definitions


CLASS_ORDER = [
    "Amazon",
    "Assassin",
    "Barbarian",
    "Druid",
    "Necromancer",
    "Paladin",
    "Sorceress",
]


def _builds_page_javascript() -> str:
    return """
    <script>
    document.querySelectorAll('.collapsible').forEach(button => {
        button.addEventListener('click', function () {
            this.classList.toggle('active');
            const content = this.nextElementSibling;
            if (!content) return;

            const openIcon = this.querySelector('img.open-icon');
            const closeIcon = this.querySelector('img.close-icon');
            const expand = content.style.display === 'none' || content.style.display === '';

            content.style.display = expand ? 'block' : 'none';
            if (openIcon && closeIcon) {
                openIcon.classList.toggle('hidden', !expand);
                closeIcon.classList.toggle('hidden', expand);
            }
        });
    });

    function scrollWithOffset(element, offset = -50) {
        const y = element.getBoundingClientRect().top + window.pageYOffset + offset;
        window.scrollTo({ top: y, behavior: 'smooth' });
    }

    function expandToAnchor(anchorId) {
        const target = document.getElementById(anchorId);
        if (!target) return;

        const stack = [];
        let current = target;
        while (current) {
            if (current.classList && current.classList.contains('content')) {
                stack.unshift(current);
            }
            current = current.parentElement;
        }

        stack.forEach(content => {
            const button = content.previousElementSibling;
            if (!button || !button.classList.contains('collapsible')) return;

            button.classList.add('active');
            content.style.display = 'block';

            const openIcon = button.querySelector('img.open-icon');
            const closeIcon = button.querySelector('img.close-icon');
            if (openIcon) openIcon.classList.remove('hidden');
            if (closeIcon) closeIcon.classList.add('hidden');
        });

        setTimeout(() => scrollWithOffset(target), 250);
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.anchor-link, a[href^="#"]').forEach(link => {
            link.addEventListener('click', function (event) {
                const href = this.getAttribute('href') || '';
                if (!href.startsWith('#')) return;

                event.preventDefault();
                const anchorId = href.substring(1);
                const fullUrl = `${window.location.origin}${window.location.pathname}#${anchorId}`;

                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(fullUrl).catch(() => {});
                }
                history.pushState(null, '', `#${anchorId}`);
                expandToAnchor(anchorId);
            });
        });

        if (window.location.hash) {
            setTimeout(() => expandToAnchor(window.location.hash.substring(1)), 200);
        }
    });
    </script>
    """


def summarize_builds_by_class(
    all_characters: Sequence[Dict[str, Any]],
    definitions=None,
    minimum_score: float = 0.45,
    overlap_delta: float = 0.08,
    class_order: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Summarize classified builds grouped by class for page rendering."""
    if definitions is None:
        definitions = default_build_definitions()

    ordered_classes = list(class_order or CLASS_ORDER)
    characters_by_class: Dict[str, List[Dict[str, Any]]] = {class_name: [] for class_name in ordered_classes}
    definition_counts = defaultdict(int)
    for definition in definitions:
        definition_counts[definition.class_name] += 1
        if definition.class_name not in characters_by_class:
            characters_by_class[definition.class_name] = []
            ordered_classes.append(definition.class_name)

    for character in all_characters:
        if not isinstance(character, dict):
            continue
        class_name = character.get("Class")
        if class_name in characters_by_class:
            characters_by_class[class_name].append(character)

    class_sections: List[Dict[str, Any]] = []
    unmatched_characters: List[Dict[str, Any]] = []
    for class_name in ordered_classes:
        class_characters = characters_by_class.get(class_name, [])
        build_buckets: Dict[str, Dict[str, Any]] = {}
        matched_character_names = set()
        unmatched_class_characters: List[Dict[str, Any]] = []

        for character in class_characters:
            matches = classify_character(
                character,
                definitions,
                minimum_score=minimum_score,
                overlap_delta=overlap_delta,
            )
            if matches:
                matched_character_names.add(character.get("Name", "Unknown"))
            else:
                unmatched_summary = _unmatched_character_summary(character)
                unmatched_class_characters.append(unmatched_summary)
                unmatched_characters.append(unmatched_summary)

            for match in matches:
                bucket = build_buckets.setdefault(
                    match.build_id,
                    {
                        "build_id": match.build_id,
                        "label": match.label,
                        "family": match.family,
                        "count": 0,
                        "characters": [],
                        "scores": [],
                        "confidence_counts": defaultdict(int),
                    },
                )
                bucket["count"] += 1
                bucket["scores"].append(match.score)
                bucket["confidence_counts"][match.confidence] += 1
                bucket["characters"].append(
                    _character_summary(character, match)
                )

        builds = []
        total_class_characters = len(class_characters)
        for bucket in build_buckets.values():
            characters = sorted(
                bucket["characters"],
                key=lambda item: (-item["score"], -item["level"], item["name"].lower()),
            )
            builds.append(
                {
                    "build_id": bucket["build_id"],
                    "label": bucket["label"],
                    "family": bucket["family"],
                    "count": bucket["count"],
                    "class_percentage": (bucket["count"] / total_class_characters * 100) if total_class_characters else 0.0,
                    "average_score": (sum(bucket["scores"]) / len(bucket["scores"])) if bucket["scores"] else 0.0,
                    "confidence_counts": dict(bucket["confidence_counts"]),
                    "characters": characters,
                }
            )

        builds.sort(key=lambda build: (-build["count"], -build["average_score"], build["label"].lower()))
        unmatched_class_characters.sort(
            key=lambda item: (item["class_name"].lower(), -item["level"], item["name"].lower())
        )

        class_sections.append(
            {
                "class_name": class_name,
                "total_characters": total_class_characters,
                "matched_characters": len(matched_character_names),
                "unmatched_characters": unmatched_class_characters,
                "definition_count": definition_counts[class_name],
                "builds": builds,
            }
        )

    unmatched_characters.sort(
        key=lambda item: (item["class_name"].lower(), -item["level"], item["name"].lower())
    )

    return {
        "class_sections": class_sections,
        "total_characters": sum(section["total_characters"] for section in class_sections),
        "total_build_matches": sum(build["count"] for section in class_sections for build in section["builds"]),
        "unmatched_characters": unmatched_characters,
    }


class BuildsHTMLGenerator:
    """Generate a standalone builds overview page."""

    @staticmethod
    def generate_full_builds_page(summary_data: Dict[str, Any], timestamp: str, is_hardcore: bool = False) -> str:
        mode_title = "Hardcore" if is_hardcore else "Softcore"
        content_html = "".join(
            BuildsHTMLGenerator._generate_class_section(section)
            for section in summary_data.get("class_sections", [])
        )

        overview_html = f"""
        <h1>PoD Build Explorer</h1>
        <h2>{mode_title} Build Matches</h2>
        <p>
            Builds are grouped by class and ordered from most popular to least popular.
            Each build expands to show the character names currently matching that definition.
        </p>
        <div class="fun-facts-row">
            <div class="fun-facts-column">
                <h3>Total Characters Checked: {summary_data.get('total_characters', 0):,}</h3>
            </div>
            <div class="fun-facts-column">
                <h3>Total Build Matches: {summary_data.get('total_build_matches', 0):,}</h3>
            </div>
            <div class="fun-facts-column">
                <h3>Unmatched Characters: {len(summary_data.get('unmatched_characters', [])):,}</h3>
            </div>
        </div>
        """

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PoD Build Explorer</title>
            <link rel="shortcut icon" type="image/x-icon" href="icons/pod.ico">
            <link rel="stylesheet" type="text/css" href="./css/test-css.css">
        </head>
        <body class="special-background">
            <div class="is-clipped">
                <div class="banner" style="top:10px; left:10%; width:80%;">
                    ⚠️ This is a beta version of a better builds finder. Feel free to contribute directly or reach out to Qord with feedback. ⚠️
                </div>

                <div class="main page-intro">
                    {overview_html}
                    <hr>
                    {content_html}
                </div>

                <div class="footer">
                    <p>PoD data current as of {escape(timestamp)}</p>
                </div>
            </div>

            <script src="js/armory-popup.js"></script>
            {_builds_page_javascript()}
        </body>
        </html>
        """

    @staticmethod
    def _generate_class_section(section: Dict[str, Any]) -> str:
        class_slug = _slugify(section["class_name"])
        builds = section.get("builds", [])
        unmatched_characters = section.get("unmatched_characters", [])
        builds_html = "".join(
            BuildsHTMLGenerator._generate_build_block(section["class_name"], build, index)
            for index, build in enumerate(builds, 1)
        ) or "<p>No build definitions are matching this class yet.</p>"
        unmatched_html = BuildsHTMLGenerator._generate_class_unmatched_block(
            section["class_name"],
            unmatched_characters,
        )

        return f"""
        <h2 id="builds-{class_slug}">
            {escape(section['class_name'])}
            <a href="#builds-{class_slug}" class="anchor-link">
                <img src="icons/anchor.png" alt="🔗" class="anchor-icon">
            </a>
        </h2>
        <p>
            {section['matched_characters']:,} of {section['total_characters']:,} characters matched a defined build.
            {section['definition_count']} build definitions currently exist for this class.
        </p>
        {builds_html}
        {unmatched_html}
        <hr>
        """

    @staticmethod
    def _generate_build_block(class_name: str, build: Dict[str, Any], index: int) -> str:
        build_slug = _slugify(f"{class_name}-{build['label']}-{build['build_id']}")
        character_rows = "".join(
            f"""
            <div class="character-info">
                <div class="character-link">
                    <a href="https://beta.pathofdiablo.com/armory?name={escape(character['name'])}" target="_blank">
                        {escape(character['name'])}
                    </a>
                </div>
                <div>Level {character['level']} {escape(class_name)} - {character['confidence']} confidence ({character['score']:.3f})</div>
                <div class="hover-trigger" data-character-name="{escape(character['name'])}"></div>
            </div>
            <div class="character">
                <div class="popup hidden"></div>
            </div>
            """
            for character in build.get("characters", [])
        )

        high_count = build.get("confidence_counts", {}).get("high", 0)
        medium_count = build.get("confidence_counts", {}).get("medium", 0)
        low_count = build.get("confidence_counts", {}).get("low", 0)

        return f"""
        <button type="button" class="collapsible" id="{build_slug}">
            <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
            <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
            <strong>#{index} - {escape(build['label'])}</strong>
            <span style="margin-left: 10px; color: #ccc;">{build['count']} matches ({build['class_percentage']:.1f}% of class)</span>
        </button>
        <div class="content" style="display: none;">
            <div style="margin: 8px 0 14px 0; color: #ccc;">
                <div><strong>Family:</strong> {escape(build['family'])}</div>
                <div><strong>Average score:</strong> {build['average_score']:.3f}</div>
                <div><strong>Confidence mix:</strong> high {high_count}, medium {medium_count}, low {low_count}</div>
            </div>
            {character_rows if character_rows else '<p>No matching characters found.</p>'}
        </div>
        """

    @staticmethod
    def _generate_class_unmatched_block(class_name: str, unmatched_characters: Sequence[Dict[str, Any]]) -> str:
        if not unmatched_characters:
            return ""

        character_rows = "".join(
            f"""
            <div class="character-info">
                <div class="character-link">
                    <a href="https://beta.pathofdiablo.com/armory?name={escape(character['name'])}" target="_blank">
                        {escape(character['name'])}
                    </a>
                </div>
                <div>Level {character['level']} {escape(character['class_name'])} - no build match</div>
                <div class="hover-trigger" data-character-name="{escape(character['name'])}"></div>
            </div>
            <div class="character">
                <div class="popup hidden"></div>
            </div>
            """
            for character in unmatched_characters
        )

        class_slug = _slugify(class_name)

        return f"""
        <button type="button" class="collapsible" id="unmatched-{class_slug}-characters">
            <img src="icons/open.png" alt="Open" class="icon-small open-icon hidden">
            <img src="icons/closed.png" alt="Close" class="icon-small close-icon">
            <strong>Unmatched {escape(class_name)} Characters</strong>
            <span style="margin-left: 10px; color: #ccc;">{len(unmatched_characters):,} characters with no build match</span>
        </button>
        <div class="content" style="display: none;">
            <div style="margin: 8px 0 14px 0; color: #ccc;">
                <div><strong>Sort:</strong> highest level, then name</div>
            </div>
            {character_rows}
        </div>
        """


def generate_builds_page(all_characters, timestamp: Optional[str] = None, is_hardcore: bool = False) -> str:
    """Generate a standalone builds page from classified character data."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary_data = summarize_builds_by_class(all_characters)
    return BuildsHTMLGenerator.generate_full_builds_page(summary_data, timestamp, is_hardcore=is_hardcore)


def _character_summary(character: Dict[str, Any], match: BuildMatch) -> Dict[str, Any]:
    return {
        "name": character.get("Name", "Unknown"),
        "level": int(character.get("Stats", {}).get("Level", 0) or 0),
        "score": match.score,
        "confidence": match.confidence,
    }


def _unmatched_character_summary(character: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": character.get("Name", "Unknown"),
        "class_name": character.get("Class", "Unknown"),
        "level": int(character.get("Stats", {}).get("Level", 0) or 0),
    }


def _slugify(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")


__all__ = [
    "BuildsHTMLGenerator",
    "generate_builds_page",
    "summarize_builds_by_class",
]


def _load_characters_from_json(json_file_path: Path) -> List[Dict[str, Any]]:
    with json_file_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        if "ladder" in payload and isinstance(payload["ladder"], list):
            return payload["ladder"]
        if "characters" in payload and isinstance(payload["characters"], list):
            return payload["characters"]
        raise ValueError(f"Unsupported top-level dict keys: {list(payload)[:10]}")

    if isinstance(payload, list):
        return payload

    raise ValueError(f"Unsupported top-level JSON type: {type(payload).__name__}")


def _default_output_path(input_path: Path, is_hardcore: bool) -> Path:
    if is_hardcore:
        return input_path.parent / "hcBuilds.html"
    return input_path.parent / "Builds.html"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a standalone builds HTML page from ladder JSON data.")
    parser.add_argument(
        "input_json",
        nargs="?",
        default="sc_ladder.json",
        help="Path to the source ladder JSON file. Defaults to sc_ladder.json.",
    )
    parser.add_argument(
        "--output",
        dest="output_html",
        help="Path for the generated HTML file. Defaults to Builds.html or hcBuilds.html next to the input JSON.",
    )
    parser.add_argument(
        "--hc",
        action="store_true",
        help="Render the page in hardcore mode styling and naming.",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input_json).resolve()
    if not input_path.exists():
        print(f"Error: input JSON not found: {input_path}")
        return 1

    is_hardcore = args.hc or input_path.name.lower().startswith("hc")
    output_path = Path(args.output_html).resolve() if args.output_html else _default_output_path(input_path, is_hardcore)

    try:
        characters = _load_characters_from_json(input_path)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html_content = generate_builds_page(characters, timestamp=timestamp, is_hardcore=is_hardcore)
        output_path.write_text(html_content, encoding="utf-8")
    except Exception as exc:
        print(f"Error generating builds page: {exc}")
        return 1

    print(f"Generated builds page: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())