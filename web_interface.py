#!/usr/bin/env python3
"""
Simple Web Interface for One-Click Arbitrage Execution
Provides mobile-friendly interface for Discord → Laptop execution

FEATURES:
- Mobile-responsive design
- One-click execution buttons
- Real-time opportunity display
- Emergency halt controls
- Performance dashboard
"""

from flask import Flask, render_template_string, request, jsonify, redirect
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List

app = Flask(__name__)

# Global state
execution_handler = None
current_opportunities = {}
performance_stats = {
    'total_opportunities': 0,
    'total_profit': 0.0,
    'executed_trades': 0,
    'last_update': datetime.now().isoformat()
}

# Mobile-friendly HTML template
MOBILE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Arbitrage Bot - One-Click Execution</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: white; min-height: 100vh;
        }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #00ff00; font-size: 28px; margin-bottom: 10px; }
        .status { background: #333; padding: 15px; border-radius: 12px; margin-bottom: 20px; }
        .opportunity { 
            background: #2a2a2a; border-radius: 12px; padding: 20px; margin-bottom: 20px;
            border-left: 4px solid #00ff00; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .profit { color: #00ff00; font-size: 24px; font-weight: bold; margin-bottom: 15px; }
        .details { margin-bottom: 15px; line-height: 1.6; }
        .details div { margin-bottom: 8px; }
        .label { color: #888; font-size: 14px; }
        .value { color: white; font-weight: 500; }
        .buttons { display: flex; gap: 10px; flex-wrap: wrap; }
        .btn {
            flex: 1; min-width: 120px; padding: 15px; border: none; border-radius: 8px;
            font-size: 16px; font-weight: bold; cursor: pointer; text-decoration: none;
            text-align: center; transition: all 0.3s ease;
        }
        .btn-execute { background: #00ff00; color: black; }
        .btn-execute:hover { background: #00cc00; transform: translateY(-2px); }
        .btn-decline { background: #ff3333; color: white; }
        .btn-decline:hover { background: #cc0000; transform: translateY(-2px); }
        .btn-details { background: #0066ff; color: white; }
        .btn-details:hover { background: #0052cc; transform: translateY(-2px); }
        .btn-halt { background: #ff6600; color: white; width: 100%; margin-top: 20px; }
        .performance { background: #1a3d1a; border-radius: 12px; padding: 20px; margin-top: 30px; }
        .perf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .perf-item { text-align: center; }
        .perf-value { font-size: 20px; font-weight: bold; color: #00ff00; }
        .perf-label { font-size: 12px; color: #888; margin-top: 5px; }
        .no-opportunities { 
            text-align: center; padding: 40px; color: #888;
            background: #2a2a2a; border-radius: 12px;
        }
        .loading { text-align: center; padding: 20px; }
        .spinner { 
            border: 3px solid #333; border-top: 3px solid #00ff00;
            border-radius: 50%; width: 30px; height: 30px;
            animation: spin 1s linear infinite; margin: 0 auto;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .timestamp { font-size: 12px; color: #666; margin-top: 10px; }
        @media (max-width: 480px) {
            .buttons { flex-direction: column; }
            .btn { min-width: auto; }
            .perf-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Arbitrage Bot</h1>
            <div class="status">
                <div class="label">Status</div>
                <div class="value">{{ status }}</div>
                <div class="timestamp">Last updated: {{ last_update }}</div>
            </div>
        </div>

        {% if opportunities %}
            {% for opp in opportunities %}
            <div class="opportunity">
                <div class="profit">💰 ${{ "%.2f"|format(opp.guaranteed_profit) }} Profit</div>
                
                <div class="details">
                    <div><span class="label">Contract:</span> <span class="value">{{ opp.kalshi_ticker }}</span></div>
                    <div><span class="label">Strategy:</span> <span class="value">{{ opp.strategy_type }}</span></div>
                    <div><span class="label">Profit %:</span> <span class="value">{{ "%.1f"|format(opp.profit_percentage) }}%</span></div>
                    <div><span class="label">Hourly Rate:</span> <span class="value">${{ "%.0f"|format(opp.profit_per_hour) }}/hour</span></div>
                    <div><span class="label">Confidence:</span> <span class="value">{{ "%.0f"|format(opp.match_confidence * 100) }}%</span></div>
                    <div><span class="label">Recommendation:</span> <span class="value">{{ opp.recommendation }}</span></div>
                </div>

                <div class="buttons">
                    <a href="/execute/{{ opp.opportunity_id }}" class="btn btn-execute">✅ EXECUTE</a>
                    <a href="/decline/{{ opp.opportunity_id }}" class="btn btn-decline">❌ DECLINE</a>
                    <a href="/details/{{ opp.opportunity_id }}" class="btn btn-details">📊 DETAILS</a>
                </div>
                
                <div class="timestamp">ID: {{ opp.opportunity_id }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="no-opportunities">
                <h3>😴 No Active Opportunities</h3>
                <p>The bot is scanning for profitable arbitrage opportunities...</p>
                <div class="loading">
                    <div class="spinner"></div>
                </div>
            </div>
        {% endif %}

        <div class="performance">
            <h3 style="text-align: center; margin-bottom: 20px;">📊 Performance</h3>
            <div class="perf-grid">
                <div class="perf-item">
                    <div class="perf-value">{{ total_opportunities }}</div>
                    <div class="perf-label">Opportunities Found</div>
                </div>
                <div class="perf-item">
                    <div class="perf-value">${{ "%.2f"|format(total_profit) }}</div>
                    <div class="perf-label">Total Profit Potential</div>
                </div>
                <div class="perf-item">
                    <div class="perf-value">{{ executed_trades }}</div>
                    <div class="perf-label">Executed Trades</div>
                </div>
                <div class="perf-item">
                    <div class="perf-value">{{ "%.1f"|format((total_profit/1000)*100) }}%</div>
                    <div class="perf-label">Daily Goal Progress</div>
                </div>
            </div>
        </div>

        <button onclick="emergencyHalt()" class="btn btn-halt">🛑 EMERGENCY HALT</button>
        
        <div style="text-align: center; margin-top: 30px; font-size: 12px; color: #666;">
            Auto-refresh every 30 seconds
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => {
            window.location.reload();
        }, 30000);

        function emergencyHalt() {
            if (confirm('Are you sure you want to halt all trading?')) {
                fetch('/halt', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        window.location.reload();
                    });
            }
        }

        // Add click feedback
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                if (this.href && !this.href.includes('/halt')) {
                    e.preventDefault();
                    this.style.transform = 'scale(0.95)';
                    this.style.opacity = '0.7';
                    setTimeout(() => {
                        window.location.href = this.href;
                    }, 200);
                }
            });
        });
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    """Main dashboard showing current opportunities"""
    opportunities = list(current_opportunities.values())
    
    return render_template_string(MOBILE_TEMPLATE,
        opportunities=opportunities,
        status="🟢 ACTIVE" if not execution_handler or execution_handler.execution_enabled else "🔴 HALTED",
        last_update=datetime.now().strftime("%H:%M:%S"),
        total_opportunities=performance_stats['total_opportunities'],
        total_profit=performance_stats['total_profit'],
        executed_trades=performance_stats['executed_trades']
    )

@app.route('/execute/<opportunity_id>')
async def execute_opportunity(opportunity_id):
    """Execute arbitrage opportunity"""
    if not execution_handler:
        return jsonify({'success': False, 'message': 'Execution handler not available'})
    
    try:
        result = await execution_handler.execute_arbitrage(opportunity_id)
        
        if result['success']:
            performance_stats['executed_trades'] += 1
            if opportunity_id in current_opportunities:
                del current_opportunities[opportunity_id]
        
        # Return simple success page
        success_html = f"""
        <html>
        <head>
            <title>Execution Result</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: white; text-align: center; }}
                .result {{ max-width: 400px; margin: 50px auto; padding: 30px; background: #2a2a2a; border-radius: 12px; }}
                .success {{ color: #00ff00; font-size: 48px; }}
                .failed {{ color: #ff3333; font-size: 48px; }}
                .btn {{ padding: 15px 30px; background: #0066ff; color: white; text-decoration: none; border-radius: 8px; display: inline-block; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="result">
                <div class="{'success' if result['success'] else 'failed'}">
                    {'✅' if result['success'] else '❌'}
                </div>
                <h2>{'Execution Successful!' if result['success'] else 'Execution Failed'}</h2>
                <p>{result['message']}</p>
                <p><small>{result['details']}</small></p>
                <a href="/" class="btn">← Back to Dashboard</a>
            </div>
        </body>
        </html>
        """
        return success_html
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/decline/<opportunity_id>')
def decline_opportunity(opportunity_id):
    """Decline an opportunity"""
    if opportunity_id in current_opportunities:
        del current_opportunities[opportunity_id]
    
    return redirect('/')

@app.route('/details/<opportunity_id>')
def opportunity_details(opportunity_id):
    """Show detailed opportunity analysis"""
    opportunity = current_opportunities.get(opportunity_id)
    
    if not opportunity:
        return redirect('/')
    
    details_html = f"""
    <html>
    <head>
        <title>Opportunity Details</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: white; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .detail-item {{ background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 8px; }}
            .profit {{ color: #00ff00; font-size: 24px; font-weight: bold; }}
            .btn {{ padding: 15px 30px; background: #0066ff; color: white; text-decoration: none; border-radius: 8px; display: inline-block; margin: 10px 5px; }}
            .execute {{ background: #00ff00; color: black; }}
            .decline {{ background: #ff3333; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Opportunity Details</h1>
            
            <div class="detail-item">
                <h3>💰 Financial Analysis</h3>
                <div class="profit">${opportunity.guaranteed_profit:.2f} Guaranteed Profit</div>
                <p>Profit Percentage: {opportunity.profit_percentage:.2f}%</p>
                <p>Hourly Rate: ${opportunity.profit_per_hour:.0f}/hour</p>
                <p>Trade Size: ${opportunity.trade_size_usd:.0f}</p>
            </div>
            
            <div class="detail-item">
                <h3>📋 Strategy Details</h3>
                <p>Strategy: {opportunity.strategy_type}</p>
                <p>Buy: {opportunity.buy_platform} {opportunity.buy_side} @ ${opportunity.kalshi_execution_price:.3f}</p>
                <p>Sell: {opportunity.sell_platform} {opportunity.sell_side} @ ${opportunity.polymarket_execution_price:.3f}</p>
            </div>
            
            <div class="detail-item">
                <h3>🎯 Risk Analysis</h3>
                <p>Match Confidence: {opportunity.match_confidence:.1%}</p>
                <p>Liquidity Score: {opportunity.liquidity_score:.0f}/100</p>
                <p>Execution Certainty: {opportunity.execution_certainty:.0f}/100</p>
                <p>Time to Expiry: {opportunity.time_to_expiry_hours:.1f} hours</p>
            </div>
            
            <div class="detail-item">
                <h3>📊 Slippage Analysis</h3>
                <p>Kalshi Slippage: {opportunity.kalshi_slippage_percent:.2f}%</p>
                <p>Polymarket Slippage: {opportunity.polymarket_slippage_percent:.2f}%</p>
            </div>
            
            <div class="detail-item">
                <h3>🤖 Recommendation</h3>
                <p><strong>{opportunity.recommendation}</strong></p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/execute/{opportunity_id}" class="btn execute">✅ EXECUTE TRADE</a>
                <a href="/decline/{opportunity_id}" class="btn decline">❌ DECLINE</a>
                <a href="/" class="btn">← Back to Dashboard</a>
            </div>
            
            <div style="margin-top: 30px; font-size: 12px; color: #666;">
                <p>ID: {opportunity_id}</p>
                <p>Kalshi: {opportunity.kalshi_question[:100]}...</p>
                <p>Polymarket: {opportunity.polymarket_question[:100]}...</p>
            </div>
        </div>
    </body>
    </html>
    """
    return details_html

@app.route('/halt', methods=['POST'])
def emergency_halt():
    """Emergency halt all trading"""
    if execution_handler:
        message = execution_handler.emergency_halt()
    else:
        message = "🛑 Emergency halt activated (handler not available)"
    
    return jsonify({'success': True, 'message': message})

@app.route('/api/opportunities')
def api_opportunities():
    """API endpoint for current opportunities"""
    return jsonify({
        'opportunities': [opp.__dict__ for opp in current_opportunities.values()],
        'performance': performance_stats,
        'status': 'active' if not execution_handler or execution_handler.execution_enabled else 'halted'
    })

def update_opportunities(opportunities):
    """Update current opportunities from the bot"""
    global current_opportunities, performance_stats
    
    # Clear old opportunities
    current_opportunities.clear()
    
    # Add new opportunities
    for opp in opportunities:
        current_opportunities[opp.opportunity_id] = opp
    
    # Update performance stats
    performance_stats['total_opportunities'] += len(opportunities)
    performance_stats['total_profit'] += sum(opp.guaranteed_profit for opp in opportunities)
    performance_stats['last_update'] = datetime.now().isoformat()

def run_web_interface(port=8080, execution_handler_instance=None):
    """Run the web interface"""
    global execution_handler
    execution_handler = execution_handler_instance
    
    print(f"🌐 Starting web interface on http://localhost:{port}")
    print(f"📱 Mobile-friendly interface ready for one-click execution")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    print("🌐 Testing Web Interface...")
    
    # Create mock opportunities for testing
    from dataclasses import dataclass
    from datetime import datetime
    
    @dataclass
    class MockOpportunity:
        opportunity_id: str = "TEST_WEB_001"
        kalshi_ticker: str = "NASDAQ100-24DEC31"
        guaranteed_profit: float = 35.75
        profit_percentage: float = 17.9
        profit_per_hour: float = 1250.0
        strategy_type: str = "YES_ARBITRAGE"
        buy_platform: str = "Kalshi"
        sell_platform: str = "Polymarket"
        buy_side: str = "YES"
        sell_side: str = "NO"
        kalshi_execution_price: float = 0.465
        polymarket_execution_price: float = 0.548
        match_confidence: float = 0.94
        liquidity_score: float = 88.0
        execution_certainty: float = 95.0
        time_to_expiry_hours: float = 18.5
        kalshi_slippage_percent: float = 0.9
        polymarket_slippage_percent: float = 1.1
        recommendation: str = "EXECUTE_IMMEDIATELY"
        kalshi_question: str = "Will NASDAQ-100 close above 19000 on Dec 31?"
        polymarket_question: str = "NASDAQ-100 above 19000 at year end?"
        trade_size_usd: float = 200.0
    
    # Test with mock data
    mock_opp = MockOpportunity()
    update_opportunities([mock_opp])
    
    run_web_interface(port=8080)
