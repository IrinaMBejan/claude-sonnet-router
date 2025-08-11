#!/bin/bash
set -e

# claude-sonnet-3.5 Router Startup Script
# Generated automatically - simplified version with service spawning

echo "🚀 Starting claude-sonnet-3.5 router..."

# Basic environment setup
echo "🔧 Running basic setup..."

# Create virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies with extras: chat
echo "📥 Installing/updating dependencies..."
pip install --upgrade pip
pip install -e .[chat]

# Copy environment file if missing
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Created .env file from template. Please edit with your configuration."
fi

echo "✅ Basic setup complete!"
export OPENROUTER_API_KEY=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

# Spawn services using Python script
echo "🔄 Spawning services..."
if python spawn_services.py --project-name claude-sonnet-3.5 --config-path /home/azureuser/.syftbox/config.json; then
    echo "✅ Services spawned successfully"
    
    # Start the router
    echo "🎯 Starting router server..."
    python server.py --project-name claude-sonnet-3.5
else
    echo "❌ Service spawning failed - router will not start"
    exit 1
fi

deactivate
