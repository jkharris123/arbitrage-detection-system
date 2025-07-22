#!/usr/bin/env python3
"""
CONTRACT MATCHING MODULE
Pure matching logic with DATE PRIORITIZATION - ZERO FALSE MATCHES!

Responsibilities:
- Date extraction and comparison
- Keyword analysis  
- Enhanced similarity scoring
- Contract categorization

Single Responsibility: Contract matching logic only
"""

import re
from datetime import datetime
from typing import List, Dict, Optional, Set
from difflib import SequenceMatcher

class DateAwareContractMatcher:
    """
    ENHANCED contract matcher with DATE PRIORITIZATION
    
    Key Features:
    - 50% weight on date alignment (prevents false matches)
    - Economic keyword analysis
    - Configurable scoring weights by category
    - Comprehensive date pattern extraction
    """
    
    # Enhanced economic keywords
    ECONOMIC_KEYWORDS = {
        'fed': ['federal reserve', 'fed', 'fomc', 'monetary policy', 'interest rate decision'],
        'rates': ['interest rate', 'fed rate', 'federal funds', 'basis points', 'bps'],
        'inflation': ['cpi', 'consumer price index', 'pce', 'inflation', 'deflation'],
        'employment': ['unemployment', 'jobs', 'payroll', 'employment', 'jobless', 'nonfarm'],
        'gdp': ['gdp', 'gross domestic product', 'economic growth', 'recession'],
        'markets': ['sp500', 's&p 500', 'nasdaq', 'dow', 'stock market', 'market close'],
        'crypto': ['bitcoin', 'btc', 'ethereum', 'eth', 'cryptocurrency'],
        'earnings': ['earnings', 'eps', 'revenue', 'quarterly results'],
        'housing': ['housing', 'mortgage', 'real estate', 'home prices'],
        'bonds': ['treasury', 'yield', 'bonds', '10-year', 'yield curve'],
        'election': ['election', 'president', 'congress', 'senate', 'house', 'vote', 'midterm']
    }
    
    # Date patterns for extraction - CRITICAL FOR AVOIDING FALSE MATCHES
    DATE_PATTERNS = [
        r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "December 12, 2025"
        r'(\w+)\s+(\d{4})',                # "December 2025" 
        r'(\d{1,2})/(\d{1,2})/(\d{4})',   # "12/12/2025"
        r'(\d{4})-(\d{1,2})-(\d{1,2})',   # "2025-12-12"
        r'end of (\w+) (\d{4})',          # "end of December 2025"
        r'end of (\d{4})',                # "end of 2025" - FIXED!
        r'by (\w+) (\d{4})',              # "by December 2025"
        r'by (\d{4})',                    # "by 2025" - ADDED!
        r'(\w+) (\d{1,2})(?:st|nd|rd|th)?,? (\d{4})',  # "December 12th, 2025"
        r'Q([1-4])\s+(\d{4})',            # "Q4 2025"
        r'(\d{4})\s*Q([1-4])',            # "2025 Q4"
    ]
    
    # Month name mapping
    MONTH_NAMES = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """
        Initialize matcher with optional custom scoring weights
        
        Args:
            custom_weights: Dict with 'date', 'keyword', 'text' weights
                          Default: {'date': 0.5, 'keyword': 0.3, 'text': 0.2}
        """
        self.weights = custom_weights or {
            'date': 0.5,      # 50% weight on dates - CRITICAL!
            'keyword': 0.3,   # 30% weight on keywords  
            'text': 0.2       # 20% weight on text similarity
        }
    
    def extract_dates(self, text: str) -> List[Dict]:
        """Extract all dates from contract text - FIXED: No duplicates!"""
        text_lower = text.lower()
        dates = []
        seen_dates = set()
        
        for pattern in self.DATE_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                try:
                    date_info = self._parse_date_match(match)
                    if date_info:
                        # Convert to tuple for deduplication
                        date_tuple = tuple(sorted(date_info.items()))
                        if date_tuple not in seen_dates:
                            dates.append(date_info)
                            seen_dates.add(date_tuple)
                except Exception:
                    continue
        
        return dates
    
    def _parse_date_match(self, match) -> Optional[Dict]:
        """Parse a regex match into date info"""
        groups = match.groups()
        
        if len(groups) == 3:
            # Full date: month, day, year or year, month, day
            if groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                # Numeric format
                if len(groups[0]) == 4:  # yyyy-mm-dd
                    return {'year': int(groups[0]), 'month': int(groups[1]), 'day': int(groups[2])}
                else:  # mm/dd/yyyy
                    return {'year': int(groups[2]), 'month': int(groups[0]), 'day': int(groups[1])}
            else:
                # Text month format
                month_name = groups[0].lower()
                if month_name in self.MONTH_NAMES:
                    return {
                        'year': int(groups[2]), 
                        'month': self.MONTH_NAMES[month_name], 
                        'day': int(groups[1])
                    }
        
        elif len(groups) == 2:
            # Month and year, or Q and year
            if groups[0].lower().startswith('q'):
                # Quarter format
                quarter = int(groups[0][1])
                year = int(groups[1])
                return {'year': year, 'quarter': quarter}
            elif groups[1].isdigit() and len(groups[1]) == 4:
                # Month year format
                month_name = groups[0].lower()
                if month_name in self.MONTH_NAMES:
                    return {'year': int(groups[1]), 'month': self.MONTH_NAMES[month_name]}
        
        elif len(groups) == 1:
            # Just year - FIXED for "end of 2025", "by 2025"
            if groups[0].isdigit() and len(groups[0]) == 4:
                return {'year': int(groups[0])}
        
        return None
    
    def calculate_date_alignment(self, text1: str, text2: str) -> float:
        """
        Calculate how well the dates align between contracts
        Returns 0.0 for no alignment, 1.0 for perfect alignment
        """
        dates1 = self.extract_dates(text1)
        dates2 = self.extract_dates(text2)
        
        if not dates1 or not dates2:
            return 0.0  # No dates found = poor alignment = NO MATCH
        
        best_alignment = 0.0
        
        for date1 in dates1:
            for date2 in dates2:
                alignment = self._compare_dates(date1, date2)
                best_alignment = max(best_alignment, alignment)
        
        return best_alignment
    
    def _compare_dates(self, date1: Dict, date2: Dict) -> float:
        """Compare two date dictionaries and return alignment score (0-1) - FIXED LOGIC!"""
        score = 0.0
        
        # Year match (most important)
        if date1.get('year') == date2.get('year'):
            score += 0.6
        elif date1.get('year') and date2.get('year'):  # Both have years
            if abs(date1.get('year', 0) - date2.get('year', 0)) <= 1:
                score += 0.3  # Adjacent years get partial credit
        
        # Month match - CRITICAL FOR PREVENTING FALSE MATCHES!
        if date1.get('month') == date2.get('month'):
            score += 0.3  # Same month
        elif date1.get('month') and date2.get('month'):  # Both have months
            month_diff = abs(date1.get('month', 0) - date2.get('month', 0))
            if month_diff == 1:  # Adjacent months (Aug/Sep)
                score += 0.15  # Partial credit - still RISKY for economic indicators!
            # No credit for months >1 apart
        
        # Day match (less important for economic indicators)
        if date1.get('day') and date2.get('day'):
            if date1.get('day') == date2.get('day'):
                score += 0.1
        
        # Quarter match
        if date1.get('quarter') and date2.get('quarter'):
            if date1.get('quarter') == date2.get('quarter'):
                score += 0.3
        
        return min(score, 1.0)
    
    def extract_keywords(self, text: str) -> Set[str]:
        """Extract economic keywords from text"""
        text_lower = text.lower()
        keywords = set()
        
        for category, terms in self.ECONOMIC_KEYWORDS.items():
            for term in terms:
                if term in text_lower:
                    keywords.add(category)
        
        return keywords
    
    def categorize_contract(self, text: str) -> str:
        """Categorize contract based on content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['fed', 'federal reserve', 'fomc', 'interest rate']):
            return 'fed_rates'
        elif any(word in text_lower for word in ['cpi', 'inflation', 'consumer price']):
            return 'inflation'
        elif any(word in text_lower for word in ['unemployment', 'jobs', 'payroll']):
            return 'employment'
        elif any(word in text_lower for word in ['sp500', 's&p', 'nasdaq', 'dow']):
            return 'markets'
        elif any(word in text_lower for word in ['bitcoin', 'btc', 'ethereum', 'crypto']):
            return 'crypto'
        elif any(word in text_lower for word in ['election', 'president', 'vote', 'midterm']):
            return 'politics'
        elif any(word in text_lower for word in ['gdp', 'recession', 'growth']):
            return 'economy'
        else:
            return 'other'
    
    def calculate_keyword_score(self, text1: str, text2: str) -> float:
        """Calculate keyword overlap score"""
        keywords1 = self.extract_keywords(text1)
        keywords2 = self.extract_keywords(text2)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        overlap = len(keywords1.intersection(keywords2))
        total = len(keywords1.union(keywords2))
        
        return overlap / total if total > 0 else 0.0
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate basic text similarity"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def enhanced_similarity_score(self, text1: str, text2: str, 
                                category: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate enhanced similarity with DATE PRIORITIZATION
        
        Args:
            text1: First contract text
            text2: Second contract text  
            category: Optional category for custom weights
            
        Returns:
            Dict with individual scores and final weighted score
        """
        
        # Calculate individual components
        text_sim = self.calculate_text_similarity(text1, text2)
        date_alignment = self.calculate_date_alignment(text1, text2)
        keyword_score = self.calculate_keyword_score(text1, text2)
        
        # Auto-detect category if not provided
        if not category:
            category = self._detect_category_from_text(text1, text2)
        
        # Get weights (potentially category-specific)
        weights = self._get_category_weights(category) if category else self.weights
        
        # SPECIAL PENALTY for economic indicators with different months
        date_penalty = self._calculate_economic_date_penalty(text1, text2, category, date_alignment)
        
        # WEIGHTED FINAL SCORE - Date alignment prevents false matches!
        final_score = (date_alignment * weights['date'] + 
                      keyword_score * weights['keyword'] + 
                      text_sim * weights['text'])
        
        # Apply penalty for economic indicators with wrong dates
        final_score *= date_penalty
        
        return {
            'text_similarity': text_sim,
            'date_alignment': date_alignment,
            'keyword_score': keyword_score,
            'final_score': final_score,
            'weights_used': weights,
            'date_penalty': date_penalty
        }
    
    def _get_category_weights(self, category: str) -> Dict[str, float]:
        """Get category-specific weights for enhanced accuracy"""
        category_weights = {
            'inflation': {'date': 0.6, 'keyword': 0.3, 'text': 0.1},  # Dates critical for CPI
            'employment': {'date': 0.6, 'keyword': 0.3, 'text': 0.1}, # Dates critical for jobs data
            'fed_rates': {'date': 0.6, 'keyword': 0.3, 'text': 0.1},  # Specific meeting dates
            'politics': {'date': 0.4, 'keyword': 0.4, 'text': 0.2},   # Keywords important
            'markets': {'date': 0.5, 'keyword': 0.3, 'text': 0.2},    # Balanced
            'crypto': {'date': 0.4, 'keyword': 0.4, 'text': 0.2},     # Balanced
        }
        
        return category_weights.get(category, self.weights)
    
    def _detect_category_from_text(self, text1: str, text2: str) -> str:
        """Auto-detect category from text content"""
        combined_text = (text1 + " " + text2).lower()
        
        if any(word in combined_text for word in ['cpi', 'inflation', 'consumer price']):
            return 'inflation'
        elif any(word in combined_text for word in ['fed', 'federal reserve', 'fomc', 'interest rate']):
            return 'fed_rates'
        elif any(word in combined_text for word in ['unemployment', 'jobs', 'payroll']):
            return 'employment'
        elif any(word in combined_text for word in ['gdp', 'recession', 'growth']):
            return 'economy'
        else:
            return 'other'
    
    def _calculate_economic_date_penalty(self, text1: str, text2: str, category: str, date_alignment: float) -> float:
        """Calculate penalty for economic indicators with misaligned dates - PREVENTS FALSE MATCHES!"""
        
        # For economic indicators, different months = HIGH PENALTY
        if category in ['inflation', 'employment', 'fed_rates', 'economy']:
            dates1 = self.extract_dates(text1)
            dates2 = self.extract_dates(text2)
            
            if dates1 and dates2:
                # Check if any dates have different months
                for date1 in dates1:
                    for date2 in dates2:
                        # Same year but different months = DANGER!
                        if (date1.get('year') == date2.get('year') and 
                            date1.get('month') and date2.get('month') and
                            date1.get('month') != date2.get('month')):
                            return 0.3  # 70% penalty for different months in economic data!
                
                # No dates or unclear = moderate penalty
                if date_alignment < 0.5:
                    return 0.7  # 30% penalty for unclear dates
        
        return 1.0  # No penalty
    
    def similarity_score(self, text1: str, text2: str) -> float:
        """
        Legacy compatibility method - returns final score only
        
        Args:
            text1: First contract text
            text2: Second contract text
            
        Returns:
            Final similarity score (0-1)
        """
        result = self.enhanced_similarity_score(text1, text2)
        return result['final_score']
    
    def assess_match_risk(self, text1: str, text2: str) -> str:
        """
        Assess the risk level of a potential match
        
        Returns:
            "SAFE", "RISKY", or "DANGEROUS"
        """
        scores = self.enhanced_similarity_score(text1, text2)
        
        # High confidence with good date alignment = SAFE
        if scores['final_score'] > 0.8 and scores['date_alignment'] > 0.7:
            return "SAFE"
        
        # Good keyword match but poor dates = DANGEROUS (could be wrong event)
        elif scores['keyword_score'] > 0.7 and scores['date_alignment'] < 0.3:
            return "DANGEROUS"
        
        # Medium confidence = RISKY  
        elif 0.5 < scores['final_score'] <= 0.8:
            return "RISKY"
        
        # Low confidence = SAFE (unlikely to be matched anyway)
        else:
            return "SAFE"
    
    def find_best_matches(self, target_text: str, candidate_texts: List[str], 
                         min_threshold: float = 0.5) -> List[Dict]:
        """
        Find best matches for a target contract from candidates
        
        Args:
            target_text: Contract to match
            candidate_texts: List of potential matches
            min_threshold: Minimum score to consider
            
        Returns:
            List of match results sorted by score
        """
        matches = []
        
        for i, candidate in enumerate(candidate_texts):
            scores = self.enhanced_similarity_score(target_text, candidate)
            
            if scores['final_score'] >= min_threshold:
                matches.append({
                    'candidate_index': i,
                    'candidate_text': candidate,
                    'scores': scores,
                    'risk_level': self.assess_match_risk(target_text, candidate)
                })
        
        # Sort by final score (highest first)
        matches.sort(key=lambda x: x['scores']['final_score'], reverse=True)
        
        return matches

