#!/usr/bin/env python3
"""
PostgreSQL ADL/IADL Assessment Database Seeder
Initializes the database with SQLAlchemy models and creates tables.
Now uses SQLAlchemy models from api/database/models.py instead of raw SQL.
"""
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database.connection import initialize_database, database_health_check
from api.database.models import Base

class PostgresAssessmentSeeder:
    """Database seeder using SQLAlchemy models"""
    
    def __init__(self):
        self.initialized = False
    
    def initialize_database(self):
        """Initialize database with SQLAlchemy models"""
        try:
            print("🗄️ Initializing PostgreSQL database with SQLAlchemy models...")
            db_info = initialize_database()
            
            print(f"✅ Database initialized successfully")
            print(f"   Database: {db_info['database_name']}")
            print(f"   Active connections: {db_info['active_connections']}")
            
            # SQLAlchemy tables are created automatically
            print(f"   Tables: Created by SQLAlchemy models")
            
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    
    def check_database_health(self):
        """Check database health and connectivity"""
        try:
            health = database_health_check()
            
            if health['status'] == 'healthy':
                print(f"✅ Database health check passed")
                print(f"   Database: {health['database']}")
                print(f"   Active connections: {health['connections']}")
                return True
            else:
                print(f"❌ Database health check failed: {health.get('error', 'unknown')}")
                return False
                
        except Exception as e:
            print(f"❌ Database health check error: {e}")
            return False
    
    def run_full_seed(self):
        """Run complete database seeding process"""
        print("🚀 Starting PostgreSQL database seeding...")
        print("📋 Using SQLAlchemy models from api/database/models.py")
        print()
        
        # Initialize database
        if not self.initialize_database():
            print("❌ Failed to initialize database")
            return False
        
        print()
        
        # Check health
        if not self.check_database_health():
            print("❌ Database health check failed")
            return False
        
        print()
        print("🎉 Database seeding completed successfully!")
        print("📊 Database is ready for clinical assessments")
        print()
        print("💡 Note: Question data is now managed by Neo4j service")
        print("   - Questions are loaded dynamically from Neo4j")
        print("   - Assessment responses are stored in PostgreSQL")
        print("   - Run 'scripts/seed_neo4j.py' to populate question data")
        
        return True


def main():
    """Main function to run the database seeder"""
    print("=== AssessBot2 PostgreSQL Database Seeder ===")
    print("📋 Using SQLAlchemy models for database initialization")
    print()
    
    try:
        seeder = PostgresAssessmentSeeder()
        success = seeder.run_full_seed()
        
        if success:
            print("\n✅ Database seeding completed successfully!")
            print("🔗 Next steps:")
            print("   1. Run 'scripts/seed_neo4j.py' to populate question data")
            print("   2. Start the API server with 'python api/main.py'")
            print("   3. Access the API at http://localhost:8000")
            return 0
        else:
            print("\n❌ Database seeding failed")
            return 1
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
