# CLI Tests

This directory contains tests for the CLI utilities in arduino-devops.

These tests serve as a collection of examples and use cases for the CLI, demonstrating how to use the various commands and options available in the package. They are not exhaustive and do not cover every possible scenario, but they check the happy path and main functionality of the CLI.

The test tool used is [shelltestrunner](https://github.com/simonmichael/shelltestrunner) V1.9.0.1. 

It can be easily installed (Linux/Ubuntu only) using the following command:
```
$ apt install shelltestrunner
```
Go to the `tests` directory and run the tests calling `shelltest` with the test file as an argument. For example:
```
$ cd <path_to_arduino-devops_parent_dir>/arduino-devops/tests
$ shelltest <test_file>
```
