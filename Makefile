.PHONY: test
test:
	pytest

.PHONY: check
check:
	flake8 src; flake8 cli; mypy src; mypy cli

.PHONY: install-local
install-local:
	python -m pip install -e .
