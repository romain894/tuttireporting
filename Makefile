PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
BISO_ENTITY ?= UNIV-PARIS-SACLAY
BISO_YEAR ?= 2024
BISO_BIBLIOGRAPHY_LIMIT ?= 100
SPHINXOPTS ?=

.DEFAULT_GOAL := help
.PHONY: help test test-unit test-live test-live-biso test-biso example example-biso \
	test-catalogs test-catalogs-pdf test-reports test-reports-pdf docs doc clean

define build_test_reports
	rm -rf build/test-reports
	$(PYTHON) examples/biso/produce.py --full --entity-id "$(BISO_ENTITY)" --year "$(BISO_YEAR)" --bibliography-limit "$(BISO_BIBLIOGRAPHY_LIMIT)" --output build/test-reports/data
	test -s build/test-reports/data/plots/works_bibtex.bib
	$(PYTHON) -m tuttireporting build --manifest build/test-reports/data/manifest.toml --catalog biso --output build/test-reports/biso $(1)
	test -s build/test-reports/biso/references.bib
	$(PYTHON) -m tuttireporting build --manifest build/test-reports/data/manifest.toml --catalog pubpart --output build/test-reports/pubpart $(1)
endef

help:
	@echo "make test                 Run the Python test suite"
	@echo "make test-live            Run all live integration tests"
	@echo "make test-live-biso       Test the live BiSO example (HAL and LaTeX required)"
	@echo "make example              Generate all documented examples"
	@echo "make example-biso         Generate the BiSO example under build/biso"
	@echo "make test-catalogs        Generate all catalog layouts from full producer data"
	@echo "make test-catalogs-pdf    Compile catalog layouts and verify the BiSO bibliography"
	@echo "make docs   Build HTML documentation in docs/html"
	@echo "make clean  Remove the build directory, documentation output, and Python caches"

test: test-unit

test-unit:
	$(PYTHON) -m pytest tests --ignore=tests/integration -v

test-live: test-live-biso

test-live-biso:
	BISO_ENTITY="$(BISO_ENTITY)" BISO_YEAR="$(BISO_YEAR)" $(PYTHON) -m unittest discover -s tests/integration -v

test-biso: test-live-biso

example: example-biso

example-biso:
	$(PYTHON) examples/biso/produce.py --entity-id "$(BISO_ENTITY)" --year "$(BISO_YEAR)"
	$(PYTHON) -m tuttireporting build --manifest build/biso/data/manifest.toml --report examples/biso/report.toml --output build/biso/report --compile --zip

test-catalogs:
	$(call build_test_reports)

test-catalogs-pdf:
	$(call build_test_reports,--compile)

test-reports: test-catalogs

test-reports-pdf: test-catalogs-pdf

docs:
	$(PYTHON) -m sphinx -M html sphinx-doc docs $(SPHINXOPTS)

doc: docs

clean:
	rm -rf build
	rm -rf dist docs tuttireporting.egg-info
	find tuttireporting tests sphinx-doc -type d -name __pycache__ -prune -exec rm -rf {} +
