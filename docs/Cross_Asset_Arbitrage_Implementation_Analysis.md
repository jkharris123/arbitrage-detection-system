# Cross-Asset Arbitrage Implementation Analysis
## Kalshi vs Options Markets Strategy

**Date:** August 10, 2025  
**Version:** 1.1  
**Purpose:** Technical assessment for cross-asset arbitrage implementation  
**Update:** Added IBKR actual commission structure and real-world costs

---

## Executive Summary

This document analyzes the existing arbitrage bot infrastructure and outlines requirements for implementing cross-asset arbitrage between Kalshi prediction markets and traditional options markets. The strategy targets **5-10% typical edge** compared to 0.01% in traditional arbitrage, with expected daily profits of **$500-1,500**.

**Key Finding:** Approximately 60% of existing infrastructure can be reused, with the main development effort focused on options data integration and cross-asset matching logic.

---

## 1. Current System Architecture

### 1.1 Existing Components (Reusable)

#### **Data Collection Layer** ✅
- **kalshi_client.py**: Fully functional API client with:
  - Authentication and RSA signing
  - Market data retrieval
  - Order placement
  - Fee calculation
  - Real-time pricing
- **ibkr_client.py**: Currently configured for ForecastEx, but architecture supports modification for options data
- **discord_bot.py**: Alert and notification system

#### **Detection & Matching Layer** ✅
- **detector.py**: Core arbitrage detection logic with:
  - Volume optimization algorithm
  - Slippage calculation
  - Profit maximization framework
  - CSV tracking system
- **liquidity_optimizer.py**: Volume-based optimization (directly applicable)
- **verified_matches_manager.py**: Match caching system

#### **Execution Infrastructure** ✅
- **fully_automated_enhanced.py**: Automated execution framework
- Discord integration for alerts and confirmations
- Position tracking and daily summaries
- Risk management controls

### 1.2 Components Requiring Modification

#### **IBKR Client Transformation** 🔧
Current state: ForecastEx contracts
Required state: SPY/SPX options data

Key modifications needed:
```python
# FROM:
contract.secType = "OPT"
contract.exchange = "FORECASTX"

# TO:
contract.secType = "OPT"
contract.exchange = "SMART"  # For SPY options
contract.symbol = "SPY"
contract.currency = "USD"
```

#### **Matching Logic Enhancement** 🔧
Current: Text-based contract matching
Required: Price level and expiry matching

---

## 2. New Components Required

### 2.1 Options Data Module 🆕
**File:** `src/data_collectors/options_data_client.py`

Required functionality:
- Real-time options chain retrieval
- Greeks calculation (delta, gamma, theta, vega)
- Implied volatility extraction
- Bid/ask spread tracking
- Strike/expiry filtering

### 2.2 Cross-Asset Matcher 🆕
**File:** `src/matchers/cross_asset_matcher.py`

Core logic:
```python
def match_kalshi_to_options(kalshi_contract, options_chain):
    """
    Match Kalshi S&P level to appropriate option spread
    
    Example:
    Kalshi: "S&P closes above 6400" → SPY 640/641 spread
    """
    target_level = extract_sp_level(kalshi_contract)
    spy_strike = target_level / 10  # S&P to SPY conversion
    
    return find_optimal_spread(options_chain, spy_strike)
```

### 2.3 Settlement Risk Manager 🆕
**File:** `src/risk/settlement_manager.py`

Critical functionality:
- Track SPY vs Kalshi settlement times
- Auto-close positions before 3:50 PM
- Handle assignment risk
- Emergency close procedures

### 2.4 Probability Extractor 🆕
**File:** `src/analytics/probability_calculator.py`

Black-Scholes implementation for:
- Extract implied probabilities from options
- Compare with Kalshi probabilities
- Identify divergences > 5%

### 2.5 Commission Tracker 🆕  
**File:** `src/analytics/commission_tracker.py`

