PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PYTEST_ARGS ?=
BISO_ENTITY ?= UNIV-PARIS-SACLAY
BISO_YEAR ?= 2024
BISO_BIBLIOGRAPHY_LIMIT ?= 100
SPHINXOPTS ?=

.DEFAULT_GOAL := help
.PHONY: help test test-pdf test-live test-all example docs clean

help:
	@echo "make test       Run the fast offline tests"
	@echo "make test-pdf   Run offline tests including LaTeX compilation"
	@echo "make test-live  Run live producer and catalog integration tests"
	@echo "make test-all   Run all tests, including PDF and live integration tests"
	@echo "make example    Generate the BiSO example under build/biso"
	@echo "make docs       Build HTML documentation in docs/html"
	@echo "make clean      Remove build outputs and Python caches"
	@echo "Use PYTEST_ARGS='...' to pass pytest options to any test command"

test:
	$(PYTHON) -m pytest $(PYTEST_ARGS)

test-pdf:
	$(PYTHON) -m pytest --run-pdf $(PYTEST_ARGS)

test-live:
	BISO_ENTITY="$(BISO_ENTITY)" BISO_YEAR="$(BISO_YEAR)" BISO_BIBLIOGRAPHY_LIMIT="$(BISO_BIBLIOGRAPHY_LIMIT)" $(PYTHON) -m pytest --run-live -m live $(PYTEST_ARGS)

test-all:
	BISO_ENTITY="$(BISO_ENTITY)" BISO_YEAR="$(BISO_YEAR)" BISO_BIBLIOGRAPHY_LIMIT="$(BISO_BIBLIOGRAPHY_LIMIT)" $(PYTHON) -m pytest --run-pdf --run-live $(PYTEST_ARGS)

example:
	$(PYTHON) examples/biso/produce.py --entity-id "$(BISO_ENTITY)" --year "$(BISO_YEAR)"
	$(PYTHON) -m tuttireporting build --manifest build/biso/data/manifest.toml --report examples/biso/report.toml --output build/biso/report --compile --zip

docs:
	$(PYTHON) -m sphinx -M html sphinx-doc docs $(SPHINXOPTS)

clean:
	rm -rf build
	rm -rf dist docs tuttireporting.egg-info
	find tuttireporting tests sphinx-doc -type d -name __pycache__ -prune -exec rm -rf {} +
