.PHONY: install lint test audit docker-build docker-run smoke

install:
	python -m pip install --upgrade pip
	pip install -e ".[dev]"
	pip install pre-commit
	pre-commit install

lint:
	ruff check .
	ruff format --check .
	mypy app

test:
	pytest --cov=app --cov-report=term-missing --cov-fail-under=90

audit:
	pip install pip-audit bandit
	pip-audit -r requirements.txt
	bandit -r app -ll

docker-build:
	docker build -t sakhi-app:local .

docker-run:
	docker run --rm -p 8080:8080 --env-file .env.example sakhi-app:local

smoke:
	bash scripts/smoke_test.sh
