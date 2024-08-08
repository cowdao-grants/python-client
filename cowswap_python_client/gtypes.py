from typing import NewType

from pydantic.types import SecretStr
from web3.types import (  # noqa: F401  # Import for the sake of easy importing with others from here.
    Nonce,
    TxParams,
    TxReceipt,
    Wei,
)

PrivateKey = NewType("PrivateKey", SecretStr)
