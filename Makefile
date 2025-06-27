VENV?=.venv
BIN=$(VENV)/bin
PY=$(BIN)/python

.PHONY: venv build test profile html info

venv:
	python3 -m venv $(VENV)
	$(PY) -m pip install -U pip wheel

build: venv
	$(PY) -m pip install -e .

test: build
	$(BIN)/pytest -q

profile: build
	$(PY) -m pynytprof.tracer tests/example_script.py

html: profile
	nytprofhtml -f nytprof.out -o report

info:
	$(PY) -m pip list
