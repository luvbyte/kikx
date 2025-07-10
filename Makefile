PHONY: venv install run

VENV_BIN=./venv/bin

# Create a virtual environment
venv:
	@echo "Creating virtual environment"
	python3 -m venv venv
	@echo "Virtual environment created."

# Install dependencies from requirements.txt
install:
	$(VENV_BIN)/pip install -r requirements.txt
	@echo "Dependencies installed."

# Run the Python script
run:
	cd kikx && ../venv/bin/uvicorn main:app --host 0.0.0.0 --port 8055

serve:
	cd kikx && ../venv/bin/uvicorn main:app --reload

test:
	cd kikx && ../venv/bin/python3 test.py

# Clean up the virtual environment and cache
clean:
	rm -rf venv __pycache__ kikx/__pycache__ */__pycache__
	@echo "Cleaned up."
