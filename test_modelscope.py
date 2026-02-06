import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def test_modelscope_api():
    print("="*60)
    print("Testing ModelScope API Connection")
    print("="*60)
    
    api_key = os.getenv("MODELSCOPE_API_KEY", "ms-dd2baa58-4a47-448b-93c6-1a14869a170e")
    base_url = os.getenv("MODELSCOPE_BASE_URL", "https://api-inference.modelscope.cn/v1")
    model = os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507")
    
    print(f"\nAPI Configuration:")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    print(f"  API Key: {api_key[:20]}...{api_key[-10:]}")
    print()
    
    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        print("Sending test request...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a helpful assistant.'
                },
                {
                    'role': 'user',
                    'content': '你好，请用一句话介绍你自己。'
                }
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        print("\n" + "="*60)
        print("Response:")
        print("="*60)
        print(response.choices[0].message.content)
        print("\n" + "="*60)
        print("✅ ModelScope API is working correctly!")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ Error occurred:")
        print("="*60)
        print(f"{type(e).__name__}: {e}")
        print("="*60 + "\n")
        
        print("Troubleshooting tips:")
        print("1. Check your internet connection")
        print("2. Verify the API key is valid")
        print("3. Check if the API endpoint is accessible")
        print("4. Try a different model if available")
        print()
        
        return False

if __name__ == "__main__":
    success = test_modelscope_api()
    
    if success:
        print("You can now run the blog crew:")
        print("  - Basic version: python blog_crew.py")
        print("  - Advanced version: python advanced_blog_crew.py")
    else:
        print("Please fix the issues above before running the blog crew.")
