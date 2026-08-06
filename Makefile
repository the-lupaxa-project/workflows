# Lupaxa makefile-skills project wrapper
# Copy this file to your project root as Makefile.
#
# Library development (this repo): set MAKEFILES_MODE=library and
# MAKEFILES_DIR=. before including, or use the root Makefile.

SKILLS         ?=
MAKEFILES_DIR  ?= .makefiles
MAKEFILES_REF  ?= head
MAKEFILES_MODE ?= consumer

# Transport: ssh | https | http
MAKEFILES_TRANSPORT ?= https
MAKEFILES_REPO_SSH  ?= git@github.com:lupaxa-developers-toolbox/makefile-skills.git
MAKEFILES_REPO_HTTP ?= https://github.com/lupaxa-developers-toolbox/makefile-skills.git

ifeq ($(MAKEFILES_TRANSPORT),ssh)
MAKEFILES_REPO ?= $(MAKEFILES_REPO_SSH)
else ifneq ($(filter $(MAKEFILES_TRANSPORT),https http),)
MAKEFILES_REPO ?= $(MAKEFILES_REPO_HTTP)
else
$(error MAKEFILES_TRANSPORT must be ssh, https, or http (got '$(MAKEFILES_TRANSPORT)'))
endif

.DEFAULT_GOAL := help

.PHONY: init install update help doctor version bump-dev bump-minor bump-major bump-rc release bump-final show-version-flow status completion completion-path print-targets

# -----------------------------------------------------------------------------
# Lifecycle
# -----------------------------------------------------------------------------

ifeq ($(MAKEFILES_MODE),library)

init install:
	@echo "This repository hosts the skills library under skills/."
	@echo "No clone is required. Consumers should copy templates/Makefile."

update:
	@echo "Library mode: update skills with git in this repository (not make update)."

else

init install:
	@set -e; \
	if [ -e "$(MAKEFILES_DIR)" ]; then \
		echo "ERROR: $(MAKEFILES_DIR) already exists. Use 'make update' or remove it first." >&2; \
		exit 2; \
	fi; \
	echo "==> Cloning skills from $(MAKEFILES_REPO) into $(MAKEFILES_DIR)"; \
	if ! git clone --filter=blob:none --no-checkout "$(MAKEFILES_REPO)" "$(MAKEFILES_DIR)" \
		|| ! $(MAKE) --no-print-directory _makefiles-checkout; then \
		echo "==> Removing incomplete $(MAKEFILES_DIR) so 'make init' can be retried" >&2; \
		rm -rf "$(MAKEFILES_DIR)"; \
		exit 2; \
	fi

update:
	@set -e; \
	if [ ! -d "$(MAKEFILES_DIR)/.git" ]; then \
		echo "ERROR: $(MAKEFILES_DIR) is not a git clone. Run: make init" >&2; \
		exit 2; \
	fi; \
	echo "==> Updating makefile skills in $(MAKEFILES_DIR) (ref=$(MAKEFILES_REF))"; \
	git -C "$(MAKEFILES_DIR)" fetch --tags origin; \
	git -C "$(MAKEFILES_DIR)" fetch origin; \
	$(MAKE) --no-print-directory _makefiles-checkout

.PHONY: _makefiles-checkout
_makefiles-checkout:
	@set -e; \
	git -C "$(MAKEFILES_DIR)" sparse-checkout init --no-cone; \
	git -C "$(MAKEFILES_DIR)" sparse-checkout set --no-cone 'skills/**'; \
	if [ "$(MAKEFILES_REF)" = "head" ]; then \
		git -C "$(MAKEFILES_DIR)" checkout -f master; \
		git -C "$(MAKEFILES_DIR)" pull --ff-only origin master; \
	else \
		git -C "$(MAKEFILES_DIR)" checkout -f "$(MAKEFILES_REF)"; \
	fi; \
	git -C "$(MAKEFILES_DIR)" sparse-checkout reapply; \
	if [ ! -f "$(MAKEFILES_DIR)/skills/versioning.mk" ]; then \
		short_sha="$$(git -C "$(MAKEFILES_DIR)" rev-parse --short HEAD 2>/dev/null || echo unknown)"; \
		echo "ERROR: $(MAKEFILES_DIR)/skills/versioning.mk not found after checking out MAKEFILES_REF=$(MAKEFILES_REF) (commit $$short_sha)." >&2; \
		echo "This ref does not look like a valid makefile-skills checkout." >&2; \
		exit 2; \
	fi; \
	extra="$$(find "$(MAKEFILES_DIR)" -mindepth 1 -maxdepth 1 ! -name .git ! -name skills -print)"; \
	if [ -n "$$extra" ]; then \
		echo "ERROR: sparse checkout leaked non-skills paths into $(MAKEFILES_DIR):" >&2; \
		printf '%s\n' "$$extra" >&2; \
		echo "Expected only skills/. Check git sparse-checkout support and retry." >&2; \
		exit 2; \
	fi; \
	echo "==> makefile skills at $$(git -C "$(MAKEFILES_DIR)" rev-parse --short HEAD) ($(MAKEFILES_REF)) [skills/ only]"

