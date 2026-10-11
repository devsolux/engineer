# Canonical build/test entrypoint. All default operations are offline.
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help
PYTHON ?= $(if $(wildcard .venv/bin/python),$(CURDIR)/.venv/bin/python,python3)
export PYTHONDONTWRITEBYTECODE := 1
export PATH := $(shell "$(PYTHON)" -c 'from pathlib import Path; import sys; print(Path(sys.executable).parent)' 2>/dev/null):$(CURDIR)/node_modules/.bin:$(PATH)
JOBS ?= 1
PLUGIN := engineer@devsolux-engineer
REPOSITORY := devsolux/engineer

.PHONY: help setup lint validate evals check test build verify-build package fixtures clean doctor install-claude install-codex install-claude-local install-codex-local host-validate

help: ## Show available targets (no installation or live model calls)
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Explicit network opt-in: create .venv and install pinned Python dev dependencies
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements-dev.txt

lint: ## Parse Python, Bash, JSON, YAML and SVG; check key links and marketplace metadata
	"$(PYTHON)" scripts/check-source.py

validate: ## Run repository structure, security, and fixture-binding checks
	bash scripts/validate-repo.sh

evals: ## Validate the full static eval bank; no model calls
	bash scripts/run-evals.sh --full --json

check: lint validate evals ## Run static gates without changing source or fixtures

fixtures: ## Explicitly rebind illustrative skill-eval fixtures after reviewed source changes
	"$(PYTHON)" scripts/rebind-skill-eval.py

test: ## Run all discovered offline suites in isolated copies (JOBS=4 optional)
	"$(PYTHON)" scripts/run-tests.py --jobs $(JOBS)

build: ## Generate the install-ready shared plugin and host-specific adapters
	"$(PYTHON)" scripts/build-plugin.py

verify-build: ## Fail on generated bundle drift (read-only)
	"$(PYTHON)" scripts/build-plugin.py --check

package: check ## Run static gates and create deterministic plugin ZIP + SHA-256
	"$(PYTHON)" scripts/build-plugin.py --package

clean: ## Remove known build/test output only; preserve plugin sources, .venv and .engineer
	"$(PYTHON)" scripts/clean-build.py

doctor: ## Report the local toolchain without installing tools
	@"$(PYTHON)" --version
	@for tool in bash make node tsc claude codex; do command -v "$$tool" || echo "$$tool: unavailable"; done
	@"$(PYTHON)" -c 'import yaml; print("PyYAML " + yaml.__version__)'

host-validate: build ## Explicit local Claude manifest validation; requires Claude CLI
	@command -v claude >/dev/null || { echo "Claude CLI is required" >&2; exit 1; }
	claude plugin validate --strict .
	claude plugin validate --strict ./plugins/engineer

install-claude: ## Explicit host-state change: install from the GitHub marketplace
	@command -v claude >/dev/null || { echo "Claude CLI is required" >&2; exit 1; }
	claude plugin marketplace add https://github.com/$(REPOSITORY)
	claude plugin install $(PLUGIN)

install-codex: ## Explicit host-state change: install from the GitHub marketplace
	@command -v codex >/dev/null || { echo "Codex CLI is required" >&2; exit 1; }
	codex plugin marketplace add $(REPOSITORY)
	codex plugin add $(PLUGIN)

install-claude-local: build ## Explicit host-state change: install this working-tree marketplace
	@command -v claude >/dev/null || { echo "Claude CLI is required" >&2; exit 1; }
	claude plugin marketplace add "$(CURDIR)"
	claude plugin install $(PLUGIN)

install-codex-local: build ## Explicit host-state change: install this working-tree marketplace
	@command -v codex >/dev/null || { echo "Codex CLI is required" >&2; exit 1; }
	codex plugin marketplace add "$(CURDIR)"
	codex plugin add $(PLUGIN)

# -----------------------------------------------------------------------------
# Publishing — explicit, outward-facing operations. Nothing above depends on them.
# Marketplace installs read the committed tree, so plugins/engineer must be current.
# -----------------------------------------------------------------------------

