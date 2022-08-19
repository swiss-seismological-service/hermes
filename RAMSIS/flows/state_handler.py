from prefect import Task, Flow
from typing import Union, Optional
from prefect.engine.state import State


def state_handler(
        obj: Union[Task, Flow],
        old_state: State, new_state: State) -> Optional[State]:
    """
    Any function with this signature can serve as a state handler.

    Args:
        - obj (Union[Task, Flow]): the underlying object to which this
            state handler is attached
        - old_state (State): the previous state of this object
        - new_state (State): the proposed new state of this object

    Returns:
        - Optional[State]: the new state of this object (typically this
            is just `new_state`)
    """
    return new_state
