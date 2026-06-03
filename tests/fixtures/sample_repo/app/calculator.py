"""Modulo di esempio per i test di chunking sintattico (Python)."""

PI = 3.14159


def add(a, b):
    """Somma due numeri."""
    return a + b


class Calculator:
    """Una calcolatrice minimale."""

    def __init__(self, start=0):
        self.value = start

    def add(self, n):
        """Aggiunge n al valore corrente."""
        self.value += n
        return self.value

    def reset(self):
        self.value = 0
        return self.value
