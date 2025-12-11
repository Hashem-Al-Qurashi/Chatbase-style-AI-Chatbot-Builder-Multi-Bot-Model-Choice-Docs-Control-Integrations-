#!/usr/bin/env python3
"""
Test chat with the newly uploaded test document
"""

import requests

# Test configuration
BASE_URL = "http://localhost:8000"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMzFmMzc2NTItYmY2Mi00Y2ZmLThiODctOGUwM2YxMGEwZGEyIiwiZW1haWwiOiJhZG1pbkB0ZXN0LmNvbSIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJleHAiOjE3NjEzMjI2NDcsImlhdCI6MTc2MTMyMTc0NywianRpIjoiYWExNjg3OTQtZWY1YS00ZDFkLWFlYTEtNjIxODZmZmNkZDBlIiwic2NvcGVzIjpbInJlYWQiLCJ3cml0ZSJdfQ.ZjQpieuvrGoLG1ZcbQlcaLPm5TuC_j4Do48ByxLihmU"
CHATBOT_ID = "d6d1e8cc-fb61-439b-8b45-1339b369d31d"

session = requests.Session()
session.headers.update({
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json'
})

# Test query about the new document content
query = "Tell me about the document I just uploaded about testing RAG system"

print(f"🔍 Testing query: {query}")

response = session.post(
    f"{BASE_URL}/api/v1/chat/private/{CHATBOT_ID}/",
    json={"message": query}
)

if response.status_code == 200:
    data = response.json()
    
    print(f"\n✅ Response received:")
    print(f"Message: {data['message']}")
    
    print(f"\n📚 Citations ({len(data.get('citations', []))}):")
    for i, citation in enumerate(data.get('citations', [])):
        print(f"   {i+1}. {citation[:100]}...")
    
    print(f"\n🔒 Privacy compliant: {data.get('privacy_status', {}).get('compliant')}")
    print(f"📖 Sources used: {data.get('sources', {}).get('total_used')}")
    print(f"📖 Citable sources: {data.get('sources', {}).get('citable')}")
    
    # Check if the response mentions content from our new document
    content = data['message'].lower()
    new_doc_indicators = [
        'testing ai chatbot',
        'rag pipeline',
        'vector embeddings',
        'privacy-first architecture',
        'natural language processing'
    ]
    
    found_indicators = [indicator for indicator in new_doc_indicators if indicator in content]
    
    if found_indicators:
        print(f"\n✅ NEW DOCUMENT CONTENT DETECTED!")
        print(f"Found indicators: {found_indicators}")
    else:
        print(f"\n⚠️  Could not definitively identify new document content")
        
else:
    print(f"❌ Request failed: {response.status_code} - {response.text}")