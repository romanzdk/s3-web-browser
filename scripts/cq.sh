#!/usr/bin/env bash

echo "Running black"
black app.py

echo 
echo "Running isort"
isort app.py

echo
echo "Running ruff check"
ruff check app.py

echo
echo "Running mypy"
mypy app.py
