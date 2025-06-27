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

.PHONY: demo

demo: build
	@echo '[*] Writing test_prog.py...'
	@printf '%s\n' \
'import time' \
'' \
'def factorial(n):' \
'    if n == 0:' \
'        return 1' \
'    return n * factorial(n - 1)' \
'' \
'def main():' \
'    for i in range(5):' \
'        print("factorial(%d) = %d" % (i, factorial(i)))' \
'        time.sleep(0.1)' \
'' \
'if __name__ == "__main__":' \
'    main()' > test_prog.py
	@echo '[*] Profiling test_prog.py...'
	@$(PY) -m pynytprof.tracer test_prog.py
	@echo '[*] Generating HTML report...'
	@nytprofhtml -f nytprof.out -o report
	@echo '[*] Opening report in browser...'
	@xdg-open report/index.html || echo 'Open report/index.html manually.'

