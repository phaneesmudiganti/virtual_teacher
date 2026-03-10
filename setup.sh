#!/usr/bin/env bash

# Setup script for OpenAI-backed Virtual Teacher

set -euo pipefail

echo 'Setting up OpenAI for Virtual Teacher...'

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo 'OPENAI_API_KEY is not set.'
    echo 'Export it before running the app, for example:'
    echo '  export OPENAI_API_KEY="your-api-key-here"'
    exit 1
fi

echo 'OPENAI_API_KEY is set.'
echo 'You can now run: crewai run'
