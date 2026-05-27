"""Rule-based build classification utilities.

This module is intentionally standalone so new build definitions can be developed
without changing the existing class-page clustering outputs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ThresholdSignal:
    """A single threshold-based signal for a skill, stat, or text marker."""

    name: str
    minimum: float = 0
    weight: float = 1.0
    reason: Optional[str] = None


@dataclass(frozen=True)
class GearRule:
    """A same-item gear rule based on title, tag, slot, and property text."""

    title_contains: Sequence[str] = field(default_factory=tuple)
    tag_contains: Sequence[str] = field(default_factory=tuple)
    property_contains: Sequence[str] = field(default_factory=tuple)
    worn_slots: Sequence[str] = field(default_factory=tuple)
    minimum_count: int = 1
    weight: float = 1.0
    reason: Optional[str] = None


@dataclass(frozen=True)
class SkillSumRequirement:
    """A required total investment across a named group of skills."""

    names: Sequence[str] = field(default_factory=tuple)
    minimum_total: float = 0
    reason: Optional[str] = None


@dataclass(frozen=True)
class BuildDefinition:
    """A build definition that can be scored against a character profile."""

    build_id: str
    class_name: str
    label: str
    family: str
    description: str = ""
    required_skills_all: Sequence[ThresholdSignal] = field(default_factory=tuple)
    required_skill_groups_any: Sequence[Sequence[ThresholdSignal]] = field(default_factory=tuple)
    required_skill_sums: Sequence[SkillSumRequirement] = field(default_factory=tuple)
    required_gear_rule_groups_any: Sequence[Sequence[GearRule]] = field(default_factory=tuple)
    signature_skills: Sequence[ThresholdSignal] = field(default_factory=tuple)
    supporting_skills: Sequence[ThresholdSignal] = field(default_factory=tuple)
    penalty_skills: Sequence[ThresholdSignal] = field(default_factory=tuple)
    stat_requirements: Sequence[ThresholdSignal] = field(default_factory=tuple)
    required_gear_rules_all: Sequence[GearRule] = field(default_factory=tuple)
    gear_text_any: Sequence[ThresholdSignal] = field(default_factory=tuple)
    gear_titles_any: Sequence[ThresholdSignal] = field(default_factory=tuple)
    supporting_gear_rules: Sequence[GearRule] = field(default_factory=tuple)
    penalty_gear_rules: Sequence[GearRule] = field(default_factory=tuple)
    notes: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class BuildMatch:
    """A scored match for a character against one build definition."""

    build_id: str
    label: str
    family: str
    score: float
    confidence: str
    matched_skills: Dict[str, float]
    matched_stats: Dict[str, float]
    matched_gear: List[str]
    reasons: List[str]


def extract_skill_map(character: Dict[str, Any]) -> Dict[str, int]:
    """Flatten the nested SkillTabs structure into a skill-to-level map."""
    skill_map: Dict[str, int] = {}
    for tab in character.get("SkillTabs", []):
        for skill in tab.get("Skills", []):
            skill_name = skill.get("Name")
            skill_level = skill.get("Level", 0)
            if skill_name:
                normalized_name = _normalize_name(skill_name)
                skill_map[normalized_name] = max(skill_map.get(normalized_name, 0), skill_level)
    return skill_map


def extract_search_blob(character: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Create normalized gear text and title lists for substring matching."""
    blob_parts: List[str] = []
    titles: List[str] = []

    for item in character.get("Equipped", []):
        title = str(item.get("Title", "")).strip()
        if title:
            titles.append(title.lower())
            blob_parts.append(title.lower())
        tag = str(item.get("Tag", "")).strip()
        if tag:
            blob_parts.append(tag.lower())
        for prop in item.get("PropertyList", []):
            blob_parts.append(str(prop).lower())
        for socket in item.get("Sockets", []):
            socket_title = str(socket.get("Title", "")).strip()
            if socket_title:
                blob_parts.append(socket_title.lower())
            for prop in socket.get("PropertyList", []):
                blob_parts.append(str(prop).lower())

    return " | ".join(blob_parts), titles


