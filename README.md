# PodBuildExplorer

Standalone build-classification project for Path of Diablo ladder data.

This package contains the build classifier, JSON build definitions, the static page generator, ladder JSON inputs, and the assets referenced by the generated HTML.

## What is here

- `scripts/modules/build_classifier.py`: rule-based classifier
- `scripts/modules/build_definitions/*.json`: per-class build definitions
- `scripts/modules/builds_page.py`: standalone HTML generator
- `sc_ladder.json`: softcore source data
- `hc_ladder.json`: hardcore source data
- `css/`, `icons/`, `js/`: static assets used by the generated page
- `BUILD_CLASSIFICATION_FRAMEWORK.md`: design notes for the rule system

## Generate the pages

From the repository root:

```bash
python3 scripts/modules/builds_page.py sc_ladder.json
python3 scripts/modules/builds_page.py hc_ladder.json --hc
```

That writes:

- `Builds.html`
- `hcBuilds.html`

## How build matching works

Each build definition is a JSON object that the classifier scores against a ladder character.

The classifier works in two phases:

1. Gate checks
	 - Required skill thresholds must pass.
	 - Required any-of skill groups must have at least one match in each group.
	 - Required summed skill investment must pass.
	 - Required stat thresholds must pass.
	 - Required gear rules must pass.

2. Scoring
	 - Matching `signature_skills`, `supporting_skills`, `stat_requirements`, `gear_text_any`, `gear_titles_any`, and `supporting_gear_rules` add score.
	 - Matching `penalty_skills` and `penalty_gear_rules` subtract score.
	 - Final score is normalized to a `0.0` to `1.0` range.

By default, a build only appears if it scores at least `0.45`. If multiple builds are within `0.08` of the best score, they are all returned. That means the system is intentionally overlap-friendly rather than strictly forcing one winner.

## Creating more builds

Most contribution work should happen in:

- `scripts/modules/build_definitions/*.json`

Each class file contains one or more build definitions for a single class. All JSON files in that directory are loaded automatically, so most additions are just edits to the relevant class file.

Typical workflow:

1. Pick the right class file in `scripts/modules/build_definitions/`.
2. Copy an existing build that is structurally similar to the one you want.
3. Change `build_id`, `label`, `family`, and `description` first.
4. Add the minimum required gates that must be true for the build to count at all.
5. Add signature and supporting signals that should raise confidence.
6. Add penalty signals for nearby builds that commonly overlap.
7. Regenerate `Builds.html` and `hcBuilds.html` and inspect the affected class section.
8. Tighten or loosen thresholds until the matches look believable.

## Build definition schema

Every build object should start with these top-level fields:

- `build_id`: unique stable identifier such as `druid-flamedash`
- `class_name`: must match the ladder class name exactly, such as `Druid`
- `label`: short display name shown on the page
- `family`: broader grouping label shown in the build details
- `description`: plain-language explanation of what the build represents

The remaining fields are optional and can be combined as needed.

### Skill gates

- `required_skills_all`: every listed skill threshold must pass
- `required_skill_groups_any`: for each inner array, at least one skill threshold must pass
- `required_skill_sums`: named skills whose combined levels must reach a minimum total

Use these when a build should not match at all unless the character clearly invested in the core package.

### Positive scoring signals

- `signature_skills`: strongest positive indicators of the build
- `supporting_skills`: weaker positive indicators that reinforce the identity
- `stat_requirements`: stat thresholds that both gate and add score
- `gear_text_any`: substring checks against item property text, socket text, titles, and tags
- `gear_titles_any`: substring checks only against equipped item titles
- `supporting_gear_rules`: item-level same-item rules that add score when matched

### Negative scoring signals

- `penalty_skills`: subtract score when a competing skill package is also heavily invested
- `penalty_gear_rules`: subtract score when gear strongly suggests another build

### Hard gear gates

- `required_gear_rules_all`: every listed gear rule must match
- `required_gear_rule_groups_any`: for each inner array, at least one gear rule must match

These are useful when a build is fundamentally defined by an item or one of several equivalent item patterns.

## Signal and gear rule formats

### Threshold signal

Used by most skill, stat, and text-based fields:

```json
{
	"name": "Flame Dash",
	"minimum": 15,
	"weight": 2.0,
	"reason": "Flame Dash is heavily invested"
}
```

- `name`: skill name, stat name, or text fragment depending on the field
- `minimum`: threshold to count as matched
- `weight`: contribution to score when matched
- `reason`: optional explanation used in match details

### Skill sum requirement

