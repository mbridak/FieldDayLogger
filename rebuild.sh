#!/bin/bash
pip3 uninstall -y fdlogger
rm dist/*
python3 -m build
pip3 install -e .

