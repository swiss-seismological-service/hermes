def futures_wait(futures: list) -> None:
    """
    Wait for all futures to finish.
    """
    for future in futures:
        future.wait()
