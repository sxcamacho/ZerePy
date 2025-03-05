import logging
from typing import Any, Dict, List, Tuple
from .baibysitter_middleware import BaibysitterMiddleware
from .baibysitter_middleware import BaibysitterConfig

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
            
        super().__init__(BaibysitterConfig(
            api_url=baibysitter_config["api_url"],
            enabled=baibysitter_config.get("enabled", False),
            name=baibysitter_config.get("name", "BaibySitter")
        ))

    def should_validate_action(self, action_name: str) -> bool:
        return action_name in ["transfer", "swap", "get-balance"]
    
    def _extract_transaction_data(self, action_name: str, params: List[Any]) -> Dict[str, Any]:
        tx_data = {
            "action": action_name,
            "params": params
        }
        
        if action_name == "transfer":
            tx_data.update({
                "to_address": params[0],
                "amount": params[1],
                "token_address": params[2] if len(params) > 2 else None
            })
        elif action_name == "swap":
            tx_data.update({
                "token_in": params[0],
                "token_out": params[1],
                "amount": params[2],
                "slippage": params[3] if len(params) > 3 else 0.5
            })
        elif action_name == "get-balance":
            tx_data.update({
                "address": params[0],
                "token_address": params[1] if len(params) > 1 else None
            })
            
        return tx_data
    
    def _update_params_with_modified_tx(self, original_params: List[Any], modified_tx: Dict[str, Any]) -> List[Any]:
        action = modified_tx.get("action")
        
        if action == "transfer":
            return [
                modified_tx.get("to_address", original_params[0]),
                modified_tx.get("amount", original_params[1]),
                modified_tx.get("token_address", original_params[2] if len(original_params) > 2 else None)
            ]
        elif action == "swap":
            return [
                modified_tx.get("token_in", original_params[0]),
                modified_tx.get("token_out", original_params[1]),
                modified_tx.get("amount", original_params[2]),
                modified_tx.get("slippage", original_params[3] if len(original_params) > 3 else 0.5)
            ]
        elif action == "get-balance":
            return [
                modified_tx.get("address", original_params[0]),
                modified_tx.get("token_address", original_params[1] if len(original_params) > 1 else None)
            ]
            
        return original_params 