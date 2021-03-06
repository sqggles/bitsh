# Makefile variables.
SHELL = /bin/bash

# Misc.
TOPDIR = $(shell git rev-parse --show-toplevel)
YAPF_EXCLUDE=*.tox/*,*venv/*

# Docker.
DOCKER_IMAGE = bitsh
DOCKER_IMAGE_VERSION = 0.0.1
DOCKER_IMAGE_FULL = $(DOCKER_IMAGE):$(DOCKER_IMAGE_VERSION)-dev

# External images.
DOCKER_IMAGE_COALA = coala/base:pre

# Docker run command.
DOCKER_RUN_CMD = docker run -t -v=$$(pwd):/code --rm $(DOCKER_IMAGE_FULL)

default: setup

help: # Display help
	@awk -F ':|##' \
		'/^[^\t].+?:.*?##/ {\
			printf "\033[36m%-30s\033[0m %s\n", $$1, $$NF \
		}' $(MAKEFILE_LIST) | sort

ci-coala: ## Run the static analyzers
	@docker pull $(DOCKER_IMAGE_COALA)
	@docker run -t -v=$$(pwd):/app --workdir=/app --rm $(DOCKER_IMAGE_COALA) coala --ci

ci-docs: ## Ensure the documentation builds
	$(DOCKER_RUN_CMD) tox -e docs

ci-tests: ## Run the unit tests
	$(DOCKER_RUN_CMD) tox

clean: ## Remove unwanted files in project (!DESTRUCTIVE!)
	cd $(TOPDIR); git clean -ffdx && git reset --hard

docker-build: Dockerfile ## Build a docker development image
	@docker build -t $(DOCKER_IMAGE_FULL) .

docker-clean:
	@echo "Not implemented"

docs: ## Build documentation
	$(DOCKER_RUN_CMD) sphinx-build -W -b html -d docs/build/doctrees docs/source/ docs/build/html

format: ## Format the codebase using YAPF
	$(DOCKER_RUN_CMD) yapf -r -i -e{$(YAPF_EXCLUDE)} .

format-check: ## Check the code formatting using YAPF
	$(DOCKER_RUN_CMD) yapf -r -d -e{$(YAPF_EXCLUDE)} .

setup: docker-build ## Setup the full environment (default)

venv: venv/bin/activate ## Setup local venv

venv/bin/activate: requirements/local.txt
	test -d venv || virtualenv -p $(PYTHON_EXE) venv
	. venv/bin/activate && pip install -U pip && pip install -r requirements/local.txt
	. venv/bin/activate && python setup.py develop

venv-check-deps: venv ## Check whether the dependencies are up to date
	@{ \
		. venv/bin/activate && OUTDATED_PKGS=$$(pip list -o --format=columns); \
		if [ -n "$${OUTDATED_PKGS}" ]; then \
			echo "$${OUTDATED_PKGS}"; \
			exit 1; \
		fi \
	}

wheel: docker-build ## Build a wheel package
	$(DOCKER_RUN_CMD) python setup.py bdist_wheel

.PHONY: ci-coala ci-docs ci-tests clean docker-build docker-clean docs format format-check service-api setup wheel venv-check
