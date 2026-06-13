"""Sample module for syntactic chunking tests (Python)."""

PI = 3.14159


def add(a, b):
    """Adds two numbers."""
    return a + b


class Calculator:
    """A minimal calculator."""

    def __init__(self, start=0):
        self.value = start

    def add(self, n):
        """Adds n to the current value."""
        self.value += n
        return self.value

    def reset(self):
        self.value = 0
        return self.value
