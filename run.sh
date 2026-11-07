#!/usr/bin/env bash
set -e

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

uv sync --locked
uv build
exec uv run --no-sync database
