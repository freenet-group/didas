#!/bin/bash

sudo chown -R vscode:vscode ~
pip install --upgrade pip
mkdir -p ~/.aws
ln -s "$(realpath .devcontainer/aws_config.ini)" ~/.aws/config
pipx install thefuck
echo "source $(realpath .devcontainer/bashrc_extension.sh)" >>~/.bashrc