```json
{
	"names": ["Rabies", "Poison Creeper", "Summon Dire Wolf", "Lycanthropy"],
	"minimum_total": 45,
	"reason": "Rabies support investment reaches the combined threshold"
}
```

### Gear rule

```json
{
	"title_contains": ["Enigma"],
	"property_contains": ["+1 to teleport"],
	"worn_slots": ["body"],
	"minimum_count": 1,
	"weight": 1.0,
	"reason": "Teleport armor is equipped"
}
```

Gear rules match against normalized equipped item records. They can test:

- `title_contains`: fragments that must all appear in the item title
- `tag_contains`: fragments that must all appear in the item tag
- `property_contains`: fragments that must appear somewhere in the item property text
- `worn_slots`: slot restrictions such as `weapon1`, `weapon2`, `body`, `amulet`, `ring1`
- `minimum_count`: how many equipped items must satisfy the rule
- `weight`: score contribution when used in supporting or penalty rules
- `reason`: optional explanation shown in match details

## Practical guidance for defining a new build

Start narrow. If you begin with only broad supporting signals, the build will usually absorb characters that belong somewhere else.

Good pattern:

1. Add one or two hard gates for the build's core skill or package.
2. Add two to five `signature_skills` with heavier weights.
3. Add a few `supporting_skills` for common synergies.
4. Add `penalty_skills` for the closest competing archetypes.
5. Add gear checks only if the build is truly gear-defined.

Examples:

- A summon build is usually best defined by combined summon investment plus one heavy summon threshold.
- An attack build is usually best defined by the attack skill itself, then support synergies, then penalties for adjacent attacks.
- A niche item-defined build may need a required gear rule or a required any-of gear group.

Avoid these common mistakes:

- Making `required_skills_all` too broad. That turns soft evidence into a hard gate and causes many false negatives.
- Using item text as the primary identity when the build is really skill-defined.
- Forgetting penalty signals for neighboring builds with the same support package.
- Reusing a `build_id`.
- Using a `class_name` that does not exactly match the source data.

## Minimal example

```json
[
	{
		"build_id": "druid-example-build",
		"class_name": "Druid",
		"label": "Example Build",
		"family": "Caster Druid",
		"description": "Example showing the typical structure of a build definition.",
		"required_skills_all": [
			{
				"name": "Example Core Skill",
				"minimum": 15,
				"reason": "Example Core Skill is heavily invested"
			}
		],
		"required_skill_groups_any": [
			[
				{
					"name": "Example Synergy A",
					"minimum": 10,
					"reason": "Example Synergy A is invested"
				},
				{
					"name": "Example Synergy B",
					"minimum": 10,
					"reason": "Example Synergy B is invested"
				}
			]
		],
		"signature_skills": [
			{
				"name": "Example Core Skill",
				"minimum": 15,
				"weight": 2.0
			}
		],
		"supporting_skills": [
			{
				"name": "Example Support Skill",
				"minimum": 10,
				"weight": 0.75
			}
		],
		"penalty_skills": [
			{
				"name": "Competing Skill",
				"minimum": 15,
				"weight": 0.8
			}
		],
		"notes": [
			"Use notes for human guidance when the thresholds are not obvious."
		]
	}
]
```

## How to validate a new build

After changing any definition file:

```bash
python3 scripts/modules/builds_page.py sc_ladder.json
python3 scripts/modules/builds_page.py hc_ladder.json --hc
```

Then review:

1. The expected class section in `Builds.html` and `hcBuilds.html`
2. Whether the new build is catching the intended characters
3. Whether it is stealing characters from nearby builds
4. Whether the unmatched list for that class shrank or grew in a sensible way

If a build is matching too many characters:

- add or strengthen hard gates
- raise signature thresholds
- add penalties for the neighboring archetype it is colliding with

If a build is matching too few characters:

- lower a required threshold
- move a condition from a hard gate into `signature_skills` or `supporting_skills`
- replace a strict `required_skills_all` rule with an `required_skill_groups_any` group

## Where to look for examples

- `scripts/modules/build_definitions/druid.json`: good examples of skill-sum and overlap-heavy Druid variants
- `scripts/modules/build_definitions/sorceress.json`: good examples of stat and gear-assisted caster definitions
- `scripts/modules/build_definitions/necromancer.json`: good examples of gear-rule groups

## Notes

- The current generator uses only Python standard library modules.
- The generated page is static HTML and can be hosted with GitHub Pages.
- The generated page uses the bundled armory iframe assets and local ladder snapshots for popup data.
