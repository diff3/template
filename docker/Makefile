MAKEFLAGS += --silent

ifneq ("$(wildcard .env)","")
    include .env
    export
endif

CONFIG_ENV := .generated.env
DOCKER_COMPOSE := docker compose --env-file .env --env-file $(CONFIG_ENV)
SERVICES := authserver worldserver proxyserver admin_panel

.DEFAULT_GOAL := help

help:
	@echo "PyPandariaEmu Docker"
	@echo ""
	@echo "Usage:"
	@echo "  make <command>"
	@echo ""
	@echo "Build & setup:"
	@echo "  make config-env     Generate Docker env values from ../config"
	@echo "  make build          Build all service images"
	@echo "  make build-nocache  Build all service images without cache"
	@echo "  make check          Check required local tools"
	@echo ""
	@echo "Server operations:"
	@echo "  make start          Start authserver, worldserver, proxyserver and admin_panel"
	@echo "  make stop           Stop the containers"
	@echo "  make restart        Restart the containers"
	@echo "  make logs           Follow logs for all services"
	@echo "  make ps             Show container status"
	@echo ""
	@echo "Shells:"
	@echo "  make shell SERVICE=authserver"
	@echo "  make shell SERVICE=worldserver"
	@echo "  make shell SERVICE=proxyserver"
	@echo "  make shell SERVICE=admin_panel"
	@echo ""
	@echo "Cleanup:"
	@echo "  make down           Stop and remove containers, keep images"
	@echo "  make clean          Remove dangling Docker images"

check:
	@echo "Checking required dependencies..."
	@if ! command -v docker >/dev/null 2>&1; then \
		echo "Error: docker is not installed."; exit 1; \
	fi
	@if ! docker compose version >/dev/null 2>&1; then \
		echo "Error: docker compose is missing."; exit 1; \
	fi
	@echo "OK"

config-env:
	python generate-env.py

config: config-env
	$(DOCKER_COMPOSE) config

build: config-env
	$(DOCKER_COMPOSE) build $(SERVICES)

build-nocache: config-env
	$(DOCKER_COMPOSE) build --no-cache $(SERVICES)

start: config-env
	$(DOCKER_COMPOSE) up -d $(SERVICES)

stop: config-env
	$(DOCKER_COMPOSE) stop $(SERVICES)

restart: config-env
	$(DOCKER_COMPOSE) restart $(SERVICES)

logs: config-env
	$(DOCKER_COMPOSE) logs -f $(SERVICES)

ps: config-env
	$(DOCKER_COMPOSE) ps

down: config-env
	$(DOCKER_COMPOSE) down

clean:
	docker image prune -f

SERVICE ?= authserver
shell:
	python generate-env.py
	$(DOCKER_COMPOSE) run --rm --entrypoint /bin/sh $(SERVICE)
