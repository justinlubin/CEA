.PHONY: test
test:
	python -m unittest

.PHONY: check
check:
	flake8 src; mypy --strict src

.PHONY: install-local
install-local:
	python -m pip install -e .

.PHONY: deps
deps:
	python -m pip install -r direct_requirements.txt

.PHONY: dev-deps
dev-deps:
	python -m pip install -r dev_requirements.txt

.PHONY: freeze
freeze:
	python -m pip freeze > requirements.txt
