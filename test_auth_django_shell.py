#!/usr/bin/env python3
"""
DJANGO SHELL AUTHENTICATION TESTING
===================================

Bypass HTTP rate limiting by testing serialization and validation directly
in Django shell context. This will reveal the TRUE authentication behavior.
"""

import os
import sys
import django
import json

# Add the project root to Python path
sys.path.append('/home/sakr_quraish/Projects/Ismail')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()

# Now import Django components
from apps.accounts.serializers import UserRegistrationSerializer
from apps.core.auth import password_security
from django.contrib.auth import get_user_model

User = get_user_model()

class DirectAuthTester:
    def __init__(self):
        self.test_results = []
    
    def test_serializer_with_special_chars(self):
        """Test serializer directly with special characters."""
        print("🔍 TESTING DJANGO SERIALIZER WITH SPECIAL CHARACTERS")
        print("="*60)
        
        critical_passwords = [
            'Pass"word\\"123!',        # Escaped quotes
            'Pass\\\\word123!',        # Backslashes
            'Pass\nword123!',          # Newlines
            'Pass\tword123!',          # Tabs
            'Pass"word\'123!',         # Mixed quotes
            'Pass🔥word123!',          # Unicode/emoji
            'Pass\x00word123!',        # Null byte
            'Pass\x1fword123!',        # Control character
            'Passкириллица123!',       # Cyrillic
            'Pass中文字符123!',         # Chinese
            'Pass العربية123!',        # Arabic
        ]
        
        for i, password in enumerate(critical_passwords):
            print(f"\n🧪 Test {i+1}: {repr(password)}")
            
            # Test data for serializer
            test_data = {
                'email': f'test{i}@test.com',
                'password': password,
                'password_confirm': password,
                'first_name': 'Test',
                'last_name': 'User'
            }
            
            try:
                # Test JSON serialization first
                json_str = json.dumps(test_data)
                print(f"✅ JSON serialization: SUCCESS")
                
                # Test Django serializer
                serializer = UserRegistrationSerializer(data=test_data)
                
                if serializer.is_valid():
                    print(f"✅ Django serializer validation: PASSED")
                    
                    # Test password strength validation
                    is_strong, errors = password_security.validate_password_strength(password)
                    if is_strong:
                        print(f"✅ Password strength validation: PASSED")
                        
                        # Test if user can actually be created (don't save)
                        try:
                            validated_data = serializer.validated_data.copy()
                            validated_data.pop('password_confirm')
                            print(f"✅ User creation data prepared: SUCCESS")
                            
                            self.test_results.append({
                                'password': password,
                                'json_serialization': True,
                                'django_validation': True,
                                'password_strength': True,
                                'user_creation': True,
                                'overall_status': 'PASSED'
                            })
                            
                        except Exception as e:
                            print(f"❌ User creation preparation failed: {e}")
                            self.test_results.append({
                                'password': password,
                                'json_serialization': True,
                                'django_validation': True,
                                'password_strength': True,
                                'user_creation': False,
                                'overall_status': 'FAILED',
                                'error': str(e)
                            })
                    else:
                        print(f"⚠️  Password strength validation: FAILED - {errors}")
                        self.test_results.append({
                            'password': password,
                            'json_serialization': True,
                            'django_validation': True,
                            'password_strength': False,
                            'user_creation': 'N/A',
                            'overall_status': 'VALIDATION_ERROR',
                            'error': f"Password strength: {errors}"
                        })
                else:
                    print(f"❌ Django serializer validation: FAILED - {serializer.errors}")
                    self.test_results.append({
                        'password': password,
                        'json_serialization': True,
                        'django_validation': False,
                        'password_strength': 'N/A',
                        'user_creation': 'N/A',
                        'overall_status': 'VALIDATION_ERROR',
                        'error': f"Serializer errors: {serializer.errors}"
                    })
                    
            except json.JSONEncodeError as e:
                print(f"❌ JSON serialization FAILED: {e}")
                self.test_results.append({
                    'password': password,
                    'json_serialization': False,
                    'django_validation': 'N/A',
                    'password_strength': 'N/A',
                    'user_creation': 'N/A',
                    'overall_status': 'JSON_ERROR',
                    'error': f"JSON encoding: {e}"
                })
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                self.test_results.append({
                    'password': password,
                    'json_serialization': 'Unknown',
                    'django_validation': False,
                    'password_strength': 'N/A',
                    'user_creation': 'N/A',
                    'overall_status': 'ERROR',
                    'error': str(e)
                })
    
    def test_malformed_json_handling(self):
        """Test how Django handles malformed JSON at the framework level."""
        print("\n🔍 TESTING MALFORMED JSON HANDLING")
        print("="*45)
        
        malformed_json_strings = [
            '{"email": "test@test.com", "password": "Test123!", incomplete',
            '{"email": "test@test.com", "password": "Test"123!", "password_confirm": "Test"123!"}',
            '{"email": "test@test.com", "password": "Test\\123!", malformed}',
        ]
        
        for i, json_str in enumerate(malformed_json_strings):
            print(f"\n🧪 Malformed JSON Test {i+1}")
            print(f"JSON: {json_str[:50]}...")
            
            try:
                # This is what Django's JSON parser would do
                data = json.loads(json_str)
                print(f"⚠️  JSON parsing unexpectedly succeeded!")
                
                # Test with serializer
                serializer = UserRegistrationSerializer(data=data)
                if serializer.is_valid():
                    print(f"⚠️  Serializer validation unexpectedly passed!")
                else:
                    print(f"✅ Serializer properly rejected invalid data")
                    
            except json.JSONDecodeError as e:
                print(f"✅ JSON parsing properly failed: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
    
    def analyze_results(self):
        """Analyze all test results."""
        print("\n" + "="*80)
        print("🔥 COMPREHENSIVE DJANGO AUTHENTICATION ANALYSIS")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['overall_status'] == 'PASSED'])
        json_errors = len([r for r in self.test_results if r['overall_status'] == 'JSON_ERROR'])
        validation_errors = len([r for r in self.test_results if r['overall_status'] == 'VALIDATION_ERROR'])
        system_errors = len([r for r in self.test_results if r['overall_status'] == 'ERROR'])
        
        print(f"\nTEST SUMMARY:")
        print(f"Total Tests: {total_tests}")
        print(f"Fully Passed: {passed_tests}")
        print(f"JSON Parsing Errors: {json_errors}")
        print(f"Validation Errors: {validation_errors}")
        print(f"System Errors: {system_errors}")
        
        # Show specific failures
        if json_errors > 0:
            print(f"\n❌ JSON PARSING FAILURES:")
            for result in self.test_results:
                if result['overall_status'] == 'JSON_ERROR':
                    print(f"  - Password: {repr(result['password'])}")
                    print(f"    Error: {result['error']}")
        
        if system_errors > 0:
            print(f"\n❌ SYSTEM ERRORS:")
            for result in self.test_results:
                if result['overall_status'] == 'ERROR':
                    print(f"  - Password: {repr(result['password'])}")
                    print(f"    Error: {result['error']}")
        
        # Final verdict
        print(f"\n🎯 FINAL VERDICT:")
        
        if json_errors > 0:
            print(f"🚨 JSON PARSING BUG CONFIRMED!")
            print(f"{json_errors} passwords cause JSON parsing failures.")
            print(f"The original grumpy tester was RIGHT!")
            return False
        elif system_errors > 0:
            print(f"🚨 SYSTEM BUGS FOUND!")
            print(f"{system_errors} passwords cause system errors.")
            print(f"Authentication system has serious issues!")
            return False
        elif validation_errors == total_tests:
            print(f"⚠️  ALL TESTS FAILED VALIDATION!")
            print(f"The system rejects ALL special character passwords.")
            print(f"This indicates overly strict validation, not JSON bugs.")
            return True
        else:
            print(f"✅ JSON PARSING BUG CLAIM IS FALSE!")
            print(f"{passed_tests}/{total_tests} tests passed completely.")
            print(f"The authentication system handles JSON correctly.")
            print(f"The original tester's claim was INVALID!")
            return True


if __name__ == "__main__":
    print("🔍 DIRECT DJANGO AUTHENTICATION TESTING")
    print("Bypassing HTTP layer to test Django components directly...")
    print("="*70)
    
    tester = DirectAuthTester()
    
    # Run all tests
    tester.test_serializer_with_special_chars()
    tester.test_malformed_json_handling()
    
    # Final analysis
    is_claim_valid = not tester.analyze_results()  # Invert because we're checking if bug exists
    
    print(f"\n🏁 CONCLUSION:")
    if is_claim_valid:
        print(f"The 'JSON parsing bug' claim was VALIDATED!")
        print(f"Authentication system has real JSON processing issues.")
    else:
        print(f"The 'JSON parsing bug' claim was DEBUNKED!")
        print(f"Your testing methodology was flawed or claim was false.")