import importlib
import math
from argparse import Namespace
from pathlib import Path

from mflux.utils.dimension_resolver import DimensionResolver

from mflux.web.x746b_ui.memory import MemoryGuard


class AdapterError(ValueError): ...


class CommandAdapter:
    # Keep loading separate from generation for the runner's cache and callbacks.
    # Commands with an upstream Python facade delegate through SharedCommandAdapter.
    command: str = ""
    module: str = ""
    latent_creator_path: str = ""
    builtin_models: tuple[str, ...] = ()
    default_guidance: float | None = None
    default_scheduler: str | None = None
    passes_pid: bool = True
    generation_args: tuple[str, ...] = ()

    def build_parser(self):
        return importlib.import_module(self.module).build_parser()

    def validate(self, args: Namespace) -> None:
        if args.guidance is None and self.default_guidance is not None:
            args.guidance = self.default_guidance
        if self.default_scheduler is not None and "--scheduler" not in args.web_provided_flags:
            args.scheduler = self.default_scheduler

    def load(self, args: Namespace):
        raise NotImplementedError

    def latent_creator(self):
        module_path, name = self.latent_creator_path.rsplit(".", 1)
        return getattr(importlib.import_module(module_path), name)

    def generate(self, model, args: Namespace, seed: int, prompt: str):
        width, height = DimensionResolver.resolve(
            width=args.width, height=args.height, reference_image_path=args.image_path
        )
        kwargs = dict(
            seed=seed,
            prompt=prompt,
            width=width,
            height=height,
            guidance=args.guidance,
            scheduler=args.scheduler,
            image_path=args.image_path,
            num_inference_steps=args.steps,
            image_strength=args.image_strength,
            negative_prompt=args.negative_prompt,
        )
        if self.passes_pid:
            kwargs.update(pid_decode=args.pid_decode, pid_degrade_sigma=args.pid_degrade_sigma)
        kwargs.update({name: getattr(args, name) for name in self.generation_args})
        return model.generate_image(**kwargs)

    @staticmethod
    def lora_kwargs(args: Namespace) -> dict:
        from mflux.cli.parser.parsers import lora_init_kwargs_from_args

        return lora_init_kwargs_from_args(args)

    @staticmethod
    def restricted_config(args: Namespace, registry_key: str, extra_keys: tuple[str, ...] = ()):
        from mflux.models.common.resolution.config_resolution import ConfigResolution

        return ConfigResolution.resolve_restricted(
            args.model, registry_key, model_path=args.model_path, extra_keys=extra_keys, base_model=args.base_model
        )


class SharedCommandAdapter(CommandAdapter):
    command_class: str = ""

    def core_command(self):
        return getattr(importlib.import_module(self.module), self.command_class)

    def validate(self, args: Namespace) -> None:
        self.core_command().validate(args)

    def load(self, args: Namespace):
        return self.core_command().load(args)

    def generate(self, model, args: Namespace, seed: int, prompt: str):
        return self.core_command().generate(model, args, seed, prompt)


def compute_precision(args: Namespace):
    from mflux.models.common.compute_precision import ComputePrecision

    return ComputePrecision.dtype_for(args.compute_precision)


def validate_viggle(args: Namespace) -> None:
    from mflux.models.qwen21.model.qwen21_scheduler import ViggleTurboScheduler

    if args.scheduler == "viggle_turbo" and args.steps != len(ViggleTurboScheduler.SIGMA_NODES):
        raise AdapterError("The viggle_turbo scheduler requires --steps 6.")


class ValidationErrors:
    """Let upstream's cheap argparse validation report web errors without SystemExit."""

    @staticmethod
    def error(message: str):
        raise AdapterError(message)


