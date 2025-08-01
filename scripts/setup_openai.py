#!/usr/bin/env python3
"""
Quick setup script for OpenAI matching
"""

import subprocess
import sys
import os

print("🚀 Setting up OpenAI (GPT-4o-mini) for contract matching\n")

# Check if openai is installed
try:
    import openai
    print("✅ openai package is already installed")
except ImportError:
    print("📦 Installing openai package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
    print("✅ openai package installed successfully")

# Check for API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key or api_key == 'your-openai-api-key-here':
    print("\n⚠️ OPENAI_API_KEY not configured!")
    print("\n📝 To get your OpenAI API key:")
    print("1. Go to: https://platform.openai.com/api-keys")
    print("2. Sign up or log in")
    print("3. Create a new API key")
    print("4. Add to your .env file: OPENAI_API_KEY='sk-...'")
    print("\n💰 Pricing info:")
    print("   - GPT-4o-mini: $0.00015/1K input + $0.0006/1K output tokens")
    print("   - Estimated cost for matching: $0.05-$0.25 per full run")
    print("   - 10x cheaper than GPT-3.5-turbo!")
    print("   - 100x cheaper than Claude!")
else:
    print("✅ OpenAI API key is configured")
    print(f"   Key starts with: {api_key[:7]}...")

print("\n✅ Setup complete!")
print("\n📝 Next steps:")
print("1. Make sure your API key is in .env file")
print("2. Run: python test_openai_matching.py")
print("3. If tests pass, run: python openai_enhanced_matcher.py --full")
