# Makefile for mados-wifi tests

.PHONY: all test-unit test-system clean

all: test-unit

test-unit:
	./run-unit-tests.sh

test-system:
	./run-system-tests.sh

clean:
	rm -rf build
	rm -f /tmp/test_wifi_backend.py
