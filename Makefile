PROJECT_NAME = nc-plus-one
REGION = eu-west-2
PYTHON_INTERPRETER = python
WD=$(shell pwd)
PYTHONPATH=${WD}
MODULE_DIR=${WD}/nc_plus_one
TEST_DIR=${WD}/tests
TEST_DATABASE_NAME=nc_plus_one_test
SHELL := /bin/bash
PROFILE = default
INGRESS_PORT = 80
INTERNAL_PORT = 8000
PIP:=pip

## Create python interpreter environment.
create-environment:
	@echo ">>> About to create environment: $(PROJECT_NAME)..."
	@echo ">>> check python3 version"
	( \
		$(PYTHON_INTERPRETER) --version; \
	)
	@echo ">>> Setting up venv."
	( \
	    $(PYTHON_INTERPRETER) -m venv venv; \
	)


# Define utility variable to help calling Python from the virtual environment
ACTIVATE_ENV := source venv/bin/activate

# Execute python related functionalities from within the project's environment
define execute_in_env
	$(ACTIVATE_ENV) && $1
endef


## Set up log directory
logdirs:
	mkdir -p logs

## Build the environment requirements
requirements: create-environment logdirs
	$(call execute_in_env, $(PIP) install -r ./requirements.txt)

# Set Up
## Install bandit
bandit:
	$(call execute_in_env, $(PIP) install bandit)

## Install black
black:
	$(call execute_in_env, $(PIP) install black)

## Install coverage
coverage:
	$(call execute_in_env, $(PIP) install pytest-cov)

## Set up dev requirements (bandit, black & coverage)
dev-setup: bandit black coverage 

# Build / Run

## Run the security test (bandit)
security-test:
	$(call execute_in_env, bandit -lll ${MODULE_DIR}/*.py ${MODULE_DIR}/*/*.py)

## Run the black code check
run-black:
	$(call execute_in_env, black ${MODULE_DIR}/*.py ${MODULE_DIR}/*/*.py ${TEST_DIR}/*.py ${TEST_DIR}/*/*.py)

## Set up test database
setup-test-database:
	psql -c "CREATE DATABASE $(TEST_DATABASE_NAME);"

## Tear down test database
teardown-test-database:
	psql -c "DROP DATABASE IF EXISTS $(TEST_DATABASE_NAME);"

## Run the unit tests
unit-test:
	$(MAKE) --no-print-directory setup-test-database
	trap '$(MAKE) --no-print-directory teardown-test-database' EXIT; \
	$(call execute_in_env, TEST_DATABASE_URL='dbname=${TEST_DATABASE_NAME}' PYTHONPATH=${PYTHONPATH} pytest -v ${TEST_DIR})

## Run the coverage check
check-coverage:
	$(MAKE) --no-print-directory setup-test-database
	trap '$(MAKE) --no-print-directory teardown-test-database' EXIT; \
	$(call execute_in_env, TEST_DATABASE_URL='dbname=${TEST_DATABASE_NAME}' PYTHONPATH=${PYTHONPATH} pytest --cov=nc_plus_one ${TEST_DIR})

## Run all checks
run-checks: security-test run-black unit-test check-coverage

## Start server
start-server:
	$(call execute_in_env, PYTHONPATH=${PYTHONPATH} uvicorn nc_plus_one.main:app --reload --host 0.0.0.0)