endif

# -----------------------------------------------------------------------------
# Help / missing-skills guards
# -----------------------------------------------------------------------------

help:
	@echo "$(or $(PROJECT_NAME),$(notdir $(CURDIR))) Makefile"
	@echo
	@echo "Lifecycle:"
ifeq ($(MAKEFILES_MODE),library)
	@echo "  init / install      (library mode — skills/ is this repository)"
	@echo "  update              (library mode — use git in this repository)"
else
	@echo "  init / install      Clone skills/ into $(MAKEFILES_DIR) (sparse checkout)"
	@echo "  update              Refresh skills to MAKEFILES_REF ($(MAKEFILES_REF))"
endif
	@echo "  completion          Print bash completion script (eval \"\$$(make -s completion)\")"
	@echo "  transport           $(MAKEFILES_TRANSPORT) -> $(MAKEFILES_REPO)"
	@echo
	@if [ ! -f "$(MAKEFILES_DIR)/skills/versioning.mk" ]; then \
		echo "Status:"; \
		echo "  status              Show project, version, Git, and enabled-skill status"; \
		echo "  doctor              Run all doctors (lifecycle + versioning + enabled skills)"; \
		echo; \
		echo "Skills not installed. Run: make init"; \
		echo; \
	else \
		$(MAKE) --no-print-directory help-versioning; \
		for s in $(SKILLS); do \
			$(MAKE) --no-print-directory help-$$s; \
		done; \
	fi

# doctor / status come from skills/versioning.mk once installed.
ifeq ($(wildcard $(MAKEFILES_DIR)/skills/versioning.mk),)
doctor version bump-dev bump-minor bump-major bump-rc release bump-final show-version-flow status:
	@echo "ERROR: makefile skills not installed. Run: make init" >&2
	@exit 2
endif

# Bash completion for make targets (including skill includes).
# Usage: eval "$(make -s completion)"   or   source "$(make -s completion-path)"
completion:
	@completion_file="$(MAKEFILES_DIR)/skills/completion/bash"; \
	if [ ! -f "$$completion_file" ]; then \
		echo "ERROR: completion script not found: $$completion_file" >&2; \
		echo "Run: make init (or use library mode with skills/ present)" >&2; \
		exit 2; \
	fi; \
	cat "$$completion_file"

completion-path:
	@completion_file="$(MAKEFILES_DIR)/skills/completion/bash"; \
	if [ ! -f "$$completion_file" ]; then \
		echo "ERROR: completion script not found: $$completion_file" >&2; \
		exit 2; \
	fi; \
	printf '%s\n' "$$completion_file"

# Targets for shell completion (excludes private _* helpers).
print-targets:
	@$(MAKE) -pRrq : 2>/dev/null | awk -F: '/^[a-zA-Z0-9][^\#\/\t=]*:([^=]|$$)/ { \
		split($$1, names, / /); \
		for (i in names) { \
			n = names[i]; \
			if (n ~ /^[a-zA-Z0-9]/ && n !~ /^_/ && n != "Makefile" && n !~ /\//) print n; \
		} \
	}' | sort -u

# -----------------------------------------------------------------------------
# Skills includes
# -----------------------------------------------------------------------------

-include $(MAKEFILES_DIR)/skills/versioning.mk
$(foreach s,$(SKILLS),$(eval -include $(MAKEFILES_DIR)/skills/$(s).mk))
