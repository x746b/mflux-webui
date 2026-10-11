import re
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files


class CoreCompatibility:
    REQUIRED_VERSION = ">=0.22.0,<0.23.0"
    REQUIRED_FILES = (
        "cli/capabilities.py",
        "models/qwen21/cli/qwen21_edit_generate.py",
        "models/qwen21/variants/edit/qwen_image_21_edit.py",
        "models/qwen21/latent_creator/qwen_image21_latent_creator.py",
        "utils/exif_orientation.py",
    )

    @staticmethod
    def check() -> None:
        requirement = f"mflux{CoreCompatibility.REQUIRED_VERSION}"
        remedy = (
            f"Reinstall mflux-webui-uno using the README instructions with {requirement} from PyPI; "
            "remove any old mflux Git override."
        )
        try:
            installed_version = version("mflux")
        except PackageNotFoundError as exc:
            raise RuntimeError(f"The mflux core is not installed. {remedy}") from exc
        # Accept normalized stable 0.22 releases, including post/local versions,
        # while rejecting prereleases and development snapshots.
        if not re.fullmatch(r"0\.22\.\d+(?:\.post\d+)?(?:\+[a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*)?", installed_version):
            raise RuntimeError(f"This UI requires {requirement}; found mflux {installed_version}. {remedy}")
        root = files("mflux")
        missing = [name for name in CoreCompatibility.REQUIRED_FILES if not root.joinpath(name).is_file()]
        if missing:
            raise RuntimeError(
                f"The installed mflux {installed_version} is missing required files: {', '.join(missing)}. {remedy}"
            )
