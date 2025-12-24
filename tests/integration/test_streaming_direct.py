#!/usr/bin/env python3
"""
Direct test of streaming service components to validate Step 6 claims
"""

import os
import sys
import django
import asyncio
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_saas.settings')
django.setup()


class StreamingTestResults:
    def __init__(self):
        self.tests = []
        self.failures = []
    
    def add_test(self, name, passed, details=""):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if details:
            print(f"   {details}")
        
        self.tests.append({"name": name, "passed": passed, "details": details})
        if not passed:
            self.failures.append(name)
    
    def print_summary(self):
        total = len(self.tests)
        passed = len([t for t in self.tests if t["passed"]])
        print(f"\n📊 RESULTS: {passed}/{total} tests passed")
        
        if self.failures:
            print(f"\n❌ FAILED TESTS:")
            for failure in self.failures:
                print(f"   - {failure}")
        
        return len(self.failures) == 0


async def test_streaming_components():
    """Test individual streaming components."""
    results = StreamingTestResults()
    
    print("🔍 TESTING STREAMING SERVICE COMPONENTS")
    print("=" * 50)
    
    # Test 1: Import streaming components
    try:
        from apps.core.streaming_service import (
            RAGStreamingConsumer, RateLimiter, StreamingAuthenticator,
            StreamingSession, streaming_health_checker
        )
        results.add_test("Import streaming components", True, "All components imported successfully")
    except ImportError as e:
        results.add_test("Import streaming components", False, f"Import failed: {e}")
        return results
    
    # Test 2: Rate limiter functionality
    try:
        rate_limiter = RateLimiter(max_requests=3, window_minutes=1)
        user_id = "test_user_streaming"
        
        # Should allow first 3 requests
        allowed_count = 0
        for i in range(3):
            if rate_limiter.is_allowed(user_id):
                allowed_count += 1
        
        # Should deny 4th request
        fourth_denied = not rate_limiter.is_allowed(user_id)
        
        rate_limit_works = (allowed_count == 3 and fourth_denied)
        results.add_test("Rate limiter functionality", rate_limit_works, 
                        f"Allowed {allowed_count}/3 requests, 4th denied: {fourth_denied}")
    except Exception as e:
        results.add_test("Rate limiter functionality", False, f"Error: {e}")
    
    # Test 3: Authenticator
    try:
        authenticator = StreamingAuthenticator()
        
        # Test valid token
        valid_result = await authenticator.authenticate_token("user_test123")
        valid_auth = (valid_result is not None and 
                     valid_result.get('user_id') == 'test123' and
                     valid_result.get('is_authenticated') is True)
        
        # Test invalid token
        invalid_result = await authenticator.authenticate_token("invalid")
        invalid_rejected = invalid_result is None
        
        auth_works = valid_auth and invalid_rejected
        results.add_test("Authenticator functionality", auth_works,
                        f"Valid token: {valid_auth}, Invalid rejected: {invalid_rejected}")
    except Exception as e:
        results.add_test("Authenticator functionality", False, f"Error: {e}")
    
    # Test 4: Session management
    try:
        session = StreamingSession(
            user_id="test_user",
            chatbot_id="test_bot",
            session_id="test_session_123",
            channel_name="test.channel",
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        
        session_valid = (
            session.user_id == "test_user" and
            session.message_count == 0 and
            session.rate_limit_tokens == 60
        )
        
        # Test serialization
        session_dict = session.to_dict()
        serialization_works = (
            isinstance(session_dict, dict) and
            'user_id' in session_dict and
            'connected_at' in session_dict
        )
        
        session_mgmt_works = session_valid and serialization_works
        results.add_test("Session management", session_mgmt_works,
                        f"Session valid: {session_valid}, Serialization: {serialization_works}")
    except Exception as e:
        results.add_test("Session management", False, f"Error: {e}")
    
    # Test 5: Health checker
    try:
        health_status = await streaming_health_checker.check_health()
        
        health_structure_valid = (
            isinstance(health_status, dict) and
            'status' in health_status and
            'timestamp' in health_status
        )
        
        # Health might be degraded due to Redis, but structure should be valid
        results.add_test("Health checker structure", health_structure_valid,
                        f"Status: {health_status.get('status')}")
    except Exception as e:
        results.add_test("Health checker", False, f"Error: {e}")
    
    # Test 6: Consumer initialization
    try:
        consumer = RAGStreamingConsumer()
        
        # Check that consumer has required attributes
        consumer_components = (
            hasattr(consumer, 'rate_limiter') and
            hasattr(consumer, 'authenticator') and
            hasattr(consumer, 'rag_orchestrator') and
            hasattr(consumer, 'query_processor')
        )
        
        results.add_test("Consumer initialization", consumer_components,
                        "All consumer components initialized")
    except Exception as e:
        results.add_test("Consumer initialization", False, f"Error: {e}")
    
    # Test 7: RAG Orchestrator integration
    try:
        from apps.core.rag_orchestrator import RAGOrchestrator, RAGQuery, PrivacyMode
        
        orchestrator = RAGOrchestrator()
        init_success = await orchestrator.initialize()
        
        # Test query construction
        query = RAGQuery(
            text="Test query for streaming",
            user_id="test_user",
            chatbot_id="test_bot",
            privacy_mode=PrivacyMode.STRICT
        )
        
        query_valid = (
            hasattr(query, 'request_id') and
            query.text == "Test query for streaming" and
            query.privacy_mode == PrivacyMode.STRICT
        )
        
        rag_integration_works = init_success and query_valid
        results.add_test("RAG Orchestrator integration", rag_integration_works,
                        f"Init: {init_success}, Query: {query_valid}")
    except Exception as e:
        results.add_test("RAG Orchestrator integration", False, f"Error: {e}")
    
    # Test 8: WebSocket routing
    try:
        from apps.conversations.routing import websocket_urlpatterns
        
        # Check that RAG streaming route exists
        rag_route_exists = any(
            'rag' in str(pattern.pattern) if hasattr(pattern, 'pattern') else False
            for pattern in websocket_urlpatterns
        )
        
        routing_works = len(websocket_urlpatterns) > 0 and rag_route_exists
        results.add_test("WebSocket routing", routing_works,
                        f"Routes: {len(websocket_urlpatterns)}, RAG route: {rag_route_exists}")
    except Exception as e:
        results.add_test("WebSocket routing", False, f"Error: {e}")
    
    return results


async def test_end_to_end_streaming_logic():
    """Test end-to-end streaming logic without actual WebSocket."""
    results = StreamingTestResults()
    
    print("\n🚀 TESTING END-TO-END STREAMING LOGIC")
    print("=" * 50)
    
    try:
        from apps.core.streaming_service import RAGStreamingConsumer
        from apps.core.rag_orchestrator import RAGQuery, PrivacyMode
        
        # Test message validation logic
        consumer = RAGStreamingConsumer()
        
        # Test valid query message
        valid_query_msg = {
            "type": "query",
            "query": "What is the purpose of this system?",
            "privacy_mode": "strict",
            "chatbot_id": "test_bot"
        }
        
        # Validate message structure
        query_valid = (
            valid_query_msg.get("type") == "query" and
            len(valid_query_msg.get("query", "")) > 0 and
            valid_query_msg.get("privacy_mode") in ["strict", "contextual", "internal"]
        )
        
        results.add_test("Query message validation", query_valid, 
                        "Valid query message structure")
        
        # Test privacy mode conversion
        try:
            privacy_mode = PrivacyMode(valid_query_msg["privacy_mode"])
            privacy_enum_valid = isinstance(privacy_mode, PrivacyMode)
        except ValueError:
            privacy_enum_valid = False
        
        results.add_test("Privacy mode conversion", privacy_enum_valid,
                        "Privacy mode string to enum conversion")
        
        # Test query object creation
        try:
            rag_query = RAGQuery(
                text=valid_query_msg["query"],
                user_id="test_user",
                chatbot_id=valid_query_msg["chatbot_id"],
                privacy_mode=privacy_mode,
                top_k_results=10
            )
            
            query_creation_valid = (
                hasattr(rag_query, 'request_id') and
                rag_query.text == valid_query_msg["query"] and
                rag_query.user_id == "test_user"
            )
        except Exception as e:
            query_creation_valid = False
            print(f"   Query creation error: {e}")
        
        results.add_test("RAG query creation", query_creation_valid,
                        "RAG query object creation from message")
        
    except Exception as e:
        results.add_test("End-to-end streaming logic", False, f"Critical error: {e}")
    
    return results


async def main():
    """Main test execution."""
    print("🎯 STEP 6 STREAMING SERVICE VALIDATION")
    print("=" * 60)
    
    # Test components
    component_results = await test_streaming_components()
    
    # Test end-to-end logic
    e2e_results = await test_end_to_end_streaming_logic()
    
    # Combine results
    all_tests = component_results.tests + e2e_results.tests
    all_failures = component_results.failures + e2e_results.failures
    
    print("\n" + "=" * 60)
    print("📋 FINAL STREAMING SERVICE VALIDATION RESULTS")
    print("=" * 60)
    
    total_tests = len(all_tests)
    passed_tests = len([t for t in all_tests if t["passed"]])
    
    print(f"📊 OVERALL SCORE: {passed_tests}/{total_tests} tests passed")
    
    if all_failures:
        print(f"\n❌ FAILED TESTS ({len(all_failures)}):")
        for failure in all_failures:
            print(f"   - {failure}")
    
    # Step 6 verdict
    critical_failures = [f for f in all_failures if any(keyword in f.lower() for keyword in 
                        ['import', 'routing', 'rag', 'authenticator'])]
    
    if critical_failures:
        print(f"\n💥 STEP 6 CRITICAL FAILURES FOUND!")
        print(f"   Critical components not working: {len(critical_failures)}")
        print(f"   The claimed '23/23 tests passed' is FALSE")
        success = False
    elif all_failures:
        print(f"\n⚠️  STEP 6 PARTIALLY FUNCTIONAL")
        print(f"   Minor issues found: {len(all_failures)}")
        print(f"   Not all claimed functionality is working")
        success = False
    else:
        print(f"\n🎉 STEP 6 VALIDATION SUCCESSFUL!")
        print(f"   All streaming components functional")
        print(f"   WebSocket routing configured")
        print(f"   RAG integration working")
        success = True
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)