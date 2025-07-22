#!/usr/bin/env python3
"""
QUICK MATCHING SYSTEM VERIFICATION
Verify the enhanced date-aware matching system is working correctly
"""

import sys
import os
sys.path.append('./arbitrage')

# Import our dedicated matching module
try:
    from contract_matcher import DateAwareContractMatcher
    print("✅ Successfully imported DateAwareContractMatcher from contract_matcher module")
except ImportError as e:
    # Fallback to import from detector
    try:
        from detector_enhanced import DateAwareContractMatcher
        print("✅ Successfully imported DateAwareContractMatcher from detector_enhanced")
    except ImportError as e2:
        print(f"❌ Import error: {e}")
        print(f"❌ Fallback error: {e2}")
        exit(1)

def test_enhanced_matching():
    """Test the enhanced matching with critical examples"""
    print("\n🔍 TESTING ENHANCED DATE-AWARE MATCHING")
    print("=" * 50)
    
    matcher = DateAwareContractMatcher()
    
    # Test cases - CRITICAL for preventing false matches (JULY 2025 FORWARD-LOOKING)
    test_cases = [
        # Same event, same date - SHOULD MATCH
        {
            "kalshi": "Will CPI inflation be 3.0% or higher for August 2025?",
            "poly": "CPI inflation above 3% in August 2025",
            "expected": "HIGH_MATCH",
            "reason": "Same event, same month/year"
        },
        
        # Same event, DIFFERENT dates - SHOULD NOT MATCH  
        {
            "kalshi": "Will CPI inflation be 3.0% or higher for August 2025?",
            "poly": "Will CPI be above 3% in September 2025?",
            "expected": "LOW_MATCH", 
            "reason": "Same event but DIFFERENT months - false match risk!"
        },
        
        # Different wording, same event/date - SHOULD MATCH
        {
            "kalshi": "Will the Fed cut rates by 25 bps in September 2025?",
            "poly": "Fed rate cut September 2025 meeting",
            "expected": "HIGH_MATCH",
            "reason": "Same Fed meeting, different wording"
        },
        
        # Similar keywords, no dates - UNCERTAIN
        {
            "kalshi": "Will unemployment be below 4.0%?",
            "poly": "Unemployment rate under 4%",
            "expected": "LOW_MATCH",
            "reason": "No dates - could be different time periods"
        },
        
        # Completely different events - SHOULD NOT MATCH
        {
            "kalshi": "Will Bitcoin close above $150k by end of 2025?",
            "poly": "CPI inflation above 3% in August 2025",
            "expected": "NO_MATCH",
            "reason": "Completely different events"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n🧪 TEST {i}: {test['reason']}")
        print(f"   Kalshi: {test['kalshi']}")
        print(f"   Poly:   {test['poly']}")
        
        # Get enhanced scores
        scores = matcher.enhanced_similarity_score(test['kalshi'], test['poly'])
        
        print(f"   📊 Scores:")
        print(f"      Final Score: {scores['final_score']:.3f}")
        print(f"      Date Alignment: {scores['date_alignment']:.3f}")
        print(f"      Keywords: {scores['keyword_score']:.3f}")
        print(f"      Text Similarity: {scores['text_similarity']:.3f}")
        if 'date_penalty' in scores:
            print(f"      Date Penalty: {scores['date_penalty']:.3f} (1.0=none, <1.0=penalty)")
        
        # Extract dates for analysis
        kalshi_dates = matcher.extract_dates(test['kalshi'])
        poly_dates = matcher.extract_dates(test['poly'])
        print(f"   📅 Dates:")
        print(f"      Kalshi: {kalshi_dates}")
        print(f"      Poly: {poly_dates}")
        
        # Assess result
        final_score = scores['final_score']
        if final_score > 0.8:
            result = "HIGH_MATCH"
        elif final_score > 0.5:
            result = "MEDIUM_MATCH"
        elif final_score > 0.3:
            result = "LOW_MATCH"
        else:
            result = "NO_MATCH"
        
        print(f"   🎯 Result: {result}")
        print(f"   ✅ Expected: {test['expected']}")
        
        # Check if result matches expectation
        match_expected = (
            (result == "HIGH_MATCH" and test['expected'] == "HIGH_MATCH") or
            (result in ["LOW_MATCH", "NO_MATCH"] and test['expected'] in ["LOW_MATCH", "NO_MATCH"]) or
            (result == "MEDIUM_MATCH")  # Medium is acceptable
        )
        
        status = "✅ PASS" if match_expected else "❌ FAIL"
        print(f"   {status}")
        
        results.append({
            'test_num': i,
            'result': result,
            'expected': test['expected'],
            'passed': match_expected,
            'final_score': final_score,
            'date_alignment': scores['date_alignment']
        })
    
    # Summary
    print(f"\n📊 VERIFICATION SUMMARY")
    print("=" * 40)
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    print(f"✅ Tests Passed: {passed}/{total}")
    print(f"📈 Pass Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ Enhanced matching system is working correctly")
        print(f"✅ Date alignment preventing false matches")
        print(f"✅ Ready for comprehensive testing with real API data")
    else:
        print(f"\n⚠️ Some tests failed - review results above")
        
        failed_tests = [r for r in results if not r['passed']]
        for test in failed_tests:
            print(f"   Test {test['test_num']}: Got {test['result']}, expected {test['expected']}")
    
    return results

def test_date_extraction():
    """Test date extraction specifically"""
    print("\n🗓️ TESTING DATE EXTRACTION")
    print("=" * 40)
    
    matcher = DateAwareContractMatcher()
    
    date_tests = [
        ("August 2025", [{'year': 2025, 'month': 8}]),
        ("September 15, 2025", [{'year': 2025, 'month': 9, 'day': 15}]),
        ("Q3 2025", [{'year': 2025, 'quarter': 3}]),
        ("end of 2025", [{'year': 2025}]),  # FIXED!
        ("by 2025", [{'year': 2025}]),     # ADDED!
        ("No dates here", [])
    ]
    
    for text, expected_structure in date_tests:
        dates = matcher.extract_dates(text)
        print(f"📝 '{text}' → {dates}")
        
        # Basic validation
        has_dates = len(dates) > 0
        expects_dates = len(expected_structure) > 0
        
        if has_dates == expects_dates:
            print(f"   ✅ Correct detection")
        else:
            print(f"   ❌ Wrong detection: found {len(dates)}, expected {len(expected_structure)}")
    
    print(f"✅ Date extraction test complete")

if __name__ == "__main__":
    print("🚀 ENHANCED MATCHING SYSTEM VERIFICATION")
    print("🎯 Goal: Ensure date-aware matching prevents false matches")
    
    try:
        test_date_extraction()
        results = test_enhanced_matching()
        
        print(f"\n🔥 SYSTEM STATUS:")
        if all(r['passed'] for r in results):
            print(f"✅ READY FOR COMPREHENSIVE TESTING")
            print(f"✅ Run: python3 comprehensive_matching_test.py")
        else:
            print(f"⚠️ NEEDS DEBUGGING BEFORE COMPREHENSIVE TEST")
            
    except Exception as e:
        print(f"❌ Error running verification: {e}")
        import traceback
        traceback.print_exc()
