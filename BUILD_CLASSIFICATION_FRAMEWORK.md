# Build Classification Framework

The current class pages already do a useful job of finding similarity clusters, but a cluster is not the same thing as a build. A cluster tells you that a group of characters look alike. A build definition should tell you why they belong together and what makes them meaningfully different from nearby variants.

This document proposes an expandable framework for that second problem without changing any of the existing class pages.

## Core Principle

Define builds as scored archetypes, not rigid buckets.

That means each character can:

- strongly match one build
- weakly match one build
- overlap two neighboring builds
- fail to match any named build and fall into an unnamed or experimental bucket

This is important because the grey area is real. The framework should preserve that uncertainty instead of hiding it.

## Definition Layers

Each build definition should be made of the same layers so it stays maintainable across classes.

1. Identity signals

These are the things that most directly define the build. Usually this is one or two heavily invested skills.

Examples:

- Blizzard Sorceress: Blizzard at or near max
- Hydra / Frozen Orb Sorceress: both Hydra and Frozen Orb at or near max
- High-FCR Fireball Sorceress: Fireball at or near max

2. Supporting signals

These reinforce the identity but should not be strict gates.

Examples:

- Teleport present
- expected synergies partially invested
- Static Field or Warmth investment

3. Separation signals

These are what keep one build from swallowing another nearby build.

Examples:

- heavy Blizzard investment should reduce confidence for Hydra / Frozen Orb
- heavy Hydra investment should reduce confidence for Blizzard
- strong Faster Cast Rate can separate Fireball caster variants from slower fire hybrids

4. Non-skill signals

Use these only when they add real information that the skill tree misses.

Examples:

- Faster Cast Rate breakpoints
- item-title patterns for gear-defined variants
- Energy Shield presence for Sorceress subtypes

## Recommended Scoring Model

Use a weighted score with hard gates only for the truly defining parts.

- Required signals: must pass or the build does not apply
- Signature signals: high weight
- Supporting signals: medium or low weight
- Penalty signals: reduce score if the character looks more like a competing build
- Output: score, confidence band, and reasons

That gives you a classifier that stays explainable. If a character is tagged as a build, you can show exactly which signals made that happen.

## Recommended Output Shape

For each character, return something like:

```json
{
  "matches": [
    {
      "build_id": "sorc-hydra-frozen-orb",
      "label": "Hydra / Frozen Orb",
      "score": 0.86,
      "confidence": "high",
      "reasons": [
        "Hydra is maxed or near-maxed",
        "Frozen Orb is maxed or near-maxed",
        "Teleport meets the signature threshold"
      ]
    },
    {
      "build_id": "sorc-blizzard",
      "label": "Blizzard",
      "score": 0.49,
      "confidence": "low"
    }
  ]
}
```

The important part is not just the top label. It is also whether the second-place match is close enough to matter.

## Naming Strategy

Keep naming hierarchical so the system expands cleanly.

- Family: Cold Sorceress, Fire Sorceress, Hybrid Sorceress
- Build: Blizzard, High-FCR Fireball, Hydra / Frozen Orb
- Variant: ES Blizzard, MF Blizzard, Vita Fireball

This avoids starting with overly specific labels that become hard to maintain.

## Suggested Rules For The First Pass

Sorceress is the right place to start because many archetypes have clear skill anchors.

Suggested first-pass build set:

1. Blizzard
2. Hydra / Frozen Orb
3. High-FCR Fireball
4. Lightning Surge
5. Charged Bolt / Lightning hybrid

Start with only 3 to 5 clear archetypes and leave ambiguous cases unmatched. That will teach you where the framework is too loose or too strict.

## Threshold Guidelines

Use thresholds that reflect intent, not tiny incidental investment.

- 20 points: core or near-core skill
- 10 points: serious secondary commitment
- 1 point: utility presence

For gear or stat splits, prefer meaningful thresholds rather than raw presence.

Example:

- Fireball build with Faster Cast Rate >= 105 is a stronger separator than simply checking whether some FCR exists

## Data Model Recommendation

Keep definitions in code or data, but make the shape stable.

Each build should have:

- `build_id`
- `class_name`
- `label`
- `family`
- `required_skills_all`
- `required_skill_groups_any`
- `signature_skills`
- `supporting_skills`
- `penalty_skills`
- `stat_requirements`
- `gear_text_any`
- `gear_titles_any`
- `notes`

That exact structure is implemented in [scripts/modules/build_classifier.py](scripts/modules/build_classifier.py).

## Practical Workflow

1. Start with one class and a handful of definitions.
2. Run the classifier against real characters.
3. Review false positives and false negatives.
4. Tighten required signals before adding more penalties.
5. Only add gear-based separation when skills alone are not enough.
6. Keep overlap visible rather than forcing a single answer too early.

## Why This Is Better Than Pure Clustering

Clustering is good for discovery. Rule-based archetypes are better for presentation.

Use clustering to find candidate build families, then turn the stable ones into explicit definitions. That gives you:

- readable labels
- explainable classification
- consistent naming over time
- room for hybrid and edge-case handling

## Current Starter Implementation

A standalone starter classifier has been added in [scripts/modules/build_classifier.py](scripts/modules/build_classifier.py). It is not wired into existing pages. It currently includes example Sorceress definitions for:

- Blizzard
- Hydra / Frozen Orb
- High-FCR Fireball

That should be enough to start testing definitions against live character data before deciding how to surface the results on a new page.