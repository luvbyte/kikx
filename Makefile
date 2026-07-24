.PHONY: all venv run dev test clean

PY_PATH = venv/bin/python3

all: run

venv:
	@if [ ! -f venv/bin/activate ]; then \
		echo "Creating virtual environment..."; \
		rm -rf venv; \
		python3 -m venv venv; \
		echo "Virtual environment created."; \
	fi

venv/.installed: requirements.txt | venv
	$(PY_PATH) -m pip install -r requirements.txt
	@touch venv/.installed
	@echo "Dependencies installed."

run: venv/.installed
	cd kikx && ../$(PY_PATH) main.py

# cli: venv/.installed
# 	cd kikx && ../$(PY_PATH) cli.py

dev: venv/.installed
	cd kikx && ../$(PY_PATH) -m uvicorn core.kikx:kikx_app --reload --timeout-graceful-shutdown 5

setup: venv/.installed
	cd kikx && ../$(PY_PATH) setup.py

test: venv/.installed
	$(PY_PATH) -m pytest

clean:
	rm -rf venv __pycache__ kikx/__pycache__ */__pycache__
	@echo "Cleaned up."