Real-time commission monitoring:
- Pull actual commissions from IBKR executions
- Track commission impact on profitability
- Alert if commissions exceed thresholds
- Monthly volume tracking for tier optimization

```python
class CommissionTracker:
    def get_ibkr_commission(self, exec_id):
        """Pull actual commission from execution"""
        # Uses commissionReport() API method
        
    def calculate_total_costs(self, trade):
        """Sum all costs: Kalshi fees + IBKR commissions"""
        kalshi_fee = self.get_kalshi_fee(trade.price, trade.size)
        ibkr_comm = self.get_ibkr_commission(trade.exec_id)
        return kalshi_fee + ibkr_comm + slippage
        
    def track_monthly_volume(self):
        """Monitor volume for tier improvements"""
        # At 10k contracts/month, save $0.15/contract
```

---

## 3. Strategy Implementation from Discussion

### 3.1 Core Strategy Logic

**Arbitrage Condition:**
```
Kalshi_Probability != Options_Implied_Probability
AND |Difference| > Transaction_Costs + Required_Edge (5%)
```

**Example from PM's Trade:**
- Kalshi NO on 6350+: 64% probability (cost $0.64)
- SPY 634/635 Call Spread: ~45% implied probability
- **Edge: 19% probability difference**

### 3.2 Position Structuring

**If Kalshi "Under X" is cheap:**
1. Buy Kalshi "Under X" contracts
2. Sell Bear Call Spread at X level

**If Kalshi "Over X" is cheap:**
1. Buy Kalshi "Over X" contracts
2. Sell Bull Put Spread at X level

### 3.3 Optimal Contract Selection

**Target:** 0DTE (same-day expiry)
- SPY weekly options (Mon/Wed/Fri)
- 2-6 hour expiries preferred
- $1-wide spreads for liquidity

### 3.4 IBKR Options Commission Structure (IBKR Pro)

**Tiered Pricing Based on Monthly Volume:**
- **≤ 10,000 contracts**: $0.65/contract
- **10,001-50,000**: $0.50/contract  
- **50,001-100,000**: $0.25/contract
- **≥ 100,001**: $0.15/contract
- **Minimum per order**: $1.00

