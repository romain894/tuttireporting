PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
BISO_ENTITY ?= UNIV-PARIS-SACLAY
BISO_YEAR ?= 2024
SPHINXOPTS ?=

.DEFAULT_GOAL := help
.PHONY: help test test-biso example-biso test-reports test-reports-pdf docs doc clean

define build_test_reports
	rm -rf build/test-reports
	$(PYTHON) examples/biso/produce.py --full --entity-id "$(BISO_ENTITY)" --year "$(BISO_YEAR)" --output build/test-reports/data
	$(PYTHON) -m tuttireporting build --manifest build/test-reports/data/manifest.toml --catalog biso --output build/test-reports/biso $(1)
	$(PYTHON) -m tuttireporting build --manifest build/test-reports/data/manifest.toml --catalog pubpart --output build/test-reports/pubpart $(1)
endef

help:
	@echo "make test   Run the test suite"
	@echo "make test-biso     Test the live BiSO example (HAL and LaTeX required)"
	@echo "make example-biso  Generate the BiSO example under build/biso"
	@echo "make test-reports      Generate full BiSO and PubPart reports from scratch"
	@echo "make test-reports-pdf  Generate and compile full reports with default templates"
	@echo "make docs   Build HTML documentation in docs/html"
	@echo "make clean  Remove the build directory, documentation output, and Python caches"

test:
	$(PYTHON) -m unittest discover -s tests -v

test-biso:
	BISO_ENTITY="$(BISO_ENTITY)" BISO_YEAR="$(BISO_YEAR)" $(PYTHON) -m unittest discover -s tests/integration -v

example-biso:
	$(PYTHON) examples/biso/produce.py --entity-id "$(BISO_ENTITY)" --year "$(BISO_YEAR)"
	$(PYTHON) -m tuttireporting build --manifest build/biso/data/manifest.toml --report examples/biso/report.toml --output build/biso/report --compile --zip

test-reports:
	$(call build_test_reports)

test-reports-pdf:
	$(call build_test_reports,--compile)

docs:
	$(PYTHON) -m sphinx -M html sphinx-doc docs $(SPHINXOPTS)

doc: docs

clean:
	rm -rf build
	rm -rf dist docs tuttireporting.egg-info
	find tuttireporting tests sphinx-doc -type d -name __pycache__ -prune -exec rm -rf {} +
