#!/bin/sh

coverage run --branch --source=asynchttp ./test.py
coverage html
