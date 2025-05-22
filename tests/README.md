# Tests for Flask Test API

This directory contains tests for the Flask Test API application.

## Running Tests

To run all tests, execute the following command from the project root:

```bash
cd tests
python run_tests.py
```

Or you can run individual test files:

```bash
cd tests
python -m unittest test_sys_endpoint.py
```

## Test Files

- `test_sys_endpoint.py`: Tests for the `/sys` endpoint that provides system metrics