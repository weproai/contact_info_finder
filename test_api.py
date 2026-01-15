#!/usr/bin/env python
"""
Test script for Contact Info Finder API
"""
import requests
import json
from typing import Dict

# API base URL
BASE_URL = "http://localhost:8000"

# Test cases with various contact information formats
TEST_CASES = [
    {
        "name": "Service Request Format",
        "text": """
        Robert Scheckler
        
        4754195929
        30 Fountain St, Port Charlotte, Florida 33953
        Expert_Garage_door
        Genie Model 2028 garage door repair, new remote needed.
        4–6pm
        """
    },
    {
        "name": "Complete Contact",
        "text": """
        John Smith from TechCorp International can be reached at (555) 123-4567 ext. 234 
        or his mobile 555-987-6543. Email: john.smith@techcorp.com
        Office: Suite 1500, 123 Business Boulevard, San Francisco, CA 94105, USA
        """
    },
    {
        "name": "Multiple Phones",
        "text": """
        Contact: Sarah Johnson
        ABC Marketing Solutions
        Primary: 555-111-2222
        Cell: (555) 333-4444
        Fax: 555.555.5555
        sarah@abcmarketing.net
        789 Commerce Street, Apt 4B, New York, NY 10013
        """
    },
    {
        "name": "Structured Format",
        "text": """
        Michael Davis
        555-234-5678
        mike@techsolutions.com
        1234 Oak Avenue, Suite 100
        Dallas, TX 75201
        Tech Solutions Inc.
        Network setup required
        """
    },
    {
        "name": "International Format",
        "text": """
        Client: Maria Garcia
        Global Enterprises Ltd.
        Phone: +44 20 7946 0958
        Email: m.garcia@globalent.co.uk
        Address: Floor 25, 30 St Mary Axe, London EC3A 8BF, United Kingdom
        """
    },
    {
        "name": "Minimal Info",
        "text": "Call Bob at 555-9876 regarding the project"
    },
    {
        "name": "Complex Address",
        "text": """
        Deliver to:
        Dr. James Wilson
        MedTech Innovations
        Building A, Suite 200, Floor 2
        4567 Research Park Drive
        Boston, MA 02134
        Direct line: 617-555-1234 x567
        """
    }
]


def test_health_check():
    """Test the health endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ API Status: {data['status']}")
        print(f"  - Ollama: {data['ollama_status']}")
        print(f"  - ChromaDB: {data['chromadb_status']}")
    else:
        print(f"✗ Health check failed: {response.status_code}")


def test_extraction(test_case: Dict):
    """Test extraction endpoint with a test case"""
    print(f"\n=== Testing: {test_case['name']} ===")
    print(f"Input text: {test_case['text'][:100]}...")
    
    payload = {
        "text": test_case['text'],
        "use_cache": True
    }
    
    response = requests.post(f"{BASE_URL}/extract", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            result = data['data']
            print(f"✓ Extraction successful (took {data['processing_time']:.2f}s)")
            print(f"  Cache hit: {data['cache_hit']}")
            
            # Display extracted data
            if result.get('client_name'):
                print(f"  Client: {result['client_name']}")
            if result.get('company_name'):
                print(f"  Company: {result['company_name']}")
            if result.get('email'):
                print(f"  Email: {result['email']}")
            
            # Phone numbers
            if result.get('phone_numbers'):
                for i, phone in enumerate(result['phone_numbers']):
                    ext = f" ext. {phone['extension']}" if phone.get('extension') else ""
                    print(f"  Phone {i+1}: {phone['number']}{ext} ({phone['type']})")
            
            # Address
            if result.get('address'):
                addr = result['address']
                addr_parts = []
                if addr.get('unit'):
                    addr_parts.append(addr['unit'])
                if addr.get('street'):
                    addr_parts.append(addr['street'])
                if addr.get('city'):
                    addr_parts.append(addr['city'])
                if addr.get('state'):
                    addr_parts.append(addr['state'])
                if addr.get('postal_code'):
                    addr_parts.append(addr['postal_code'])
                if addr.get('country'):
                    addr_parts.append(addr['country'])
                
                if addr_parts:
                    print(f"  Address: {', '.join(addr_parts)}")
            
            # Confidence scores
            if result.get('confidence_scores'):
                scores = result['confidence_scores']
                avg_confidence = sum(scores.values()) / len(scores) if scores else 0
                print(f"  Average confidence: {avg_confidence:.2%}")
        else:
            print(f"✗ Extraction failed: {data.get('error', 'Unknown error')}")
    else:
        print(f"✗ Request failed: {response.status_code}")
        print(f"  Error: {response.text}")


def test_stats():
    """Test statistics endpoint"""
    print("\n=== Testing Statistics ===")
    response = requests.get(f"{BASE_URL}/stats")
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            stats = data['stats']
            print(f"✓ Total extractions: {stats.get('total_extractions', 0)}")
            print(f"  Collection: {stats.get('collection_name')}")
    else:
        print(f"✗ Stats request failed: {response.status_code}")


def main():
    """Run all tests"""
    print("Contact Info Finder API Test Suite")
    print("==================================")
    
    # Check if API is running
    try:
        requests.get(BASE_URL, timeout=2)
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: API is not running!")
        print("  Please start the API with: python run.py")
        return
    
    # Run tests
    test_health_check()
    
    for test_case in TEST_CASES:
        test_extraction(test_case)
    
    test_stats()
    
    print("\n\nTest suite completed!")


if __name__ == "__main__":
    main()