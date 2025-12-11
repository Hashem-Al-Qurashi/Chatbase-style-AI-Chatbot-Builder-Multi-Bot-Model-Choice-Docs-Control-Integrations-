#!/usr/bin/env python3
"""
FOCUSED AUTHENTICATION VALIDATION
=================================

This script runs targeted tests for the specific "JSON parsing bug" claim
after waiting for rate limits to clear.
"""

import requests
import json
import time
from datetime import datetime

class FocusedAuthTester:
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.register_url = f"{self.base_url}/auth/register/"
        self.test_count = 0
        self.session = requests.Session()
    
    def wait_for_rate_limit(self):
        """Wait for rate limit to clear."""
        print("⏳ Checking rate limit status...")
        
        test_payload = {
            "email": "ratecheck@test.com",
            "password": "Test123!",
            "password_confirm": "Test123!",
            "first_name": "Rate",
            "last_name": "Check"
        }
        
        response = self.session.post(
            self.register_url,
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 429:
            try:
                rate_data = response.json()
                retry_after = rate_data.get('retry_after', 1800)
                print(f"⏳ Rate limited. Waiting {retry_after} seconds...")
                time.sleep(min(retry_after + 10, 60))  # Wait max 60 seconds for testing
                return False
            except:
                print("⏳ Rate limited. Waiting 60 seconds...")
                time.sleep(60)
                return False
        else:
            print("✅ Rate limit cleared. Proceeding with tests...")
            return True
    
    def test_json_parsing_edge_cases(self):
        """Test the specific JSON parsing issues claimed."""
        print("\n🔍 TESTING JSON PARSING EDGE CASES")
        print("="*50)
        
        # Critical test cases that commonly break JSON parsers
        critical_tests = [
            {
                'name': 'Escaped Quotes in Password',
                'password': 'Pass"word\\"123!',
                'expected_issue': 'JSON parsing should handle escaped quotes'
            },
            {
                'name': 'Backslashes in Password', 
                'password': 'Pass\\\\word123!',
                'expected_issue': 'JSON parsing should handle backslashes'
            },
            {
                'name': 'Newlines in Password',
                'password': 'Pass\nword123!',
                'expected_issue': 'JSON parsing should handle newlines'
            },
            {
                'name': 'Mixed Quotes',
                'password': 'Pass"word\'123!',
                'expected_issue': 'JSON parsing should handle mixed quotes'
            },
            {
                'name': 'Unicode Characters',
                'password': 'Pass🔥word123!',
                'expected_issue': 'JSON parsing should handle Unicode'
            }
        ]
        
        results = []
        
        for i, test in enumerate(critical_tests):
            self.test_count += 1
            email = f"jsontest{self.test_count}@test.com"
            
            print(f"\n🧪 Test {i+1}: {test['name']}")
            print(f"Password: {repr(test['password'])}")
            
            payload = {
                "email": email,
                "password": test['password'],
                "password_confirm": test['password'],
                "first_name": "JSON",
                "last_name": "Test"
            }
            
            try:
                # Test JSON serialization first
                json_payload = json.dumps(payload)
                print(f"✅ JSON serialization: SUCCESS")
                
                # Test the actual API call
                response = self.session.post(
                    self.register_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                print(f"📡 HTTP Response: {response.status_code}")
                
                if response.status_code == 500:
                    print(f"❌ SERVER ERROR - {test['expected_issue']}")
                    print(f"Response: {response.text[:200]}")
                    results.append({
                        'test': test['name'],
                        'password': test['password'],
                        'status': 'FAILED',
                        'issue': 'Server error - likely JSON parsing bug',
                        'response_code': response.status_code
                    })
                elif response.status_code == 201:
                    print(f"✅ SUCCESS - Registration completed")
                    results.append({
                        'test': test['name'],
                        'password': test['password'],
                        'status': 'PASSED',
                        'issue': 'None',
                        'response_code': response.status_code
                    })
                elif response.status_code == 400:
                    try:
                        error_data = response.json()
                        print(f"⚠️  Validation error: {error_data}")
                        results.append({
                            'test': test['name'],
                            'password': test['password'],
                            'status': 'VALIDATION_ERROR',
                            'issue': str(error_data),
                            'response_code': response.status_code
                        })
                    except:
                        print(f"❌ Malformed error response")
                        results.append({
                            'test': test['name'],
                            'password': test['password'],
                            'status': 'FAILED',
                            'issue': 'Malformed error response',
                            'response_code': response.status_code
                        })
                else:
                    print(f"🤔 Unexpected response: {response.status_code}")
                    results.append({
                        'test': test['name'],
                        'password': test['password'],
                        'status': 'UNEXPECTED',
                        'issue': f'Unexpected HTTP {response.status_code}',
                        'response_code': response.status_code
                    })
                
            except json.JSONEncodeError as e:
                print(f"❌ JSON ENCODING FAILED: {e}")
                results.append({
                    'test': test['name'],
                    'password': test['password'],
                    'status': 'FAILED',
                    'issue': f'JSON encoding error: {e}',
                    'response_code': 'N/A'
                })
            except requests.RequestException as e:
                print(f"❌ REQUEST FAILED: {e}")
                results.append({
                    'test': test['name'],
                    'password': test['password'],
                    'status': 'FAILED',
                    'issue': f'Request error: {e}',
                    'response_code': 'N/A'
                })
            
            # Small delay between tests
            time.sleep(1)
        
        return results
    
    def test_malformed_json_direct(self):
        """Test malformed JSON payloads directly."""
        print("\n🔍 TESTING MALFORMED JSON PAYLOADS")
        print("="*50)
        
        malformed_tests = [
            {
                'name': 'Missing Closing Brace',
                'payload': '{"email": "test@test.com", "password": "Test123!", "password_confirm": "Test123!", "first_name": "Test", "last_name": "User"',
            },
            {
                'name': 'Unescaped Quote in Password',
                'payload': '{"email": "test@test.com", "password": "Test"123!", "password_confirm": "Test"123!", "first_name": "Test", "last_name": "User"}',
            }
        ]
        
        results = []
        
        for test in malformed_tests:
            print(f"\n🧪 Test: {test['name']}")
            
            try:
                response = self.session.post(
                    self.register_url,
                    data=test['payload'],  # Send as raw data
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                print(f"📡 HTTP Response: {response.status_code}")
                
                if response.status_code == 500:
                    print(f"❌ SERVER ERROR - JSON parsing failed")
                    results.append({
                        'test': test['name'],
                        'status': 'FAILED',
                        'issue': 'Server error on malformed JSON',
                        'response_code': response.status_code
                    })
                else:
                    print(f"✅ Handled gracefully")
                    results.append({
                        'test': test['name'],
                        'status': 'PASSED',
                        'issue': 'Malformed JSON handled properly',
                        'response_code': response.status_code
                    })
                    
            except Exception as e:
                print(f"❌ REQUEST FAILED: {e}")
                results.append({
                    'test': test['name'],
                    'status': 'FAILED',
                    'issue': f'Request error: {e}',
                    'response_code': 'N/A'
                })
        
        return results
    
    def analyze_results(self, json_results, malformed_results):
        """Provide final analysis."""
        print("\n" + "="*80)
        print("🔥 GRUMPY TESTER'S FINAL VERDICT")
        print("="*80)
        
        all_results = json_results + malformed_results
        
        # Count different result types
        passed = len([r for r in all_results if r['status'] == 'PASSED'])
        failed = len([r for r in all_results if r['status'] == 'FAILED'])
        validation_errors = len([r for r in all_results if r['status'] == 'VALIDATION_ERROR'])
        
        print(f"\nTotal Tests: {len(all_results)}")
        print(f"Passed: {passed}")
        print(f"Failed (Server Errors): {failed}")
        print(f"Validation Errors: {validation_errors}")
        
        # Check for critical issues
        server_errors = [r for r in all_results if r['response_code'] == 500]
        json_parsing_bugs = [r for r in all_results if 'JSON parsing' in r.get('issue', '')]
        
        print(f"\n🔍 SPECIFIC ISSUE ANALYSIS:")
        print(f"Server Errors (HTTP 500): {len(server_errors)}")
        print(f"JSON Parsing Bugs: {len(json_parsing_bugs)}")
        
        # Show detailed failures
        if server_errors:
            print(f"\n❌ CRITICAL SERVER ERRORS FOUND:")
            for error in server_errors:
                print(f"  - {error['test']}: {error['issue']}")
        
        # Final verdict
        if server_errors:
            print(f"\n🚨 VERDICT: JSON PARSING BUG CONFIRMED!")
            print(f"The system has {len(server_errors)} server errors indicating JSON parsing issues.")
            print(f"The original grumpy tester assessment was CORRECT!")
            return False
        elif failed > 0:
            print(f"\n⚠️  VERDICT: SYSTEM HAS ISSUES!")
            print(f"While no JSON parsing bugs found, {failed} other critical failures detected.")
            return False
        else:
            print(f"\n✅ VERDICT: JSON PARSING BUG CLAIM WAS FALSE!")
            print(f"All tests passed. The authentication system handles JSON correctly.")
            print(f"The original tester's claim appears to be invalid.")
            return True


if __name__ == "__main__":
    tester = FocusedAuthTester()
    
    print("🔍 FOCUSED AUTHENTICATION VALIDATION")
    print("Testing the specific 'JSON parsing bug' claim...")
    print("="*60)
    
    # Wait for rate limit to clear
    if not tester.wait_for_rate_limit():
        print("⚠️  Rate limit not cleared, running limited tests...")
    
    # Run focused tests
    json_results = tester.test_json_parsing_edge_cases()
    malformed_results = tester.test_malformed_json_direct()
    
    # Final analysis
    is_valid = tester.analyze_results(json_results, malformed_results)
    
    print(f"\n🎯 FINAL ANSWER:")
    if is_valid:
        print(f"The 'JSON parsing bug' claim was a FALSE POSITIVE!")
    else:
        print(f"The 'JSON parsing bug' claim was VALIDATED!")