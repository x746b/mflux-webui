"""Model-free checks against the installed mflux command contracts."""

import importlib
from argparse import Namespace
from types import SimpleNamespace

import mlx.core as mx
import pytest

from mflux.web.x746b_ui.adapters import ADAPTERS, ModelCacheKey, SharedCommandAdapter
from mflux.web.x746b_ui.invocation import Invocation

pytestmark = pytest.mark.fast


def parsed(command, *flags):
    args, _ = Invocation._parse(ADAPTERS[command], command, ["--prompt=teapot", *flags])
    args.web_provided_flags = {flag.split("=", 1)[0] for flag in flags}
    args.web_messages = []
    return args


@pytest.mark.parametrize(
    "adapter", [a for a in ADAPTERS.values() if isinstance(a, SharedCommandAdapter)], ids=lambda a: a.command
)
def test_shared_commands_delegate_without_owning_model_lifecycle(adapter, monkeypatch):
    calls = []
    args = parsed(adapter.command)
    model = object()
    command = adapter.core_command()
    monkeypatch.setattr(command, "validate", lambda value: calls.append(("validate", value)))
    monkeypatch.setattr(command, "load", lambda value: calls.append(("load", value)) or model)
    monkeypatch.setattr(command, "generate", lambda *values: calls.append(("generate", *values)) or "image")
    adapter.validate(args)
    assert adapter.load(args) is model
    assert adapter.generate(model, args, 7, "new prompt") == "image"
    assert calls == [("validate", args), ("load", args), ("generate", model, args, 7, "new prompt")]


@pytest.mark.parametrize(
    "command,module,class_name",
    [
        ("mflux-generate-flux2", "mflux.models.flux2.variants", "Flux2Klein"),
        ("mflux-generate-qwen-2.1", "mflux.models.qwen21.variants.txt2img.qwen_image_21", "QwenImage21"),
        ("mflux-generate-qwen-2.1-edit", "mflux.models.qwen21.variants.edit.qwen_image_21_edit", "QwenImage21Edit"),
        ("mflux-generate-z-image", "mflux.models.z_image.cli.z_image_generate", "ZImage"),
        ("mflux-generate-z-image-turbo", "mflux.models.z_image.cli.z_image_turbo_generate", "ZImage"),
    ],
)
def test_load_forwards_precision_and_lora_weights(command, module, class_name, monkeypatch):
    args = parsed(command, "--compute-precision=float16")
    args.lora_paths = ["example.safetensors"]
    args.lora_scales = [0.5]
    args.bake_lora = False
    seen = []
    monkeypatch.setattr(importlib.import_module(module), class_name, lambda **kwargs: seen.append(kwargs))
    ADAPTERS[command].load(args)
    assert seen[0]["compute_precision"] == mx.float16
    assert seen[0]["lora_paths"] == ["example.safetensors"]
    assert seen[0]["lora_scales"] == [0.5]
    assert seen[0]["bake_lora"] is False


@pytest.mark.parametrize("command", ["mflux-generate-z-image", "mflux-generate-z-image-turbo"])
def test_zimage_float32_reaches_constructor(command, monkeypatch):
    adapter = ADAPTERS[command]
    seen = []
    monkeypatch.setattr(importlib.import_module(adapter.module), "ZImage", lambda **kwargs: seen.append(kwargs))
    adapter.load(parsed(command, "--float32"))
    assert seen[0]["float32"] is True


def test_qwen21_step_cache_reaches_generation():
    adapter = ADAPTERS["mflux-generate-qwen-2.1"]
    args = parsed(adapter.command, "--step-cache-ratio=0.25")
    adapter.validate(args)
    seen = []
    adapter.generate(SimpleNamespace(generate_image=lambda **kwargs: seen.append(kwargs)), args, 42, "teapot")
    assert seen[0]["step_cache_ratio"] == 0.25
    assert not {"pid_decode", "pid_degrade_sigma"} & seen[0].keys()


def test_qwen_rejects_foreign_family_without_loading():
    adapter = ADAPTERS["mflux-generate-qwen"]
    with pytest.raises(ValueError):
        adapter.validate(parsed(adapter.command, "--model=z-image"))


def test_qwen21_viggle_validated_before_loading():
    adapter = ADAPTERS["mflux-generate-qwen-2.1"]
    with pytest.raises(ValueError, match="requires --steps 6"):
        adapter.validate(parsed(adapter.command, "--scheduler=viggle_turbo"))
    adapter.validate(parsed(adapter.command, "--scheduler=viggle_turbo", "--steps=6"))


def test_cache_key_tracks_load_precision_but_not_generation_cache_settings():
    args = parsed("mflux-generate-z-image-turbo")
    base = ModelCacheKey.of("command", args)
    assert ModelCacheKey.of("command", Namespace(**{**vars(args), "compute_precision": "float16"})) != base
    assert ModelCacheKey.of("command", Namespace(**{**vars(args), "float32": True})) != base
    assert ModelCacheKey.of("command", Namespace(**{**vars(args), "step_cache_ratio": 0.5})) == base
    description = ModelCacheKey.describe(base)
    assert description["compute_precision"] is None
    assert description["float32"] is False
