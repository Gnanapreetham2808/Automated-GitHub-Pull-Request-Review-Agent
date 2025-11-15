"""
Example script demonstrating the PR Review Agent API
"""

import asyncio
import httpx


async def test_manual_review():
    """Test the manual diff review endpoint."""
    
    # Example diff
    sample_diff = """diff --git a/example.py b/example.py
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
     return result
"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("Testing manual diff review...")
            response = await client.post(
                "http://localhost:8000/review/manual",
                json={"diff": sample_diff}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Review complete!")
                print(f"   Files reviewed: {result['files_reviewed']}")
                print(f"   Total comments: {result['total_comments']}")
                print()
                
                for i, comment in enumerate(result['comments'], 1):
                    print(f"Comment {i}:")
                    print(f"  Category: {comment['category']}")
                    print(f"  File: {comment['path']}:{comment['line']}")
                    print(f"  Confidence: {comment['confidence']:.2f}")
                    print(f"  Body: {comment['body']}")
                    print()
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except httpx.ConnectError:
            print("❌ Connection failed. Is the server running?")
            print("   Run: uvicorn app:app --reload")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_github_review():
    """Test the GitHub PR review endpoint."""
    
    # Example: Review a small public PR
    owner = "octocat"
    repo = "Hello-World"
    pr_number = 1
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print(f"Testing GitHub PR review for {owner}/{repo}#{pr_number}...")
            response = await client.post(
                "http://localhost:8000/review/github",
                json={
                    "owner": owner,
                    "repo": repo,
                    "pr": pr_number
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Review complete!")
                print(f"   Files reviewed: {result['files_reviewed']}")
                print(f"   Total comments: {result['total_comments']}")
                print()
                
                for i, comment in enumerate(result['comments'], 1):
                    print(f"Comment {i}:")
                    print(f"  Category: {comment['category']}")
                    print(f"  File: {comment['path']}:{comment['line']}")
                    print(f"  Confidence: {comment['confidence']:.2f}")
                    print(f"  Body: {comment['body']}")
                    print()
            else:
                print(f"❌ Error: {response.status_code}")
                print(response.text)
                
        except httpx.ConnectError:
            print("❌ Connection failed. Is the server running?")
            print("   Run: uvicorn app:app --reload")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def main():
    """Run example tests."""
    print("=" * 60)
    print("PR Review Agent - Example Usage")
    print("=" * 60)
    print()
    
    # Test manual review
    await test_manual_review()
    
    print()
    print("-" * 60)
    print()
    
    # Uncomment to test GitHub review (requires GITHUB_TOKEN)
    # await test_github_review()


if __name__ == "__main__":
    asyncio.run(main())
