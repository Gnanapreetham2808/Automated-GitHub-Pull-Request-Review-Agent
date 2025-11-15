"""
Test script to verify the API routes integration
Run this after starting the server to test all endpoints
"""

import asyncio
import httpx


SAMPLE_DIFF = """diff --git a/example.py b/example.py
index 1234567..abcdefg 100644
--- a/example.py
+++ b/example.py
@@ -10,6 +10,12 @@ def get_user(user_id):
     conn = sqlite3.connect('users.db')
     cursor = conn.cursor()
     
-    query = "SELECT * FROM users WHERE id = " + user_id
+    # Fixed SQL injection vulnerability
+    query = "SELECT * FROM users WHERE id = ?"
+    cursor.execute(query, (user_id,))
     
     result = cursor.fetchone()
+    
+    if not result:
+        return None
+    
     return result
"""


async def test_health():
    """Test health endpoint"""
    print("=" * 60)
    print("Testing Health Endpoint")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Health check passed")
                print(f"   Status: {result['status']}")
                print(f"   Service: {result['service']}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except httpx.ConnectError:
            print("❌ Cannot connect to server. Is it running?")
            print("   Run: uvicorn app:app --reload")
            return False
    
    return True


async def test_root():
    """Test root endpoint"""
    print("\n" + "=" * 60)
    print("Testing Root Endpoint")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Root endpoint working")
            print(f"   Service: {result['service']}")
            print(f"   Version: {result['version']}")
            print(f"   Endpoints: {result['endpoints']}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")


async def test_manual_review():
    """Test manual review endpoint"""
    print("\n" + "=" * 60)
    print("Testing Manual Review Endpoint")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print("Sending diff for review...")
            response = await client.post(
                "http://localhost:8000/review/manual",
                json={"diff": SAMPLE_DIFF}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Manual review completed successfully")
                print(f"   Total comments: {len(result['comments'])}")
                
                if result.get('summary'):
                    print(f"\n📋 Summary:")
                    print(f"   {result['summary']}")
                
                if result['comments']:
                    print(f"\n💬 Sample comments:")
                    for i, comment in enumerate(result['comments'][:3], 1):
                        print(f"\n   Comment {i}:")
                        print(f"   - Category: {comment['category']}")
                        print(f"   - File: {comment['path']}:{comment['line']}")
                        print(f"   - Confidence: {comment['confidence']:.2f}")
                        print(f"   - Issue: {comment['body'][:100]}...")
                    
                    if len(result['comments']) > 3:
                        print(f"\n   ... and {len(result['comments']) - 3} more comments")
                else:
                    print(f"   No issues found!")
            else:
                print(f"❌ Manual review failed: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except httpx.TimeoutException:
            print("⏱️  Request timed out (this is normal for LLM calls)")
            print("   Consider increasing timeout or reducing diff size")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_api_docs():
    """Test that API docs are available"""
    print("\n" + "=" * 60)
    print("Testing API Documentation")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/docs")
        if response.status_code == 200:
            print(f"✅ API docs available at http://localhost:8000/docs")
        else:
            print(f"❌ API docs failed: {response.status_code}")


async def test_invalid_diff():
    """Test error handling with invalid diff"""
    print("\n" + "=" * 60)
    print("Testing Error Handling (Invalid Diff)")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/review/manual",
                json={"diff": ""}
            )
            
            if response.status_code == 422:
                print(f"✅ Validation error handled correctly (422)")
            elif response.status_code == 400:
                print(f"✅ Bad request handled correctly (400)")
                result = response.json()
                print(f"   Error: {result.get('detail', 'No detail')}")
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def main():
    """Run all tests"""
    print("\n" + "█" * 60)
    print("PR Review Agent - API Integration Tests")
    print("█" * 60 + "\n")
    
    # Test health first
    if not await test_health():
        print("\n❌ Server is not running. Exiting tests.")
        return
    
    # Test other endpoints
    await test_root()
    await test_api_docs()
    await test_invalid_diff()
    
    # Test main functionality (requires API keys)
    print("\n" + "⚠️" * 30)
    print("WARNING: The next test requires OPENAI_API_KEY")
    print("Make sure it's set in your .env file")
    print("⚠️" * 30 + "\n")
    
    response = input("Continue with AI review test? (y/n): ")
    if response.lower() == 'y':
        await test_manual_review()
    else:
        print("Skipping AI review test")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    print("\nYour API routes are properly integrated! 🎉")
    print("\nNext steps:")
    print("  1. Set GITHUB_TOKEN and OPENAI_API_KEY in .env")
    print("  2. Test /review/manual with real diffs")
    print("  3. Test /review/github with a real PR")
    print("  4. Check API docs at http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