def extract_equipped_items(character: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return normalized equipped-item records for same-item rule matching."""
    equipped_items: List[Dict[str, Any]] = []

    for item in character.get("Equipped", []):
        title = str(item.get("Title", "")).strip().lower()
        tag = str(item.get("Tag", "")).strip().lower()
        worn = str(item.get("Worn", "")).strip().lower()
        properties = [str(prop).strip().lower() for prop in item.get("PropertyList", [])]

        for socket in item.get("Sockets", []):
            socket_title = str(socket.get("Title", "")).strip().lower()
            if socket_title:
                properties.append(socket_title)
            properties.extend(str(prop).strip().lower() for prop in socket.get("PropertyList", []))

        equipped_items.append(
            {
                "title": title,
                "tag": tag,
                "worn": worn,
                "properties": properties,
            }
        )

    return equipped_items


def classify_character(
    character: Dict[str, Any],
    definitions: Sequence[BuildDefinition],
    minimum_score: float = 0.45,
    overlap_delta: float = 0.08,
) -> List[BuildMatch]:
    """Return the best matching build definitions for one character.

    The classifier is intentionally overlap-friendly: if multiple definitions score
    within ``overlap_delta`` of the best result, all of them are returned.
    """
    class_name = character.get("Class")
    skill_map = extract_skill_map(character)
    if not class_name or not skill_map:
        return []

    stats = character.get("Stats", {})
    bonus = character.get("Bonus", {})
    gear_blob, gear_titles = extract_search_blob(character)
    equipped_items = extract_equipped_items(character)

    matches: List[BuildMatch] = []
    for definition in definitions:
        if definition.class_name != class_name:
            continue

        score, reasons, matched_skills, matched_stats, matched_gear = _score_definition(
            definition,
            skill_map,
            stats,
            bonus,
            gear_blob,
            gear_titles,
            equipped_items,
        )
        if score >= minimum_score:
            matches.append(
                BuildMatch(
                    build_id=definition.build_id,
                    label=definition.label,
                    family=definition.family,
                    score=round(score, 3),
                    confidence=_confidence_band(score),
                    matched_skills=matched_skills,
                    matched_stats=matched_stats,
                    matched_gear=matched_gear,
                    reasons=reasons,
                )
            )

    matches.sort(key=lambda match: match.score, reverse=True)
    if not matches:
        return []

    best_score = matches[0].score
    return [match for match in matches if best_score - match.score <= overlap_delta]


def default_build_definitions() -> List[BuildDefinition]:
    """Load the current default build-definition set."""
    definitions_dir = Path(__file__).parent / "build_definitions"
    definitions: List[BuildDefinition] = []
    for definition_file in sorted(definitions_dir.glob("*.json")):
        definitions.extend(_load_build_definitions_from_json(definition_file))
    return definitions


def _load_build_definitions_from_json(file_path: Path) -> List[BuildDefinition]:
    with file_path.open(encoding="utf-8") as handle:
        raw_definitions = json.load(handle)
    return [_build_definition_from_dict(definition) for definition in raw_definitions]


def _build_definition_from_dict(payload: Dict[str, Any]) -> BuildDefinition:
    return BuildDefinition(
        build_id=payload["build_id"],
        class_name=payload["class_name"],
        label=payload["label"],
        family=payload["family"],
        description=payload.get("description", ""),
        required_skills_all=tuple(_threshold_signal_from_dict(signal) for signal in payload.get("required_skills_all", [])),
        required_skill_groups_any=tuple(
            tuple(_threshold_signal_from_dict(signal) for signal in signal_group)
            for signal_group in payload.get("required_skill_groups_any", [])
        ),
        required_skill_sums=tuple(
            _skill_sum_requirement_from_dict(requirement)
            for requirement in payload.get("required_skill_sums", [])
        ),
        required_gear_rule_groups_any=tuple(
            tuple(_gear_rule_from_dict(rule) for rule in rule_group)
            for rule_group in payload.get("required_gear_rule_groups_any", [])
        ),
        signature_skills=tuple(_threshold_signal_from_dict(signal) for signal in payload.get("signature_skills", [])),
        supporting_skills=tuple(_threshold_signal_from_dict(signal) for signal in payload.get("supporting_skills", [])),
        penalty_skills=tuple(_threshold_signal_from_dict(signal) for signal in payload.get("penalty_skills", [])),
        stat_requirements=tuple(_threshold_signal_from_dict(signal) for signal in payload.get("stat_requirements", [])),
        required_gear_rules_all=tuple(_gear_rule_from_dict(rule) for rule in payload.get("required_gear_rules_all", [])),
        gear_text_any=tuple(_threshold_signal_from_dict(signal) for signal in payload.get("gear_text_any", [])),
        gear_titles_any=tuple(_threshold_signal_from_dict(signal) for signal in payload.get("gear_titles_any", [])),
        supporting_gear_rules=tuple(_gear_rule_from_dict(rule) for rule in payload.get("supporting_gear_rules", [])),
        penalty_gear_rules=tuple(_gear_rule_from_dict(rule) for rule in payload.get("penalty_gear_rules", [])),
        notes=tuple(payload.get("notes", [])),
    )


def _threshold_signal_from_dict(payload: Dict[str, Any]) -> ThresholdSignal:
    return ThresholdSignal(
        name=payload["name"],
        minimum=payload.get("minimum", 0),
        weight=payload.get("weight", 1.0),
        reason=payload.get("reason"),
    )


def _gear_rule_from_dict(payload: Dict[str, Any]) -> GearRule:
    return GearRule(
        title_contains=tuple(payload.get("title_contains", [])),
        tag_contains=tuple(payload.get("tag_contains", [])),
        property_contains=tuple(payload.get("property_contains", [])),
        worn_slots=tuple(payload.get("worn_slots", [])),
        minimum_count=payload.get("minimum_count", 1),
        weight=payload.get("weight", 1.0),
        reason=payload.get("reason"),
    )


def _skill_sum_requirement_from_dict(payload: Dict[str, Any]) -> SkillSumRequirement:
    return SkillSumRequirement(
        names=tuple(payload.get("names", [])),
        minimum_total=payload.get("minimum_total", 0),
        reason=payload.get("reason"),
    )


def _score_definition(
    definition: BuildDefinition,
    skill_map: Dict[str, int],
    stats: Dict[str, Any],
    bonus: Dict[str, Any],
    gear_blob: str,
    gear_titles: Sequence[str],
    equipped_items: Sequence[Dict[str, Any]],
) -> Tuple[float, List[str], Dict[str, float], Dict[str, float], List[str]]:
    reasons: List[str] = []
    matched_skills: Dict[str, float] = {}
    matched_stats: Dict[str, float] = {}
    matched_gear: List[str] = []

    if not _passes_all_required(definition.required_skills_all, skill_map, reasons):
        return 0.0, reasons, matched_skills, matched_stats, matched_gear
    if not _passes_any_groups(definition.required_skill_groups_any, skill_map, reasons):
        return 0.0, reasons, matched_skills, matched_stats, matched_gear
    if not _passes_skill_sum_requirements(definition.required_skill_sums, skill_map, reasons):
        return 0.0, reasons, matched_skills, matched_stats, matched_gear
    if not _passes_stat_requirements(definition.stat_requirements, stats, bonus, reasons, matched_stats):
        return 0.0, reasons, matched_skills, matched_stats, matched_gear
    if not _passes_required_gear_rules(definition.required_gear_rules_all, equipped_items, reasons, matched_gear):
        return 0.0, reasons, matched_skills, matched_stats, matched_gear
    if not _passes_any_gear_rule_groups(definition.required_gear_rule_groups_any, equipped_items, reasons, matched_gear):
        return 0.0, reasons, matched_skills, matched_stats, matched_gear

    earned = 0.0
    possible = 0.0

    for signal in definition.signature_skills:
        possible += signal.weight
        normalized_name = _normalize_name(signal.name)
        if skill_map.get(normalized_name, 0) >= signal.minimum:
            earned += signal.weight
            matched_skills[signal.name] = skill_map[normalized_name]
            reasons.append(signal.reason or f"{signal.name} meets the signature threshold")

    for signal in definition.supporting_skills:
        possible += signal.weight
        normalized_name = _normalize_name(signal.name)
        if skill_map.get(normalized_name, 0) >= signal.minimum:
            earned += signal.weight
            matched_skills[signal.name] = skill_map[normalized_name]

    for signal in definition.stat_requirements:
        possible += signal.weight
        stat_value = _lookup_stat(signal.name, stats, bonus)
        if stat_value >= signal.minimum:
            earned += signal.weight
            matched_stats[signal.name] = stat_value

    for signal in definition.gear_text_any:
        possible += signal.weight
        if signal.name.lower() in gear_blob:
            earned += signal.weight
            reasons.append(signal.reason or f"Gear text includes '{signal.name}'")

    for signal in definition.gear_titles_any:
        possible += signal.weight
        if any(signal.name.lower() in title for title in gear_titles):
            earned += signal.weight
            reasons.append(signal.reason or f"Gear title matches '{signal.name}'")

    for rule in definition.supporting_gear_rules:
        possible += rule.weight
        match_count = _count_gear_rule_matches(rule, equipped_items)
        if match_count >= rule.minimum_count:
            earned += rule.weight
            matched_gear.append(_describe_gear_rule(rule))
            reasons.append(rule.reason or _describe_gear_rule(rule))

    penalty = 0.0
    for signal in definition.penalty_skills:
        if skill_map.get(_normalize_name(signal.name), 0) >= signal.minimum:
            penalty += signal.weight
            reasons.append(f"{signal.name} also has heavy investment, which weakens this match")

    for rule in definition.penalty_gear_rules:
        if _count_gear_rule_matches(rule, equipped_items) >= rule.minimum_count:
            penalty += rule.weight
            reasons.append(rule.reason or f"Gear pattern matched competing rule: {_describe_gear_rule(rule)}")

    if possible == 0:
        return 0.0, reasons, matched_skills, matched_stats, matched_gear

    score = max(0.0, min(1.0, (earned - penalty) / possible))
    return score, reasons, matched_skills, matched_stats, matched_gear


def _passes_all_required(
    required: Iterable[ThresholdSignal],
    skill_map: Dict[str, int],
    reasons: List[str],
) -> bool:
    for signal in required:
        if skill_map.get(_normalize_name(signal.name), 0) < signal.minimum:
            return False
        reasons.append(signal.reason or f"{signal.name} passed the required threshold")
    return True


def _passes_any_groups(
    groups: Iterable[Sequence[ThresholdSignal]],
    skill_map: Dict[str, int],
    reasons: List[str],
) -> bool:
    for group in groups:
        matched = [signal for signal in group if skill_map.get(_normalize_name(signal.name), 0) >= signal.minimum]
        if not matched:
            return False
        reasons.append(matched[0].reason or f"{matched[0].name} passed an any-of requirement")
    return True


def _passes_stat_requirements(
    requirements: Iterable[ThresholdSignal],
    stats: Dict[str, Any],
    bonus: Dict[str, Any],
    reasons: List[str],
    matched_stats: Dict[str, float],
) -> bool:
    for signal in requirements:
        stat_value = _lookup_stat(signal.name, stats, bonus)
        if stat_value < signal.minimum:
            return False
        matched_stats[signal.name] = stat_value
        reasons.append(signal.reason or f"{signal.name} passed the required threshold")
    return True


def _passes_skill_sum_requirements(
    requirements: Iterable[SkillSumRequirement],
    skill_map: Dict[str, int],
    reasons: List[str],
) -> bool:
    for requirement in requirements:
        total = sum(skill_map.get(_normalize_name(name), 0) for name in requirement.names)
        if total < requirement.minimum_total:
            return False
        skill_list = ", ".join(requirement.names)
        reasons.append(
            requirement.reason or f"{skill_list} reached the required combined threshold"
        )
    return True


def _passes_required_gear_rules(
    requirements: Iterable[GearRule],
    equipped_items: Sequence[Dict[str, Any]],
    reasons: List[str],
    matched_gear: List[str],
) -> bool:
    for rule in requirements:
        if _count_gear_rule_matches(rule, equipped_items) < rule.minimum_count:
            return False
        description = rule.reason or _describe_gear_rule(rule)
        matched_gear.append(_describe_gear_rule(rule))
        reasons.append(description)
    return True


def _passes_any_gear_rule_groups(
    groups: Iterable[Sequence[GearRule]],
    equipped_items: Sequence[Dict[str, Any]],
    reasons: List[str],
    matched_gear: List[str],
) -> bool:
    for group in groups:
        matched_rule = next(
            (rule for rule in group if _count_gear_rule_matches(rule, equipped_items) >= rule.minimum_count),
            None,
        )
        if matched_rule is None:
            return False
        description = matched_rule.reason or _describe_gear_rule(matched_rule)
        matched_gear.append(_describe_gear_rule(matched_rule))
        reasons.append(description)
    return True


def _count_gear_rule_matches(rule: GearRule, equipped_items: Sequence[Dict[str, Any]]) -> int:
    return sum(1 for item in equipped_items if _item_matches_rule(item, rule))


def _item_matches_rule(item: Dict[str, Any], rule: GearRule) -> bool:
    item_worn = _normalize_name(item.get("worn", ""))
    if rule.worn_slots and item_worn not in {_normalize_name(slot) for slot in rule.worn_slots}:
        return False

    title = _normalize_name(item.get("title", ""))
    tag = _normalize_name(item.get("tag", ""))
    properties = [_normalize_name(prop) for prop in item.get("properties", [])]

    if rule.title_contains and not all(_normalize_name(fragment) in title for fragment in rule.title_contains):
        return False
    if rule.tag_contains and not all(_normalize_name(fragment) in tag for fragment in rule.tag_contains):
        return False
    if rule.property_contains and not all(
        any(_normalize_name(fragment) in prop for prop in properties)
        for fragment in rule.property_contains
    ):
        return False

    return True


def _describe_gear_rule(rule: GearRule) -> str:
    parts: List[str] = []
    if rule.title_contains:
        parts.append(f"title contains {', '.join(rule.title_contains)}")
    if rule.tag_contains:
        parts.append(f"tag contains {', '.join(rule.tag_contains)}")
    if rule.property_contains:
        parts.append(f"properties include {', '.join(rule.property_contains)}")
    if rule.worn_slots:
        parts.append(f"worn in {', '.join(rule.worn_slots)}")
    if not parts:
        return "generic gear rule"
    return "Gear rule matched: " + "; ".join(parts)


def _lookup_stat(name: str, stats: Dict[str, Any], bonus: Dict[str, Any]) -> float:
    if name in bonus:
        return float(bonus.get(name, 0) or 0)
    return float(stats.get(name, 0) or 0)


def _confidence_band(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def _normalize_name(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())


__all__ = [
    "BuildDefinition",
    "BuildMatch",
    "GearRule",
    "ThresholdSignal",
    "classify_character",
    "extract_equipped_items",
    "default_build_definitions",
    "extract_search_blob",
    "extract_skill_map",
]