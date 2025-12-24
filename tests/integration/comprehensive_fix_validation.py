#!/usr/bin/env python3
"""
Comprehensive validation of the file content corruption fix.
This test specifically validates the claims made in the fix summary.
"""

import requests
import json
import time
import os
import sys


def main():
    """Run comprehensive validation tests."""
    print("🔍 GRUMPY TESTER'S COMPREHENSIVE FILE CORRUPTION FIX VALIDATION")
    print("=" * 70)
    
    # Configuration
    BASE_URL = "http://localhost:8000"
    TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMzFmMzc2NTItYmY2Mi00Y2ZmLThiODctOGUwM2YxMGEwZGEyIiwiZW1haWwiOiJhZG1pbkB0ZXN0LmNvbSIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJleHAiOjE3NjEzMTY5NTksImlhdCI6MTc2MTMxNjA1OSwianRpIjoiMWMyZGViYzgtZDhlZS00ZjY5LWI5NTEtOWNjYjZhNDc3NjBlIiwic2NvcGVzIjpbInJlYWQiLCJ3cml0ZSJdfQ.uGbhJjOJrER-S6DXoUVhb2C1r73efOXmdWhUxmyfvRU"
    CHATBOT_ID = "d6d1e8cc-fb61-439b-8b45-1339b369d31d"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    # Test file content
    test_content = """FINAL VALIDATION TEST - COMPREHENSIVE CHECK
This content must survive the entire upload and processing pipeline.

VALIDATION MARKERS:
- FINAL_TEST_CONTENT_PRESERVED
- BUFFER_CONSUMPTION_BUG_DEFINITELY_FIXED
- TEXT_EXTRACTION_PIPELINE_WORKING
- KNOWLEDGE_CHUNKS_CREATED_SUCCESSFULLY
- END_TO_END_VALIDATION_COMPLETE

Critical test: If this exact content appears in knowledge chunks,
the file content corruption bug is truly fixed.

Test executed: 2025-10-24T14:33:00Z
Validation ID: GRUMPY_TESTER_FINAL_VALIDATION_001"""

    # Create test file
    test_file_path = "/tmp/final_validation_test.txt"
    with open(test_file_path, "w") as f:
        f.write(test_content)
    
    print(f"📄 Created test file: {test_file_path}")
    print(f"📏 File size: {len(test_content)} bytes")
    print(f"🎯 Chatbot ID: {CHATBOT_ID}")
    
    # Test 1: File Upload
    print("\n1️⃣ TESTING FILE UPLOAD")
    print("-" * 30)
    
    upload_url = f"{BASE_URL}/api/v1/knowledge/upload/document/"
    files = {"file": open(test_file_path, "rb")}
    data = {
        "chatbot_id": CHATBOT_ID,
        "privacy": "citable"
    }
    
    try:
        response = requests.post(upload_url, headers=headers, files=files, data=data)
        response.raise_for_status()
        upload_result = response.json()
        
        print(f"✅ Upload Status: {response.status_code}")
        print(f"✅ Knowledge Source ID: {upload_result['id']}")
        print(f"✅ Processing Status: {upload_result['status']}")
        print(f"✅ Chunk Count: {upload_result['chunk_count']}")
        print(f"✅ Error Message: {upload_result['error_message']}")
        
        if upload_result['status'] != 'completed':
            print("❌ CRITICAL FAILURE: Processing did not complete!")
            return False
            
        if upload_result['chunk_count'] == 0:
            print("❌ CRITICAL FAILURE: No chunks were created!")
            return False
            
        if upload_result['error_message'] is not None:
            print(f"❌ CRITICAL FAILURE: Error occurred: {upload_result['error_message']}")
            return False
            
        knowledge_source_id = upload_result['id']
        
    except Exception as e:
        print(f"❌ UPLOAD FAILED: {e}")
        return False
    finally:
        files["file"].close()
    
    # Test 2: Verify Content Preservation
    print("\n2️⃣ TESTING CONTENT PRESERVATION")
    print("-" * 35)
    
    # Small delay to ensure processing is complete
    time.sleep(1)
    
    # Use Django shell to check chunk content
    django_shell_cmd = f"""
from apps.knowledge.models import KnowledgeChunk, KnowledgeSource
source = KnowledgeSource.objects.get(id='{knowledge_source_id}')
chunk = KnowledgeChunk.objects.filter(source=source).first()
if chunk:
    content = chunk.content
    validation_phrases = [
        'FINAL_TEST_CONTENT_PRESERVED',
        'BUFFER_CONSUMPTION_BUG_DEFINITELY_FIXED',
        'TEXT_EXTRACTION_PIPELINE_WORKING',
        'KNOWLEDGE_CHUNKS_CREATED_SUCCESSFULLY',
        'END_TO_END_VALIDATION_COMPLETE',
        'GRUMPY_TESTER_FINAL_VALIDATION_001'
    ]
    results = []
    for phrase in validation_phrases:
        found = phrase in content
        results.append(f'{{phrase}}: {{\"✅\" if found else \"❌\"}}')
    print('\\n'.join(results))
    print(f'Content length: {{len(content)}}')
    print(f'Has embedding: {{\"✅\" if chunk.embedding_vector else \"❌\"}}')
    if chunk.embedding_vector:
        print(f'Embedding size: {{len(chunk.embedding_vector)}}')
else:
    print('❌ No chunk found')
"""
    
    try:
        import subprocess
        result = subprocess.run(
            ["./venv/bin/python", "manage.py", "shell", "-c", django_shell_cmd],
            capture_output=True,
            text=True,
            cwd="/home/sakr_quraish/Projects/Ismail"
        )
        
        if result.returncode == 0:
            print("Content validation results:")
            print(result.stdout)
            
            # Check if all validation phrases were found
            if "❌" in result.stdout:
                print("\n❌ CRITICAL FAILURE: Some content was not preserved!")
                return False
            else:
                print("\n✅ ALL CONTENT PRESERVED SUCCESSFULLY!")
                
        else:
            print(f"❌ Shell command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Content validation failed: {e}")
        return False
    
    # Final Result
    print("\n" + "="*70)
    print("🎉 FINAL VERDICT: FILE CONTENT CORRUPTION BUG IS FIXED!")
    print("="*70)
    print("✅ Files upload successfully")
    print("✅ Content is preserved during processing")
    print("✅ Knowledge chunks are created with correct content")
    print("✅ Processing status becomes 'completed'")
    print("✅ Embeddings are generated successfully")
    print("✅ End-to-end pipeline is working")
    
    # Cleanup
    os.unlink(test_file_path)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)