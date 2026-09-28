from importlib.metadata import distribution
from importlib.resources import files

import pytest

from mflux.web.x746b_ui.compat import CoreCompatibility
from mflux.web.x746b_ui.settings import DEFAULT_CONFIG_PATH, DEFAULT_OUTPUT_DIR


def test_namespace_assets_and_entrypoint():
    package = files("mflux.web.x746b_ui")
    for name in ("templates/index.html", "templates/settings.html", "static/chat.js", "static/app.css"):
        assert package.joinpath(name).is_file()
    entrypoints = {entry.name: entry.value for entry in distribution("mflux-webui").entry_points}
    assert entrypoints["mflux-webui"] == "mflux.web.x746b_ui.cli:main"
    assert "mflux-web" not in entrypoints


def test_core_supports_required_features():
    CoreCompatibility.check()


def test_incompatible_core_has_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setattr("mflux.web.x746b_ui.compat.files", lambda name: tmp_path)
    with pytest.raises(RuntimeError, match="upstream revision"):
        CoreCompatibility.check()


def test_existing_data_locations_are_preserved():
    assert str(DEFAULT_CONFIG_PATH).endswith("/.config/mflux/web.json")
    assert str(DEFAULT_OUTPUT_DIR).endswith("/AI/mflux-web/outputs")
