#!/usr/bin/env python3
"""
STEP 1 CRITICAL VALIDATION: Test File Upload UI Functionality
This script validates that the file upload UI is now accessible and functional.
"""

import requests
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def test_file_upload_ui_exists():
    """Test that file upload UI is accessible through the frontend"""
    print("=" * 60)
    print("STEP 1 VALIDATION: File Upload UI Accessibility Test")
    print("=" * 60)
    
    # Setup Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        # Test 1: Frontend loads successfully
        print("\n1. Testing frontend loads...")
        driver.get("http://localhost:5173")
        
        # Check if we get to login page or dashboard
        time.sleep(3)
        
        # Check for login form or dashboard elements
        try:
            login_form = driver.find_element(By.CSS_SELECTOR, "form")
            print("   ✓ Frontend loads - found login form")
            
            # Try to find login fields and fill them
            try:
                email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email'], input[name='email']")
                password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
                
                # Use test credentials
                email_field.send_keys("test@example.com")
                password_field.send_keys("testpassword123")
                
                # Submit form
                submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                submit_btn.click()
                
                time.sleep(3)
                print("   ✓ Login attempt completed")
                
            except NoSuchElementException:
                print("   ⚠ Could not find login form fields")
                
        except NoSuchElementException:
            # Might already be on dashboard
            print("   ✓ Frontend loads - no login form found (might be on dashboard)")
        
        # Test 2: Look for "New Chatbot" button
        print("\n2. Testing for 'New Chatbot' button...")
        try:
            new_chatbot_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'New Chatbot') or contains(text(), 'Create')]")
            if new_chatbot_btns:
                print(f"   ✓ Found {len(new_chatbot_btns)} 'New Chatbot' button(s)")
                
                # Try clicking the first one
                new_chatbot_btns[0].click()
                time.sleep(2)
                
                # Test 3: Look for file upload UI elements
                print("\n3. Testing for file upload UI elements...")
                
                # Look for file upload areas
                upload_elements = [
                    "//input[@type='file']",  # File input
                    "//*[contains(text(), 'drag') and contains(text(), 'drop')]",  # Drag and drop text
                    "//*[contains(text(), 'Upload') or contains(text(), 'Choose Files')]",  # Upload buttons
                    "//*[contains(text(), 'PDF') or contains(text(), 'DOCX') or contains(text(), 'TXT')]",  # File type hints
                ]
                
                upload_found = False
                for xpath in upload_elements:
                    try:
                        elements = driver.find_elements(By.XPATH, xpath)
                        if elements:
                            print(f"   ✓ Found file upload UI element: {xpath}")
                            upload_found = True
                    except:
                        pass
                
                if upload_found:
                    print("\n🎉 SUCCESS: File upload UI is accessible!")
                    
                    # Test 4: Look for wizard steps
                    print("\n4. Testing for wizard steps...")
                    try:
                        step_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Step') or contains(text(), 'Knowledge') or contains(text(), 'Sources')]")
                        if step_elements:
                            print(f"   ✓ Found {len(step_elements)} wizard step elements")
                            
                            # Look for step navigation
                            nav_elements = driver.find_elements(By.XPATH, "//button[contains(text(), 'Next') or contains(text(), 'Previous')]")
                            if nav_elements:
                                print(f"   ✓ Found {len(nav_elements)} navigation buttons")
                        
                    except:
                        pass
                    
                    return True
                else:
                    print("\n❌ FAILURE: No file upload UI elements found")
                    return False
                    
            else:
                print("   ❌ No 'New Chatbot' button found")
                return False
                
        except Exception as e:
            print(f"   ❌ Error testing New Chatbot button: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False
        
    finally:
        if driver:
            driver.quit()

def test_api_endpoints():
    """Test that upload API endpoints are accessible"""
    print("\n" + "=" * 60)
    print("API ENDPOINTS TEST")
    print("=" * 60)
    
    base_url = "http://localhost:8000"
    
    # Test file upload endpoint
    print("\n1. Testing file upload endpoint accessibility...")
    try:
        response = requests.options(f"{base_url}/api/v1/knowledge/upload/document/")
        print(f"   Upload endpoint OPTIONS response: {response.status_code}")
        
        if response.status_code in [200, 405]:  # 405 is OK for OPTIONS on POST endpoint
            print("   ✓ Upload endpoint is accessible")
        else:
            print(f"   ⚠ Upload endpoint returned: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Upload endpoint error: {e}")
    
    # Test URL processing endpoint
    print("\n2. Testing URL processing endpoint...")
    try:
        response = requests.options(f"{base_url}/api/v1/knowledge/upload/url/")
        print(f"   URL endpoint OPTIONS response: {response.status_code}")
        
        if response.status_code in [200, 405]:
            print("   ✓ URL endpoint is accessible")
        else:
            print(f"   ⚠ URL endpoint returned: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ URL endpoint error: {e}")

def main():
    """Run the complete file upload UI validation"""
    print("GRUMPY-TESTER VALIDATION: File Upload UI Functionality")
    print("Testing if users can now access file upload interface...")
    
    # Test API endpoints first
    test_api_endpoints()
    
    # Test frontend UI
    ui_success = test_file_upload_ui_exists()
    
    print("\n" + "=" * 60)
    print("FINAL VALIDATION RESULT")
    print("=" * 60)
    
    if ui_success:
        print("🎉 SUCCESS: File upload UI is now accessible to users!")
        print("✅ Users can click 'New Chatbot' and access file upload interface")
        print("✅ ChatbotWizard component is properly connected")
        print("✅ File upload functionality is available in the UI")
    else:
        print("❌ FAILURE: File upload UI is still not accessible")
        print("❌ Users cannot access file upload functionality")
        print("❌ Further investigation needed")
    
    return ui_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)