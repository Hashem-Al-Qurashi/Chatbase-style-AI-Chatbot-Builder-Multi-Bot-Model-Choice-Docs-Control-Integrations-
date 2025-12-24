#!/usr/bin/env python3
"""
CRITICAL AUTH TESTING - Testing the authentication system for fundamental failures.
This test is skeptical and assumes everything is broken until proven otherwise.
"""

import os
import sys
import django
import requests
import json
from datetime import datetime, timedelta
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
sys.path.append('/home/sakr_quraish/Projects/Ismail')

try:
    django.setup()
    print("✓ Django setup successful")
except Exception as e:
    print(f"✗ Django setup FAILED: {e}")
    sys.exit(1)

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.accounts.models import User
from apps.accounts.authentication import JWTAuthentication
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class CriticalAuthTest:
    """Brutally test auth system to find what's actually broken."""
    
    def __init__(self):
        self.client = APIClient()
        self.django_client = Client()
        self.base_url = "http://localhost:8000"
        self.test_user_data = {
            'email': f'test_auth_{int(time.time())}@test.com',
            'password': 'TestPassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
        self.failures = []
        self.successes = []
    
    def log_failure(self, test_name, error):
        """Log a test failure."""
        self.failures.append(f"{test_name}: {error}")
        print(f"✗ FAIL: {test_name} - {error}")
    
    def log_success(self, test_name):
        """Log a test success."""
        self.successes.append(test_name)
        print(f"✓ PASS: {test_name}")
    
    def test_user_model_basics(self):
        """Test if User model even works."""
        try:
            # Try to create a user
            user = User.objects.create_user(
                email=self.test_user_data['email'],
                password=self.test_user_data['password'],
                first_name=self.test_user_data['first_name'],
                last_name=self.test_user_data['last_name']
            )
            
            if not user.id:
                raise Exception("User created but has no ID")
            
            if not user.check_password(self.test_user_data['password']):
                raise Exception("Password verification failed")
            
            if user.email != self.test_user_data['email']:
                raise Exception("Email not set correctly")
            
            self.log_success("User model basic creation")
            return user
            
        except Exception as e:
            self.log_failure("User model basic creation", str(e))
            return None
    
    def test_jwt_token_generation(self):
        """Test if JWT token generation actually works."""
        try:
            from apps.accounts.authentication import JWTAuthentication
            
            user = User.objects.create_user(
                email=f'jwt_test_{int(time.time())}@test.com',
                password='TestPassword123!'
            )
            
            jwt_auth = JWTAuthentication()
            
            # Check if the method exists
            if not hasattr(jwt_auth, 'generate_tokens'):
                raise Exception("JWTAuthentication missing generate_tokens method")
            
            tokens = jwt_auth.generate_tokens(user)
            
            if not tokens.get('access'):
                raise Exception("No access token generated")
            
            if not tokens.get('refresh'):
                raise Exception("No refresh token generated")
            
            if not isinstance(tokens['access'], str):
                raise Exception("Access token is not a string")
            
            if len(tokens['access']) < 50:  # JWT tokens should be much longer
                raise Exception(f"Access token suspiciously short: {len(tokens['access'])} chars")
            
            self.log_success("JWT token generation")
            return tokens
            
        except Exception as e:
            self.log_failure("JWT token generation", str(e))
            return None
    
    def test_jwt_token_validation(self):
        """Test if JWT token validation works."""
        try:
            user = User.objects.create_user(
                email=f'jwt_validation_{int(time.time())}@test.com',
                password='TestPassword123!'
            )
            
            jwt_auth = JWTAuthentication()
            tokens = jwt_auth.generate_tokens(user)
            
            # Test token validation
            validated_user, token = jwt_auth.authenticate_credentials(tokens['access'])
            
            if validated_user != user:
                raise Exception("Token validation returned wrong user")
            
            if not token:
                raise Exception("No token returned from validation")
            
            self.log_success("JWT token validation")
            return True
            
        except Exception as e:
            self.log_failure("JWT token validation", str(e))
            return False
    
    def test_registration_endpoint(self):
        """Test user registration API endpoint."""
        try:
            registration_data = {
                'email': f'reg_test_{int(time.time())}@test.com',
                'password': 'TestPassword123!',
                'password_confirm': 'TestPassword123!',
                'first_name': 'Registration',
                'last_name': 'Test'
            }
            
            # Find registration URL
            try:
                from apps.accounts.urls import urlpatterns
                # Look for registration pattern
                found_register = False
                for pattern in urlpatterns:
                    if hasattr(pattern, 'name') and 'register' in str(pattern.name):
                        found_register = True
                        break
                
                if not found_register:
                    raise Exception("No registration URL pattern found")
                    
            except Exception as url_e:
                # Try common registration endpoints
                pass
            
            # Try different possible registration endpoints
            registration_urls = ['/api/auth/register/', '/api/accounts/register/', '/auth/register/']
            
            success = False
            for url in registration_urls:
                try:
                    response = self.client.post(url, registration_data, format='json')
                    if response.status_code in [200, 201]:
                        success = True
                        break
                    elif response.status_code == 404:
                        continue  # Try next URL
                    else:
                        # Got a response but it's an error
                        raise Exception(f"Registration failed with status {response.status_code}: {response.data if hasattr(response, 'data') else response.content}")
                except Exception as e:
                    if "404" not in str(e):
                        raise e
                    continue
            
            if not success:
                raise Exception("All registration endpoints returned 404 or failed")
            
            self.log_success("Registration endpoint")
            return True
            
        except Exception as e:
            self.log_failure("Registration endpoint", str(e))
            return False
    
    def test_login_endpoint(self):
        """Test login API endpoint."""
        try:
            # First create a user
            user = User.objects.create_user(
                email=f'login_test_{int(time.time())}@test.com',
                password='TestPassword123!'
            )
            
            login_data = {
                'email': user.email,
                'password': 'TestPassword123!'
            }
            
            # Try different possible login endpoints
            login_urls = ['/api/auth/login/', '/api/accounts/login/', '/auth/login/']
            
            success = False
            for url in login_urls:
                try:
                    response = self.client.post(url, login_data, format='json')
                    if response.status_code == 200:
                        if hasattr(response, 'data') and 'access' in response.data:
                            success = True
                            break
                        else:
                            raise Exception(f"Login successful but no access token in response: {response.data if hasattr(response, 'data') else response.content}")
                    elif response.status_code == 404:
                        continue  # Try next URL
                    else:
                        raise Exception(f"Login failed with status {response.status_code}: {response.data if hasattr(response, 'data') else response.content}")
                except Exception as e:
                    if "404" not in str(e):
                        raise e
                    continue
            
            if not success:
                raise Exception("All login endpoints returned 404 or failed")
            
            self.log_success("Login endpoint")
            return True
            
        except Exception as e:
            self.log_failure("Login endpoint", str(e))
            return False
    
    def test_authenticated_endpoint_access(self):
        """Test access to authenticated endpoints."""
        try:
            # Create user and get token
            user = User.objects.create_user(
                email=f'auth_test_{int(time.time())}@test.com',
                password='TestPassword123!'
            )
            
            jwt_auth = JWTAuthentication()
            tokens = jwt_auth.generate_tokens(user)
            
            # Set authorization header
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
            
            # Try to access protected endpoints
            protected_urls = ['/api/chatbots/', '/api/knowledge/', '/api/conversations/']
            
            access_granted = False
            for url in protected_urls:
                try:
                    response = self.client.get(url)
                    if response.status_code in [200, 201]:
                        access_granted = True
                        break
                    elif response.status_code == 404:
                        continue  # URL doesn't exist, try next
                    elif response.status_code in [401, 403]:
                        raise Exception(f"Authentication failed for {url}: status {response.status_code}")
                except Exception as e:
                    if "404" not in str(e):
                        raise e
                    continue
            
            if not access_granted:
                raise Exception("No protected endpoints accessible with valid token")
            
            self.log_success("Authenticated endpoint access")
            return True
            
        except Exception as e:
            self.log_failure("Authenticated endpoint access", str(e))
            return False
    
    def test_token_refresh(self):
        """Test JWT token refresh mechanism."""
        try:
            user = User.objects.create_user(
                email=f'refresh_test_{int(time.time())}@test.com',
                password='TestPassword123!'
            )
            
            jwt_auth = JWTAuthentication()
            tokens = jwt_auth.generate_tokens(user)
            
            # Try to refresh token
            refresh_data = {'refresh': tokens['refresh']}
            
            # Try different refresh endpoints
            refresh_urls = ['/api/auth/token/refresh/', '/api/accounts/token/refresh/', '/auth/token/refresh/']
            
            success = False
            for url in refresh_urls:
                try:
                    response = self.client.post(url, refresh_data, format='json')
                    if response.status_code == 200:
                        if hasattr(response, 'data') and 'access' in response.data:
                            success = True
                            break
                        else:
                            raise Exception(f"Refresh successful but no new access token: {response.data if hasattr(response, 'data') else response.content}")
                    elif response.status_code == 404:
                        continue
                    else:
                        raise Exception(f"Token refresh failed with status {response.status_code}")
                except Exception as e:
                    if "404" not in str(e):
                        raise e
                    continue
            
            if not success:
                raise Exception("All token refresh endpoints failed or don't exist")
            
            self.log_success("Token refresh")
            return True
            
        except Exception as e:
            self.log_failure("Token refresh", str(e))
            return False
    
    def test_permission_system(self):
        """Test permission system for chatbots."""
        try:
            # Create two users
            user1 = User.objects.create_user(
                email=f'perm1_test_{int(time.time())}@test.com',
                password='TestPassword123!'
            )
            user2 = User.objects.create_user(
                email=f'perm2_test_{int(time.time())}@test.com',
                password='TestPassword123!'
            )
            
            # Create a chatbot for user1
            from apps.chatbots.models import Chatbot
            chatbot = Chatbot.objects.create(
                name="Permission Test Bot",
                description="Test chatbot for permission testing",
                user=user1
            )
            
            # Try to access chatbot as user2 (should fail)
            jwt_auth = JWTAuthentication()
            user2_tokens = jwt_auth.generate_tokens(user2)
            
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user2_tokens["access"]}')
            
            # Try to get chatbot details (should be forbidden or not found)
            response = self.client.get(f'/api/chatbots/{chatbot.id}/')
            
            if response.status_code == 200:
                raise Exception("User2 can access User1's chatbot - permission system broken!")
            
            if response.status_code not in [403, 404]:
                raise Exception(f"Unexpected response code for unauthorized access: {response.status_code}")
            
            self.log_success("Permission system")
            return True
            
        except Exception as e:
            self.log_failure("Permission system", str(e))
            return False
    
    def run_all_tests(self):
        """Run all authentication tests."""
        print("\n" + "="*80)
        print("CRITICAL AUTHENTICATION SYSTEM TESTING")
        print("="*80)
        print("Testing assumption: Everything is broken until proven otherwise.")
        print()
        
        # Run tests
        self.test_user_model_basics()
        self.test_jwt_token_generation()
        self.test_jwt_token_validation()
        self.test_registration_endpoint()
        self.test_login_endpoint()
        self.test_authenticated_endpoint_access()
        self.test_token_refresh()
        self.test_permission_system()
        
        # Summary
        print("\n" + "="*80)
        print("AUTHENTICATION TEST RESULTS")
        print("="*80)
        
        total_tests = len(self.successes) + len(self.failures)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {len(self.successes)}")
        print(f"Failed: {len(self.failures)}")
        print(f"Success Rate: {(len(self.successes)/total_tests)*100:.1f}%" if total_tests > 0 else "0.0%")
        
        if self.failures:
            print("\nCRITICAL FAILURES:")
            for failure in self.failures:
                print(f"  ✗ {failure}")
        
        if self.successes:
            print("\nSUCCESSES:")
            for success in self.successes:
                print(f"  ✓ {success}")
        
        print("\n" + "="*80)
        
        if len(self.failures) > len(self.successes):
            print("VERDICT: AUTHENTICATION SYSTEM IS FUNDAMENTALLY BROKEN")
            return False
        else:
            print("VERDICT: Authentication system appears functional (but still suspicious)")
            return True

if __name__ == '__main__':
    tester = CriticalAuthTest()
    tester.run_all_tests()