.PHONY: setup run build clean

setup:
	uv venv
	uv sync --dev

run:
	uv run python scripts/planka_cli.py status

build:
	uv run pyinstaller --onefile --name planka-cli scripts/planka_cli.py

clean:
	rm -rf dist build *.spec __pycache__ scripts/__pycache__
