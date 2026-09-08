# Project Config (project-specific; the global org reads this)

stack: TBD (set after GATE_2)
package_manager: TBD
run_dev: TBD
run_test_unit: TBD
run_test_integration: TBD
run_test_e2e: TBD
lint: TBD
typecheck: TBD
build: TBD
db_migrate: TBD
environments: dev | test | staging | prod   # never mix; prod is human-only
base_url_dev: TBD

# app-qa integration: the existing global app-qa skill reads
# .claude/project-testing.md — /plan will generate it from the values above
# once the stack is chosen, so the QA agents and /smoke-test share one config.
