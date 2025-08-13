# IBKR Market Data Troubleshooting Guide

## Current Issue
- Getting errors 10089 and 10091 for SPY options data
- You have OPRA ($1.50/month) and US Securities Snapshot ($10/month) subscriptions
- Market is currently closed (after 3:00 PM CST)

## Troubleshooting Steps

### 1. Check Market Data Permissions in TWS
In TWS, go to:
- **Account Management** -> **Account Information** -> **Market Data Subscriptions**
- Verify "OPRA" shows as "Subscribed" with "Professional" or "Non-Professional" status
- Check if there's a separate "API" column that needs enabling

### 2. Accept Market Data Agreements
In TWS:
- **Global Configuration** -> **API** -> **Settings**
- Click "Market Data" tab
- Look for any pending agreements to sign
- Especially check for "Options Price Reporting Authority (OPRA)" agreement

### 3. Enable API Market Data
In TWS:
- **Account** -> **Trade Configuration** -> **Market Data**
- Ensure "Enable market data for API clients" is checked

### 4. Check Professional vs Non-Professional Status
- OPRA has different tiers for Professional vs Non-Professional
- Ensure your status matches your subscription

## Working Around After-Hours Limitations

Since market is closed, live data might not be available. Options:

1. **Use Snapshot Data** (one-time price fetch)
   - Modify requests to use snapshot=True
   - Works better after hours

2. **Test During Market Hours**
   - Best testing: 8:30 AM - 2:45 PM CST
   - Full live data available

3. **Use Paper Trading Account**
   - Port 7497 instead of 7496
   - Simulated data available 24/7

## Next Steps

1. **If market data still doesn't work:**
   - Contact IBKR support about API access for subscriptions
   - May need to wait 24 hours for subscriptions to fully activate
   - Check if additional "API Streaming" subscription needed

2. **Once market data works:**
   - Build the cross-asset scanner
   - Test during market hours for best results
   - Start with snapshot data if needed

3. **Alternative approach:**
   - Build scanner with simulated data first
   - Switch to live data when resolved
