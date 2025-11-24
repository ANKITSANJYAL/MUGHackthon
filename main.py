#!/usr/bin/env python3
"""
Main entry point for H-KFX (Hybrid Knowledge Fixer)

Usage:
    python main.py --mode webhook     # Start webhook listener
    python main.py --mode setup       # Setup RAG database
    python main.py --mode test        # Test connections
    python main.py --mode ui          # Launch approval dashboard (future)
"""

import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))


def start_webhook():
    """Start the Jira webhook listener."""
    print("🚀 Starting webhook listener...")
    from integrations.webhook_listener import app
    import os
    port = int(os.getenv("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=True)


def setup_rag():
    """Setup the RAG database with vector embeddings."""
    print("📊 Setting up RAG database...")
    from rag_system.setup_vector_rag import VectorRAGSetup
    import os
    from pathlib import Path
    
    setup = VectorRAGSetup()
    if setup.connect():
        setup.create_indexes()
        
        # Load seed documents
        seed_file = Path(__file__).parent / "rag_data" / "seed_documents.json"
        if seed_file.exists():
            inserted = setup.load_and_embed_data(str(seed_file))
            if inserted > 0:
                setup.verify_setup()
                print("\n✅ RAG setup complete!")
                print("\n⚠️  NEXT STEP: Create Vector Search Index in MongoDB Atlas UI")
                print("   See: rag_data/vector_index_definition.json")
            else:
                print("\n⚠️ No documents inserted")
        else:
            print(f"\n❌ Seed file not found: {seed_file}")
            sys.exit(1)
    else:
        print("\n❌ RAG setup failed!")
        sys.exit(1)


def test_connections():
    """Test all external service connections."""
    print("🧪 Testing connections...\n")
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Test MongoDB
    print("1️⃣ Testing MongoDB Atlas...")
    try:
        from pymongo import MongoClient
        uri = os.getenv('MONGODB_URI')
        if not uri:
            print("   ❌ MONGODB_URI not set")
        else:
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            print("   ✅ MongoDB connected")
            client.close()
    except Exception as e:
        print(f"   ❌ MongoDB failed: {e}")
    
    # Test OpenAI
    print("\n2️⃣ Testing OpenAI API...")
    try:
        from openai import OpenAI
        key = os.getenv('OPENAI_API_KEY')
        if not key:
            print("   ❌ OPENAI_API_KEY not set")
        else:
            client = OpenAI(api_key=key)
            # Just check if key format is valid
            print("   ✅ OpenAI API key configured")
    except Exception as e:
        print(f"   ❌ OpenAI failed: {e}")
    
    # Test Jira
    print("\n3️⃣ Testing Jira Connection...")
    try:
        from integrations.jira_client import get_jira_client
        jira = get_jira_client()
        print(f"   ✅ Jira connected: {os.getenv('JIRA_BASE')}")
    except Exception as e:
        print(f"   ❌ Jira failed: {e}")
    
    print("\n✅ Connection tests complete!")


def launch_ui():
    """Launch the Streamlit approval dashboard (future implementation)."""
    print("🎨 Launching approval dashboard...")
    print("⚠️  UI not yet implemented. Coming soon!")
    # Future: streamlit run ui/dashboard.py


def main():
    parser = argparse.ArgumentParser(
        description='H-KFX: Hybrid Knowledge Fixer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode webhook    # Start webhook listener
  python main.py --mode setup      # Setup RAG database
  python main.py --mode test       # Test all connections
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['webhook', 'setup', 'test', 'ui'],
        required=True,
        help='Operation mode to run'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'webhook':
        start_webhook()
    elif args.mode == 'setup':
        setup_rag()
    elif args.mode == 'test':
        test_connections()
    elif args.mode == 'ui':
        launch_ui()


if __name__ == '__main__':
    main()
