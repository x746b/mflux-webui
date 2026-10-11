# Core compatibility and release checks

## Core baseline

`mflux-webui-uno 0.2.2` requires `mflux>=0.22.0,<0.23.0` from PyPI. The
lockfile resolves `mflux 0.22.0`. There is no Git source override, and wheel
metadata declares the same registry dependency. No code or dependency is taken
from the `x746b/mflux` fork at installation time.

Upstream 0.22.0 includes Qwen Image 2.1 editing and the parent namespace extension
needed by editable installations. Its Qwen editing implementation lives under
`models/qwen21/variants/edit/`; the UI uses that API and the current latent creator.
Startup checks the core's release series and required files without loading model
weights. An incompatible or incomplete installation produces an error with
registry installation instructions.

The distribution name is `mflux-webui-uno`; the command remains `mflux-webui`.
This version is not yet published on PyPI. See the README for tagged Git
release installation and migration from the previous `mflux-webui` distribution.

## Package boundaries

- This distribution owns `mflux/web/x746b_ui/` only.
- Neither `mflux/__init__.py` nor `mflux/web/__init__.py` is shipped.
- Model implementation code comes from upstream mflux.
- Geometry-cache retention is limited by UI cleanup after generation; no core
  transformer class is modified or replaced.
- The console command is `mflux-webui`, avoiding another distribution's `mflux-web`.
- Existing output/config locations and `MFLUX_WEB_*` variables are retained.

## Release validation

The package compatibility tests cover bundled assets, the renamed distribution's
console entry point, the installed core's required files, actionable errors for
missing or unsupported core versions, and preserved data locations.

Validation against the registry `mflux 0.22.0` core includes:

- The full automated suite, plus focused compatibility checks for stable releases,
  prereleases, development snapshots, and missing installations.
- Ruff lint and formatting checks.
- Browser smoke checks covering all ten command schemas, prompt chat, provider
  preferences, and the gallery, against both the source installation and the
  freshly installed wheel launched outside the checkout. Chat replies were mocked.
- Wheel and sdist builds, strict Twine metadata checks, and a fresh non-editable
  wheel installation resolving `mflux 0.22.0` from the registry without overrides.
- Four offline Z-Image Turbo smoke generations at 256×256 and two steps, including
  cached reuse and cache invalidation when switching between float16 and float32.
  Output images, metadata sidecars, and progress events were checked.
- Three Qwen Image 2.1 editing smoke generations at 256×256 and two steps with
  4-bit weights: text-only editing, an uploaded reference with cached model reuse,
  and a reference with a live LoRA at strength 0.5 and float16 precision requiring
  a model reload. Images, core/UI metadata sidecars, and progress events were checked.

These small generation checks validate execution and cache behavior, not image
quality or real-weight compatibility for every supported model family.