**Real-World Commission Costs (PM's Experience):**
- **Single spread (2 legs)**: $2-3 total
- **Two spreads (4 legs)**: $4-6 total
- Includes exchange fees, clearing fees, regulatory fees

**Example Calculation for Our Strategy:**
```
Kalshi + SPY Spread Trade:
- Kalshi: ~1.5% of notional (varies by price)
- SPY Spread: $2-3 (2 legs × $0.65 + fees)
- Total cost per arbitrage: ~$3-5 on $100 trade
```

**Commission Data Retrieval:**
```python
# IBKR API methods to get actual commissions:
def get_execution_details(execId):
    """Get commission from execution"""
    # Returns commission field with actual cost
    
def commission_report(execId):
    """Detailed commission breakdown"""
    # Returns:
    # - commission: total commission
    # - currency: USD
    # - realizedPNL: P&L if closing
```

---

## 4. Implementation Roadmap

### Phase 1: Infrastructure (Week 1-2)
- [ ] Modify IBKR client for options data
- [ ] Build options data module
- [ ] Create probability calculator
- [ ] Test data feeds

### Phase 2: Core Logic (Week 2-3)
- [ ] Implement cross-asset matcher
- [ ] Build hedge ratio calculator
- [ ] Create settlement manager
- [ ] Integrate with existing detector

### Phase 3: Execution (Week 3-4)
- [ ] Adapt execution framework
- [ ] Add options order types
- [ ] Implement auto-close logic
- [ ] Test paper trading

### Phase 4: Production (Week 4+)
- [ ] Live testing with small positions
- [ ] Performance monitoring
- [ ] Scale to target size
- [ ] Optimize execution

---

## 5. Code Reuse Analysis

### Directly Reusable (No Changes)
- Discord notification system
- CSV logging infrastructure
- Performance tracking
- Daily summary reports
- Emergency stop controls

### Reusable with Minor Changes
- Kalshi API client (add S&P-specific methods)
- Execution framework (add options support)
- Risk limits (adjust for options margin)

### Major Modifications Required
- IBKR client (switch from ForecastEx to options)
- Matching logic (price levels vs text matching)
- Position management (handle spreads)

### New Development Required
- Options pricing models
- Settlement coordination
- Greeks-based risk management
- Cross-asset position tracking

---

## 6. Risk Considerations

### Technical Risks
- **Data Latency**: Need sub-second options updates
- **Execution Complexity**: Multi-leg orders
- **Settlement Mismatch**: Different close times

### Mitigation Strategies
- Colocated servers for low latency
- Pre-built spread orders
- Automated position closing by 3:45 PM

---

## 7. Expected Performance

### Capital Requirements
- Starting: $25,000 ($10k each platform + margin)
- Optimal: $50,000-100,000

### Profit Targets (Adjusted for Actual Commissions)
- Conservative: $500-750/day (net of $50-100 in commissions)
- Optimal: $1,000-1,500/day (net of $100-200 in commissions)
- Monthly: $10,000-30,000 (net)

### Cost Structure Per Trade
- **Kalshi side**: 1.4%-5.6% of notional (fee schedule)
- **IBKR options side**: $2-3 per spread
- **Total per arbitrage**: $3-5 on typical $100 position
- **Break-even edge needed**: ~5% to cover all costs

### Success Metrics
- Win rate: >95% (true arbitrage)
- Average edge: 5-10% (must exceed ~5% for profitability)
- Execution speed: <30 seconds
- Commission efficiency: Target <0.5% of profit

---

## 8. Competitive Advantages

### Why This Works
1. **Market Segmentation**: Options traders don't monitor Kalshi
2. **Liquidity Constraints**: Too small for institutions
3. **Regulatory Barriers**: Many funds can't trade prediction markets
4. **Technical Complexity**: Requires expertise in both markets

### Sustainability
- Natural moat from complexity
- Limited competition
- Persistent inefficiencies
- First-mover advantage

---

## 9. Next Steps

### Immediate Actions
1. Set up IBKR options data access
2. Create options_data_client.py
3. Build probability calculator
4. Test with historical data

### Week 1 Deliverables
- Working options data feed
- Probability extraction system
- Initial matching algorithm
- Paper trading setup

---

## 10. Conclusion

The existing arbitrage bot provides a solid foundation for cross-asset arbitrage implementation. With approximately 60% code reuse and clear development requirements for the remaining 40%, the project is technically feasible and can be completed within 4-6 weeks.

The strategy offers significantly higher returns than pure prediction market arbitrage while maintaining the core principle of risk-free profit through simultaneous offsetting positions.

**Recommendation:** Proceed with Phase 1 implementation while continuing to profit from existing prediction market arbitrage.

---

**Appendix A: File Structure**
```
arbitrage_bot/
├── src/
│   ├── data_collectors/
│   │   ├── kalshi_client.py (existing)
│   │   ├── ibkr_client.py (modify)
│   │   └── options_data_client.py (new)
│   ├── detectors/
│   │   ├── detector.py (enhance)
│   │   └── cross_asset_detector.py (new)
│   ├── matchers/
│   │   └── cross_asset_matcher.py (new)
│   ├── analytics/
│   │   ├── probability_calculator.py (new)
│   │   └── commission_tracker.py (new)
│   └── risk/
│       └── settlement_manager.py (new)
```

**Appendix B: Key Formulas**
- S&P to SPY conversion: SPY = S&P / 10
- Probability from options: Use Black-Scholes N(d2)
- Profit = Payout - Total_Cost - Fees
- Optimal volume: Test $50-$1000 range