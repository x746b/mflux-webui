# Core compatibility and release checks

## Tested baseline

The alpha package is tested against upstream `mflux-community/mflux` commit
`0db686992d65cbd84bd925dfce23b77ad0bedf7d`. The source override and lockfile pin that
revision for development. No code or dependency is taken from the `x746b/mflux` fork
at installation time.

The published `mflux 0.20.0` source distribution lacks Qwen Image 2.1 editing and
the parent namespace extension needed by editable installations. A normal registry
dependency cannot currently supply the full tested feature set. The CLI checks
for required core files and reports an actionable error when they are absent.

`[tool.uv.sources]` is development configuration, not wheel dependency metadata.
Wheel and Git-based tool installations therefore need the explicit upstream
override documented in the README until a compatible core release is published.

## Package boundaries

- This distribution owns `mflux/web/x746b_ui/` only.
- Neither `mflux/__init__.py` nor `mflux/web/__init__.py` is shipped.
- Model implementation code comes from upstream mflux.
- Geometry-cache retention is limited by UI cleanup after generation; no core
  transformer class is modified or replaced.
- The console command is `mflux-webui`, avoiding another distribution's `mflux-web`.
- Existing output/config locations and `MFLUX_WEB_*` variables are retained.

## Extraction validation

- 271 tests passed against the pinned core, including the complete web test suite
  and package compatibility checks.
- A wheel installed into a separate environment passed the same suite; imports
  resolved entirely within that environment.
- Wheel inspection confirmed namespace ownership, bundled templates/static files,
  and license notices.
- Browser checks passed against both source and wheel installations: all ten
  command schemas, startup progress, chat insertion, provider isolation, themes,
  the assistant toggle, and gallery navigation. Chat responses were mocked.
- One offline Z-Image Turbo generation through the installed UI runner completed
  with local weights, 4-bit quantization, the default nine steps, and 256×256 output.
  The image and both metadata sidecars were verified. This does not constitute
  real-weight validation of every supported model family.

## Before a PyPI release

1. Select a published upstream release that includes all required features and
   set it as the dependency minimum. Reassess the upper bound for that release.
2. Remove the Git source override, regenerate `uv.lock`, and run all tests against
   the registry package in a fresh environment.
3. Build wheel and sdist, inspect their contents, and test installation from the
   built wheel without source overrides or an editable checkout.
4. Run browser checks and representative real-generation checks, including Qwen
   editing and repeated generation with model caching.
5. Confirm the PyPI project name and publishing configuration before publication.
