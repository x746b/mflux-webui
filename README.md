# mflux-webui

A standalone browser UI for [mflux](https://github.com/mflux-community/mflux), with local image generation, a gallery, and optional oMLX/OpenAI prompt assistance. This repository contains only the UI and its supporting assets and tests.

I built the UI because I wanted to try new prompts without typing long commands each time. Pick a model, write a prompt, and press **Generate**. The forms are built from the supported CLI commands' options, and requests are validated by those commands' own argument parsers. With model caching enabled, weights stay loaded between runs so repeated generations can skip the loading step.

The optional prompt assistant helps develop ideas using local oMLX inference or the OpenAI API. A startup progress bar shows which command options or local files are being loaded, while the gallery keeps generated images and their settings easy to revisit.

### How it works

```mermaid
flowchart LR
    A["You choose a model<br/>and write a prompt"] --> B["Web UI<br/>Checks settings and queues the job"]
    B --> C["Upstream mflux<br/>Generates the image on your Mac"]
    C --> D["Image + saved settings<br/>View, download or reuse in the gallery"]
    E["Optional prompt assistant<br/>Local oMLX or OpenAI"] -.->|Suggests prompt text| A
```

- **The browser is the control panel.** Pick models and LoRAs, edit prompts, and watch generation progress.
- **mflux runs the image generation locally.** The UI validates settings using mflux's command parsers and calls its Python API in a background worker.
- **Your images stay in the output folder you choose.** The gallery reads them and their saved settings from disk.
- **Chat is optional.** Choose local oMLX or the OpenAI API to help with prompt ideas. OpenAI chat sends submitted conversation text to OpenAI; image generation still runs locally.
- **The CLI remains available.** Each job shows an equivalent command you can copy into a terminal.

For the frontend, API, worker, and execution diagrams, see [Architecture](https://github.com/x746b/mflux-webui/blob/main/docs/architecture.md).

### A look at the UI

![Generate page with the local oMLX prompt assistant](https://raw.githubusercontent.com/x746b/mflux-webui/main/docs/Screenshot-1.png)

*Generate with the local oMLX prompt assistant. Generation controls are on the left; the result and equivalent CLI command are on the right. Use **Copy CLI command** to take a run back to the terminal. The top bar shows worker status and memory use, with an **Unload** button when a cached model can be released.*

![Generate page with the OpenAI prompt assistant](https://raw.githubusercontent.com/x746b/mflux-webui/main/docs/Screenshot-2.png)

*The same prompt assistant connected to OpenAI, with GPT-6 Luna and GPT-6.1 Sol available. **Use this prompt** transfers a suggestion into the generation form. Each provider keeps its own conversation and draft.*

![Gallery](https://raw.githubusercontent.com/x746b/mflux-webui/main/docs/Screenshot-3.png)

*The gallery. Open an image to inspect its generation settings, download it, or use **Reuse settings** to restore its options and seed in the form.*

![Image generated with the standalone UI and local prompt assistant](https://raw.githubusercontent.com/x746b/mflux-webui/main/docs/Screenshot-samples-1.png)

*A sample generated with the standalone package using Krea 2, a LoRA, and the local oMLX prompt assistant.*

---

### Install and run

The distribution is named **mflux-webui-uno**, version **0.2.2**. The command remains `mflux-webui`. This release requires Apple Silicon, Python 3.12 or newer, and the published `mflux 0.22.x` core from PyPI; no Git override or mflux fork is required.

Install or update to the tagged Git release:

```bash
uv tool install --force --refresh --python 3.14 \
  "mflux-webui-uno @ git+https://github.com/x746b/mflux-webui@v0.2.2"
```

This version is not yet published on PyPI. After publication, the equivalent PyPI installation will be:

```bash
uv tool install --force --refresh --python 3.14 mflux-webui-uno
```

If you previously installed the distribution named `mflux-webui` with `uv tool`, first run `uv tool uninstall mflux-webui`, then install `mflux-webui-uno` as above. The executable name, configuration, generated images, and model directories remain the same. Remove any old `--with "mflux @ git+..."` override from your installation command so the registry dependency can be resolved normally.

#### Run

```bash
mflux-webui --models-dir ~/AI/models/_diffusers_ --lora-dir ~/AI/models/_diffusers_/_LoRAs_ --output-dir ~/AI/mflux-web/outputs --max-memory-gb 110 --cache-size 0
```

Then open http://127.0.0.1:8001.

Adjust the paths and memory budget to suit your machine. The example uses `--cache-size 0` to unload weights after each run; omit it to keep a model cached for repeated generations.

`--models-dir` is the folder where you keep downloaded checkpoints. Each subfolder shows up under Weights → Local folder. Generated images land in `--output-dir`, each with a small JSON file holding its settings; that is what the gallery reads.

---

### News

- **Prompt assistant:** discuss ideas with GPT-6 Luna, GPT-6.1 Sol, or an oMLX model, expand or shorten prompts, and insert suggestions into the generation form. Enable or disable the assistant in Settings.
- **Settings tab:** choose System, Light, or Dark appearance with Orange, Blue, or Teal accents. Select the assistant provider and check its configuration, Hugging Face token status, loaded models, directories, memory limits, and idle unload time.
- **Startup progress:** see which command is loading, followed by model-folder and LoRA scans, with elapsed time and a progress bar. Detailed timings are available in the server log.
- **Easier LoRA selection:** LoRAs sit directly below the model controls and display paths relative to `--lora-dir`. Bake LoRA into weights is unchecked by default.
- **Local weights by default:** starting with `--models-dir` selects Local folder for fresh or reset forms. Saved selections still take precedence.
- **Qwen Image 2.1 editing:** use up to 10 ordered reference images, keep uploads when switching model families, and reuse settings from the gallery.
- **Memory controls:** configure an active-memory budget and idle unloading, monitor memory in the top bar, and unload cached models when needed.

---

### Good to know

- **Prompt assistant.** Enabled by default; uncheck **Enable prompt assistant** in Settings to hide its button and stop active replies in tabs of this browser. Choose OpenAI with GPT-6 Luna (default) or GPT-6.1 Sol, or oMLX with the model configured on the server. **Use current prompt**, **Expand**, **Shorten**, and **Suggest variations** prepare a draft; **Send** starts the request. Replies stream, **Stop** cancels the connection, and **Use this prompt** inserts a suggestion after confirming replacement. Each provider has its own in-memory history and draft, so switching providers does not transfer conversations. Chat clears on reload/navigation; **Clear chat** resets only the selected provider's history and leaves the generation prompt untouched. Settings saves provider/model/style preferences per browser. OpenAI API charges apply; oMLX uses its configured inference server.
- **Settings.** The Settings tab shows whether the server detects a Hugging Face token, with login instructions if needed. This is a local presence check, not a validation of access; tokens are never displayed or stored by the Web UI. Choose System, Light, or Dark appearance and an Orange, Blue, or Teal accent; appearance is saved per browser. Runtime information lists loaded models, model/LoRA/output directories, the effective memory budget, and idle unload time. Use Refresh status to update this snapshot; change server options at startup.
- **Built-in or Local folder.** "Built-in" downloads the model from Hugging Face. With `--models-dir`, fresh or reset forms default to Local folder; set the base model to match the checkpoint (for example `qwen-image-2.1`). Saved form selections take precedence over defaults.
- **LoRAs.** The LoRA section is directly below Base model and Quantize. Local choices show paths relative to `--lora-dir`, with numbered labels for duplicate names across directories. Full paths are retained for generation. You can also enter a path, Hugging Face repository, or library name. **Bake LoRA into weights** is unchecked by default; saved settings can restore a previous choice.
- **Sizes.** The small buttons are the usual sizes around 1 megapixel. "More sizes" has wider ratios (16:10, 21:9, 2.39:1, 32:9 and portrait versions), and "Resolution" scales them from 0.5 to 4 MP.
- **Several images at once.** Put `1, 2, 3` in Seeds and you get three images from one run.
- **No scrolling to the button.** Generate is also in the top bar, and Cmd/Ctrl+Enter works anywhere in the form.
- **Memory.** The active MLX memory budget defaults to 75% of RAM; set `--max-memory-gb 64` to lower it when other apps or an LLM also need memory. The buffer cache stays capped at 25% of that budget. Jobs stop at callback checkpoints if active memory exceeds the budget, queued jobs are cancelled, and cached models unload. Retained-memory growth also triggers unloading between jobs. This is a soft guard, not a hard process-memory ceiling. The top-bar tooltip shows both limits. Use `--cache-size 0` to unload after every run, or `--idle-unload MINUTES` to change the default 10-minute idle timeout.
- **History.** Recent jobs are kept only in memory and are gone when the server stops. "Clear history" drops finished jobs, unused uploads and saved generation drafts. Appearance and assistant preferences are kept, as are references needed by queued or running jobs. Images in the gallery stay until you delete them there. Use **Clear chat** separately to reset the prompt conversation.
- **Queue capacity.** Up to 16 pending generation jobs can wait behind the running job. Further submissions receive a queue-full message and can be retried later. Each job can still contain several seeds.
- **Supported models.** Text-to-image, plus image-to-image and LoRAs, for FLUX.1, FLUX.2, Qwen Image, Qwen Image 2.1, Z-Image, Krea 2 and ERNIE-Image. Qwen Image 2.1 editing is also available. The UI exposes ten commands; newer upstream commands such as Ming and Qwen ControlNet, other edit commands, fill and upscaling remain CLI-only.
- **Qwen 2.1 editing.** Choose **qwen 2.1 edit**, select your Qwen-Image-2.1 weights, and optionally add up to 10 reference images. Their order matches “image 1”, “image 2”, etc. in your prompt. Leave width and height empty to derive the size from the last reference and the advanced **Output resolution** setting (square when no reference is supplied); explicit dimensions must be multiples of 32. RGBA output is saved as PNG. **Use KV cache** can be disabled in Advanced. Editing requires at least two steps and guidance of 1 or more. LoRAs are supported. Text-based auto-mask is supported; manual mask image uploads are not available in the UI.
- **Quiet console.** The page polls the server all the time. Those requests are only logged with `--log-level debug`.
- **Initial loading.** The Generate page shows the command currently loading, then the model-folder and LoRA scans, with elapsed time and a progress bar. Progress counts completed discovery steps, not estimated time remaining. The server logs how long each command schema takes on its first build, followed by totals for schema setup, model-folder discovery, and LoRA scanning. Shared dependency imports count toward the first command that needs them; later requests reuse cached schemas. If loading fails, the page shows an error and a reload button.

### OpenAI prompt assistant setup

The server reads `OPENAI_API_KEY` from its environment. For a terminal launch, add this line to your `~/.zshrc` using an editor, replacing the placeholder locally:

```bash
export OPENAI_API_KEY="your-api-key"
```

Open a new terminal, then start `mflux-webui` with your usual options. An already-running server must be restarted to inherit the key. Alternatively, export the variable only in the shell used to start the server. Background services need their own environment configuration; the Web UI does not read or execute `~/.zshrc` or load `.env` files.

Keep credentials outside the repository. The browser receives only key-presence status, never the key. Opening the assistant or Settings makes no paid request. Sending a chat message uses your API project; anybody permitted to use this Web UI can use its configured assistant. No image, local model path, or generation prompt is automatically attached. Requests use the Responses API with `store=false`, no tools, low reasoning, and bounded context/output; conversation history is explicitly resent with each turn.

The assistant currently supports `gpt-6-luna` and `gpt-6.1-sol`. Access depends on your API project. Provider errors are shown without exposing provider diagnostics or credentials. Cancelling closes the stream; work already processed may still be billed.

Chat requests have an overall deadline of two minutes for OpenAI and five minutes for oMLX, including model loading and response streaming. A timeout closes the upstream connection and frees the chat slot. Responses are limited to 2 MiB in total, with individual SSE lines and events limited to 256 KiB before JSON parsing. Streaming requests use uncompressed responses so these limits also bound decoding buffers.

Reference: [OpenAI API setup](https://developers.openai.com/api/docs/quickstart) and [streaming responses](https://developers.openai.com/api/docs/guides/streaming-responses).

### oMLX prompt assistant setup

Add these exports to the environment that launches `mflux-webui`, for example in `~/.zshrc`. Replace the key placeholder locally and use the exact model name or alias shown in oMLX:

```bash
export OMLX_API_KEY="your-omlx-api-key"
export OMLX_MFLUX_MODEL="Qwen3.6-35B-A3B-8bit"
# Optional: this is the default API base address.
export OMLX_BASE_URL="http://127.0.0.1:8000/v1"
```

Open a new terminal and restart `mflux-webui`, then choose **oMLX** in Settings → Prompt assistant or in the chat panel. Both the key and model variable are required. oMLX must be running and recognize the configured model. The Web UI inherits exported variables; it does not source `~/.zshrc` or store credentials in the browser.

Plain HTTP is allowed only for loopback addresses or `localhost`; `localhost` is normalized to `127.0.0.1`. For an oMLX server on another machine, use an HTTPS API base URL with a valid certificate. Redirects are not followed.

Both providers share the assistant's instructions, style preferences, prompt actions, and context/output limits. oMLX uses streaming Chat Completions and requests non-thinking replies for responsive prompt editing. Its response timeout allows additional time for local model loading. Opening Settings or the assistant only checks configuration locally; it does not contact the inference server or load models. Missing oMLX configuration or a connection failure never falls back to OpenAI automatically.

The enable switch is a browser preference, not a server access control. Normal Web UI authentication still protects both chat backends. Local inference shares system memory with image generation; mflux does not manage oMLX's model cache.

Reference: [oMLX documentation](https://github.com/jundot/omlx).

### Using it from another machine

Out of the box `mflux-webui` listens only on 127.0.0.1 and has no password, which is fine when you are the only user of your Mac. The simplest way to use it from a laptop is an SSH tunnel, which needs no configuration at all:

```sh
ssh -L 8001:127.0.0.1:8001 you@your-mac
# then open http://127.0.0.1:8001 on the laptop
```

If you do want it on the network, it will not start without an API key. Pass the key through the environment, since command lines are visible to other users on the machine:

```sh
export MFLUX_WEB_API_KEY='something-long-and-random'
mflux-webui --host 0.0.0.0 --models-dir ~/AI/models
```

This is plain HTTP, so for anything beyond your home network put TLS in front. With Tailscale that is `tailscale serve --bg 8001`, plus `--allowed-host your-mac.your-tailnet.ts.net --behind-https` for mflux-webui. Or use `--tls-cert` / `--tls-key` directly.

Whatever you choose, the UI only reads models from `--models-dir` (and LoRAs from `--lora-dir`) and only writes to `--output-dir`. It cannot be pointed at other files on the machine. `mflux-webui --help` lists every option.

Login and bearer-key authentication share failed-attempt throttling. Requests exceeding the authentication or queue limit return HTTP 429 with a `Retry-After` header. Incoming request bodies are limited before parsing: 16 KiB for login/setup, 256 KiB for ordinary JSON requests, 320,000 bytes for chat, and the configured upload size plus 1 MiB of multipart overhead for uploads. The individual uploaded image must still fit `--max-upload-mb`. Oversized bodies return HTTP 413.


### Development

```bash
git clone https://github.com/x746b/mflux-webui
cd mflux-webui
uv sync --python 3.14
uv run mflux-webui --models-dir ~/AI/models --lora-dir ~/AI/models/_LoRAs_
MFLUX_PRESERVE_TEST_OUTPUT=1 uv run pytest tests
uv run ruff check src tests
uv build
```

The `justfile` provides equivalent install, run, test, lint, format, and build recipes. Dependencies are isolated in `.venv`; no system Python installation is needed.

For browser checks, run `just browser-install` followed by `just browser-test`. Chromium is kept under `/tmp/mflux-webui-browsers`; screenshots and logs go to the ignored `artifacts/` directory. These checks use mocked chat replies and do not generate images or make paid API requests.

### Packaging and compatibility

The distribution owns only `mflux.web.x746b_ui`. It does not ship `mflux/__init__.py`, `mflux/web/__init__.py`, or any core model code. `mflux` supplies the inference implementation, while this package declares its web dependencies directly. Templates, JavaScript, CSS, and the favicon are included in the wheel.

The `mflux-webui` command is distinct from other packages' `mflux-web` commands. Existing output directories, `MFLUX_WEB_*` server settings, OpenAI/oMLX variables, and browser preferences remain compatible with the original UI. The default output directory stays `~/AI/mflux-web/outputs`.

Qwen geometry and prompt caches are trimmed by the UI after generation; upstream model files are not patched. The adapters depend on mflux APIs that can change, so every core dependency update needs automated checks and real generation testing.

The dependency is `mflux>=0.22.0,<0.23.0` from PyPI. The lockfile uses the registry release, and wheel installations carry the same version bounds without a source override. Startup checks the installed core's release series and required files and reports an actionable error for incompatible installations.

See [core compatibility and release checks](https://github.com/x746b/mflux-webui/blob/main/docs/compatibility.md) for the tested baseline, package boundaries, and validation details.

### License

MIT for the project and mflux-derived portions; the adapted authentication module also retains its Apache-2.0 notice. See `LICENSE`, `NOTICE`, and `licenses/`.
