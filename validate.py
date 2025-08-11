#!/usr/bin/env python3
"""
claude-sonnet-3.5 Router Validation Script
Tests the generated router to ensure it works correctly.
"""

import sys
import time
import requests

def test_router_health():
    """Test router health endpoint."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_chat_endpoint():
    """Test chat endpoint if enabled."""
    try:
        payload = {
            "model": "test-model",
            "messages": [
                {"role": "user", "content": "Hello, how are you?"}
            ]
        }
        response = requests.post("http://localhost:8000/chat", json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Chat endpoint test passed")
            return True
        else:
            print(f"❌ Chat endpoint test failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Chat endpoint test failed: {e}")
        return False

def test_search_endpoint():
    """Test search endpoint if enabled."""
    try:
        payload = {
            "query": "test query",
            "options": {"limit": 5}
        }
        response = requests.post("http://localhost:8000/search", json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Search endpoint test passed")
            return True
        else:
            print(f"❌ Search endpoint test failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Search endpoint test failed: {e}")
        return False

def main():
    """Run validation tests."""
    print(f"🧪 Testing {config.project_name} router...")
    print(f"🔧 Enabled services: Chat={config.enable_chat}, Search={config.enable_search}")
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(5)
    
    # Define test functions
    test_functions = {
        "test_router_health": test_router_health,
        "test_chat_endpoint": test_chat_endpoint,
        "test_search_endpoint": test_search_endpoint
    }
    
    # Run only enabled tests
    tests = [test_functions[test_name] for test_name in ['test_router_health', 'test_chat_endpoint']]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Router is ready for use.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the router configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