VERSION := $(shell sed -n 's/^  version: "\([0-9.]*\)"$$/\1/p' SKILL.md)
GITHUB_REPO ?= $(REPOSITORY)
GITHUB_VISIBILITY ?= public
GITHUB_DESCRIPTION ?= Full-stack engineering skill plugin for Claude Code and Codex
GITHUB_COMMIT_MSG ?=

.PHONY: release-check git-check github-check github-auth git-init git-main github-initial-commit \
	github-repo-create github-verify github-pull github-push github-release github-bootstrap

release-check: check test verify-build ## Every gate required before publishing (offline)
	@echo "Release $(VERSION) gates passed for $(PLUGIN)."

git-check:
	@command -v git >/dev/null 2>&1 || { echo "error: git is required" >&2; exit 1; }

github-check: git-check
	@command -v gh >/dev/null 2>&1 || { echo "error: GitHub CLI (gh) is required — https://cli.github.com" >&2; exit 1; }

# Refuse to operate while another git process may hold the index; never delete the lock blindly.
define require_no_index_lock
	@if test -f .git/index.lock; then \
		echo "error: .git/index.lock exists; finish or stop the other git process, then remove it manually" >&2; \
		exit 1; \
	fi
endef

github-auth: github-check ## Interactive: authenticate gh with GitHub (once per machine)
	gh auth login

git-init: git-check ## Initialize a local Git repository on branch main (no commit)
	@if test -d .git; then \
		echo "Git repository already initialized (.git exists)."; \
	else \
		git init -b main; \
	fi

git-main: git-check
	@git rev-parse --git-dir >/dev/null 2>&1 || { echo "error: not a git repository (run: make git-init)" >&2; exit 1; }
	@BRANCH=$$(git symbolic-ref --short HEAD 2>/dev/null || true); \
	if [ -z "$$BRANCH" ]; then \
		git symbolic-ref HEAD refs/heads/main && echo "Default branch set to main (no commits yet)."; \
	elif [ "$$BRANCH" != "main" ]; then \
		git branch -M main && echo "Renamed branch to main."; \
	else \
		echo "Already on branch main."; \
	fi

github-initial-commit: git-check ## Create the first commit ("Release <version>") when history is empty
	@git rev-parse --git-dir >/dev/null 2>&1 || { echo "error: not a git repository (run: make git-init)" >&2; exit 1; }
	$(require_no_index_lock)
	@if git rev-parse HEAD >/dev/null 2>&1; then \
		echo "Repository already has commits; skipping initial commit."; \
	else \
		git add -A && \
		if git diff --cached --quiet; then \
			echo "error: nothing staged; check .gitignore" >&2; exit 1; \
		fi && \
		git ls-files --error-unmatch plugins/engineer/.claude-plugin/plugin.json >/dev/null && \
		git commit -m "Release $(VERSION)" && \
		echo "Created initial commit."; \
	fi

github-repo-create: github-check ## Create the GitHub repository (public by default) and push main
	@if git remote get-url origin >/dev/null 2>&1; then \
		echo "Remote origin already exists:"; git remote -v; \
		echo "Skipping gh repo create. Run: make github-push"; \
	else \
		gh repo create "$(GITHUB_REPO)" --$(GITHUB_VISIBILITY) --source=. --remote=origin \
			--description "$(GITHUB_DESCRIPTION)" --push; \
	fi

github-verify: git-check ## Show remotes, branches, and the published repository visibility
	@git remote -v
	@git branch -a
	@command -v gh >/dev/null 2>&1 && gh repo view "$(GITHUB_REPO)" --json nameWithOwner,visibility,url || true

