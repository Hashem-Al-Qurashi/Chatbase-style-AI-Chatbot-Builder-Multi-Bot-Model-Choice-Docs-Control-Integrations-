# Token Refresh 401 Unauthorized Error Investigation
## Senior Engineer Instructions Implementation - Complete Error Analysis

### Document Purpose
This document provides systematic investigation and resolution of recurring 401 Unauthorized errors on token refresh endpoint following SENIOR_ENGINEER_INSTRUCTIONS.md methodology.

**Date**: October 13, 2025  
**Investigation Status**: Complete Analysis  
**Following**: SENIOR_ENGINEER_INSTRUCTIONS.md mandatory process  

---

## Executive Summary

### **Critical Issue Identified**
Frontend repeatedly receiving HTTP 401 Unauthorized responses when attempting to refresh authentication tokens, causing session failures and user logouts.

### **Root Cause**
Valid refresh tokens are being sent but failing validation due to:
1. Token expiration timing issues
2. Frontend retry logic causing rapid successive refresh attempts
3. Potential token storage corruption in localStorage

### **Impact**
- Users being logged out unexpectedly
- Session continuity broken
- Poor user experience with authentication

---

## Phase 1: Architecture Review ✅ COMPLETED

### **Documents Reviewed**
1. **SENIOR_ENGINEER_INSTRUCTIONS.md**: Mandatory testing and documentation process
2. **SYSTEM_STATE.md**: Current authentication system status (95% complete)
3. **AUTHENTICATION_ERROR_INVESTIGATION.md**: Previous authentication issues
4. **Frontend API Service**: `/frontend/src/services/api.ts`
5. **Backend Auth Views**: `/apps/accounts/auth_views.py`
6. **Vite Configuration**: `/frontend/vite.config.ts`

### **Key Findings**
- ✅ Backend refresh endpoint (`/auth/refresh/`) is fully functional
- ✅ Frontend proxy correctly configured (port 3000 → 8000)
- ✅ JWT token generation and validation working
- ⚠️ Token refresh logic in frontend has retry issues
- ⚠️ No token expiration pre-check before refresh attempts

---

## Phase 2: Error Documentation

### **ERROR-REFRESH-001: Consecutive 401 Errors on Token Refresh**

**Error Details:**
- **Component**: Frontend API Service Token Refresh
- **Severity**: Critical (breaks user sessions)
- **Detection**: Browser DevTools Network Tab
- **Environment**: Development (localhost:3000 → localhost:8000)

**Exact Error Pattern:**
```
POST http://localhost:3000/auth/refresh/ 401 (Unauthorized)
POST http://localhost:3000/auth/refresh/ 401 (Unauthorized)
POST http://localhost:3000/auth/refresh/ 401 (Unauthorized)
```

**Symptoms:**
- Multiple rapid refresh attempts within seconds
- All attempts returning 401 Unauthorized
- User session terminated after failures
- localStorage tokens potentially corrupted

---

## Phase 3: Systematic Testing ✅ COMPLETED

### **Test 1: Backend Endpoint Validation**
```bash
# Test with invalid token
curl -X POST http://localhost:8000/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"invalid_token"}'

# Result: 401 Unauthorized (EXPECTED)
{"error":"Invalid refresh token","details":"Refresh token is invalid or expired"}
```

### **Test 2: Valid Token Refresh**
```bash
# Generate valid tokens
python3 manage.py shell -c "
from apps.accounts.models import User
from apps.core.auth import jwt_manager
user = User.objects.get(email='test@example.com')
auth_result = jwt_manager.generate_tokens(user)
print(auth_result.refresh_token)
"

# Test with valid token
curl -X POST http://localhost:8000/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"[VALID_TOKEN]"}'

# Result: 200 OK (SUCCESS)
{"access_token":"[NEW_TOKEN]","expires_in":900}
```

### **Test 3: Frontend Token Flow Analysis**

**Current Implementation Issues Found:**

1. **Token Refresh on Every 401**
   - Lines 88-94 in api.ts attempt refresh on ANY 401 error
   - Creates infinite loop if refresh token is invalid
   - No check for refresh endpoint itself returning 401

2. **Missing Token Expiration Check**
   - Frontend doesn't check if access token is expired before making requests
   - Waits for 401 to trigger refresh instead of proactive refresh

3. **Token Storage Issues**
   - No validation of stored tokens before use
   - Corrupted tokens in localStorage cause persistent failures

---

## Phase 4: Root Cause Analysis

### **Primary Causes Identified**

1. **Infinite Retry Loop**
   ```typescript
   // Current problematic code (api.ts lines 87-94)
   if (response.status === 401 && this.refreshToken) {
     const refreshed = await this.refreshAccessToken();
     if (refreshed) {
       headers.Authorization = `Bearer ${this.accessToken}`;
       response = await fetch(url, { ...config, headers });
     }
   }
   ```
   - If refresh fails with 401, it tries to refresh again
   - No circuit breaker or retry limit

2. **No Token Validation**
   - Tokens loaded from localStorage without validation
   - Expired or malformed tokens cause immediate 401s

3. **Missing Expiration Management**
   - No proactive token refresh before expiration
   - No tracking of token expiry time

---

## Phase 5: Resolution Implementation

### **Solution 1: Add Refresh Endpoint Detection**
Prevent infinite loop by not refreshing on refresh endpoint 401s:

```typescript
// Enhanced refresh logic with endpoint detection
private async request<T>(
  endpoint: string,
  options: RequestInit = {},
  useAuthURL = false
): Promise<T> {
  const url = `${useAuthURL ? this.authURL : this.baseURL}${endpoint}`;
  
  // ... existing code ...

  // Handle token refresh on 401 (except for refresh endpoint itself)
  if (response.status === 401 && 
      this.refreshToken && 
      !endpoint.includes('/refresh')) {  // Don't refresh on refresh endpoint
    const refreshed = await this.refreshAccessToken();
    if (refreshed) {
      headers.Authorization = `Bearer ${this.accessToken}`;
      response = await fetch(url, { ...config, headers });
    }
  }
}
```