class FluxAdapter(CommandAdapter):
    command = "mflux-generate"
    module = "mflux.models.flux.cli.flux_generate"
    latent_creator_path = "mflux.models.flux.latent_creator.flux_latent_creator.FluxLatentCreator"
    builtin_models = ("dev", "schnell", "krea-dev")

    def validate(self, args: Namespace) -> None:
        from mflux.cli.defaults import defaults as ui_defaults

        if (args.base_model and "klein" in args.base_model.lower()) or (
            args.model and "flux2-klein" in args.model.lower()
        ):
            raise AdapterError("FLUX.2 Klein is not supported by mflux-generate. Use mflux-generate-flux2 instead.")
        if args.model is None and args.base_model is None:
            raise AdapterError("Choose a model for mflux-generate (dev, schnell, krea-dev or a local checkpoint).")
        if args.guidance is None:
            args.guidance = ui_defaults.GUIDANCE_SCALE

    def load(self, args: Namespace):
        from mflux.models.common.config import ModelConfig
        from mflux.models.flux.variants.txt2img.flux import Flux1

        model_config = ModelConfig.from_name(model_name=args.model, base_model=args.base_model)
        return Flux1(
            model_config=model_config, quantize=args.quantize, model_path=args.model_path, **self.lora_kwargs(args)
        )


class Flux2Adapter(CommandAdapter):
    scheduler_choices = ("flow_match_euler_discrete",)
    command = "mflux-generate-flux2"
    module = "mflux.models.flux2.cli.flux2_generate"
    latent_creator_path = "mflux.models.flux2.latent_creator.flux2_latent_creator.Flux2LatentCreator"
    default_guidance = 1.0

    @property
    def builtin_models(self) -> tuple[str, ...]:
        cli = importlib.import_module(self.module)
        return (cli.DEFAULT_MODEL, *cli.FAMILY_MODELS)

    def validate(self, args: Namespace) -> None:
        super().validate(args)
        cli = importlib.import_module(self.module)
        model_config = self.restricted_config(args, cli.DEFAULT_MODEL, cli.FAMILY_MODELS)
        from mflux.models.common.resolution.config_resolution import ConfigResolution

        named = args.model_path is not None and args.base_model is None
        named = (
            named
            and ConfigResolution.infer_family_member(args.model_path, cli.DEFAULT_MODEL, cli.FAMILY_MODELS) is not None
        )
        judged = args.model_path is None or args.base_model is not None or named
        if judged and args.guidance != 1.0 and "base" not in model_config.model_name.lower():
            raise AdapterError("Guidance other than 1.0 is only supported for FLUX.2 base models.")
        args.scheduler = "flow_match_euler_discrete"

    def load(self, args: Namespace):
        from mflux.models.flux2.variants import Flux2Klein

        cli = importlib.import_module(self.module)
        model_config = self.restricted_config(args, cli.DEFAULT_MODEL, cli.FAMILY_MODELS)
        return Flux2Klein(
            model_config=model_config,
            quantize=args.quantize,
            model_path=args.model_path,
            compute_precision=compute_precision(args),
            **self.lora_kwargs(args),
        )

    def generate(self, model, args: Namespace, seed: int, prompt: str):
        width, height = DimensionResolver.resolve(
            width=args.width, height=args.height, reference_image_path=args.image_path
        )
        return model.generate_image(
            seed=seed,
            prompt=prompt,
            width=width,
            height=height,
            guidance=args.guidance,
            image_path=args.image_path,
            num_inference_steps=args.steps,
            image_strength=args.image_strength,
            scheduler="flow_match_euler_discrete",
            pid_decode=args.pid_decode,
            pid_degrade_sigma=args.pid_degrade_sigma,
        )


class QwenAdapter(SharedCommandAdapter):
    command = "mflux-generate-qwen"
    module = "mflux.models.qwen.cli.qwen_image_generate"
    command_class = "QwenImageCommand"
    latent_creator_path = "mflux.models.qwen.latent_creator.qwen_latent_creator.QwenLatentCreator"
    builtin_models = ("qwen-image",)


