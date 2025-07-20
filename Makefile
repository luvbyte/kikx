PHONY: venv install run

PY_PATH=venv/bin/python3

# Create a virtual environment
venv:
	@echo "Creating virtual environment"
	python3 -m venv venv
	@echo "Virtual environment created."

# Install dependencies from requirements.txt
install:
	$(PY_PATH) -m pip install -r requirements.txt
	@echo "Dependencies installed."

# Run the Python script
run:
	cd kikx && ../$(PY_PATH) main.py

serve:
	cd kikx && ../$(PY_PATH) -m uvicorn main:app --reload

test:
	cd kikx && ../$(PY_PATH) -m pytest

# Clean up the virtual environment and cache
clean:
	rm -rf venv __pycache__ kikx/__pycache__ */__pycache__
	@echo "Cleaned up."
