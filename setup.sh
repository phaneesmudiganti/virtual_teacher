#!/bin/bash
# Setup script for Ollama and models

echo 'Setting up Ollama and models for Virtual Teacher...'

# Install Ollama (if not already installed)
if ! command -v ollama &> /dev/null; then
    echo 'Installing Ollama...'
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Start Ollama service
echo 'Starting Ollama service...'
ollama serve &

# Wait for service to start
sleep 5

# Pull recommended models
echo 'Pulling Llama 3.1 8B Instruct...'
ollama pull llama3.1:8b

echo 'Pulling Qwen 2.5 7B Instruct...'
ollama pull qwen2.5:7b-instruct

echo 'Setup complete! You can now run the Virtual Teacher.'
echo 'For better performance, consider pulling larger models:'
echo '  ollama pull mixtral:8x7b-instruct'
echo '  ollama pull llama3.1:70b-instruct'