class Qwen21Adapter(CommandAdapter):
    command = "mflux-generate-qwen-2.1"
    module = "mflux.models.qwen21.cli.qwen21_generate"
    latent_creator_path = "mflux.models.qwen21.latent_creator.qwen21_latent_creator.Qwen21LatentCreator"
    builtin_models = ("qwen-image-2.1",)
    default_guidance = 1.0
    passes_pid = False
    generation_args = ("step_cache_ratio",)

    def validate(self, args: Namespace) -> None:
        super().validate(args)
        self.restricted_config(args, "qwen-image-2.1")
        validate_viggle(args)

    def load(self, args: Namespace):
        from mflux.models.qwen21.variants.txt2img.qwen_image_21 import QwenImage21

        return QwenImage21(
            quantize=args.quantize,
            model_path=args.model_path,
            model_config=self.restricted_config(args, "qwen-image-2.1"),
            compute_precision=compute_precision(args),
            **self.lora_kwargs(args),
        )


class Qwen21EditAdapter(CommandAdapter):
    scheduler_choices = ("linear", "viggle_turbo")
    command = "mflux-generate-qwen-2.1-edit"
    module = "mflux.models.qwen21.cli.qwen21_edit_generate"
    latent_creator_path = "mflux.models.qwen21.latent_creator.qwen_image21_latent_creator.QwenImage21LatentCreator"
    builtin_models = ("qwen-image-2.1",)
    default_guidance = 1.0
    max_references = 10
    dimension_step = 32

    def validate(self, args: Namespace) -> None:
        super().validate(args)
        from mflux.models.qwen21.variants.edit.qwen_image_21_edit import EDIT_SCHEDULERS

        if args.scheduler not in EDIT_SCHEDULERS:
            raise AdapterError("Qwen-Image-2.1 editing supports linear Euler or viggle_turbo only.")
        validate_viggle(args)
        importlib.import_module(self.module).validate_edit_args(ValidationErrors, args, args.image_paths or [])
        if not math.isfinite(args.guidance) or args.guidance < 1:
            raise AdapterError("guidance must be finite and at least 1.")
        width, height = self._dimensions(args)
        creator = self.latent_creator()
        creator.validate_resolution(args.output_resolution)
        if width is None or height is None:
            from mflux.utils.exif_orientation import oriented_size

            reference_width, reference_height = oriented_size(args.image_paths[-1]) if args.image_paths else (1, 1)
            default_width, default_height = creator.dimensions(
                args.output_resolution, reference_width / reference_height
            )
            width = default_width if width is None else width
            height = default_height if height is None else height
        creator.validate(
            width,
            height,
            args.steps,
            len(args.image_paths or []),
        )
        if max(width, height) > 8192:
            raise AdapterError("Resolved dimensions must be at most 8192 pixels.")
        self.restricted_config(args, "qwen-image-2.1")
        if args.guidance == 1 and args.negative_prompt:
            args.web_messages.append("Negative prompt is ignored when guidance is 1.")

    def load(self, args: Namespace):
        from mflux.models.qwen21.variants.edit.qwen_image_21_edit import QwenImage21Edit

        return QwenImage21Edit(
            quantize=args.quantize,
            model_path=args.model_path,
            model_config=self.restricted_config(args, "qwen-image-2.1"),
            compute_precision=compute_precision(args),
            **self.lora_kwargs(args),
        )

    def generate(self, model, args: Namespace, seed: int, prompt: str):
        from mflux.utils.prompt_util import PromptUtil

        width, height = self._dimensions(args)
        try:
            return model.generate_image(
                seed=seed,
                prompt=prompt,
                negative_prompt=PromptUtil.read_negative_prompt(args),
                width=width,
                height=height,
                num_inference_steps=args.steps,
                guidance=args.guidance,
                image_paths=args.image_paths or [],
                output_resolution=args.output_resolution,
                use_kv_cache=args.use_kv_cache,
                mask_image=args.mask_image,
                auto_mask=args.auto_mask,
                strength=args.strength,
                use_step_cache=args.use_step_cache,
                step_cache_threshold=args.step_cache_threshold,
                enhance_prompt=args.enhance_prompt,
                verify=args.verify,
                verify_retries=args.verify_retries,
                scheduler=args.scheduler,
            )
        finally:
            # Upstream memoizes text-only encodings for CLI reuse without a size limit.
            MemoryGuard.trim_prompt_cache(model)

    @staticmethod
    def _dimensions(args: Namespace) -> tuple[int | None, int | None]:
        from mflux.utils.scale_factor import ScaleFactor

        width, height = args.width, args.height
        if isinstance(width, ScaleFactor) or isinstance(height, ScaleFactor):
            return DimensionResolver.resolve(
                width=width if width is not None else ScaleFactor(1),
                height=height if height is not None else ScaleFactor(1),
                reference_image_path=args.image_paths[-1] if args.image_paths else None,
            )
        return width, height


