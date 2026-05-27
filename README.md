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

## Contributing new builds

Most contribution work should happen in:

- `scripts/modules/build_definitions/*.json`

Each class file contains one or more build definitions that the classifier scores against ladder characters.

After changing definitions, regenerate the HTML pages with the commands above and review the affected class sections.

## Notes

- The current generator uses only Python standard library modules.
- The generated page is static HTML and can be hosted with GitHub Pages.
- The current popup script is lightweight and does not require the full armory iframe bundle.
