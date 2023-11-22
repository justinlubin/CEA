.PHONY: run
run:
	python -m cli

.PHONY: test
test:
	pytest

.PHONY: check
check:
	flake8 src; flake8 cli; mypy src; mypy cli
