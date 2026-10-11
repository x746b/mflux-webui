import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


class BrowserSmoke:
    @staticmethod
    def run(server_python: Path, artifacts: Path) -> None:
        artifacts = artifacts.resolve()
        artifacts.mkdir(parents=True, exist_ok=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        env = dict(os.environ)
        for name in ("OPENAI_API_KEY", "OMLX_API_KEY", "MFLUX_WEB_API_KEY", "MFLUX_WEB_SECRET_KEY"):
            env.pop(name, None)
        command = [
            str(server_python.parent / "mflux-webui"),
            "--port",
            str(port),
            "--max-memory-gb",
            "2",
            "--output-dir",
            str(artifacts / "outputs"),
            "--config",
            str(artifacts / "state.json"),
        ]
        with (artifacts / "server.log").open("w") as log:
            server = subprocess.Popen(command, env=env, stdout=log, stderr=log)
            try:
                for _ in range(300):
                    if server.poll() is not None:
                        raise RuntimeError("Server exited; see artifacts/browser/server.log")
                    try:
                        urllib.request.urlopen(url + "/api/session", timeout=1).close()
                        break
                    except urllib.error.URLError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Server startup timed out")
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    page.set_default_timeout(60000)
                    expect.set_options(timeout=60000)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("dialog", lambda dialog: dialog.accept())
                    page.goto(url)
                    expect(page.locator("#form-loading")).to_be_hidden()
                    expect(page.locator("#generate")).to_be_enabled()
                    data = page.request.get(url + "/api/commands").json()
                    assert len(data["commands"]) == 10
                    assert all(item["available"] for item in data["commands"])
                    config = page.request.get(url + "/api/chat/config").json()
                    assert config["default_model"] == "gpt-6-luna"
                    assert config["models"] == [
                        {"id": "gpt-6-luna", "name": "GPT-6 Luna"},
                        {"id": "gpt-6.1-sol", "name": "GPT-6.1 Sol"},
                    ]
                    for provider in config["providers"].values():
                        provider["configured"] = True
                    config["providers"]["omlx"].update(
                        default_model="test-model", models=[{"id": "test-model", "name": "Test model"}]
                    )
                    page.route("**/api/chat/config", lambda route: route.fulfill(json=config))
                    reply = (
                        "\n".join(
                            json.dumps(item)
                            for item in (
                                {"type": "delta", "text": "```prompt\nA quiet street in Prague\n```"},
                                {"type": "done", "usage": {"input_tokens": 10, "output_tokens": 8}},
                            )
                        )
                        + "\n"
                    )
                    page.route(
                        "**/api/chat", lambda route: route.fulfill(content_type="application/x-ndjson", body=reply)
                    )
                    page.locator('[data-flag="--prompt"]').fill("Original idea")
                    page.locator("[data-chat-launcher]").click()
                    page.locator("#chat-input").fill("Suggest a street scene")
                    page.locator("#chat-send").click()
                    page.get_by_role("button", name="Use this prompt", exact=True).click()
                    expect(page.locator('[data-flag="--prompt"]')).to_have_value("A quiet street in Prague")
                    page.locator("#chat-provider").select_option("omlx")
                    expect(page.locator("#chat-messages .chat-message")).to_have_count(0)
                    page.locator("#chat-input").fill("Local draft")
                    page.locator("#chat-provider").select_option("openai")
                    expect(page.locator("#chat-messages .chat-message")).to_have_count(2)
                    expect(page.locator("#chat-input")).to_have_value("")
                    page.locator("#chat-close").click()
                    legacy_preferences = {
                        "enabled": False,
                        "provider": "omlx",
                        "model": "gpt-6-sol",
                        "instructions": "Keep my cinematic style",
                    }
                    page.evaluate(
                        "value => localStorage.setItem('mflux-web:chat-preferences', JSON.stringify(value))",
                        legacy_preferences,
                    )
                    page.goto(url + "/settings")
                    expect(page.locator("#assistant-model")).to_have_value("gpt-6.1-sol")
                    expect(page.locator("#assistant-provider")).to_have_value("omlx")
                    expect(page.locator("#assistant-enabled")).not_to_be_checked()
                    expect(page.locator("#assistant-instructions")).to_have_value("Keep my cinematic style")
                    assert page.evaluate("JSON.parse(localStorage.getItem('mflux-web:chat-preferences'))") == {
                        **legacy_preferences,
                        "model": "gpt-6.1-sol",
                    }
                    page.locator("#assistant-enabled").check()
                    page.locator("#assistant-provider").select_option("openai")
                    expect(page.locator("#assistant-model option")).to_have_text(["GPT-6 Luna", "GPT-6.1 Sol"])
                    page.reload()
                    expect(page.locator("#assistant-model")).to_have_value("gpt-6.1-sol")
                    page.locator("#appearance-theme").select_option("dark")
                    page.locator("#appearance-accent").select_option("teal")
                    expect(page.locator("html")).to_have_attribute("data-accent", "teal")
                    page.locator("#assistant-enabled").uncheck()
                    page.goto(url)
                    expect(page.locator("#form-loading")).to_be_hidden()
                    expect(page.locator("[data-chat-launcher]")).to_be_hidden()
                    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
                    page.goto(url + "/gallery")
                    expect(page.get_by_role("heading", name="Gallery")).to_be_visible()
                    page.screenshot(path=str(artifacts / "gallery.png"))
                    assert not errors, errors
                    browser.close()
                print(
                    "Browser checks passed: all command schemas, assets, chat, provider isolation, preferences and gallery."
                )
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Browser checks without model generation or paid API requests.")
    parser.add_argument("--server-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts/browser"))
    args = parser.parse_args()
    BrowserSmoke.run(args.server_python, args.artifacts)
