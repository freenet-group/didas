install:
	rm -rf .venv
	python -m venv .venv
	.venv/bin/pip install -e .
