STATUS_FRAGMENTS ?=

.PHONY: \
	bump-dev \
	doctor \
	doctor-versioning \
	help-versioning \
	release \
	status

help-versioning:
	@echo versioning

doctor-versioning:
	@echo doctor

doctor:
	@echo all doctors

status:
	@echo status

bump-dev release:
	@echo version
