from typing import Any

import requests
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from loguru import logger
from web3 import Web3

from cowswap_client.encoding import DOMAIN, MESSAGE_TYPES, MESSAGE_TYPES_CANCELLATION
from cowswap_client.gtypes import Wei
from cowswap_client.models import (
    CowServer,
    OrderKind,
    OrderStatus,
    QuoteInput,
    QuoteOutput,
)


class CowClient:
    def __init__(
        self, account: LocalAccount, api_url: CowServer = CowServer.GNOSIS_STAGING
    ):
        self.api_url = api_url
        self.account = account

    def get_version(self) -> str:
        r = requests.get(f"{self.api_url.value}/api/v1/version")
        return r.text

    def build_swap_params(
        self, sell_token: ChecksumAddress, buy_token: ChecksumAddress, sell_amount: Wei
    ) -> QuoteInput:
        quote = QuoteInput(
            from_=self.account.address,
            sell_token=sell_token,
            buy_token=buy_token,
            receiver=self.account.address,
            sell_amount_before_fee=str(sell_amount),
            kind=OrderKind.SELL,
            app_data="0x0000000000000000000000000000000000000000000000000000000000000000",
            valid_for=1080,
        )
        return quote

    @staticmethod
    def _if_error_log_and_raise(r: requests.Response) -> None:
        try:
            r.raise_for_status()
        except Exception as e:
            logger.error(f"Error occured on response: {r.text}, Exception - {e}")
            raise

    def post_quote(self, quote: QuoteInput) -> QuoteOutput:
        quote_dict = quote.model_dump(by_alias=True, exclude_none=True)
        r = requests.post(f"{self.api_url.value}/api/v1/quote", json=quote_dict)

        self._if_error_log_and_raise(r)
        return QuoteOutput.model_validate(r.json()["quote"])

    @staticmethod
    def build_order_with_fee_and_sell_amounts(quote: QuoteOutput) -> dict[str, Any]:
        quote.sell_amount = str(int(quote.sell_amount) + int(quote.fee_amount))
        quote.fee_amount = "0"
        quote_dict = quote.model_dump(by_alias=True, exclude_none=True)
        return quote_dict

    def post_order(self, quote: QuoteOutput, web3: Web3 | None = None) -> str:
        # Note that allowance is not checked - please make sure you have enough allowance to make the order.
        order_data = self.build_order_with_fee_and_sell_amounts(quote)

        # sign
        signed_message = Account.sign_typed_data(
            self.account.key, DOMAIN, MESSAGE_TYPES, order_data
        )
        order_data["signature"] = signed_message.signature.hex()
        # post
        r = requests.post(f"{self.api_url.value}/api/v1/orders", json=order_data)
        self._if_error_log_and_raise(r)
        order_id = r.content.decode().replace('"', "")
        return order_id

    def cancel_order_if_not_already_cancelled(self, order_uids: list[str]) -> None:
        signed_message_cancellation = Account.sign_typed_data(
            self.account.key,
            DOMAIN,
            MESSAGE_TYPES_CANCELLATION,
            {"orderUids": order_uids},
        )
        cancellation_request_obj = {
            "orderUids": order_uids,
            "signature": signed_message_cancellation.signature.hex(),
            "signingScheme": "eip712",
        }

        order_status = self.get_order_status(order_uids[0])
        if order_status == OrderStatus.CANCELLED:
            return

        r = requests.delete(
            f"{self.api_url.value}/api/v1/orders", json=cancellation_request_obj
        )
        r.raise_for_status()

    def get_order_status(self, order_uid: str) -> OrderStatus:
        r = requests.get(f"{self.api_url.value}/api/v1/orders/{order_uid}/status")
        r.raise_for_status()

        order_type = r.json()["type"]
        if order_type not in iter(OrderStatus):
            raise ValueError(
                f"order_type {order_type} from order_uid {order_uid} cannot be processed."
            )
        return OrderStatus(order_type)
