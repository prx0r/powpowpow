"""
SafeTrade L2 Archival System
Stores every depth update and trade for backtesting.
"""

import json
import os
import asyncio
import websockets
import time
from datetime import datetime
import sys
sys.path.insert(0, '/home/box/powpowpow')
from warehouse import store_raw_event, store_normalized

# Coins to archive
ARCHIVE_COINS = ['qubicusdt', 'prlusdt', 'xmrusdt']

class L2Archival:
    def __init__(self):
        self.running = False
        self.start_time = None
        self.stats = {coin: {'depth': 0, 'trades': 0} for coin in ARCHIVE_COINS}
    
    async def connect(self):
        ws_url = "wss://safe.trade/api/v2/websocket/public"
        additional_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://safetrade.com"
        }
        
        print(f"[CONNECTING] {ws_url}")
        
        self.ws = await websockets.connect(
            ws_url,
            additional_headers=additional_headers,
            ping_interval=20,
            ping_timeout=10
        )
        print("[CONNECTED]")
        
        # Subscribe to all coins
        streams = []
        for market in ARCHIVE_COINS:
            streams.extend([f"{market}.trades", f"{market}.depth"])
        
        subscribe_msg = {"event": "subscribe", "streams": streams}
        await self.ws.send(json.dumps(subscribe_msg))
        print(f"[SUBSCRIBED] {len(streams)} streams")
        
        self.running = True
        self.start_time = time.time()
    
    async def listen(self, duration=None):
        print(f"\n[LISTENING] Archiving L2 data...")
        if duration:
            print(f"[DURATION] {duration} seconds")
        
        last_save = time.time()
        save_interval = 60
        
        try:
            while self.running:
                if duration and (time.time() - self.start_time) >= duration:
                    break
                
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    timestamp = datetime.now()
                    
                    for market in ARCHIVE_COINS:
                        # Depth updates
                        if f'{market}.depth' in data:
                            depth = data[f'{market}.depth']
                            
                            # Store raw
                            store_raw_event('market', 'depth', {
                                'market': market,
                                'data': depth
                            }, {
                                'source_id': 'safetrade-ws',
                                'source_type': 'websocket',
                                'endpoint': 'wss://safe.trade/api/v2/websocket/public',
                            })
                            
                            # Normalize to orderbook_level
                            bids = depth.get('bids', [])
                            asks = depth.get('asks', [])
                            
                            for i, bid in enumerate(bids):
                                store_normalized('orderbook_level', 'market', {
                                    'market': market,
                                    'side': 'bid',
                                    'price': bid[0],
                                    'quantity': bid[1],
                                    'level': i,
                                }, timestamp)
                            
                            for i, ask in enumerate(asks):
                                store_normalized('orderbook_level', 'market', {
                                    'market': market,
                                    'side': 'ask',
                                    'price': ask[0],
                                    'quantity': ask[1],
                                    'level': i,
                                }, timestamp)
                            
                            self.stats[market]['depth'] += 1
                        
                        # Trade updates
                        if f'{market}.trades' in data:
                            trade = data[f'{market}.trades']
                            
                            # Store raw
                            store_raw_event('market', 'trade', {
                                'market': market,
                                'data': trade
                            }, {
                                'source_id': 'safetrade-ws',
                                'source_type': 'websocket',
                                'endpoint': 'wss://safe.trade/api/v2/websocket/public',
                            })
                            
                            # Normalize
                            if isinstance(trade, list) and len(trade) >= 3:
                                store_normalized('trade', 'market', {
                                    'market': market,
                                    'price': str(trade[0]),
                                    'quantity': str(trade[1]),
                                    'aggressor_side': 'buy' if trade[2] == 'b' else 'sell',
                                }, timestamp)
                            elif isinstance(trade, dict):
                                store_normalized('trade', 'market', {
                                    'market': market,
                                    'price': trade.get('price'),
                                    'quantity': trade.get('amount'),
                                    'aggressor_side': trade.get('side'),
                                }, timestamp)
                            
                            self.stats[market]['trades'] += 1
                    
                    # Progress update
                    if int(time.time() - self.start_time) % 30 == 0:
                        elapsed = int(time.time() - self.start_time)
                        total_depth = sum(s['depth'] for s in self.stats.values())
                        total_trades = sum(s['trades'] for s in self.stats.values())
                        print(f"[{elapsed}s] Depth: {total_depth} | Trades: {total_trades}")
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"[ERROR] {e}")
        
        except KeyboardInterrupt:
            pass
        
        finally:
            self.running = False
    
    async def disconnect(self):
        self.running = False
        if self.ws:
            await self.ws.close()

async def run_archival(duration=None):
    archival = L2Archival()
    
    try:
        await archival.connect()
        await archival.listen(duration=duration)
    except Exception as e:
        print(f"[FATAL] {e}")
    finally:
        await archival.disconnect()
        
        print(f"\n{'='*60}")
        print("ARCHIVAL COMPLETE")
        print(f"{'='*60}")
        elapsed = time.time() - archival.start_time if archival.start_time else 0
        print(f"Duration: {elapsed:.1f}s")
        for market, stats in archival.stats.items():
            print(f"  {market}: {stats['depth']} depth, {stats['trades']} trades")

if __name__ == '__main__':
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(run_archival(duration=duration))
