.PHONY: help install run worker shell clean test

HELP_SPACING=20

help:
	@echo "Employee Recruiter Agent - Management Commands"
	@echo "============================================="
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@echo "  install             Install dependencies using pip"
	@echo "  run                 Start the full system (API + Worker)"
	@echo "  worker              Start only the RQ Worker"
	@echo "  api                 Start only the FastAPI server"
	@echo "  test                Run pytest suite"
	@echo "  clean               Remove logs and pycache"

install:
	pip install -r requirements.txt

run:
	./start.sh

worker:
	rq worker --worker-class rq.SimpleWorker

api:
	python main.py

test:
	pytest tests/

clean:
	rm -f worker.log
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
