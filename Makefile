.PHONY: setup run build package print-tarball smoke clean lint lint-fix test check

.DEFAULT_GOAL := check

# Platform detection: PyInstaller cannot cross-compile, so every artifact is
# named after the host it was built on. Release artifacts are
# planka-cli-<version>-<os>-<arch>.tar.gz and each target gets its own CI runner.
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

ifeq ($(UNAME_S),Darwin)
	OS := macos
else
	OS := linux
endif

ifneq ($(filter $(UNAME_M),arm64 aarch64),)
	ARCH := arm64
else
	ARCH := x86_64
endif

SHA256 := $(shell command -v sha256sum >/dev/null 2>&1 && echo sha256sum || echo "shasum -a 256")

# Overridable so the release workflow can make the git tag authoritative.
VERSION ?= $(shell grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
TARBALL := planka-cli-$(VERSION)-$(OS)-$(ARCH).tar.gz

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

check: lint test

# The spec has target_arch=None, so the binary follows the host arch.
build:
	uv run pyinstaller --clean --noconfirm planka-cli.spec

package: build
	@set -e; \
	echo "Packaging planka-cli v$(VERSION) for $(OS)-$(ARCH)..."; \
	cd dist && \
	rm -f "$(TARBALL)" "$(TARBALL).sha256" && \
	COPYFILE_DISABLE=1 tar -czf "$(TARBALL)" planka-cli && \
	$(SHA256) "$(TARBALL)" | cut -d' ' -f1 > "$(TARBALL).sha256" && \
	echo "SHA256: $$(cat "$(TARBALL).sha256")"

print-tarball:
	@echo "$(TARBALL)"

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
