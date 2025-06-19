#!/usr/bin/env python3
"""
Discord Clickable Execution System
Creates clickable links in Discord that execute trades when clicked
"""

import os
from flask import Flask, request, jsonify, render_template_string
from threading import Thread
import time
import asyncio
from datetime import datetime
from alerts.one_click_execution import OneClickExecutor

# Create Flask app for handling web requests
app = Flask(__name__)
executor = OneClickExecutor()

# Simple HTML template for execution confirmation
EXECUTION_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Arbitrage Trade Execution</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px; 
            margin: 50px auto; 
            padding: 20px;
            background: #2f3136;
            color: #dcddde;
        }
        .card {
            background: #36393f;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #00ff00;
        }
        .profit { color: #00ff00; font-weight: bold; font-size: 1.2em; }
        .danger { color: #ff6b6b; }
        .button {
            background: #5865f2;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            margin: 10px 5px;
            text-decoration: none;
            display: inline-block;
        }
        .button:hover { background: #4752c4; }
        .button.danger { background: #ed4245; }
        .button.danger:hover { background: #c53030; }
        .details {
            background: #40444b;
            padding: 15px;
            border-radius: 4px;
            margin: 15px 0;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        .loading {
            text-align: center;
            padding: 20px;
        }
        .success { border-left-color: #00ff00; }
        .error { border-left-color: #ff6b6b; }
    </style>
</head>
<body>
    <div class="card {{ status }}">
        <h2>🚀 Arbitrage Trade Execution</h2>
        
        {% if not executed %}
        <h3>{{ contract_name }}</h3>
        <div class="profit">Estimated Profit: ${{ "%.2f"|format(profit) }}</div>
        <div class="details">
            <strong>Execution Plan:</strong><br>
            • Buy {{ buy_platform }}: {{ volume }} contracts @ ${{ "%.3f"|format(buy_price) }}<br>
            • Sell {{ sell_platform }}: {{ volume }} contracts @ ${{ "%.3f"|format(sell_price) }}<br>
            • Net per contract: ${{ "%.3f"|format(profit_per_contract) }}<br>
            • ROI: {{ "%.1f"|format(roi) }}%
        </div>
        
        <div class="danger">
            ⚠️ <strong>Warning:</strong> This will execute REAL trades with REAL money!<br>
            Testing mode: {{ "✅ ON" if testing_mode else "❌ OFF" }}
        </div>
        
        <div style="margin-top: 20px;">
            <a href="/execute/{{ opportunity_id }}" class="button" onclick="return confirm('Execute this trade for ${{ \"%.2f\"|format(profit) }} profit?')">
                🚀 EXECUTE TRADE
            </a>
            <a href="/reject/{{ opportunity_id }}" class="button danger">
                ❌ REJECT
            </a>
        </div>
        
        {% else %}
        
        {% if success %}
        <h3>✅ Trade Executed Successfully!</h3>
        <div class="profit">Actual Profit: ${{ "%.2f"|format(actual_profit) }}</div>
        <div class="details">
            <strong>Execution Results:</strong><br>
            • Kalshi Order: {{ kalshi_status }}<br>
            • IBKR Order: {{ ibkr_status }}<br>
            • Estimated: ${{ "%.2f"|format(estimated_profit) }}<br>
            • Actual: ${{ "%.2f"|format(actual_profit) }}<br>
            • Difference: ${{ "%.2f"|format(actual_profit - estimated_profit) }}
        </div>
        {% else %}
        <h3>❌ Trade Execution Failed</h3>
        <div class="details">
            <strong>Errors:</strong><br>
            {% for error in errors %}
            • {{ error }}<br>
            {% endfor %}
        </div>
        {% endif %}
        
        {% endif %}
        
        <p><small>Trade ID: {{ opportunity_id }}</small></p>
    </div>
    
    {% if not executed %}
    <script>
        // Auto-refresh every 30 seconds to check if executed elsewhere
        setTimeout(() => location.reload(), 30000);
    </script>
    {% endif %}
</body>
</html>
"""

@app.route('/trade/<opportunity_id>')
def show_trade(opportunity_id):
    """Show trade details and execution options"""
    
    if opportunity_id not in executor.pending_requests:
        return "Trade opportunity not found or expired", 404
    
    request_data = executor.pending_requests[opportunity_id]
    
    if request_data.executed:
        # Show execution results
        results = request_data.execution_results or {}
        return render_template_string(EXECUTION_PAGE,
            opportunity_id=opportunity_id,
            contract_name=request_data.contract_name,
            executed=True,
            success=results.get('success', False),
            actual_profit=results.get('actual_profit', 0),
            estimated_profit=request_data.estimated_profit,
            kalshi_status="✅ Success" if results.get('kalshi_order', {}).get('success') else "❌ Failed",
            ibkr_status="✅ Success" if results.get('ibkr_order', {}).get('success') else "❌ Failed",
            errors=results.get('errors', []),
            status='success' if results.get('success') else 'error'
        )
    else:
        # Show execution options
        profit_per_contract = request_data.estimated_profit / request_data.volume if request_data.volume > 0 else 0
        investment = request_data.volume * max(request_data.buy_price, request_data.sell_price)
        roi = (request_data.estimated_profit / investment * 100) if investment > 0 else 0
        
        return render_template_string(EXECUTION_PAGE,
            opportunity_id=opportunity_id,
            contract_name=request_data.contract_name,
            profit=request_data.estimated_profit,
            volume=request_data.volume,
            buy_platform=request_data.buy_platform,
            sell_platform=request_data.sell_platform,
            buy_price=request_data.buy_price,
            sell_price=request_data.sell_price,
            profit_per_contract=profit_per_contract,
            roi=roi,
            testing_mode=executor.testing_mode,
            executed=False
        )

@app.route('/execute/<opportunity_id>')
def execute_trade(opportunity_id):
    """Execute the trade when link is clicked"""
    
    if opportunity_id not in executor.pending_requests:
        return "Trade opportunity not found", 404
    
    request_data = executor.pending_requests[opportunity_id]
    
    if request_data.executed:
        return f"Trade {opportunity_id} already executed", 400
    
    # Execute the trade asynchronously
    def run_execution():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(executor.execute_arbitrage_trade(opportunity_id))
        loop.close()
    
    # Start execution in background
    execution_thread = Thread(target=run_execution)
    execution_thread.start()
    
    # Return immediate response
    return render_template_string("""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; background: #2f3136; color: #dcddde;">
        <h2>🚀 Executing Trade...</h2>
        <p>Trade {{ opportunity_id }} is being executed.</p>
        <p>This page will automatically refresh to show results.</p>
        <div class="loading">⏳ Please wait...</div>
        <script>
            setTimeout(() => location.href = '/trade/{{ opportunity_id }}', 3000);
        </script>
    </div>
    """, opportunity_id=opportunity_id)

@app.route('/reject/<opportunity_id>')
def reject_trade(opportunity_id):
    """Reject/cancel the trade"""
    
    if opportunity_id in executor.pending_requests:
        del executor.pending_requests[opportunity_id]
        return render_template_string("""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; background: #2f3136; color: #dcddde;">
            <h2>❌ Trade Rejected</h2>
            <p>Trade {{ opportunity_id }} has been cancelled.</p>
        </div>
        """, opportunity_id=opportunity_id)
    else:
        return "Trade not found", 404

def start_web_server():
    """Start the web server in background"""
    app.run(host='0.0.0.0', port=5000, debug=False)

# Enhanced OneClickExecutor with web links
class WebExecutor(OneClickExecutor):
    """Extended executor that creates web links for Discord"""
    
    def __init__(self):
        super().__init__()
        
        # Start web server in background
        web_thread = Thread(target=start_web_server, daemon=True)
        web_thread.start()
        
        print("🌐 Web server started on http://localhost:5000")
        time.sleep(1)  # Give server time to start
    
    def _create_execution_embed(self, request):
        """Create Discord embed with clickable links instead of buttons"""
        
        # Calculate metrics
        profit_per_contract = request.estimated_profit / request.volume if request.volume > 0 else 0
        investment_required = request.volume * max(request.buy_price, request.sell_price)
        roi_percent = (request.estimated_profit / investment_required * 100) if investment_required > 0 else 0
        
        # Determine color
        if request.estimated_profit >= 50:
            color = 0x00FF00  # Green
        elif request.estimated_profit >= 20:
            color = 0xFFFF00  # Yellow  
        else:
            color = 0xFFA500  # Orange
        
        # Create web URLs
        base_url = "http://localhost:5000"  # Change to your public URL if deployed
        trade_url = f"{base_url}/trade/{request.opportunity_id}"
        execute_url = f"{base_url}/execute/{request.opportunity_id}"
        reject_url = f"{base_url}/reject/{request.opportunity_id}"
        
        embed_data = {
            "content": f"🚨 **ARBITRAGE OPPORTUNITY READY** 🚨",
            "embeds": [{
                "title": f"💎 {request.contract_name}",
                "description": f"**PROFIT: ${request.estimated_profit:.2f}** ({roi_percent:.1f}% ROI)",
                "color": color,
                "fields": [
                    {
                        "name": "🔄 Execution Plan",
                        "value": f"**Buy** {request.buy_platform}: {request.volume} @ ${request.buy_price:.3f}\n"
                                f"**Sell** {request.sell_platform}: {request.volume} @ ${request.sell_price:.3f}\n"
                                f"**Net per contract**: ${profit_per_contract:.3f}",
                        "inline": False
                    },
                    {
                        "name": "💰 Financial Impact",
                        "value": f"Investment: ${investment_required:.2f}\n"
                                f"Expected profit: **${request.estimated_profit:.2f}**\n"
                                f"ROI: **{roi_percent:.1f}%**",
                        "inline": True
                    },
                    {
                        "name": "📊 Risk Assessment",
                        "value": f"Volume: {request.volume} contracts\n"
                                f"Daily trades: {self.daily_trades}\n"
                                f"Daily P&L: ${self.daily_pnl:.2f}",
                        "inline": True
                    },
                    {
                        "name": "🎯 One-Click Execution",
                        "value": f"**[🚀 EXECUTE TRADE]({execute_url})**\n"
                                f"**[📊 VIEW DETAILS]({trade_url})**\n"
                                f"**[❌ REJECT]({reject_url})**",
                        "inline": False
                    },
                    {
                        "name": "⚠️ Important",
                        "value": f"Testing mode: {'✅ ON' if self.testing_mode else '❌ OFF'}\n"
                                f"Click links above to execute REAL trades",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"ID: {request.opportunity_id} | Expires in 5 minutes"
                },
                "timestamp": datetime.utcnow().isoformat()
            }]
        }
        
        return embed_data

def test_web_execution():
    """Test the web-based execution system"""
    
    print("🌐 Testing web-based execution system...")
    
    # Create web executor
    web_executor = WebExecutor()
    
    # Create test opportunity
    test_opportunity = {
        "contract_name": "FED-25DEC-T3.50",
        "buy_platform": "Kalshi",
        "sell_platform": "IBKR", 
        "buy_ticker": "FED-25DEC-T3.50",
        "sell_ticker": "FF Dec25 3.50 Call",
        "volume": 10,
        "buy_price": 0.485,
        "sell_price": 0.523,
        "estimated_profit": 37.50
    }
    
    # Send execution alert with clickable links
    opportunity_id = web_executor.send_execution_alert(test_opportunity)
    
    print(f"✅ Web execution alert sent!")
    print(f"🌐 View trade details: http://localhost:5000/trade/{opportunity_id}")
    print(f"🚀 Execute directly: http://localhost:5000/execute/{opportunity_id}")
    print(f"❌ Reject trade: http://localhost:5000/reject/{opportunity_id}")
    print(f"\n📱 Check Discord for clickable links!")
    
    # Keep server running
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down web server...")

if __name__ == "__main__":
    test_web_execution()