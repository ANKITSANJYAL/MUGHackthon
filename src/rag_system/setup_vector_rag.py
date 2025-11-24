"""
MongoDB Atlas Vector RAG Setup Script

This script sets up the RAG database with vector embeddings for semantic search.
It follows the proper schema with OpenAI embeddings for the JIAE system.

Usage:
    1. Create MongoDB Atlas account with M0 cluster
    2. Copy .env.example to .env and configure
    3. Get OpenAI API key for embeddings
    4. Run: python rag/setup_vector_rag.py
"""

import json
import os
from datetime import datetime
from typing import List, Dict
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
from openai import OpenAI


class VectorRAGSetup:
    """Handles setup of vector-enabled RAG database."""
    
    def __init__(self):
        """Initialize connections from environment variables."""
        load_dotenv()
        
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'JIAE_Knowledge_Base')
        self.collection_name = os.getenv('MONGODB_COLLECTION_NAME', 'PastFixes')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        if not self.mongodb_uri:
            raise ValueError("MONGODB_URI not found. Create .env file from .env.example")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found. Add to .env file")
        
        self.openai_client = OpenAI(api_key=openai_key)
        self.client = None
        self.db = None
        self.collection = None
        
        # Embedding model configuration
        self.embedding_model = "text-embedding-3-small"  # 1536 dimensions
        self.embedding_dimensions = 1536
    
    def connect(self) -> bool:
        """Establish MongoDB Atlas connection."""
        try:
            print(f"🔌 Connecting to MongoDB Atlas...")
            self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            print(f"✅ Connected to database: {self.db_name}")
            print(f"   Collection: {self.collection_name}")
            return True
            
        except ConnectionFailure as e:
            print(f"❌ MongoDB connection failed: {e}")
            return False
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text using OpenAI.
        
        Args:
            text: Text to embed (internal_context field)
            
        Returns:
            List of floats (1536 dimensions)
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"⚠️  Embedding generation failed: {e}")
            return [0.0] * self.embedding_dimensions  # Fallback
    
    def create_indexes(self):
        """Create standard indexes (vector index created separately in Atlas UI)."""
        print("\n📊 Creating database indexes...")
        
        try:
            # Standard indexes
            self.collection.create_index([("source_id", ASCENDING)], unique=True)
            print("  ✓ Created unique index on source_id")
            
            self.collection.create_index([("project_module", ASCENDING)])
            print("  ✓ Created index on project_module")
            
            self.collection.create_index([("fix_type", ASCENDING)])
            print("  ✓ Created index on fix_type")
            
            self.collection.create_index([("ticket_summary", "text")])
            print("  ✓ Created text index on ticket_summary")
            
            print("\n⚠️  IMPORTANT: You must create the Vector Search Index manually in Atlas UI:")
            print("   1. Go to Atlas → Your Cluster → Search Indexes")
            print("   2. Click 'Create Search Index' → 'JSON Editor'")
            print("   3. Use the vector_index_definition.json file")
            print("   4. Name it: 'vector_index'")
            
        except Exception as e:
            print(f"⚠️  Error creating indexes: {e}")
    
    def load_and_embed_data(self, json_file_path: str) -> int:
        """
        Load seed data and generate embeddings.
        
        Args:
            json_file_path: Path to seed_documents.json
            
        Returns:
            Number of documents inserted
        """
        print(f"\n📥 Loading and embedding documents from: {json_file_path}")
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            print(f"  Found {len(documents)} documents to process")
            print(f"  Generating embeddings with {self.embedding_model}...\n")
            
            inserted_count = 0
            
            for idx, doc in enumerate(documents, 1):
                # Generate embedding for internal_context
                print(f"  [{idx}/{len(documents)}] Embedding {doc['source_id']}...")
                embedding = self.generate_embedding(doc['internal_context'])
                
                # Add metadata
                doc['embedding'] = embedding
                doc['embedding_model'] = self.embedding_model
                doc['embedding_dimensions'] = len(embedding)
                doc['created_at'] = datetime.utcnow()
                doc['indexed_at'] = datetime.utcnow()
                
                # Insert document
                try:
                    self.collection.insert_one(doc)
                    inserted_count += 1
                    print(f"      ✓ Inserted with {len(embedding)}-dim vector")
                except Exception as e:
                    print(f"      ✗ Failed: {e}")
            
            print(f"\n✅ Successfully inserted {inserted_count} documents with embeddings")
            return inserted_count
            
        except FileNotFoundError:
            print(f"❌ File not found: {json_file_path}")
            return 0
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            return 0
    
    def verify_setup(self) -> Dict:
        """Verify database setup and return statistics."""
        print("\n🔍 Verifying RAG database setup...")
        
        stats = {
            'total_documents': self.collection.count_documents({}),
            'documents_with_embeddings': self.collection.count_documents({'embedding': {'$exists': True}}),
            'modules': list(self.collection.distinct('project_module')),
            'fix_types': list(self.collection.distinct('fix_type')),
            'indexes': [idx['name'] for idx in self.collection.list_indexes()]
        }
        
        # Sample document to verify embedding
        sample = self.collection.find_one({'embedding': {'$exists': True}})
        if sample:
            stats['embedding_dimension'] = len(sample.get('embedding', []))
            stats['embedding_model'] = sample.get('embedding_model', 'unknown')
        
        # Print stats
        print(f"  📊 Total Documents: {stats['total_documents']}")
        print(f"  🔢 With Embeddings: {stats['documents_with_embeddings']}")
        print(f"  📁 Modules: {', '.join(stats['modules'])}")
        print(f"  🏷️  Fix Types: {', '.join(stats['fix_types'])}")
        print(f"  🧮 Embedding Model: {stats.get('embedding_model', 'N/A')}")
        print(f"  📐 Embedding Dimensions: {stats.get('embedding_dimension', 0)}")
        print(f"  📑 Indexes: {', '.join(stats['indexes'])}")
        
        return stats
    
    def demo_queries(self):
        """Demonstrate query capabilities (non-vector)."""
        print("\n🔎 Demo: Standard queries (vector search requires Atlas UI setup)")
        
        # Query by module
        print("\n  Query 1: Authentication module fixes")
        auth_docs = list(self.collection.find(
            {"project_module": "user_auth"},
            {"source_id": 1, "ticket_summary": 1, "_id": 0}
        ).limit(3))
        for doc in auth_docs:
            print(f"    • {doc['source_id']}: {doc['ticket_summary']}")
        
        # Query by fix type
        print("\n  Query 2: Configuration fixes")
        config_docs = list(self.collection.find(
            {"fix_type": "Config"},
            {"source_id": 1, "ticket_summary": 1, "_id": 0}
        ))
        for doc in config_docs:
            print(f"    • {doc['source_id']}: {doc['ticket_summary'][:60]}...")
        
        print("\n  💡 For semantic similarity queries, use the query_rag.py script")
        print("      after setting up the Vector Search Index in Atlas UI")
    
    def close(self):
        """Close connections."""
        if self.client:
            self.client.close()
            print("\n👋 Database connection closed")


