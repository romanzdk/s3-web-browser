# Inspired by: https://blog.mathieu-leplatre.info/tips-for-your-makefile-with-python.html

PYMODULE := project_name
TESTS := tests
INSTALL_STAMP := .install.stamp
POETRY := $(shell command -v poetry 2> /dev/null)

.DEFAULT_GOAL := help

.PHONY: all
all: install cq test

.PHONY: help
help:
	@echo "Please use 'make <target>', where <target> is one of"
	@echo ""
	@echo "  install     install packages and prepare environment"
	@echo "  cq          run the code linters"
	@echo "  test        run all the tests"
	@echo "  all         install, lint, and test the project"
	@echo "  clean       remove all temporary files listed in .gitignore"
	@echo ""
	@echo "Check the Makefile to know exactly what each target is doing."
	@echo "Most actions are configured in 'pyproject.toml'."

install: $(INSTALL_STAMP)
$(INSTALL_STAMP): pyproject.toml
	@if [ -z $(POETRY) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(POETRY) install --with dev
	touch $(INSTALL_STAMP)

.PHONY: cq
cq: $(INSTALL_STAMP)
    # Configured in pyproject.toml
	$(POETRY) run ruff format .
	$(POETRY) run ruff check --unsafe-fixes --fix .

.PHONY: test
test: $(INSTALL_STAMP)
    # Configured in pyproject.toml
	$(POETRY) run pytest

.PHONY: clean
clean:
    # Delete all files in .gitignore
	git clean -Xdf
