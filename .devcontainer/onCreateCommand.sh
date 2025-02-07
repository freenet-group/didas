#!/bin/bash

sudo chown -R vscode:vscode ~
pip install --upgrade pip
pipx install thefuck
echo "source $(realpath .devcontainer/bashrc_extension.sh)" >>~/.bashrc
