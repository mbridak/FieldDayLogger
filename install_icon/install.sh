#!/bin/bash

if [ -f "../dist/fielddaylogger" ]; then
	cp ../dist/fielddaylogger ~/.local/bin/
fi

xdg-icon-resource install --size 64 --context apps --mode user k6gte-FieldDay.png k6gte-FieldDay

xdg-desktop-icon install k6gte-FieldDay.desktop

xdg-desktop-menu install k6gte-FieldDay.desktop

