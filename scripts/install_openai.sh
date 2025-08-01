#!/bin/bash
# Quick install script for OpenAI package

echo "🔍 Checking OpenAI package installation..."

if python -c "import openai" 2>/dev/null; then
    echo "✅ OpenAI package is already installed"
else
    echo "📦 Installing OpenAI package..."
    pip install openai
    echo "✅ OpenAI package installed"
fi

echo ""
echo "🔑 Don't forget to add your API key to .env:"
echo "   OPENAI_API_KEY=sk-..."
echo ""
echo "Ready to test? Run:"
echo "   python test_openai_matching.py"
