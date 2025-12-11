#!/usr/bin/env python3
"""
COMPREHENSIVE AUTHENTICATION TESTING
====================================

This script will BRUTALLY test the authentication system to find JSON parsing bugs,
special character handling issues, and security vulnerabilities that basic testing misses.

The grumpy tester demands PROOF that this system can handle real-world edge cases.
"""

import requests
import json
import urllib.parse
import time
from typing import Dict, List, Tuple, Any

class AuthenticationTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.register_url = f"{base_url}/auth/register/"
        self.login_url = f"{base_url}/auth/login/"
        self.test_results = []
        self.session = requests.Session()
        
    def log_result(self, test_name: str, password: str, response_code: int, 
                   success: bool, error_details: str = ""):
        """Log test results for analysis."""
        result = {
            'test_name': test_name,
            'password': password,
            'response_code': response_code,
            'success': success,
            'error_details': error_details,
            'timestamp': time.time()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {password[:20]}{'...' if len(password) > 20 else ''} -> HTTP {response_code}")
        if error_details:
            print(f"    Error: {error_details}")
    
    def test_registration(self, email: str, password: str, test_name: str) -> Tuple[bool, int, str]:
        """Test user registration with given password."""
        try:
            payload = {
                "email": email,
                "password": password,
                "password_confirm": password,
                "first_name": "Test",
                "last_name": "User"
            }
            
            response = self.session.post(
                self.register_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            success = response.status_code == 201
            error_details = ""
            
            if not success:
                try:
                    error_data = response.json()
                    error_details = str(error_data)
                except:
                    error_details = response.text[:200]
            
            return success, response.status_code, error_details
            
        except requests.exceptions.RequestException as e:
            return False, 0, f"Request failed: {str(e)}"
        except Exception as e:
            return False, 0, f"Unexpected error: {str(e)}"
    
    def test_extreme_special_characters(self):
        """Test passwords with characters that commonly break JSON parsers."""
        print("\n🔥 TESTING EXTREME SPECIAL CHARACTERS 🔥")
        
        extreme_passwords = [
            # JSON-breaking characters
            'Pass"word\\"123',           # Escaped quotes
            'Pass\\\\word123',           # Backslashes
            'Pass\nword\r123',           # Newlines and carriage returns
            'Pass\tword\b123',           # Tabs and backspaces
            'Pass\fword\v123',           # Form feeds and vertical tabs
            'Pass/word\\123',            # Mixed slashes
            'Pass"word\'123',            # Mixed quotes
            
            # Control characters
            'Pass\x00word123',           # Null byte
            'Pass\x01word123',           # Start of heading
            'Pass\x1fword123',           # Unit separator
            'Pass\x7fword123',           # Delete character
            
            # Unicode edge cases
            'Pass🔥word123',             # Emoji
            'Passкириллица123',          # Cyrillic
            'Pass中文字符123',            # Chinese characters
            'Pass العربية123',          # Arabic
            'Pass\u200bword123',         # Zero-width space
            'Pass\ufeffword123',         # Byte order mark
            
            # JSON injection attempts
            '{"evil": "injection"}Pass123',
            'Pass123"},"hacked": true}',
            'Pass123\\n"},"evil": "payload"}',
            
            # Length edge cases
            'P' + 'a' * 120 + '123!',    # Very long password
            '🔥' * 50 + '123!',          # Many emojis
            
            # Encoding confusion
            'Pass%22word%22123',         # URL encoded quotes
            'Pass&quot;word&quot;123',   # HTML encoded quotes
        ]
        
        for i, password in enumerate(extreme_passwords):
            email = f"extreme{i}@test.com"
            success, code, error = self.test_registration(email, password, f"Extreme Special Chars {i+1}")
            self.log_result(f"extreme_chars_{i+1}", password, code, success, error)
            
            # Brief delay to avoid overwhelming the server
            time.sleep(0.1)
    
    def test_malformed_json_payloads(self):
        """Test with malformed JSON to catch parsing errors."""
        print("\n🔥 TESTING MALFORMED JSON PAYLOADS 🔥")
        
        malformed_payloads = [
            # Intentionally broken JSON
            '{"email": "test@test.com", "password": "Pass123!", "password_confirm": "Pass123!", "first_name": "Test", "last_name": "User"',  # Missing closing brace
            '{"email": "test@test.com", "password": "Pass123!"", "password_confirm": "Pass123!", "first_name": "Test", "last_name": "User"}',  # Extra quote
            '{"email": "test@test.com", "password": "Pass123!\", "password_confirm": "Pass123!", "first_name": "Test", "last_name": "User"}',  # Unescaped quote
            '{"email": "test@test.com", "password": "Pass123!", "password_confirm": "Pass123!", "first_name": "Test", "last_name": "User",}',  # Trailing comma
        ]
        
        for i, payload in enumerate(malformed_payloads):
            try:
                response = self.session.post(
                    self.register_url,
                    data=payload,  # Send as raw data, not JSON
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                success = response.status_code not in [500, 502, 503]  # Server errors indicate parsing problems
                error_details = ""
                
                if response.status_code >= 500:
                    error_details = f"SERVER ERROR: {response.status_code} - {response.text[:200]}"
                
                self.log_result(f"malformed_json_{i+1}", payload[:50], response.status_code, success, error_details)
                
            except Exception as e:
                self.log_result(f"malformed_json_{i+1}", payload[:50], 0, False, str(e))
    
    def test_unicode_and_encoding_issues(self):
        """Test various Unicode and encoding edge cases."""
        print("\n🔥 TESTING UNICODE AND ENCODING ISSUES 🔥")
        
        unicode_passwords = [
            # Different Unicode categories
            'Pass™℗©®123',               # Symbol characters
            'Pass𝓅𝒶𝓈𝓈𝓌𝑜𝓇𝒹123',           # Mathematical script
            'Pass\u202e123drowssaP',     # Right-to-left override (visual spoofing)
            'Pass\u200d\u200c123',       # Zero-width joiner/non-joiner
            'Pass\ufeff123',             # Byte order mark
            'Pass\u0001\u0002123',       # Control characters
            
            # Normalization issues
            'Café123!',                  # Composed character
            'Cafe\u0301123!',           # Decomposed character (same visually)
            
            # Emoji combinations
            'Pass👨‍👩‍👧‍👦123',              # Family emoji (ZWJ sequence)
            'Pass🏳️‍🌈123',              # Flag emoji (ZWJ sequence)
            
            # Bidirectional text
            'Pass\u200fPassword123',     # Right-to-left mark
            'Pass\u200ePassword123',     # Left-to-right mark
        ]
        
        for i, password in enumerate(unicode_passwords):
            email = f"unicode{i}@test.com"
            success, code, error = self.test_registration(email, password, f"Unicode Test {i+1}")
            self.log_result(f"unicode_{i+1}", password, code, success, error)
            time.sleep(0.1)
    
    def test_payload_size_limits(self):
        """Test with oversized payloads to check limits."""
        print("\n🔥 TESTING PAYLOAD SIZE LIMITS 🔥")
        
        # Test very long passwords
        size_tests = [
            ('A' * 1000 + '123!', 'Very long password'),
            ('🔥' * 500 + '123!', 'Many emojis'),
            ('Pass123!' + 'A' * 10000, 'Extremely long password'),
        ]
        
        for i, (password, description) in enumerate(size_tests):
            email = f"size{i}@test.com"
            success, code, error = self.test_registration(email, password, description)
            self.log_result(f"size_test_{i+1}", f"{description} ({len(password)} chars)", code, success, error)
            time.sleep(0.1)
    
    def test_injection_attempts(self):
        """Test various injection attempts in password fields."""
        print("\n🔥 TESTING INJECTION ATTEMPTS 🔥")
        
        injection_passwords = [
            # JSON injection
            '"},"admin":true,"password":"',
            '\\"},"role":"admin","x":"',
            
            # SQL injection patterns (even though this is NoSQL)
            "Pass123'; DROP TABLE users; --",
            "Pass123' OR '1'='1",
            
            # NoSQL injection
            '{"$ne": ""}',
            '{"$gt": ""}',
            
            # Command injection
            'Pass123!; rm -rf /',
            'Pass123!`whoami`',
            
            # XSS attempts
            'Pass123!<script>alert("xss")</script>',
            'Pass123!javascript:alert("xss")',
        ]
        
        for i, password in enumerate(injection_passwords):
            email = f"injection{i}@test.com"
            success, code, error = self.test_registration(email, password, f"Injection Test {i+1}")
            self.log_result(f"injection_{i+1}", password, code, success, error)
            time.sleep(0.1)
    
    def analyze_results(self):
        """Analyze test results and provide grumpy assessment."""
        print("\n" + "="*80)
        print("🔥 GRUMPY TESTER'S BRUTAL ANALYSIS 🔥")
        print("="*80)
        
        total_tests = len(self.test_results)
        failed_tests = [r for r in self.test_results if not r['success']]
        server_errors = [r for r in self.test_results if r['response_code'] >= 500]
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Failed Tests: {len(failed_tests)}")
        print(f"Server Errors (500+): {len(server_errors)}")
        
        if server_errors:
            print("\n❌ CRITICAL ISSUES FOUND:")
            for error in server_errors:
                print(f"  - {error['test_name']}: HTTP {error['response_code']}")
                print(f"    Password: {error['password'][:50]}")
                print(f"    Error: {error['error_details'][:200]}")
        
        # Group failures by type
        failure_types = {}
        for failure in failed_tests:
            test_type = failure['test_name'].split('_')[0]
            if test_type not in failure_types:
                failure_types[test_type] = []
            failure_types[test_type].append(failure)
        
        print(f"\nFailure breakdown:")
        for failure_type, failures in failure_types.items():
            print(f"  {failure_type}: {len(failures)} failures")
        
        # Final assessment
        if server_errors:
            print("\n🚨 VERDICT: SYSTEM IS NOT READY FOR PRODUCTION!")
            print("Server errors indicate JSON parsing or internal processing bugs.")
            return False
        elif len(failed_tests) > total_tests * 0.1:  # More than 10% failure rate
            print("\n⚠️  VERDICT: SYSTEM HAS SIGNIFICANT ISSUES!")
            print("High failure rate indicates poor error handling or validation bugs.")
            return False
        else:
            print("\n✅ VERDICT: SYSTEM APPEARS STABLE (for now)")
            print("But don't get cocky - this is just the beginning!")
            return True
    
    def run_comprehensive_tests(self):
        """Run all comprehensive authentication tests."""
        print("🔥 STARTING COMPREHENSIVE AUTHENTICATION TESTING 🔥")
        print("Prepare to see your system's TRUE weaknesses!\n")
        
        # Run all test categories
        self.test_extreme_special_characters()
        self.test_malformed_json_payloads()
        self.test_unicode_and_encoding_issues()
        self.test_payload_size_limits()
        self.test_injection_attempts()
        
        # Analyze and report
        return self.analyze_results()


if __name__ == "__main__":
    tester = AuthenticationTester()
    
    print("🔥 GRUMPY TESTER'S COMPREHENSIVE AUTHENTICATION VALIDATION 🔥")
    print("="*80)
    print("Your basic testing was PATHETIC!")
    print("Let's see how this system REALLY handles edge cases...")
    print("="*80)
    
    try:
        is_ready = tester.run_comprehensive_tests()
        
        if not is_ready:
            print("\n🔥 THE GRUMPY TESTER'S FINAL WORD:")
            print("This system is NOT ready for production!")
            print("Fix the issues and come back when you're serious about quality.")
        else:
            print("\n🔥 THE GRUMPY TESTER'S GRUDGING ACKNOWLEDGMENT:")
            print("Fine... it passed these tests. But I'm still watching!")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nTest suite failed: {e}")
        print("Even the testing failed! This system is hopeless!")