# Utility functions for external use
def quick_match(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """Quick boolean match check"""
    matcher = DateAwareContractMatcher()
    return matcher.similarity_score(text1, text2) >= threshold

def detailed_match_analysis(text1: str, text2: str) -> Dict:
    """Get detailed match analysis"""
    matcher = DateAwareContractMatcher()
    scores = matcher.enhanced_similarity_score(text1, text2)
    scores['risk_level'] = matcher.assess_match_risk(text1, text2)
    scores['dates_1'] = matcher.extract_dates(text1)
    scores['dates_2'] = matcher.extract_dates(text2)
    scores['keywords_1'] = list(matcher.extract_keywords(text1))
    scores['keywords_2'] = list(matcher.extract_keywords(text2))
    
    # Add category detection
    scores['detected_category'] = matcher._detect_category_from_text(text1, text2)
    
    return scores

if __name__ == "__main__":
    # Quick test of the matcher
    matcher = DateAwareContractMatcher()
    
    # Test case
    kalshi = "Will CPI inflation be 3.0% or higher for August 2025?"
    poly = "CPI inflation above 3% in August 2025"
    
    result = detailed_match_analysis(kalshi, poly)
    print(f"Match Analysis:")
    print(f"  Final Score: {result['final_score']:.3f}")
    print(f"  Date Alignment: {result['date_alignment']:.3f}")
    print(f"  Date Penalty: {result.get('date_penalty', 1.0):.3f}")
    print(f"  Category: {result.get('detected_category', 'unknown')}")
    print(f"  Risk Level: {result['risk_level']}")
    print(f"  Should Match: {result['final_score'] > 0.8}")
    
    # Test problematic case
    print(f"\nTesting DANGEROUS case:")
    kalshi2 = "Will CPI inflation be 3.0% or higher for August 2025?"
    poly2 = "Will CPI be above 3% in September 2025?"
    
    result2 = detailed_match_analysis(kalshi2, poly2)
    print(f"  Final Score: {result2['final_score']:.3f}")
    print(f"  Date Alignment: {result2['date_alignment']:.3f}")
    print(f"  Date Penalty: {result2.get('date_penalty', 1.0):.3f}")
    print(f"  Category: {result2.get('detected_category', 'unknown')}")
    print(f"  Should Match: {result2['final_score'] > 0.8} (should be FALSE!)")
