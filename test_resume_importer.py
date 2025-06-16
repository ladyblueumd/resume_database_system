#!/usr/bin/env python3
"""
Test Resume Importer Component Creation
This script tests the Resume Importer workflow to ensure component creation works correctly.
"""

import requests
import json

def test_resume_importer():
    """Test the Resume Importer component creation workflow"""
    base_url = 'http://127.0.0.1:5001'
    
    print("🧪 Testing Resume Importer Component Creation Workflow")
    print("=" * 60)
    
    # Test 1: Check if the main page loads
    print("1. Testing main page load...")
    try:
        response = requests.get(f'{base_url}/')
        if response.status_code == 200:
            print("   ✅ Main page loads successfully")
        else:
            print(f"   ❌ Main page failed to load: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Error loading main page: {e}")
        return
    
    # Test 2: Check if add_component endpoint exists
    print("2. Testing add_component endpoint...")
    test_component = {
        "section_type": "professional_summary",
        "title": "Test Component from Resume Importer",
        "content": "This is a test component created to verify the Resume Importer functionality works correctly.",
        "keywords": "test, resume, importer",
        "industry_tags": "technology"
    }
    
    try:
        response = requests.post(
            f'{base_url}/add_component',
            headers={'Content-Type': 'application/json'},
            json=test_component
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"   ✅ Component created successfully: {result.get('message')}")
                component_id = result.get('id')
                print(f"   📝 Component ID: {component_id}")
            else:
                print(f"   ❌ Component creation failed: {result.get('error')}")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error testing add_component: {e}")
    
    # Test 3: Check if components can be retrieved
    print("3. Testing component retrieval...")
    try:
        response = requests.get(f'{base_url}/api/components')
        if response.status_code == 200:
            components = response.json()
            print(f"   ✅ Retrieved {len(components)} components")
            if components:
                print(f"   📋 Latest component: {components[0].get('title', 'No title')}")
        else:
            print(f"   ❌ Failed to retrieve components: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error retrieving components: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Resume Importer Troubleshooting Guide:")
    print("1. Go to the Resume Importer tab")
    print("2. Either:")
    print("   a) Paste resume text in the text area and click 'Display Text'")
    print("   b) Upload a resume file (.txt, .doc, .docx, .pdf)")
    print("3. Once text is displayed, SELECT some text with your mouse")
    print("4. Click 'Create Component from Selection' button")
    print("5. Fill out the modal form and click 'Save Component'")
    print("\n💡 If the modal doesn't appear, check browser console for errors")
    print("💡 If text selection doesn't work, try refreshing the page")

if __name__ == '__main__':
    test_resume_importer() 