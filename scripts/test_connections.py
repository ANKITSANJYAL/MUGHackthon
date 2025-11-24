"""
Quick connection tests for MongoDB Atlas and OpenAI

Run this before setup_vector_rag.py to verify your credentials work.
"""

import os
from dotenv import load_dotenv

def test_mongodb():
    """Test MongoDB Atlas connection."""
    print("🧪 Testing MongoDB Atlas connection...")
    try:
        from pymongo import MongoClient
        
        load_dotenv()
        uri = os.getenv('MONGODB_URI')
        
        if not uri:
            print("❌ MONGODB_URI not found in .env file")
            return False
        
        if '<password>' in uri or '<username>' in uri:
            print("❌ Replace <username> and <password> in your connection string!")
            return False
        
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        print("✅ MongoDB Atlas connection successful!")
        print(f"   URI: {uri[:50]}...{uri[-20:]}")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check MONGODB_URI in .env file")
        print("   2. Verify password (no brackets!)")
        print("   3. Check IP whitelist in Atlas Network Access")
        return False


def test_openai():
    """Test OpenAI API connection."""
    print("\n🧪 Testing OpenAI API...")
    try:
        from openai import OpenAI
        
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            print("❌ OPENAI_API_KEY not found in .env file")
            return False
        
        if 'your-key' in api_key or api_key == 'sk-proj-...your-key...':
            print("❌ Replace with your actual OpenAI API key!")
            return False
        
        client = OpenAI(api_key=api_key)
        
        # Test embedding generation
        response = client.embeddings.create(
            model='text-embedding-3-small',
            input='test connection'
        )
        
        embedding_dim = len(response.data[0].embedding)
        
        print(f"✅ OpenAI API connection successful!")
        print(f"   Model: text-embedding-3-small")
        print(f"   Dimensions: {embedding_dim}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI API connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Check OPENAI_API_KEY in .env file")
        print("   2. Verify key at https://platform.openai.com/api-keys")
        print("   3. Ensure billing is set up and you have credits")
        return False


def main():
    """Run all connection tests."""
    print("=" * 70)
    print("  Connection Tests - MongoDB Atlas + OpenAI")
    print("=" * 70)
    
    # Check if .env exists
    if not os.path.exists('.env'):
        print("\n❌ .env file not found!")
        print("   Run: cp .env.example .env")
        print("   Then edit .env with your credentials")
        return
    
    # Test connections
    mongodb_ok = test_mongodb()
    openai_ok = test_openai()
    
    print("\n" + "=" * 70)
    if mongodb_ok and openai_ok:
        print("  ✅ All tests passed! Ready to run setup_vector_rag.py")
        print("=" * 70)
        print("\nNext step:")
        print("  python rag/setup_vector_rag.py")
    else:
        print("  ❌ Some tests failed. Fix the issues above before continuing.")
        print("=" * 70)


if __name__ == "__main__":
    main()
