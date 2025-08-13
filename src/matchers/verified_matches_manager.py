#!/usr/bin/env python3
"""
Verified Matches Manager
Handles PM-verified contract matches to avoid redundant confirmation requests
"""

import os
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class VerifiedMatchesManager:
    """Manages verified and rejected contract matches"""
    
    def __init__(self):
        self.verified_file = "data/verified_matches.csv"
        self.rejected_file = "data/rejected_matches.csv"
        self.pending_file = "data/pending_matches.json"
        
        # Ensure files exist
        self._ensure_files_exist()
        
        # Load data into memory for fast lookups
        self.verified_matches = self._load_verified_matches()
        self.rejected_matches = self._load_rejected_matches()
        self.pending_matches = self._load_pending_matches()
    
    def _ensure_files_exist(self):
        """Create files if they don't exist"""
        os.makedirs("data", exist_ok=True)
        
        # Verified matches CSV
        if not os.path.exists(self.verified_file):
            with open(self.verified_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'kalshi_ticker', 'poly_condition_id', 'verified_by', 
                    'verified_at', 'active', 'notes'
                ])
        
        # Rejected matches CSV
        if not os.path.exists(self.rejected_file):
            with open(self.rejected_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'kalshi_ticker', 'poly_condition_id', 'rejected_by', 
                    'rejected_at', 'reason'
                ])
        
        # Pending matches JSON
        if not os.path.exists(self.pending_file):
            with open(self.pending_file, 'w') as f:
                json.dump({}, f)
    
    def _load_verified_matches(self) -> Dict[str, Dict]:
        """Load verified matches into memory"""
        verified = {}
        try:
            with open(self.verified_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = f"{row['kalshi_ticker']}|{row['poly_condition_id']}"
                    verified[key] = row
        except Exception as e:
            logger.error(f"Error loading verified matches: {e}")
        return verified
    
    def _load_rejected_matches(self) -> Dict[str, Dict]:
        """Load rejected matches into memory"""
        rejected = {}
        try:
            with open(self.rejected_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = f"{row['kalshi_ticker']}|{row['poly_condition_id']}"
                    rejected[key] = row
        except Exception as e:
            logger.error(f"Error loading rejected matches: {e}")
        return rejected
    
    def _load_pending_matches(self) -> Dict[str, Dict]:
        """Load pending matches from JSON"""
        try:
            with open(self.pending_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading pending matches: {e}")
            return {}
    
    def is_verified(self, kalshi_ticker: str, poly_condition_id: str) -> bool:
        """Check if a match is verified"""
        key = f"{kalshi_ticker}|{poly_condition_id}"
        return key in self.verified_matches and self.verified_matches[key].get('active') == 'true'
    
    def is_rejected(self, kalshi_ticker: str, poly_condition_id: str) -> bool:
        """Check if a match was rejected"""
        key = f"{kalshi_ticker}|{poly_condition_id}"
        return key in self.rejected_matches
    
    def is_pending(self, kalshi_ticker: str, poly_condition_id: str) -> bool:
        """Check if a match is pending verification"""
        key = f"{kalshi_ticker}|{poly_condition_id}"
        return key in self.pending_matches
    
    def get_match_status(self, kalshi_ticker: str, poly_condition_id: str) -> str:
        """Get the status of a match: 'verified', 'rejected', 'pending', or 'unknown'"""
        if self.is_verified(kalshi_ticker, poly_condition_id):
            return 'verified'
        elif self.is_rejected(kalshi_ticker, poly_condition_id):
            return 'rejected'
        elif self.is_pending(kalshi_ticker, poly_condition_id):
            return 'pending'
        else:
            return 'unknown'
    
    def add_verified_match(self, kalshi_ticker: str, poly_condition_id: str, 
                          verified_by: str = 'PM', notes: str = ''):
        """Add a verified match"""
        key = f"{kalshi_ticker}|{poly_condition_id}"
        
        # Add to memory
        self.verified_matches[key] = {
            'kalshi_ticker': kalshi_ticker,
            'poly_condition_id': poly_condition_id,
            'verified_by': verified_by,
            'verified_at': datetime.now().isoformat(),
            'active': 'true',
            'notes': notes
        }
        
        # Remove from pending if exists
        if key in self.pending_matches:
            del self.pending_matches[key]
            self._save_pending_matches()
        
        # Append to CSV
        with open(self.verified_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                kalshi_ticker, poly_condition_id, verified_by,
                datetime.now().isoformat(), 'true', notes
            ])
        
        logger.info(f"✅ Added verified match: {kalshi_ticker} ↔ {poly_condition_id}")
    
    def add_rejected_match(self, kalshi_ticker: str, poly_condition_id: str, 
                          rejected_by: str = 'PM', reason: str = 'different_events'):
        """Add a rejected match"""
        key = f"{kalshi_ticker}|{poly_condition_id}"
        
        # Add to memory
        self.rejected_matches[key] = {
            'kalshi_ticker': kalshi_ticker,
            'poly_condition_id': poly_condition_id,
            'rejected_by': rejected_by,
            'rejected_at': datetime.now().isoformat(),
            'reason': reason
        }
        
        # Remove from pending if exists
        if key in self.pending_matches:
            del self.pending_matches[key]
            self._save_pending_matches()
        
        # Append to CSV
        with open(self.rejected_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                kalshi_ticker, poly_condition_id, rejected_by,
                datetime.now().isoformat(), reason
            ])
        
        logger.info(f"❌ Added rejected match: {kalshi_ticker} ↔ {poly_condition_id} ({reason})")
    
    def add_pending_match(self, kalshi_ticker: str, poly_condition_id: str,
                         kalshi_question: str, poly_question: str,
                         confidence: float, notes: str = ''):
        """Add a match pending verification"""
        key = f"{kalshi_ticker}|{poly_condition_id}"
        
        # Don't add if already processed
        if key in self.verified_matches or key in self.rejected_matches:
            return False
        
        # Add to pending
        self.pending_matches[key] = {
            'kalshi_ticker': kalshi_ticker,
            'poly_condition_id': poly_condition_id,
            'kalshi_question': kalshi_question,
            'poly_question': poly_question,
            'confidence': confidence,
            'notes': notes,
            'added_at': datetime.now().isoformat()
        }
        
        self._save_pending_matches()
        logger.info(f"⏳ Added pending match: {kalshi_ticker} ↔ {poly_condition_id}")
        return True
    
    def _save_pending_matches(self):
        """Save pending matches to JSON"""
        with open(self.pending_file, 'w') as f:
            json.dump(self.pending_matches, f, indent=2)
    
    def get_pending_matches(self) -> List[Dict]:
        """Get all pending matches for verification"""
        return list(self.pending_matches.values())
    
    def get_stats(self) -> Dict:
        """Get statistics about matches"""
        return {
            'verified': len([m for m in self.verified_matches.values() if m.get('active') == 'true']),
            'rejected': len(self.rejected_matches),
            'pending': len(self.pending_matches),
            'total_processed': len(self.verified_matches) + len(self.rejected_matches)
        }
    
    def deactivate_match(self, kalshi_ticker: str, poly_condition_id: str):
        """Deactivate a verified match (e.g., if contracts expire)"""
        key = f"{kalshi_ticker}|{poly_condition_id}"
        if key in self.verified_matches:
            self.verified_matches[key]['active'] = 'false'
            # TODO: Update CSV file
            logger.info(f"🔒 Deactivated match: {kalshi_ticker} ↔ {poly_condition_id}")