# Fast-forward main from origin only when GitHub has newer commits.
# Diverged history or a dirty worktree during an update stops without changing files.
github-pull: git-check ## Fast-forward main from origin/main (never merges or overwrites)
	@git rev-parse --git-dir >/dev/null 2>&1 || { echo "error: not a git repository" >&2; exit 1; }
	@git remote get-url origin >/dev/null 2>&1 || { echo "error: no origin remote (run: make github-repo-create)" >&2; exit 1; }
	@BRANCH=$$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true); \
	if [ "$$BRANCH" != "main" ]; then \
		echo "error: github-pull expects branch main (current: $${BRANCH:-detached})" >&2; \
		exit 1; \
	fi
	$(require_no_index_lock)
	@git fetch origin main
	@REMOTE=$$(git rev-parse --verify refs/remotes/origin/main 2>/dev/null || true); \
	LOCAL=$$(git rev-parse --verify HEAD 2>/dev/null || true); \
	if [ -z "$$REMOTE" ]; then \
		echo "No commit found on origin/main; nothing to pull."; \
	elif [ -z "$$LOCAL" ]; then \
		if [ -n "$$(git status --porcelain)" ]; then \
			echo "error: local repository has no commit and the worktree is not clean; refusing to overwrite files" >&2; \
			exit 1; \
		fi; \
		git checkout -B main origin/main && \
		echo "Updated main to remote commit $$REMOTE."; \
	elif [ "$$LOCAL" = "$$REMOTE" ]; then \
		echo "Already up to date ($$LOCAL)."; \
	elif git merge-base --is-ancestor "$$REMOTE" "$$LOCAL"; then \
		echo "Local main already contains origin/main; nothing to pull."; \
	elif git merge-base --is-ancestor "$$LOCAL" "$$REMOTE"; then \
		if [ -n "$$(git status --porcelain)" ]; then \
			echo "error: origin/main is newer, but the worktree is not clean; commit or stash first" >&2; \
			exit 1; \
		fi; \
		git merge --ff-only origin/main && \
		echo "Updated main: $$LOCAL -> $$REMOTE"; \
	else \
		echo "error: local main and origin/main have diverged; resolve with an explicit merge or rebase" >&2; \
		exit 1; \
	fi

# Stage everything, commit (custom message or a local timestamp), then push main.
# Custom message: make github-push GITHUB_COMMIT_MSG='Describe the change'
github-push: github-check verify-build ## Commit all changes and push main (refuses a stale plugin bundle)
	@git rev-parse --git-dir >/dev/null 2>&1 || { echo "error: not a git repository" >&2; exit 1; }
	@git remote get-url origin >/dev/null 2>&1 || { echo "error: no origin remote (run: make github-repo-create)" >&2; exit 1; }
	@test "$$(git symbolic-ref --quiet --short HEAD 2>/dev/null)" = main || { echo "error: github-push publishes main; switch to main first" >&2; exit 1; }
	$(require_no_index_lock)
	@STAMP=$$(date +%Y%m%d-%H%M%S); \
	git add -A; \
	if git diff --cached --quiet; then \
		echo "No changes to commit; pushing."; \
	elif [ -n "$(GITHUB_COMMIT_MSG)" ]; then \
		git commit -m "$(GITHUB_COMMIT_MSG)"; \
	else \
		git commit -m "$$STAMP" && echo "Committed: $$STAMP"; \
	fi
	git push -u origin main

github-release: github-check package ## Tag v<version> and publish a GitHub release with the plugin ZIP
	@git rev-parse HEAD >/dev/null 2>&1 || { echo "error: commit before releasing" >&2; exit 1; }
	@test -z "$$(git status --porcelain)" || { echo "error: worktree is not clean; commit before releasing" >&2; exit 1; }
	gh release create "v$(VERSION)" "dist/engineer-$(VERSION)-plugin.zip" "dist/engineer-$(VERSION)-plugin.zip.sha256" \
		--repo "$(GITHUB_REPO)" --target main --title "Engineer $(VERSION)" \
		--notes "Install: claude plugin marketplace add https://github.com/$(GITHUB_REPO) && claude plugin install $(PLUGIN). See CHANGELOG.md."

# Full first publication (sequential; safe with make -j): gates → init → commit → create public repo → verify
github-bootstrap: ## Run release gates, then create the public GitHub repository and push
	@$(MAKE) release-check
	@$(MAKE) github-check
	@$(MAKE) git-init
	@$(MAKE) git-main
	@$(MAKE) github-initial-commit
	@$(MAKE) github-repo-create
	@$(MAKE) github-verify
