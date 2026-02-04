.PHONY: setup run build smoke clean lint test

setup:
	uv venv
	uv sync --dev

run:
	uv run python scripts/planka_cli.py status

lint:
	uv run ruff check scripts/ tests/
	uv run ruff format --check scripts/ tests/

lint-fix:
	uv run ruff check --fix scripts/ tests/
	uv run ruff format scripts/ tests/

test:
	uv run pytest tests/ -v

build:
	uv run pyinstaller planka-cli.spec --noconfirm

smoke: build
	@set -e; \
	tmp_home="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmp_home"' EXIT; \
	env -i PATH="/usr/bin:/bin:/usr/sbin:/sbin" HOME="$$tmp_home" \
		PYTHONNOUSERSITE=1 PYTHONPATH= PYTHONHOME= \
		VIRTUAL_ENV= CONDA_PREFIX= CONDA_DEFAULT_ENV= PIPENV_ACTIVE= \
		PYENV_VERSION= UV_PROJECT_ENV= \
		./dist/planka-cli --help

clean:
	rm -rf dist build __pycache__ scripts/__pycache__ tests/__pycache__ .pytest_cache
