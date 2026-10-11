from importlib.metadata import PackageNotFoundError, distribution
from importlib.resources import files

import pytest

from mflux.web.x746b_ui.compat import CoreCompatibility
from mflux.web.x746b_ui.settings import DEFAULT_CONFIG_PATH, DEFAULT_OUTPUT_DIR


def test_namespace_assets_and_entrypoint():
    package = files("mflux.web.x746b_ui")
    for name in ("templates/index.html", "templates/settings.html", "static/chat.js", "static/app.css"):
        assert package.joinpath(name).is_file()
    entrypoints = {entry.name: entry.value for entry in distribution("mflux-webui-uno").entry_points}
    assert entrypoints["mflux-webui"] == "mflux.web.x746b_ui.cli:main"
    assert "mflux-web" not in entrypoints


def test_core_supports_required_features():
    CoreCompatibility.check()


def test_incompatible_core_has_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setattr("mflux.web.x746b_ui.compat.files", lambda name: tmp_path)
    with pytest.raises(RuntimeError, match="missing required files.*from PyPI"):
        CoreCompatibility.check()


@pytest.mark.parametrize(
    "installed_version", ["0.20.0", "0.21.0", "0.23.0", "1.0.0", "0.22.0rc1", "0.22.0a1", "0.22.1.dev1", "0.22.invalid"]
)
def test_incompatible_core_version_has_actionable_error(monkeypatch, installed_version):
    monkeypatch.setattr("mflux.web.x746b_ui.compat.version", lambda name: installed_version)
    with pytest.raises(RuntimeError, match=r"requires mflux>=0\.22\.0,<0\.23\.0; found mflux"):
        CoreCompatibility.check()


@pytest.mark.parametrize("installed_version", ["0.22.0", "0.22.1", "0.22.0.post1", "0.22.0+local.1"])
def test_stable_core_series_is_accepted(monkeypatch, installed_version):
    monkeypatch.setattr("mflux.web.x746b_ui.compat.version", lambda name: installed_version)
    CoreCompatibility.check()


def test_missing_core_has_actionable_error(monkeypatch):
    def missing_version(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr("mflux.web.x746b_ui.compat.version", missing_version)
    with pytest.raises(RuntimeError, match="core is not installed.*mflux-webui-uno"):
        CoreCompatibility.check()


def test_existing_data_locations_are_preserved():
    assert str(DEFAULT_CONFIG_PATH).endswith("/.config/mflux/web.json")
    assert str(DEFAULT_OUTPUT_DIR).endswith("/AI/mflux-web/outputs")
