import logging
import requests
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import asyncio

logger = logging.getLogger("middlewares.baibysitter")

@dataclass
class BaibysitterConfig:
    api_url: str
    enabled: bool = True
    name: str = None

class BaibysitterMiddleware(ABC):
    def __init__(self, config: BaibysitterConfig):
        self.config = config
        self.name = config.name or self.__class__.__name__
        
    def __call__(self, action_name: str, params: Any) -> Tuple[bool, List[Any], str]:
        if not self.config.enabled:
            return True, params.get("args", params), ""
            
        if not self.should_validate_action(action_name):
            return True, params.get("args", params), ""
            
        try:
            args = params.get("args", params)
            metadata = params.get("metadata", {})
            from_address = metadata.get("from", "")
            reason = metadata.get("reason", "")
            
            tx_data = self._extract_transaction_data(action_name, args)
            should_execute, _, message = self._validate_transaction(
                from_address=from_address,
                reason=reason,
                tx_data=tx_data
            )            
            return should_execute, args, f"{message}"
            
        except Exception as e:
            error_message = f"Error in middleware: {e}"
            logger.error(error_message)
            return True, params.get("args", params), error_message

    @abstractmethod
    def should_validate_action(self, action_name: str) -> bool:
        """Define which actions should be validated"""
        pass

    @abstractmethod            
    def _extract_transaction_data(self, action_name: str, params: List[Any]) -> Dict[str, Any]:
        """Extract transaction data from params based on action type"""
        pass 
            
    def _validate_transaction(self, from_address: str, reason: str, tx_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        try:
            if not from_address:
                return False, tx_data, "The transaction was rejected because the from address is empty"
            
            if not reason:
                return False, tx_data, "The transaction was rejected because the reason is empty"

            logger.info(f"Validating transaction: {tx_data}")
            response = requests.post(
                f"{self.config.api_url}/agent/transaction",
                json={
                    "transactions": [tx_data],
                    "safeAddress": from_address,
                    "reason": reason,
                    # TODO: delete this field
                    "erc20TokenAddress": "0x0000000000000000000000000000000000000000",
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # data = {"should_execute": True, "tx_data": tx_data, "message": "Transaction validated"}
            # Simulate API call
            # fake_message_response = f"success!"
            # async def mock_api_call() -> Dict[str, Any]:
            #     await asyncio.sleep(0.1)
            #     return {
            #         "from_address": from_address,
            #         "should_execute": True,
            #         "tx_data": tx_data,
            #         "message": fake_message_response
            #     }

            # Try to get the running loop, if not available create a new one
            # try:
            #     loop = asyncio.get_running_loop()
            # except RuntimeError:
            #     loop = asyncio.new_event_loop()
            #     asyncio.set_event_loop(loop)
            
            # data = loop.run_until_complete(mock_api_call())
            should_execute = "APPROVED" in data.get("message", "")
            return should_execute, data.get("transaction_hashstring", ""), data.get("message", "")
            
        except Exception as e:
            logger.error(f"Error validating transaction: {e}")
            return True, tx_data, reason
