#!/usr/bin/env python3
"""
Market hours utility for Central Time operations
"""
from datetime import datetime, time
import pytz

def is_market_hours():
    """Check if currently within trading hours (8:30 AM - 2:45 PM CST)"""
    central = pytz.timezone('US/Central')
    now = datetime.now(central)
    
    # Check if weekend
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False, "Weekend - Markets Closed"
    
    # Trading hours: 8:30 AM - 2:45 PM CST (market close 3:00 PM)
    market_open = time(8, 30)
    market_close = time(14, 45)  # Stop 15 min before close for execution
    current_time = now.time()
    
    if market_open <= current_time <= market_close:
        return True, "Market Open"
    else:
        return False, f"Outside Trading Hours (Current: {current_time.strftime('%I:%M %p')} CST)"

def get_next_spy_expiry():
    """Get next available SPY expiry (Mon/Wed/Fri)"""
    from datetime import date, timedelta
    
    today = date.today()
    spy_days = [0, 2, 4]  # Monday, Wednesday, Friday
    
    # Find next expiry
    for i in range(7):
        check_date = today + timedelta(days=i)
        if check_date.weekday() in spy_days:
            if i == 0 and not is_market_hours()[0]:
                # If today is expiry but market closed, skip to next
                continue
            return check_date.strftime("%Y%m%d"), i
    
    return today.strftime("%Y%m%d"), 0

if __name__ == "__main__":
    print("🕐 Market Hours Check")
    print("=" * 40)
    
    is_open, status = is_market_hours()
    print(f"Status: {status}")
    print(f"Market Open: {'✅ YES' if is_open else '❌ NO'}")
    
    next_expiry, days_away = get_next_spy_expiry()
    print(f"\nNext SPY Expiry: {next_expiry} ({days_away} days away)")
    
    # Show schedule
    print("\n📅 Trading Schedule (CST):")
    print("Monday-Friday: 8:30 AM - 2:45 PM")
    print("Market Close: 3:00 PM CST")
    print("SPY Options Expiry: Mon, Wed, Fri")
