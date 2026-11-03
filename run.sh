#!/usr/bin/env bash
# KORVARC OS Launch Script

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Ensure local stream configuration and run app
export HOME="$DIR"
streamlit run app.py

