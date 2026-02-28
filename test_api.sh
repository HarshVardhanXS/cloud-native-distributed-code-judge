#!/bin/bash

# Test script for Cloud-Native Code Judge API

BASE_URL="http://localhost:8000"
USERNAME="testuser"
PASSWORD="password123"

echo "==== Cloud-Native Code Judge API Test ===="
echo ""

# 1. Health Check
echo "1. Health Check:"
curl -s -X GET "$BASE_URL/health" | python -m json.tool
echo ""

# 2. Get Token
echo "2. Login (Get JWT Token):"
TOKEN=$(curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME&password=$PASSWORD" | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: ${TOKEN:0:50}..."
echo ""

# 3. Get Current User
echo "3. Get Current User:"
curl -s -X GET "$BASE_URL/me" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
echo ""

# 4. Create Problem
echo "4. Create Problem:"
curl -s -X POST "$BASE_URL/problems" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Addition",
    "description": "Add two numbers",
    "difficulty": "easy",
    "test_cases": "[{\"input\": {\"a\": 2, \"b\": 3}, \"output\": 5}, {\"input\": {\"a\": 1, \"b\": 1}, \"output\": 2}]"
  }' | python -m json.tool
echo ""

# 5. List Problems
echo "5. List Problems:"
curl -s -X GET "$BASE_URL/problems" | python -m json.tool
echo ""

# 6. Submit Solution
echo "6. Submit Solution:"
curl -s -X POST "$BASE_URL/problems/1/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def solution(a, b):\n    return a + b"
  }' | python -m json.tool
echo ""

# 7. Get Submissions
echo "7. List User Submissions:"
curl -s -X GET "$BASE_URL/submissions" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
echo ""

# 8. Get Stats
echo "8. Get User Statistics:"
curl -s -X GET "$BASE_URL/stats" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
echo ""

echo "==== Test Complete ===="
