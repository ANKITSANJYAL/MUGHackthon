"""
MongoDB Atlas RAG Database Setup Script

This script initializes the MongoDB Atlas database with historical JIRA ticket data
for the JIAE (JIRA-Integrated Autonomous Engineer) system.

Usage:
    1. Create a MongoDB Atlas account and cluster
    2. Copy .env.example to .env and fill in your connection details
    3. Run: python rag/setup_database.py
"""

import json
import os
from datetime import datetime
from typing import List, Dict
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from dotenv import load_dotenv


class RAGDatabaseSetup:
    """Handles the setup and initialization of the RAG database."""
    
    def __init__(self):
        """Initialize database connection from environment variables."""
        load_dotenv()
        
        self.mongodb_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'jiae_rag')
        self.collection_name = os.getenv('MONGODB_COLLECTION_NAME', 'historical_fixes')
        
        if not self.mongodb_uri:
            raise ValueError("MONGODB_URI not found in environment variables. Please create .env file.")
        
        self.client = None
        self.db = None
        self.collection = None
    
    def connect(self) -> bool:
        """
        Establish connection to MongoDB Atlas.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            print(f"🔌 Connecting to MongoDB Atlas...")
            self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            
            # Test the connection
            self.client.admin.command('ping')
            
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            print(f"✅ Successfully connected to database: {self.db_name}")
            return True
            
        except ConnectionFailure as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            return False
    
    def create_indexes(self):
        """Create necessary indexes for efficient querying."""
        print("\n📊 Creating database indexes...")
        
        try:
            # Index on ticket_id for quick lookups
            self.collection.create_index([("ticket_id", ASCENDING)], unique=True)
            print("  ✓ Created unique index on ticket_id")
            
            # Index on tags for similarity searches
            self.collection.create_index([("tags", ASCENDING)])
            print("  ✓ Created index on tags")
            
            # Index on component for filtering
            self.collection.create_index([("component", ASCENDING)])
            print("  ✓ Created index on component")
            
            # Index on severity for prioritization
            self.collection.create_index([("severity", ASCENDING)])
            print("  ✓ Created index on severity")
            
            # Compound index for common query patterns
            self.collection.create_index([
                ("component", ASCENDING),
                ("severity", DESCENDING)
            ])
            print("  ✓ Created compound index on component + severity")
            
            print("✅ All indexes created successfully")
            
        except Exception as e:
            print(f"⚠️  Error creating indexes: {e}")
    
    def load_historical_data(self, json_file_path: str) -> int:
        """
        Load historical ticket data from JSON file into MongoDB.
        
        Args:
            json_file_path: Path to the JSON file containing historical tickets
            
        Returns:
            int: Number of documents inserted
        """
        print(f"\n📥 Loading historical tickets from: {json_file_path}")
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                tickets = json.load(f)
            
            print(f"  Found {len(tickets)} tickets to load")
            
            # Add metadata to each document
            for ticket in tickets:
                ticket['created_at'] = datetime.utcnow()
                ticket['indexed_at'] = datetime.utcnow()
                ticket['source'] = 'seed_data'
            
            # Insert documents
            inserted_count = 0
            skipped_count = 0
            
            for ticket in tickets:
                try:
                    self.collection.insert_one(ticket)
                    inserted_count += 1
                    print(f"  ✓ Inserted {ticket['ticket_id']}: {ticket['title']}")
                    
                except DuplicateKeyError:
                    skipped_count += 1
                    print(f"  ⊙ Skipped {ticket['ticket_id']} (already exists)")
            
            print(f"\n✅ Successfully inserted {inserted_count} tickets")
            if skipped_count > 0:
                print(f"⊙ Skipped {skipped_count} duplicate tickets")
            
            return inserted_count
            
        except FileNotFoundError:
            print(f"❌ Error: File not found: {json_file_path}")
            return 0
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON format: {e}")
            return 0
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return 0
    
    def verify_setup(self) -> Dict:
        """
        Verify the database setup and return statistics.
        
        Returns:
            dict: Database statistics
        """
        print("\n🔍 Verifying database setup...")
        
        stats = {
            'total_documents': self.collection.count_documents({}),
            'unique_components': len(self.collection.distinct('component')),
            'unique_tags': len(self.collection.distinct('tags')),
            'severity_distribution': {},
            'indexes': [idx['name'] for idx in self.collection.list_indexes()]
        }
        
        # Get severity distribution
        pipeline = [
            {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        severity_counts = list(self.collection.aggregate(pipeline))
        stats['severity_distribution'] = {item['_id']: item['count'] for item in severity_counts}
        
        # Print statistics
        print(f"  📊 Total Documents: {stats['total_documents']}")
        print(f"  🏷️  Unique Components: {stats['unique_components']}")
        print(f"  🔖 Unique Tags: {stats['unique_tags']}")
        print(f"  📈 Severity Distribution:")
        for severity, count in stats['severity_distribution'].items():
            print(f"      {severity}: {count}")
        print(f"  📑 Indexes: {', '.join(stats['indexes'])}")
        
        return stats
    
    def sample_queries(self):
        """Run sample queries to demonstrate RAG capabilities."""
        print("\n🔎 Running sample queries...")
        
        # Query 1: Find authentication-related issues
        print("\n  Query 1: Authentication-related issues")
        auth_issues = list(self.collection.find(
            {"tags": "authentication"},
            {"ticket_id": 1, "title": 1, "_id": 0}
        ).limit(3))
        for issue in auth_issues:
            print(f"    • {issue['ticket_id']}: {issue['title']}")
        
        # Query 2: Critical severity issues
        print("\n  Query 2: Critical severity issues")
        critical_issues = list(self.collection.find(
            {"severity": "critical"},
            {"ticket_id": 1, "title": 1, "_id": 0}
        ).limit(3))
        for issue in critical_issues:
            print(f"    • {issue['ticket_id']}: {issue['title']}")
        
        # Query 3: Database-related issues
        print("\n  Query 3: Database-related issues")
        db_issues = list(self.collection.find(
            {"component": "database"},
            {"ticket_id": 1, "title": 1, "root_cause": 1, "_id": 0}
        ))
        for issue in db_issues:
            print(f"    • {issue['ticket_id']}: {issue['title']}")
            print(f"      Root cause: {issue['root_cause'][:80]}...")
    
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            print("\n👋 Database connection closed")


def main():
    """Main execution function."""
    print("=" * 70)
    print("  JIAE RAG Database Setup")
    print("  MongoDB Atlas + Historical JIRA Tickets")
    print("=" * 70)
    
    # Initialize setup
    setup = RAGDatabaseSetup()
    
    try:
        # Connect to database
        if not setup.connect():
            print("\n❌ Setup failed: Could not connect to database")
            return
        
        # Create indexes
        setup.create_indexes()
        
        # Load historical data
        data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'historical_tickets.json')
        inserted_count = setup.load_historical_data(data_file)
        
        if inserted_count == 0:
            print("\n⚠️  Warning: No documents were inserted")
        
        # Verify setup
        stats = setup.verify_setup()
        
        # Run sample queries
        setup.sample_queries()
        
        print("\n" + "=" * 70)
        print("  ✅ RAG Database Setup Complete!")
        print("=" * 70)
        print(f"\n  Database: {setup.db_name}")
        print(f"  Collection: {setup.collection_name}")
        print(f"  Total Documents: {stats['total_documents']}")
        print("\n  🚀 Ready for RAG-powered bug fixes!")
        
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
    
    finally:
        setup.close()


if __name__ == "__main__":
    main()