def main():
    """Main execution."""
    print("=" * 80)
    print("  JIAE Vector RAG Database Setup")
    print("  MongoDB Atlas + OpenAI Embeddings")
    print("=" * 80)
    
    setup = VectorRAGSetup()
    
    try:
        # Connect
        if not setup.connect():
            print("\n❌ Setup failed: Could not connect to database")
            return
        
        # Create indexes
        setup.create_indexes()
        
        # Load and embed data
        seed_file = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            'rag_data', 
            'seed_documents.json'
        )
        inserted_count = setup.load_and_embed_data(seed_file)
        
        if inserted_count == 0:
            print("\n⚠️  No documents were inserted")
            return
        
        # Verify
        stats = setup.verify_setup()
        
        # Demo queries
        setup.demo_queries()
        
        print("\n" + "=" * 80)
        print("  ✅ Vector RAG Database Setup Complete!")
        print("=" * 80)
        print(f"\n  📊 Loaded {stats['total_documents']} documents with embeddings")
        print(f"  🎯 Scenarios: 3 (auth, db_query, config)")
        print(f"  📐 Embedding: {stats.get('embedding_dimension', 0)} dimensions")
        print("\n  ⚠️  NEXT STEP: Create Vector Search Index in Atlas UI")
        print("      Follow instructions in rag/README.md")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        setup.close()


if __name__ == "__main__":
    main()
