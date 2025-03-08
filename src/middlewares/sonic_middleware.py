import logging
from typing import Any, Dict, List, Tuple
from .baibysitter_middleware import BaibysitterMiddleware, BaibysitterConfig
from web3 import Web3
from src.connections.sonic_connection import SonicConnection

logger = logging.getLogger("middlewares.sonic")

class SonicMiddleware(BaibysitterMiddleware):
    def __init__(self, agent_config: List[Dict]):
        # Find sonic config in agent configuration
        sonic_config = next((config for config in agent_config if config["name"] == "sonic"), None)
        if not sonic_config:
            raise ValueError("Sonic configuration not found in agent config")

        baibysitter_config = sonic_config.get("baibysitter", {})
        if not baibysitter_config.get("api_url"):
            raise ValueError("api_url must be configured in the baibysitter configuration")
            
        # Create SonicConnection instance to reuse its methods
        self.sonic = SonicConnection(sonic_config)
            
        super().__init__(BaibysitterConfig(
            api_url=baibysitter_config["api_url"],
            enabled=baibysitter_config.get("enabled", False),
            name=baibysitter_config.get("name", "BaibySitter")
        ))

    def should_validate_action(self, action_name: str) -> bool:
        return action_name in ["transfer", "swap"]
    
    def _extract_transaction_data(self, action_name: str, params: List[Any]) -> Dict[str, Any]:
        if action_name == "transfer":
            to_address, amount, token_address = params
            
            # Use SonicConnection's contract to encode transfer
            token_contract = self.sonic._web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.sonic.ERC20_ABI
            )
            
            data = token_contract.encodeABI(
                fn_name="transfer",
                args=[
                    Web3.to_checksum_address(to_address),
                    int(amount)
                ]
            )
            
            return {
                "to": Web3.to_checksum_address(token_address),
                "data": data[2:] if data.startswith('0x') else data,
                "value": "0"
            }
            
        elif action_name == "swap":
            token_in, token_out, amount, slippage = params
            
            # Use SonicConnection's methods directly
            route_data = self.sonic._get_swap_route(token_in, token_out, amount)
            encoded_data = self.sonic._get_encoded_swap_data(
                route_data["routeSummary"], 
                slippage=slippage if slippage else 0.5
            )
            
            return {
                "to": Web3.to_checksum_address(route_data["routerAddress"]),
                "data": encoded_data[2:] if encoded_data.startswith('0x') else encoded_data,
                "value": self.sonic._web3.to_wei(amount, 'ether') if token_in.lower() == self.sonic.NATIVE_TOKEN.lower() else "0"
            }
        
        return {}
