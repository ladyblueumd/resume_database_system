#!/usr/bin/env python3
"""
Test script to verify database functionality
"""

import sqlite3
import json
from pathlib import Path

def test_database():
    """Test database connectivity and content"""
    db_path = "resume_database.db"
    
    if not Path(db_path).exists():
        print("❌ Database not found. Run resume_extractor.py first.")
        return False
    
    print("✅ Database found")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Test 1: Check tables exist
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name;
    """)
    tables = cursor.fetchall()
    print(f"\n📊 Found {len(tables)} tables:")
    for table in tables:
        print(f"   - {table[0]}")
    
    # Test 2: Count components
    cursor.execute("SELECT COUNT(*) FROM resume_components")
    component_count = cursor.fetchone()[0]
    print(f"\n📋 Resume components: {component_count}")
    
    # Test 3: Show component breakdown
    cursor.execute("""
        SELECT st.name, COUNT(*) as count
        FROM resume_components rc
        JOIN section_types st ON rc.section_type_id = st.id
        GROUP BY st.name
        ORDER BY count DESC
    """)
    print("\n📑 Components by section:")
    for row in cursor.fetchall():
        print(f"   - {row[0]}: {row[1]}")
    
    # Test 4: Sample components
    cursor.execute("""
        SELECT title, keywords 
        FROM resume_components 
        LIMIT 5
    """)
    print("\n🔍 Sample components:")
    for row in cursor.fetchall():
        print(f"   - {row[0][:60]}...")
        if row[1]:
            print(f"     Keywords: {row[1][:50]}...")
    
    # Test 5: Employment history
    cursor.execute("SELECT COUNT(*) FROM employment_history")
    emp_count = cursor.fetchone()[0]
    print(f"\n💼 Employment records: {emp_count}")
    
    conn.close()
    return True

def test_api():
    """Test API connectivity"""
    print("\n🌐 Testing API...")
    try:
        import requests
        response = requests.get("http://localhost:5000/api/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ API is running")
            print(f"   - Database connected: {data.get('database', False)}")
            print(f"   - AI model loaded: {data.get('semantic_model', False)}")
            return True
        else:
            print("❌ API returned error:", response.status_code)
    except Exception as e:
        print("❌ Cannot connect to API. Make sure Flask is running (python3 app.py)")
        print(f"   Error: {e}")
    return False

def main():
    print("🧪 Resume Database System Test")
    print("=" * 50)
    
    # Test database
    db_ok = test_database()
    
    # Test API
    api_ok = test_api()
    
    print("\n" + "=" * 50)
    if db_ok:
        print("✅ Database is ready")
    else:
        print("❌ Database issues detected")
    
    if api_ok:
        print("✅ API is ready")
    else:
        print("⚠️  API not running - start with: python3 app.py")
    
    print("\n📝 Next steps:")
    if db_ok and not api_ok:
        print("1. Start the API: python3 app.py")
        print("2. Open browser to: http://localhost:5000")
    elif db_ok and api_ok:
        print("1. System is ready!")
        print("2. Open browser to: http://localhost:5000")
    else:
        print("1. Run: python3 resume_extractor.py")
        print("2. Then: python3 app.py")

if __name__ == "__main__":
    main() 