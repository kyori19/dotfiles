#!/bin/sh

set -e

if [ "$CODESPACES" = "true" ]; then
  if command -v apt >/dev/null && ! command -v gh >/dev/null; then
    type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)
    sudo mkdir -p -m 755 /etc/apt/keyrings
    wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
    sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update
    sudo apt install gh -y
  fi
fi

if command -v gh >/dev/null; then
  gh extension install seachicken/gh-poi --force
fi
