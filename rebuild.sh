#!/bin/bash
pip uninstall -y fdlogger
rm dist/*
python3 -m build
pip install -e .

