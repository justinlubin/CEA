.PHONY: test
test:
	pytest

.PHONY: check
check:
	flake8 src; mypy src

.PHONY: install-local
install-local:
	python -m pip install -e .
