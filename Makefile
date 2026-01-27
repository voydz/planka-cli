.PHONY: setup run build smoke clean

setup:
	uv venv
	uv sync --dev

run:
	uv run python scripts/planka_cli.py status

build:
	uv run pyinstaller --onefile --name planka-cli --collect-all plankapy scripts/planka_cli.py
	chmod +x dist/planka-cli

smoke: build
	@tmp_home="$$(mktemp -d)"; \
	env -i PATH="/usr/bin:/bin:/usr/sbin:/sbin" HOME="$$tmp_home" \
		PYTHONNOUSERSITE=1 PYTHONPATH= PYTHONHOME= \
		./dist/planka-cli --help; \
	rm -rf "$$tmp_home"

clean:
	rm -rf dist build *.spec __pycache__ scripts/__pycache__
