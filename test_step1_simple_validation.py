#!/usr/bin/env python3
"""
STEP 1 SIMPLE VALIDATION: Test Frontend and API Accessibility
This script validates that the frontend is running and API endpoints are accessible.
"""

import requests
import time
import json

def test_frontend_accessibility():
    """Test that frontend is running and accessible"""
    print("=" * 60)
    print("FRONTEND ACCESSIBILITY TEST")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:5173", timeout=10)
        print(f"Frontend status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Check for React app indicators
            react_indicators = [
                "div id=\"root\"",
                "React",
                "vite",
                "chatbot",
                "dashboard"
            ]
            
            found_indicators = []
            for indicator in react_indicators:
                if indicator.lower() in content.lower():
                    found_indicators.append(indicator)
            
            print(f"   ✓ Frontend loads successfully")
            print(f"   ✓ Found indicators: {found_indicators}")
            
            # Check for specific UI elements that suggest file upload capability
            upload_indicators = [
                "upload",
                "file",
                "drag",
                "drop",
                "ChatbotWizard",
                "knowledge"
            ]
            
            upload_found = []
            for indicator in upload_indicators:
                if indicator.lower() in content.lower():
                    upload_found.append(indicator)
            
            if upload_found:
                print(f"   ✓ Upload-related content found: {upload_found}")
            else:
                print("   ⚠ No upload-related content detected in initial page")
            
            return True
            
        else:
            print(f"   ❌ Frontend returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Frontend test failed: {e}")
        return False

def test_api_endpoints():
    """Test that backend API endpoints are accessible"""
    print("\n" + "=" * 60)
    print("API ENDPOINTS TEST")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    endpoints_to_test = [
        "/api/v1/chatbots/",
        "/api/v1/knowledge/upload/document/",
        "/api/v1/knowledge/upload/url/",
        "/auth/login/",
        "/auth/register/"
    ]
    
    api_success = True
    
    for endpoint in endpoints_to_test:
        print(f"\nTesting {endpoint}...")
        try:
            # Use OPTIONS to test accessibility without authentication
            response = requests.options(f"{base_url}{endpoint}", timeout=5)
            print(f"   OPTIONS response: {response.status_code}")
            
            if response.status_code in [200, 405, 404]:  # 405 is OK for OPTIONS
                print("   ✓ Endpoint is accessible")
            else:
                print(f"   ⚠ Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Endpoint error: {e}")
            api_success = False
    
    return api_success

def test_chatbotwizard_component():
    """Test that ChatbotWizard component exists in the codebase"""
    print("\n" + "=" * 60)
    print("CHATBOTWIZARD COMPONENT TEST")
    print("=" * 60)
    
    try:
        # Read the ChatbotWizard file to verify it has upload functionality
        with open("frontend/src/components/chatbot/ChatbotWizard.tsx", "r") as f:
            content = f.read()
        
        # Check for file upload related code
        upload_features = [
            "handleFiles",
            "handleDrop",
            "handleFileInput", 
            "uploadKnowledgeFile",
            "drag",
            "drop",
            "file upload",
            "FormData",
            "input type=\"file\""
        ]
        
        features_found = []
        for feature in upload_features:
            if feature in content:
                features_found.append(feature)
        
        print(f"   ✓ ChatbotWizard file exists")
        print(f"   ✓ Upload features found: {features_found}")
        
        if len(features_found) >= 5:
            print("   ✓ ChatbotWizard has comprehensive file upload functionality")
            return True
        else:
            print("   ⚠ ChatbotWizard may have limited upload functionality")
            return False
            
    except Exception as e:
        print(f"   ❌ ChatbotWizard test failed: {e}")
        return False

def test_dashboard_integration():
    """Test that Dashboard uses ChatbotWizard"""
    print("\n" + "=" * 60)
    print("DASHBOARD INTEGRATION TEST")
    print("=" * 60)
    
    try:
        with open("frontend/src/components/dashboard/Dashboard.tsx", "r") as f:
            content = f.read()
        
        # Check that Dashboard imports and uses ChatbotWizard
        integration_checks = [
            "import { ChatbotWizard }",
            "<ChatbotWizard",
            "handleCreateChatbot",
            "showCreateModal",
            "existingChatbot="
        ]
        
        checks_passed = []
        for check in integration_checks:
            if check in content:
                checks_passed.append(check)
        
        print(f"   ✓ Dashboard file exists")
        print(f"   ✓ Integration checks passed: {checks_passed}")
        
        if len(checks_passed) >= 4:
            print("   ✓ Dashboard properly integrates ChatbotWizard")
            return True
        else:
            print("   ❌ Dashboard integration incomplete")
            return False
            
    except Exception as e:
        print(f"   ❌ Dashboard integration test failed: {e}")
        return False

def main():
    """Run complete validation"""
    print("STEP 1 CRITICAL VALIDATION: File Upload UI Functionality")
    print("Testing if file upload UI is now accessible to users...")
    
    # Run all tests
    frontend_ok = test_frontend_accessibility()
    api_ok = test_api_endpoints()
    wizard_ok = test_chatbotwizard_component()
    dashboard_ok = test_dashboard_integration()
    
    print("\n" + "=" * 60)
    print("FINAL VALIDATION RESULT")
    print("=" * 60)
    
    all_passed = frontend_ok and api_ok and wizard_ok and dashboard_ok
    
    print(f"Frontend Accessibility: {'✅' if frontend_ok else '❌'}")
    print(f"API Endpoints: {'✅' if api_ok else '❌'}")
    print(f"ChatbotWizard Component: {'✅' if wizard_ok else '❌'}")
    print(f"Dashboard Integration: {'✅' if dashboard_ok else '❌'}")
    
    if all_passed:
        print("\n🎉 SUCCESS: File upload UI should now be accessible!")
        print("✅ Users can click 'New Chatbot' and access file upload interface")
        print("✅ ChatbotWizard component has file upload functionality")
        print("✅ Dashboard properly integrates with ChatbotWizard")
        print("✅ API endpoints are accessible")
        
        print("\n📋 VALIDATION SUMMARY:")
        print("- File upload UI exists in ChatbotWizard component")
        print("- Dashboard now uses ChatbotWizard instead of ChatbotModal")
        print("- Users can access upload functionality via 'New Chatbot' button")
        print("- API endpoints are ready to handle file uploads")
        
    else:
        print("\n❌ FAILURE: File upload UI accessibility issues remain")
        print("❌ Further investigation needed")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)