class ZImageAdapter(SharedCommandAdapter):
    command = "mflux-generate-z-image"
    module = "mflux.models.z_image.cli.z_image_generate"
    command_class = "ZImageCommand"
    latent_creator_path = "mflux.models.z_image.latent_creator.ZImageLatentCreator"
    builtin_models = ("z-image", "z-image-turbo")


class ZImageTurboAdapter(SharedCommandAdapter):
    command = "mflux-generate-z-image-turbo"
    module = "mflux.models.z_image.cli.z_image_turbo_generate"
    command_class = "ZImageTurboCommand"
    latent_creator_path = "mflux.models.z_image.latent_creator.ZImageLatentCreator"
    builtin_models = ("z-image-turbo",)


class Krea2Adapter(SharedCommandAdapter):
    command = "mflux-generate-krea2"
    module = "mflux.models.krea2.cli.krea2_generate"
    command_class = "Krea2Command"
    latent_creator_path = "mflux.models.krea2.latent_creator.Krea2LatentCreator"
    builtin_models = ("krea-2",)


class ErnieImageAdapter(SharedCommandAdapter):
    command = "mflux-generate-ernie-image"
    module = "mflux.models.ernie_image.cli.ernie_image_generate"
    command_class = "ErnieImageCommand"
    latent_creator_path = "mflux.models.ernie_image.latent_creator.ErnieLatentCreator"
    builtin_models = ("ernie-image",)


class ErnieImageTurboAdapter(ErnieImageAdapter):
    command = "mflux-generate-ernie-image-turbo"
    module = "mflux.models.ernie_image.cli.ernie_image_turbo_generate"
    command_class = "ErnieImageTurboCommand"
    builtin_models = ("ernie-image-turbo",)


ADAPTERS: dict[str, CommandAdapter] = {
    adapter.command: adapter
    for adapter in (
        FluxAdapter(),
        Flux2Adapter(),
        QwenAdapter(),
        Qwen21Adapter(),
        Qwen21EditAdapter(),
        ZImageAdapter(),
        ZImageTurboAdapter(),
        Krea2Adapter(),
        ErnieImageAdapter(),
        ErnieImageTurboAdapter(),
    )
}


class ModelCacheKey:
    @staticmethod
    def of(command: str, args: Namespace) -> tuple:
        lora_paths = tuple(getattr(args, "lora_paths", None) or ())
        # Scales and baking only change the weights when there are LoRAs; keying on them
        # otherwise reloads an identical model whenever the checkbox is toggled.
        return (
            command,
            args.model,
            args.model_path,
            args.base_model,
            args.quantize,
            lora_paths,
            tuple(args.lora_scales or ()) if lora_paths else (),
            bool(args.bake_lora) if lora_paths else None,
            getattr(args, "compute_precision", None),
            bool(getattr(args, "float32", False)),
        )

    @staticmethod
    def describe(key: tuple) -> dict:
        command, model, model_path, base_model, quantize, lora_paths, lora_scales, _, precision, float32 = key
        return {
            "command": command,
            "model": model_path and Path(model_path).name or model,
            "base_model": base_model,
            "quantize": quantize,
            "loras": [Path(p).name for p in lora_paths],
            "lora_scales": list(lora_scales),
            "compute_precision": precision,
            "float32": float32,
        }
