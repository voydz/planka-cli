.PHONY: setup run build smoke clean

setup:
	uv venv
	uv sync --dev

run:
	uv run python scripts/planka_cli.py status

build:
	uv run pyinstaller --onefile --name planka-cli --collect-all plankapy scripts/planka_cli.py

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
	rm -rf dist build *.spec __pycache__ scripts/__pycache__
