# Monorepo command contract (blueprint 09 §8). Every target below must exist
# and do what it says; a target that cannot run must FAIL, never silently pass.
# No `|| true`, no `2>/dev/null || true` anywhere in this file.
# Recipes use only syntax shared by POSIX sh and Windows cmd (GNU make falls back
# to cmd when no sh is on PATH): `cd dir && cmd`, make functions, Python scripts.
# Compose resolves .env next to the first -f file, so the root .env is passed explicitly.
COMPOSE := docker compose --env-file .env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml
UV_BE := uv run --frozen --extra dev
# Repo scripts run in the locked backend environment (pyyaml etc.) on every OS.
PY := uv run --project apps/backend --frozen --extra dev python
BACKEND_IMAGE := backend:ci
WEB_IMAGE := web:ci
# Tool images are digest-pinned here. CI does not repeat the tags.
TRIVY_IMAGE := aquasec/trivy:0.63.0@sha256:6fb0646988fcd2fdf7bf123f7174945ebc2c9c72d1fa1567c8d7daeeb70f8037
SYFT_IMAGE := anchore/syft:v1.29.0@sha256:e86b0ba0b1d2fe8a2e9f96ed9b22033df9781f43b9a7eb27c57e6c89234946bc
export MP_API_BASE_URL := https://api.example.com
ifeq ($(OS),Windows_NT)
BASH := "C:/Program Files/Git/bin/bash.exe"
else
BASH := bash
endif

.PHONY: help
help: ## Show this help
	@$(PY) -c "import re; [print(f'  {t:<24}{d}') for t, d in re.findall(r'(?m)^([a-zA-Z_-]+):.*?## (.*)', open('Makefile', encoding='utf-8').read())]"

# ---------- setup ----------
.PHONY: bootstrap
bootstrap: ## Check tools, lockfiles and prerequisites (installs nothing)
	$(PY) scripts/dev/bootstrap.py

.PHONY: doctor
doctor: ## Diagnose selected clients, tools, ports, external deps (no secrets printed)
	$(PY) scripts/dev/doctor.py

.PHONY: dev
dev: ## Start the selected dev topology
	$(COMPOSE) up --build

.PHONY: dev-down
dev-down: ## Stop the dev topology
	$(COMPOSE) down

# ---------- contracts ----------
.PHONY: check-contract
check-contract: ## Lint the hand-written contract (Spectral ruleset)
	pnpm exec spectral lint contracts/http/openapi.yaml --ruleset .spectral.yaml
# begin template-only
	$(PY) scripts/quality/check_wechat_contract.py
# end template-only

# begin template-only
.PHONY: check-generator
check-generator: ## Copy few-shot and empty-capability projects; Spectral, compose, ruff
	$(PY) scripts/quality/check_generator.py
# end template-only

.PHONY: check-breaking
check-breaking: ## Fail on breaking contract changes vs git HEAD (oasdiff)
	$(PY) scripts/quality/check_breaking.py

.PHONY: generate
generate: check-contract ## Validate contract sources, regenerate SDKs/DTOs (blueprint 02 §8)
	$(PY) scripts/contracts/generate.py

.PHONY: check-generated
check-generated: ## Regenerate into a clean temp dir and diff the full file set
	$(PY) scripts/contracts/generate.py --check

# ---------- quality ----------
.PHONY: lint-py
lint-py: ## Static checks: Python (ruff)
	cd apps/backend && $(UV_BE) ruff check src tests ../../scripts
	cd apps/backend && $(UV_BE) ruff format --check src tests ../../scripts

.PHONY: lint-ts
lint-ts: ## Static checks: TypeScript (eslint)
	pnpm exec eslint .

.PHONY: lint
lint: lint-py lint-ts ## Static checks: Python + TS + configs

.PHONY: typecheck-py
typecheck-py: ## Typecheck backend
	cd apps/backend && $(UV_BE) mypy src

.PHONY: typecheck-ts
typecheck-ts: ## Typecheck every selected app and shared package
	pnpm -r exec tsc --noEmit

.PHONY: typecheck
typecheck: typecheck-ts typecheck-py ## Typecheck every selected app and shared package

.PHONY: check-architecture
check-architecture: ## Enforce import direction, module/package/workspace boundaries
	cd apps/backend && $(UV_BE) pytest tests/architecture -q

.PHONY: check-specs
check-specs: ## Spec format, IDs and test traceability (blueprint 10 §3)
	$(PY) scripts/quality/check_traceability.py

.PHONY: check-counterexamples
check-counterexamples: ## Directed fault injection: key rules must be caught by tests
	$(PY) scripts/quality/check_counterexamples.py

.PHONY: check-toolchain
check-toolchain: ## Version files match CI, engines, images, and Action SHAs
	$(PY) scripts/quality/check_toolchain.py

.PHONY: check-docs
check-docs: ## Links, entry points and doc/change traceability
	$(PY) scripts/quality/check_docs.py

