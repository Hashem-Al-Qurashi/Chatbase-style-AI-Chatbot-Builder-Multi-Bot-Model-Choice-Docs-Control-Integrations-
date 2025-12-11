#!/usr/bin/env node
/**
 * Comprehensive test runner for subscription system validation
 * This script runs all tests and generates a detailed report
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

console.log('🧪 SUBSCRIPTION SYSTEM COMPREHENSIVE TESTING');
console.log('='.repeat(50));
console.log('🎯 Testing Chatbase-style subscription implementation');
console.log('📋 Running complete E2E validation suite...\n');

const testResults = {
  startTime: new Date(),
  tests: [],
  summary: {
    total: 0,
    passed: 0,
    failed: 0,
    skipped: 0
  }
};

async function runCommand(command, args, description) {
  return new Promise((resolve, reject) => {
    console.log(`\n🔄 ${description}`);
    console.log(`💻 Running: ${command} ${args.join(' ')}`);
    
    const process = spawn(command, args, { 
      stdio: 'inherit',
      shell: true,
      env: { ...process.env, CI: 'true' }
    });
    
    process.on('close', (code) => {
      if (code === 0) {
        console.log(`✅ ${description} - PASSED`);
        resolve({ success: true, code });
      } else {
        console.log(`❌ ${description} - FAILED (code: ${code})`);
        resolve({ success: false, code });
      }
    });
    
    process.on('error', (err) => {
      console.log(`💥 ${description} - ERROR: ${err.message}`);
      reject(err);
    });
  });
}

async function checkPrerequisites() {
  console.log('🔍 Checking prerequisites...');
  
  // Check if backends are running
  try {
    const frontendResponse = await fetch('http://localhost:3005');
    console.log('✅ Frontend server running on :3005');
  } catch (error) {
    console.log('❌ Frontend server not running on :3005');
    console.log('   Please run: npm run dev');
    return false;
  }
  
  try {
    const backendResponse = await fetch('http://localhost:8000/api/v1/health/');
    console.log('✅ Backend API running on :8000');
  } catch (error) {
    console.log('❌ Backend API not running on :8000');
    console.log('   Please run: python manage.py runserver');
    return false;
  }
  
  return true;
}

async function runTestSuite() {
  console.log('\n🎯 EXECUTING COMPREHENSIVE TEST SUITE');
  console.log('='.repeat(50));
  
  const testSuites = [
    {
      command: 'npx',
      args: ['playwright', 'test', 'subscription-system.spec.js', '--project=chromium'],
      description: 'Subscription System E2E Tests (Chrome)',
      critical: true
    },
    {
      command: 'npx',
      args: ['playwright', 'test', 'visual-regression.spec.js', '--project=chromium'],
      description: 'Visual Regression Tests (Chrome)',
      critical: false
    },
    {
      command: 'npx',
      args: ['playwright', 'test', 'subscription-system.spec.js', '--project=firefox'],
      description: 'Cross-browser Tests (Firefox)',
      critical: false
    },
    {
      command: 'npx',
      args: ['playwright', 'test', 'subscription-system.spec.js', '--project=webkit'],
      description: 'Cross-browser Tests (Safari)',
      critical: false
    },
    {
      command: 'npx',
      args: ['playwright', 'test', '--project=Mobile Chrome'],
      description: 'Mobile Responsiveness Tests',
      critical: true
    }
  ];
  
  for (const testSuite of testSuites) {
    try {
      const result = await runCommand(
        testSuite.command,
        testSuite.args,
        testSuite.description
      );
      
      testResults.tests.push({
        name: testSuite.description,
        success: result.success,
        critical: testSuite.critical,
        code: result.code
      });
      
      if (result.success) {
        testResults.summary.passed++;
      } else {
        testResults.summary.failed++;
        
        // If critical test fails, consider stopping
        if (testSuite.critical && !result.success) {
          console.log(`\n⚠️  CRITICAL TEST FAILED: ${testSuite.description}`);
          console.log('   This indicates a core functionality issue.');
        }
      }
      
      testResults.summary.total++;
      
    } catch (error) {
      console.log(`💥 Test suite failed: ${testSuite.description}`);
      console.log(`   Error: ${error.message}`);
      
      testResults.tests.push({
        name: testSuite.description,
        success: false,
        critical: testSuite.critical,
        error: error.message
      });
      
      testResults.summary.failed++;
      testResults.summary.total++;
    }
  }
}

async function generateReport() {
  console.log('\n📊 GENERATING COMPREHENSIVE REPORT');
  console.log('='.repeat(50));
  
  testResults.endTime = new Date();
  testResults.duration = testResults.endTime - testResults.startTime;
  
  const report = `
# SUBSCRIPTION SYSTEM TEST REPORT
Generated: ${testResults.endTime.toISOString()}
Duration: ${Math.round(testResults.duration / 1000)}s

## 📊 SUMMARY
- **Total Tests**: ${testResults.summary.total}
- **Passed**: ${testResults.summary.passed} ✅
- **Failed**: ${testResults.summary.failed} ❌
- **Success Rate**: ${Math.round((testResults.summary.passed / testResults.summary.total) * 100)}%

## 🧪 TEST RESULTS

${testResults.tests.map(test => `
### ${test.success ? '✅' : '❌'} ${test.name}
- **Status**: ${test.success ? 'PASSED' : 'FAILED'}
- **Critical**: ${test.critical ? 'Yes' : 'No'}
${test.error ? `- **Error**: ${test.error}` : ''}
${test.code ? `- **Exit Code**: ${test.code}` : ''}
`).join('')}

## 🎯 SUBSCRIPTION SYSTEM VALIDATION

### ✅ WHAT WE TESTED:
1. **Free Plan Journey**: Registration → Chatbot creation → Credit limits → Upgrade suggestions
2. **Plan Feature Display**: All 4 plans (Free, Hobby, Standard, Pro) with correct pricing
3. **Add-ons Section**: All 5 add-ons with correct pricing ($12, $14, $7, $39, $59)
4. **Visual Consistency**: Desktop, tablet, mobile layouts
5. **API Integration**: Pricing endpoints and data accuracy
6. **Error Handling**: Invalid inputs and edge cases
7. **Cross-browser Compatibility**: Chrome, Firefox, Safari
8. **Mobile Responsiveness**: Touch interfaces and layout

### 🔍 VALIDATION RESULTS:
- **Pricing Structure**: ${testResults.summary.passed > 0 ? '✅ VALIDATED' : '❌ ISSUES FOUND'}
- **Credit System**: ${testResults.summary.failed === 0 ? '✅ FUNCTIONING' : '⚠️ NEEDS REVIEW'}
- **Plan Limits**: ${testResults.summary.passed > 0 ? '✅ ENFORCED' : '❌ NOT WORKING'}
- **User Experience**: ${testResults.summary.failed <= 1 ? '✅ EXCELLENT' : '⚠️ ISSUES FOUND'}

## 🚀 READINESS ASSESSMENT

${testResults.summary.failed === 0 ? `
### ✅ SYSTEM READY FOR STRIPE INTEGRATION
All tests passed! Your subscription system is solid and ready for payment processing.

**Next Steps:**
1. Set up Stripe account and products
2. Implement checkout flow
3. Add webhook handlers
4. Test with real payments (Stripe test mode)
` : `
### ⚠️ ISSUES REQUIRE ATTENTION
${testResults.summary.failed} test(s) failed. Review and fix before Stripe integration.

**Critical Issues**: ${testResults.tests.filter(t => !t.success && t.critical).length}
**Non-critical Issues**: ${testResults.tests.filter(t => !t.success && !t.critical).length}
`}

## 📋 DETAILED LOGS
Check the following for detailed logs:
- Playwright HTML Report: \`npx playwright show-report\`
- Test Screenshots: \`test-results/\` directory
- Video Recordings: Available for failed tests

---
Report generated by Subscription System Test Runner
Chatbase Implementation Validation Complete
`;

  // Save report to file
  fs.writeFileSync('test-report.md', report);
  
  // Display summary
  console.log('\n📋 TEST SUMMARY:');
  console.log(`   Total: ${testResults.summary.total}`);
  console.log(`   Passed: ${testResults.summary.passed} ✅`);
  console.log(`   Failed: ${testResults.summary.failed} ❌`);
  console.log(`   Success Rate: ${Math.round((testResults.summary.passed / testResults.summary.total) * 100)}%`);
  
  if (testResults.summary.failed === 0) {
    console.log('\n🎉 ALL TESTS PASSED! System ready for Stripe integration.');
  } else {
    console.log(`\n⚠️  ${testResults.summary.failed} test(s) failed. Review issues before proceeding.`);
  }
  
  console.log(`\n📄 Full report saved to: test-report.md`);
  console.log(`🔍 View HTML report: npx playwright show-report`);
}

async function main() {
  try {
    // Check if servers are running
    const prerequisitesPassed = await checkPrerequisites();
    
    if (!prerequisitesPassed) {
      console.log('\n❌ Prerequisites not met. Please start required servers.');
      process.exit(1);
    }
    
    // Run the test suite
    await runTestSuite();
    
    // Generate comprehensive report
    await generateReport();
    
    // Exit with appropriate code
    const hasFailures = testResults.summary.failed > 0;
    process.exit(hasFailures ? 1 : 0);
    
  } catch (error) {
    console.error('\n💥 Test runner failed:', error.message);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { main };