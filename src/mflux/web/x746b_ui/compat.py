from importlib.resources import files


class CoreCompatibility:
    UPSTREAM_REVISION = "0db686992d65cbd84bd925dfce23b77ad0bedf7d"
    REQUIRED_FILES = (
        "cli/capabilities.py",
        "models/qwen21/cli/qwen21_edit_generate.py",
        "utils/exif_orientation.py",
    )

    @staticmethod
    def check() -> None:
        root = files("mflux")
        missing = [name for name in CoreCompatibility.REQUIRED_FILES if not root.joinpath(name).is_file()]
        if missing:
            raise RuntimeError(
                "This preview requires newer upstream mflux features than the installed core provides. "
                "Install the upstream revision specified in the README; mflux 0.20.0 from PyPI is not sufficient."
            )
