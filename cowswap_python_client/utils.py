from typing import Optional, Type, TypeVar

T = TypeVar("T")

def check_not_none(
    value: Optional[T],
    msg: str = "Value shouldn't be None.",
    exp: Type[ValueError] = ValueError,
) -> T:
    """
    Utility to remove optionality from a variable.

    Useful for cases like this:

    ```
    keys = pma.utils.get_keys()
    pma.omen.omen_buy_outcome_tx(
        from_addres=check_not_none(keys.bet_from_address),  # <-- No more Optional[HexAddress], so type checker will be happy.
        ...,
    )
    ```
    """
    if value is None:
        should_not_happen(msg=msg, exp=exp)
    return value
