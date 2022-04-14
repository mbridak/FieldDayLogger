#!/bin/bash

if [ -f "~/local/bin/fielddaylogger" ]; then
	rm ~/.local/bin/fielddaylogger
fi

xdg-icon-resource uninstall --size 64 k6gte-FieldDay

xdg-desktop-icon uninstall k6gte-FieldDay.desktop

xdg-desktop-menu uninstall k6gte-FieldDay.desktop

