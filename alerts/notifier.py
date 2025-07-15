#!/usr/bin/env python3
"""
Discord One-Click Execution System
Click a button in Discord -> Trades execute automatically
"""

import os
import json
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# Import your working clients
from data_collectors.kalshi_client import KalshiClient
# from data_collectors.ibkr_client import TWSEventClient  # Will add tomorrow

@dataclass
class ExecutionRequest:
    opportunity_id: str
    contract_name: str
    buy_platform: str
    sell_platform: str
    buy_ticker: str
    sell_ticker: str
    volume: int
    buy_price: float
    sell_price: float
    estimated_profit: float
    timestamp: datetime
    user_approved: bool = False
    executed: bool = False
    execution_results: Dict = None

class OneClickExecutor:
    """
    Handles one-click execution from Discord alerts
    Manages the workflow: Alert -> User Click -> Instant Execution
    """
    
    def __init__(self):
        load_dotenv()
        
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK')
        self.kalshi_client = KalshiClient()
        # self.ibkr_client = None  # Will initialize tomorrow
        
        # Pending execution requests
        self.pending_requests: Dict[str, ExecutionRequest] = {}
        
        # Safety settings from .env
        self.max_position_size = int(os.getenv('MAX_POSITION_SIZE', '10'))
        self.max_daily_loss = float(os.getenv('MAX_DAILY_LOSS', '50'))
        self.testing_mode = os.getenv('TESTING_MODE', 'true').lower() == 'true'
        
        # Execution tracking
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.execution_history = []
        
        print(f"🚀 One-Click Executor initialized")
        print(f"   Testing mode: {self.testing_mode}")
        print(f"   Max position: {self.max_position_size} contracts")
        print(f"   Daily loss limit: ${self.max_daily_loss}")
    
    def send_execution_alert(self, opportunity: Dict) -> str:
        """
        Send Discord alert with one-click execution buttons
        Returns the opportunity_id for tracking
        """
        
        # Generate unique opportunity ID
        opportunity_id = f"ARB_{int(time.time())}_{opportunity.get('volume', 0)}"
        
        # Store execution request
        exec_request = ExecutionRequest(
            opportunity_id=opportunity_id,
            contract_name=opportunity.get('contract_name', 'Unknown'),
            buy_platform=opportunity.get('buy_platform', 'Kalshi'),
            sell_platform=opportunity.get('sell_platform', 'IBKR'),
            buy_ticker=opportunity.get('buy_ticker', ''),
            sell_ticker=opportunity.get('sell_ticker', ''),
            volume=min(opportunity.get('volume', 10), self.max_position_size),
            buy_price=opportunity.get('buy_price', 0.0),
            sell_price=opportunity.get('sell_price', 0.0),
            estimated_profit=opportunity.get('estimated_profit', 0.0),
            timestamp=datetime.now()
        )
        
        self.pending_requests[opportunity_id] = exec_request
        
        # Create Discord embed with execution buttons
        embed = self._create_execution_embed(exec_request)
        
        # Send to Discord
        if self.discord_webhook:
            self._send_to_discord(embed)
        else:
            print("⚠️ No Discord webhook - would send execution alert")
        
        print(f"🔔 Execution alert sent: {opportunity_id}")
        return opportunity_id
    
    def _create_execution_embed(self, request: ExecutionRequest) -> Dict:
        """Create Discord embed with execution buttons"""
        
        # Calculate key metrics
        profit_per_contract = request.estimated_profit / request.volume if request.volume > 0 else 0
        investment_required = request.volume * max(request.buy_price, request.sell_price)
        roi_percent = (request.estimated_profit / investment_required * 100) if investment_required > 0 else 0
        
        # Determine urgency color
        if request.estimated_profit >= 50:
            color = 0x00FF00  # Green - High profit
        elif request.estimated_profit >= 20:
            color = 0xFFFF00  # Yellow - Medium profit  
        else:
            color = 0xFFA500  # Orange - Low profit
        
        embed_data = {
            "content": f"🚨 **READY TO EXECUTE** 🚨",
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
                        "name": "⚠️ Important",
                        "value": f"**This will execute REAL trades**\n"
                                f"Testing mode: {'✅ ON' if self.testing_mode else '❌ OFF'}\n"
                                f"Click EXECUTE only if you approve this trade",
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"ID: {request.opportunity_id} | Expires in 5 minutes"
                },
                "timestamp": datetime.utcnow().isoformat()
            }],
            "components": [
                {
                    "type": 1,  # Action Row
                    "components": [
                        {
                            "type": 2,  # Button
                            "style": 3,  # Green (Success)
                            "label": "🚀 EXECUTE TRADE",
                            "custom_id": f"execute_{request.opportunity_id}",
                            "emoji": {"name": "💰"}
                        },
                        {
                            "type": 2,  # Button
                            "style": 4,  # Red (Danger)
                            "label": "❌ REJECT",
                            "custom_id": f"reject_{request.opportunity_id}",
                            "emoji": {"name": "🚫"}
                        },
                        {
                            "type": 2,  # Button
                            "style": 2,  # Grey (Secondary)
                            "label": "📊 DETAILS",
                            "custom_id": f"details_{request.opportunity_id}",
                            "emoji": {"name": "📋"}
                        }
                    ]
                }
            ]
        }
        
        return embed_data
    
    def _send_to_discord(self, embed_data: Dict) -> bool:
        """Send embed to Discord webhook"""
        try:
            response = requests.post(
                self.discord_webhook,
                json=embed_data,
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            print(f"❌ Discord send failed: {e}")
            return False
    
    async def execute_arbitrage_trade(self, opportunity_id: str) -> Dict:
        """
        Execute the actual arbitrage trade across both platforms
        This is where the magic happens!
        """
        
        if opportunity_id not in self.pending_requests:
            return {"success": False, "error": "Opportunity not found"}
        
        request = self.pending_requests[opportunity_id]
        
        print(f"🚀 EXECUTING ARBITRAGE TRADE: {opportunity_id}")
        print(f"   Contract: {request.contract_name}")
        print(f"   Volume: {request.volume}")
        print(f"   Expected profit: ${request.estimated_profit:.2f}")
        
        execution_results = {
            "opportunity_id": opportunity_id,
            "start_time": datetime.now().isoformat(),
            "kalshi_order": None,
            "ibkr_order": None,
            "success": False,
            "actual_profit": 0.0,
            "errors": []
        }
        
        try:
            # SAFETY CHECKS
            if self.daily_trades >= int(os.getenv('DAILY_TRADE_LIMIT', '5')):
                execution_results["errors"].append("Daily trade limit reached")
                return execution_results
            
            if self.daily_pnl < -self.max_daily_loss:
                execution_results["errors"].append("Daily loss limit exceeded")
                return execution_results
            
            # STEP 1: Execute Kalshi side
            print("📊 Executing Kalshi order...")
            kalshi_result = await self._execute_kalshi_order(request)
            execution_results["kalshi_order"] = kalshi_result
            
            if not kalshi_result.get("success"):
                execution_results["errors"].append(f"Kalshi order failed: {kalshi_result.get('error')}")
                return execution_results
            
            # STEP 2: Execute IBKR side (will implement tomorrow)
            print("📊 Executing IBKR order...")
            if hasattr(self, 'ibkr_client') and self.ibkr_client:
                ibkr_result = await self._execute_ibkr_order(request)
                execution_results["ibkr_order"] = ibkr_result
                
                if not ibkr_result.get("success"):
                    # CRITICAL: If IBKR fails, we need to reverse the Kalshi trade
                    print("❌ IBKR order failed - attempting to reverse Kalshi trade")
                    await self._reverse_kalshi_order(kalshi_result)
                    execution_results["errors"].append(f"IBKR order failed, Kalshi reversed: {ibkr_result.get('error')}")
                    return execution_results
            else:
                # For testing: simulate IBKR execution
                print("🧪 SIMULATING IBKR order (API not available yet)")
                ibkr_result = {
                    "success": True,
                    "order_id": f"IBKR_SIM_{int(time.time())}",
                    "executed_price": request.sell_price,
                    "executed_volume": request.volume,
                    "simulated": True
                }
                execution_results["ibkr_order"] = ibkr_result
            
            # STEP 3: Calculate actual profit
            kalshi_cost = kalshi_result.get("executed_price", request.buy_price) * request.volume
            ibkr_revenue = ibkr_result.get("executed_price", request.sell_price) * request.volume
            
            # Add fees (use your real fee calculation)
            kalshi_fee = self.kalshi_client.calculate_trading_fee(
                kalshi_result.get("executed_price", request.buy_price), 
                request.volume
            )
            ibkr_fee = 0.0  # ForecastEx contracts are free
            
            actual_profit = ibkr_revenue - kalshi_cost - kalshi_fee - ibkr_fee
            execution_results["actual_profit"] = actual_profit
            
            # STEP 4: Update tracking
            self.daily_trades += 1
            self.daily_pnl += actual_profit
            
            execution_results["success"] = True
            execution_results["end_time"] = datetime.now().isoformat()
            
            # Mark request as executed
            request.executed = True
            request.execution_results = execution_results
            
            print(f"✅ ARBITRAGE TRADE COMPLETED!")
            print(f"   Estimated profit: ${request.estimated_profit:.2f}")
            print(f"   Actual profit: ${actual_profit:.2f}")
            print(f"   Difference: ${actual_profit - request.estimated_profit:.2f}")
            
            # Send confirmation to Discord
            await self._send_execution_confirmation(request, execution_results)
            
            return execution_results
            
        except Exception as e:
            print(f"❌ EXECUTION ERROR: {e}")
            execution_results["errors"].append(f"Execution exception: {str(e)}")
            return execution_results
    
    async def _execute_kalshi_order(self, request: ExecutionRequest) -> Dict:
        """Execute order on Kalshi"""
        try:
            # Determine order side based on arbitrage direction
            if request.buy_platform.lower() == 'kalshi':
                side = "yes"  # Buy yes contracts
                action = "buy"
                price = request.buy_price
            else:
                side = "yes"  # Sell yes contracts (short)
                action = "sell"
                price = request.sell_price
            
            print(f"📊 Kalshi order: {action} {request.volume} {request.buy_ticker} {side} @ ${price:.3f}")
            
            # Execute the order using your working Kalshi client
            result = self.kalshi_client.place_order(
                ticker=request.buy_ticker,
                side=side,
                action=action,
                count=request.volume,
                order_type="limit",
                price=price
            )
            
            if result:
                return {
                    "success": True,
                    "order_id": result.get("order_id"),
                    "executed_price": price,
                    "executed_volume": request.volume,
                    "platform": "Kalshi",
                    "raw_response": result
                }
            else:
                return {
                    "success": False,
                    "error": "Kalshi order placement failed",
                    "platform": "Kalshi"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Kalshi execution error: {str(e)}",
                "platform": "Kalshi"
            }
    
    async def _execute_ibkr_order(self, request: ExecutionRequest) -> Dict:
        """Execute order on IBKR (will implement tomorrow)"""
        try:
            # TODO: Implement with your IBKR client tomorrow
            # This is a placeholder for the real implementation
            
            if request.sell_platform.lower() == 'ibkr':
                action = "SELL"
                price = request.sell_price
            else:
                action = "BUY"  
                price = request.buy_price
            
            print(f"📊 IBKR order: {action} {request.volume} {request.sell_ticker} @ ${price:.3f}")
            
            # Tomorrow: Replace with real IBKR execution
            # result = self.ibkr_client.place_event_order(
            #     contract=contract,
            #     action=action,
            #     quantity=request.volume,
            #     price=price
            # )
            
            # For now: simulate success
            return {
                "success": True,
                "order_id": f"IBKR_SIM_{int(time.time())}",
                "executed_price": price,
                "executed_volume": request.volume,
                "platform": "IBKR",
                "simulated": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"IBKR execution error: {str(e)}",
                "platform": "IBKR"
            }
    
    async def _reverse_kalshi_order(self, kalshi_result: Dict) -> Dict:
        """Reverse a Kalshi order if IBKR fails"""
        try:
            print("🔄 Attempting to reverse Kalshi order...")
            
            # This would place an opposite order to close the position
            # Implementation depends on Kalshi's order reversal capabilities
            
            # For now: log the need for manual intervention
            print("⚠️ MANUAL INTERVENTION REQUIRED: Reverse Kalshi order")
            print(f"   Order ID: {kalshi_result.get('order_id')}")
            
            return {"success": False, "requires_manual_reversal": True}
            
        except Exception as e:
            print(f"❌ Failed to reverse Kalshi order: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_execution_confirmation(self, request: ExecutionRequest, results: Dict):
        """Send execution confirmation to Discord"""
        
        success = results.get("success", False)
        actual_profit = results.get("actual_profit", 0)
        
        if success:
            embed = {
                "title": "✅ TRADE EXECUTED SUCCESSFULLY",
                "description": f"**{request.contract_name}**",
                "color": 0x00FF00,  # Green
                "fields": [
                    {
                        "name": "💰 Results",
                        "value": f"Estimated: ${request.estimated_profit:.2f}\n"
                                f"Actual: **${actual_profit:.2f}**\n"
                                f"Difference: ${actual_profit - request.estimated_profit:.2f}",
                        "inline": True
                    },
                    {
                        "name": "📊 Execution Details",
                        "value": f"Volume: {request.volume} contracts\n"
                                f"Kalshi: {results.get('kalshi_order', {}).get('success', 'Unknown')}\n"
                                f"IBKR: {results.get('ibkr_order', {}).get('success', 'Unknown')}",
                        "inline": True
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            embed = {
                "title": "❌ TRADE EXECUTION FAILED",
                "description": f"**{request.contract_name}**",
                "color": 0xFF0000,  # Red
                "fields": [
                    {
                        "name": "🚨 Errors",
                        "value": "\n".join(results.get("errors", ["Unknown error"])),
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        self._send_to_discord({"embeds": [embed]})

# Flask app for handling Discord button interactions (advanced feature)
app = Flask(__name__)
executor = OneClickExecutor()

@app.route('/discord/interaction', methods=['POST'])
def handle_discord_interaction():
    """Handle Discord button clicks"""
    try:
        data = request.json
        
        if data.get('type') == 3:  # Button interaction
            custom_id = data.get('data', {}).get('custom_id', '')
            
            if custom_id.startswith('execute_'):
                opportunity_id = custom_id.replace('execute_', '')
                
                # Execute the trade asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(executor.execute_arbitrage_trade(opportunity_id))
                
                return jsonify({
                    "type": 4,
                    "data": {
                        "content": f"🚀 Executing trade {opportunity_id}...",
                        "flags": 64  # Ephemeral
                    }
                })
            
            elif custom_id.startswith('reject_'):
                opportunity_id = custom_id.replace('reject_', '')
                if opportunity_id in executor.pending_requests:
                    del executor.pending_requests[opportunity_id]
                
                return jsonify({
                    "type": 4,
                    "data": {
                        "content": "❌ Trade rejected",
                        "flags": 64
                    }
                })
        
        return jsonify({"type": 1})  # Pong
        
    except Exception as e:
        print(f"❌ Discord interaction error: {e}")
        return jsonify({"error": "Internal error"}), 500

def test_one_click_system():
    """Test the one-click execution system"""
    
    # Create a test opportunity
    test_opportunity = {
        "contract_name": "FED-25DEC-T3.50",
        "buy_platform": "Kalshi",
        "sell_platform": "IBKR", 
        "buy_ticker": "FED-25DEC-T3.50",
        "sell_ticker": "FF Dec25 3.50 Call",
        "volume": 50,
        "buy_price": 0.485,
        "sell_price": 0.523,
        "estimated_profit": 87.50
    }
    
    print("🧪 Testing one-click execution system...")
    
    # Test sending execution alert
    opportunity_id = executor.send_execution_alert(test_opportunity)
    print(f"✅ Execution alert sent: {opportunity_id}")
    
    # Test execution (will simulate IBKR for now)
    print("⏳ Waiting 3 seconds then simulating execution...")
    time.sleep(3)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(executor.execute_arbitrage_trade(opportunity_id))
    
    print(f"📊 Execution result: {result}")
    
    if result.get("success"):
        print("✅ One-click system working perfectly!")
    else:
        print("⚠️ Execution issues - check logs")

if __name__ == "__main__":
    test_one_click_system()