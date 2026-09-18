"""
PowPowPow MCP Server
Exposes data as Model Context Protocol for AI agents.
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, '/home/box/powpowpow')

# MCP Server Implementation
# This exposes PowPowPow data as tools for AI agents

MCP_SERVER = {
    "name": "powpowpow",
    "version": "1.0.0",
    "description": "Physical economics of mineable/compute crypto",
    "tools": [
        {
            "name": "get_chain_status",
            "description": "Get current status of a blockchain (hashrate, difficulty, price, etc)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Chain symbol (PRL, QUBIC, XMR, etc)"}
                },
                "required": ["symbol"]
            }
        },
        {
            "name": "get_mining_profitability",
            "description": "Calculate mining profitability for a specific hardware on a chain",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chain": {"type": "string", "description": "Chain symbol"},
                    "hardware": {"type": "string", "description": "Hardware model (H100, RTX_4090, etc)"},
                    "electricity_cost": {"type": "number", "description": "Electricity cost in $/kWh"}
                },
                "required": ["chain", "hardware"]
            }
        },
        {
            "name": "get_best_mining_option",
            "description": "Find the most profitable mining option for a given hardware",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "hardware": {"type": "string", "description": "Hardware model"},
                    "electricity_cost": {"type": "number", "description": "Electricity cost in $/kWh"}
                },
                "required": ["hardware"]
            }
        },
        {
            "name": "get_compute_market_prices",
            "description": "Get current GPU rental prices from Akash, Clore, Nosana",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gpu_class": {"type": "string", "description": "GPU class (h100, a100, rtx4090)"}
                }
            }
        },
        {
            "name": "get_pressure_metrics",
            "description": "Get sell pressure and absorption metrics for a chain",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Chain symbol"}
                },
                "required": ["symbol"]
            }
        },
        {
            "name": "compare_chains",
            "description": "Compare mining economics across multiple chains",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chains": {"type": "array", "items": {"type": "string"}, "description": "List of chain symbols"},
                    "hardware": {"type": "string", "description": "Hardware model to compare"}
                },
                "required": ["chains"]
            }
        },
        {
            "name": "get_resource_premium",
            "description": "Calculate resource premium (mining revenue vs external rental)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "chain": {"type": "string", "description": "Chain symbol"}
                },
                "required": ["chain"]
            }
        },
        {
            "name": "get_all_live_cards",
            "description": "Get profitability cards for all V1 chains",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        }
    ]
}

# Tool implementations
def get_chain_status(symbol):
    from v1_registry import get_v1_coin
    import json
    
    coin = get_v1_coin(symbol.upper())
    if not coin:
        return {"error": f"Unknown chain: {symbol}"}
    
    # Load data
    data_file = f'/home/box/powpowpow/chains/{symbol.lower()}/{symbol.lower()}_data.json'
    data = {}
    if os.path.exists(data_file):
        with open(data_file) as f:
            data = json.load(f)
    
    price = data.get('price', {})
    price_usd = price.get('usd', 0) if isinstance(price, dict) else price
    
    return {
        'symbol': symbol.upper(),
        'name': coin.get('name'),
        'physical_resource': coin.get('physical_resource'),
        'price_usd': price_usd,
        'data': data
    }

def get_mining_profitability(chain, hardware, electricity_cost=0.10):
    from v1_live_cards import generate_card
    
    # Load price
    data_file = f'/home/box/powpowpow/chains/{chain.lower()}/{chain.lower()}_data.json'
    data = {}
    if os.path.exists(data_file):
        with open(data_file) as f:
            data = json.load(f)
    
    price = data.get('price', {})
    price_usd = price.get('usd', 0) if isinstance(price, dict) else price
    
    if not price_usd:
        return {"error": f"No price data for {chain}"}
    
    card = generate_card(chain, price_usd)
    
    if hardware in card.get('hardware', {}):
        return card['hardware'][hardware]
    else:
        return {"error": f"Hardware {hardware} not found for {chain}"}

def get_best_mining_option(hardware, electricity_cost=0.10):
    from v1_live_cards import generate_card
    
    best = None
    best_profit = float('-inf')
    
    # Load all prices
    for chain in ['PRL', 'XMR', 'KAS', 'QUAN']:
        data_file = f'/home/box/powpowpow/chains/{chain.lower()}/{chain.lower()}_data.json'
        data = {}
        if os.path.exists(data_file):
            with open(data_file) as f:
                data = json.load(f)
        
        price = data.get('price', {})
        price_usd = price.get('usd', 0) if isinstance(price, dict) else price
        
        if price_usd:
            card = generate_card(chain, price_usd)
            if hardware in card.get('hardware', {}):
                hw = card['hardware'][hardware]
                profit = hw.get('net_profit_usd_day', 0)
                
                if profit > best_profit:
                    best_profit = profit
                    best = {
                        'chain': chain,
                        'hardware': hardware,
                        'profit_usd_day': profit,
                        'revenue_usd_day': hw.get('revenue_usd_day', 0),
                        'electricity_usd_day': hw.get('electricity_usd_day', 0),
                    }
    
    return best or {"error": f"No profitability data found for {hardware}"}

def get_compute_market_prices(gpu_class=None):
    import json
    
    # Load compute benchmark data
    data_file = '/home/box/powpowpow/chains/benchmarks/compute_benchmarks.json'
    if os.path.exists(data_file):
        with open(data_file) as f:
            data = json.load(f)
        return data
    
    return {"error": "No compute benchmark data available"}

def get_pressure_metrics(symbol):
    import json
    
    factors_file = '/home/box/powpowpow/chains/factors/cross_chain_factors.json'
    if os.path.exists(factors_file):
        with open(factors_file) as f:
            factors = json.load(f)
        return factors.get(symbol.upper(), {"error": f"No pressure data for {symbol}"})
    
    return {"error": "No factor data available"}

def compare_chains(chains, hardware=None):
    from v1_live_cards import generate_card
    
    results = []
    
    for chain in chains:
        data_file = f'/home/box/powpowpow/chains/{chain.lower()}/{chain.lower()}_data.json'
        data = {}
        if os.path.exists(data_file):
            with open(data_file) as f:
                data = json.load(f)
        
        price = data.get('price', {})
        price_usd = price.get('usd', 0) if isinstance(price, dict) else price
        
        if price_usd:
            card = generate_card(chain, price_usd)
            results.append({
                'chain': chain,
                'price_usd': price_usd,
                'hardware': card.get('hardware', {})
            })
    
    return results

def get_resource_premium(chain):
    import json
    
    econ_file = '/home/box/powpowpow/chains/economics/miner_economics.json'
    if os.path.exists(econ_file):
        with open(econ_file) as f:
            economics = json.load(f)
        return economics.get(chain.upper(), {"error": f"No economics data for {chain}"})
    
    return {"error": "No economics data available"}

def get_all_live_cards():
    from v1_live_cards import generate_card
    
    cards = {}
    for chain in ['PRL', 'QUBIC', 'QUAN', 'XMR', 'KAS']:
        data_file = f'/home/box/powpowpow/chains/{chain.lower()}/{chain.lower()}_data.json'
        data = {}
        if os.path.exists(data_file):
            with open(data_file) as f:
                data = json.load(f)
        
        price = data.get('price', {})
        price_usd = price.get('usd', 0) if isinstance(price, dict) else price
        
        if price_usd:
            cards[chain] = generate_card(chain, price_usd)
    
    return cards

# Tool dispatcher
TOOLS = {
    'get_chain_status': get_chain_status,
    'get_mining_profitability': get_mining_profitability,
    'get_best_mining_option': get_best_mining_option,
    'get_compute_market_prices': get_compute_market_prices,
    'get_pressure_metrics': get_pressure_metrics,
    'compare_chains': compare_chains,
    'get_resource_premium': get_resource_premium,
    'get_all_live_cards': get_all_live_cards,
}

def handle_tool_call(tool_name, arguments):
    if tool_name in TOOLS:
        func = TOOLS[tool_name]
        return func(**arguments)
    return {"error": f"Unknown tool: {tool_name}"}

# MCP Server entry point
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # CLI mode - test a tool
        tool = sys.argv[1]
        args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        result = handle_tool_call(tool, args)
        print(json.dumps(result, indent=2, default=str))
    else:
        # Print server info
        print(json.dumps(MCP_SERVER, indent=2))
