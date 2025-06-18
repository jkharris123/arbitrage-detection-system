def validate_arbitrage_opportunity(self, buy_platform: MarketData, sell_platform: MarketData, 
                                     volume: int) -> Optional[Dict]:
        """
        Comprehensive validation of arbitrage opportunity
        Returns detailed analysis or None if not profitable
        """
        try:
            # Get best prices
            buy_price = buy_platform.ask_price  # We buy at ask price
            sell_price = sell_platform.bid_price  # We sell at bid price
            
            # Basic arbitrage check
            if buy_price >= sell_price:
                return None
            
            # Calculate REAL execution costs using order book depth
            buy_execution = buy_platform.order_book.calculate_market_impact('buy', volume)
            sell_execution = sell_platform.order_book.calculate_market_impact('sell', volume)
            
            # Use actual execution prices (not just best prices)
            actual_buy_price = buy_execution.get('average_price', buy_price)
            actual_sell_price = sell_execution.get('average_price', sell_price)
            
            # Calculate all costs
            fees = self.calculate_total_fees(
                buy_platform.platform, sell_platform.platform,
                actual_buy_price, actual_sell_price, volume
            )
            
            # Slippage is already calculated in market_impact
            buy_slippage = buy_execution.get('slippage', 0)
            sell_slippage = sell_execution.get('slippage', 0)
            total_slippage = buy_slippage + sell_slippage
            
            # Net profit calculation with REAL execution prices
            gross_profit = (actual_sell_price - actual_buy_price) * volume
            net_profit = gross_profit - fees - total_slippage
            
            # Only proceed if actually profitable after ALL costs
            if net_profit <= 0:
                return None
            
            profit_margin = (net_profit / (actual_buy_price * volume)) * 100
            
            # Calculate daily profit rate (assume 1 day to expiry for now)
            daily_profit_rate = profit_margin  # Will be enhanced with real expiry dates
            
            # Determine if this qualifies for auto-execution
            should_auto_execute = (daily_profit_rate >= 5.0) or (net_profit >= 250.0)
            
            return {
                'gross_profit': gross_profit,
                'total_fees': fees,
                'total_slippage': total_slippage,
                'net_profit': net_profit,
                'profit_margin_percent': profit_margin,
                'daily_profit_rate': daily_profit_rate,
                'volume': volume,
                'buy_price': actual_buy_price,
                'sell_price': actual_sell_price,
                'should_auto_execute': should_auto_execute,
                'buy_execution': buy_execution,
                'sell_execution': sell_execution,
                'execution_quality': min(buy_execution.get('filled_volume', 0), sell_execution.get('filled_volume', 0))
            }
            
        except Exception as e:
            print(f"⚠️ Error validating arbitrage: {e}")
            return None