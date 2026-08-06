# Mew AI Control Makefile

.PHONY: help start start-backend start-frontend stop status clean

help:
	@echo "Mew AI Control Panel:"
	@echo "  make start            - Launch both backend & frontend servers in background"
	@echo "  make start-backend    - Run FastAPI backend in foreground"
	@echo "  make start-frontend   - Run Frontend HTTP server in foreground"
	@echo "  make stop             - Stop any running Mew servers"
	@echo "  make status           - Check if servers are running"
	@echo "  make clean            - Remove logs and python cache files"

start: stop
	@echo "Launching backend server..."
	@nohup backend/.venv/bin/uvicorn backend.main:app --port 8000 --reload > backend.log 2>&1 &
	@echo "Launching frontend server..."
	@nohup python3 -m http.server 3000 --directory claude_frontend/landing.html > frontend.log 2>&1 &
	@sleep 1
	@make status

start-backend:
	@echo "Starting FastAPI backend on port 8000..."
	backend/.venv/bin/uvicorn backend.main:app --port 8000 --reload

start-frontend:
	@echo "Starting Frontend HTTP server on port 3000..."
	python3 -m http.server 3000 --directory claude_frontend/landing.html

stop:
	@echo "Stopping any running servers..."
	-@kill -9 $$(lsof -t -i :8000) 2>/dev/null || true
	-@kill -9 $$(lsof -t -i :3000) 2>/dev/null || true
	@echo "Stopped."

status:
	@echo "Checking server ports..."
	@lsof -i :8000 && echo "Backend (8000): RUNNING" || echo "Backend (8000): STOPPED"
	@lsof -i :3000 && echo "Frontend (3000): RUNNING" || echo "Frontend (3000): STOPPED"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f backend.log frontend.log