### **Solution 2: Add Token Expiration Tracking**
Track token expiry and refresh proactively:

```typescript
class ApiService {
  private accessTokenExpiry: Date | null = null;
  
  private saveTokensToStorage(tokens: AuthTokens) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    
    // Calculate and store expiry time (default 15 minutes)
    const expiresIn = tokens.expires_in || 900;
    this.accessTokenExpiry = new Date(Date.now() + expiresIn * 1000);
    
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    localStorage.setItem('access_token_expiry', this.accessTokenExpiry.toISOString());
  }
  
  private async ensureValidToken(): Promise<boolean> {
    if (!this.accessToken || !this.accessTokenExpiry) return false;
    
    // Check if token will expire in next 60 seconds
    const now = new Date();
    const expiryBuffer = new Date(this.accessTokenExpiry.getTime() - 60000);
    
    if (now >= expiryBuffer && this.refreshToken) {
      return await this.refreshAccessToken();
    }
    
    return true;
  }
}
```

### **Solution 3: Add Token Validation**
Validate tokens on load and clear if invalid:

```typescript
private loadTokensFromStorage() {
  this.accessToken = localStorage.getItem('access_token');
  this.refreshToken = localStorage.getItem('refresh_token');
  const expiryStr = localStorage.getItem('access_token_expiry');
  
  // Validate loaded tokens
  if (this.accessToken && expiryStr) {
    const expiry = new Date(expiryStr);
    if (expiry <= new Date()) {
      // Token expired, try to refresh
      this.refreshAccessToken().catch(() => {
        this.clearTokensFromStorage();
      });
    } else {
      this.accessTokenExpiry = expiry;
    }
  }
}
```

### **Solution 4: Add Retry Limiting**
Implement circuit breaker for failed refresh attempts:

```typescript
class ApiService {
  private refreshAttempts = 0;
  private maxRefreshAttempts = 2;
  
  async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken || this.refreshAttempts >= this.maxRefreshAttempts) {
      this.clearTokensFromStorage();
      return false;
    }
    
    this.refreshAttempts++;
    
    try {
      const tokens = await this.request<AuthTokens>('/refresh/', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      }, true);
      
      this.saveTokensToStorage(tokens);
      this.refreshAttempts = 0; // Reset on success
      return true;
    } catch (error) {
      if (this.refreshAttempts >= this.maxRefreshAttempts) {
        this.clearTokensFromStorage();
        // Optionally trigger logout or redirect to login
        window.location.href = '/login';
      }
      return false;
    }
  }
}
```

---

## Phase 6: Implementation Files to Update

### **Files Requiring Updates:**

1. **`/frontend/src/services/api.ts`**
   - Add refresh endpoint detection (line 88)
   - Implement token expiration tracking
   - Add token validation on load
   - Implement retry limiting

2. **`/frontend/src/types/index.ts`** (if needed)
   - Add `expires_in` field to AuthTokens interface if missing

3. **`/frontend/src/hooks/useAuth.tsx`**
   - Add token expiration monitoring
   - Implement proactive refresh logic

---

## Phase 7: Testing Strategy

### **Test Scenarios to Validate:**

1. **Normal Token Refresh Flow**
   - Login with valid credentials
   - Wait for token to near expiration
   - Verify automatic refresh occurs
   - Confirm session continuity

2. **Invalid Refresh Token Handling**
   - Corrupt refresh token in localStorage
   - Make authenticated request
   - Verify graceful logout after max retries

3. **Expired Token Recovery**
   - Set expired access token in localStorage
   - Load application
   - Verify automatic refresh attempt on load

4. **Network Error Resilience**
   - Simulate network failure during refresh
   - Verify retry logic with backoff
   - Confirm eventual logout if persistent failure

---

## Phase 8: Prevention Strategies

### **Long-term Improvements:**

1. **Token Refresh Scheduler**
   - Implement background timer to refresh tokens before expiry
   - Use Web Workers for background refresh

2. **Token Storage Security**
   - Consider using httpOnly cookies for refresh tokens
   - Implement token encryption in localStorage

3. **Session State Management**
   - Centralize auth state in Redux/Context
   - Implement session persistence across tabs

4. **Monitoring and Alerting**
   - Log all 401 errors with context
   - Track refresh failure rates
   - Alert on unusual patterns

---

## Compliance with SENIOR_ENGINEER_INSTRUCTIONS.md

### **Checklist** ✅

- [x] Architecture Review Complete
- [x] Systematic Testing Performed
- [x] Every Error Documented
- [x] Root Cause Analysis Complete
- [x] Resolution Strategy Defined
- [x] Prevention Strategies Documented
- [x] Testing Strategy Created
- [x] Implementation Plan Ready

### **Next Steps**
1. Implement the four solutions in api.ts
2. Test all scenarios systematically
3. Update SYSTEM_STATE.md with resolution
4. Document in INTEGRATION_ISSUES_LOG.md

---

## Summary

**Problem**: Token refresh causing 401 errors due to infinite retry loops and missing expiration management.

**Solution**: Implement refresh endpoint detection, token expiration tracking, validation, and retry limiting.

**Impact**: Will restore session continuity and prevent unexpected logouts.

**Priority**: CRITICAL - Implement immediately to restore authentication stability.

---

**Status**: ✅ Investigation Complete - Ready for Implementation  
**Next Document**: Implementation and testing results  
**Expected Outcome**: 100% token refresh success rate with graceful failure handling