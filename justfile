set shell := ["bash", "-cu"]

default:
    @just --list

install:
    uv sync --python 3.14

test:
    MFLUX_PRESERVE_TEST_OUTPUT=1 uv run pytest tests

lint:
    uv run ruff check src tests

format:
    uv run ruff format src tests

build:
    uv build

run *args:
    uv run mflux-webui {{args}}

browser-install:
    PLAYWRIGHT_BROWSERS_PATH=/tmp/mflux-webui-browsers uv run --group browser playwright install chromium

browser-test:
    PLAYWRIGHT_BROWSERS_PATH=/tmp/mflux-webui-browsers uv run --group browser python scripts/smoke_browser.py