.PHONY: check-gate
check-gate: ## CI make targets are exactly the verify prerequisites
	$(PY) scripts/quality/check_gate.py

# ---------- tests ----------
.PHONY: test-unit-py
test-unit-py: ## Pure logic and isolated unit tests (backend)
	cd apps/backend && $(UV_BE) pytest -q -m "unit"

.PHONY: test-unit-ts
test-unit-ts: ## Unit tests: TS api-client + web + miniprogram (vitest)
	pnpm --filter @project/api-client test
	pnpm --filter @project/web test
	pnpm --filter @project/miniprogram test

.PHONY: test-unit
test-unit: test-unit-py test-unit-ts ## Pure logic and isolated unit tests

.PHONY: test-integration
test-integration: ## Real DB/adapters and module collaboration
	cd apps/backend && $(UV_BE) pytest -q -m "integration or api"

.PHONY: test-contract
test-contract: ## Live interface + Problem error responses vs contracts/
	cd apps/backend && $(UV_BE) pytest -q -m "contract"

.PHONY: test-migrations
test-migrations: ## Migration upgrade/downgrade, constraints, data backfill
	cd apps/backend && $(UV_BE) pytest -q -m "migration"

.PHONY: test-security
test-security: ## AuthN/AuthZ allow/deny, no-side-effect on deny, scope isolation
	cd apps/backend && $(UV_BE) pytest -q -m "security"

.PHONY: test-e2e
test-e2e: ## Required end-to-end suites for every selected client
	$(BASH) tests/e2e/run.sh

# begin client:mobile-flutter
.PHONY: check-dart
check-dart: ## Analyze and test the Dart SDK and the Flutter app
	cd packages/dart/api_client && dart pub get && dart analyze && dart test
	cd apps/mobile && flutter pub get && flutter analyze && flutter test
# end client:mobile-flutter

.PHONY: build-clients build-web build-web-next build-mp
build-clients: ## Build the Vite app, the Next app, and the miniprogram
# begin client:web-vite
build-clients: build-web
build-web:
	pnpm --filter @project/web build
# end client:web-vite
# begin client:web-next
build-clients: build-web-next
build-web-next:
	pnpm --filter @project/web-next build
# end client:web-next
# begin client:wechat-native
build-clients: build-mp
build-mp:
	node scripts/miniprogram/build.mjs
# end client:wechat-native

.PHONY: images
images: ## Build the backend image and the web runtime-static image
	docker build -f infra/docker/backend.Dockerfile -t $(BACKEND_IMAGE) .
	docker build -f infra/docker/web.Dockerfile --target runtime-static -t $(WEB_IMAGE) .

.PHONY: scan-images
scan-images: ## Fail on HIGH/CRITICAL findings that already have a fix
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(TRIVY_IMAGE) image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 $(BACKEND_IMAGE)
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock $(TRIVY_IMAGE) image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 $(WEB_IMAGE)

.PHONY: sbom
sbom: ## Write an SPDX SBOM for the backend image
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v $(subst \,/,$(CURDIR)):/work -w /work $(SYFT_IMAGE) $(BACKEND_IMAGE) -o spdx-json=sbom-backend.spdx.json

.PHONY: verify
verify: check-toolchain check-gate check-contract check-breaking check-generated lint-py lint-ts typecheck-py typecheck-ts check-architecture check-specs check-counterexamples check-docs test-unit-py test-unit-ts test-integration test-contract test-migrations test-security build-clients ## Merge gate. CI runs this set and nothing else.
# begin client:mobile-flutter
verify: check-dart
# end client:mobile-flutter
verify: test-e2e images scan-images sbom
# begin template-only
verify: check-generator
# end template-only

.PHONY: verify-release
verify-release: verify ## Same set as verify

# ---------- build / deploy ----------
.PHONY: build
build: ## Build selected apps and controlled artifacts from lockfiles
	$(COMPOSE) build

.PHONY: migrate
migrate: ## Run a single controlled migration against an explicit environment
	$(PY) scripts/ops/migrate.py --env $(or $(ENV),dev)

.PHONY: seed
seed: ## Seed data through controlled app capabilities (no business-rule copies)
	$(PY) scripts/ops/seed.py --env $(or $(ENV),dev)

# ---------- miniprogram ----------
.PHONY: mp-build
mp-build: ## Build miniprogram src/ → dist/ (blueprint 07 §2-§4)
	node scripts/miniprogram/build.mjs

.PHONY: mp-preview
mp-preview: ## Preview the built dist via miniprogram-ci
	node scripts/miniprogram/preview.mjs

.PHONY: mp-upload
mp-upload: ## Upload dist (versioned artifact, protected env)
	node scripts/miniprogram/upload.mjs

.PHONY: clean
clean: ## Delete only reproducible artifacts (never volumes, secrets, backups)
	$(PY) scripts/dev/clean.py
