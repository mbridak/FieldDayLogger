#!/bin/bash
pip uninstall -y fdlogger
rm dist/*
python3 -m build
python3 -m twine upload dist/*
