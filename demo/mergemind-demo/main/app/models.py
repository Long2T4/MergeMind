class User:
    """A fictional user account."""

    def __init__(self, name: str, email: str):
        if not name:
            raise ValueError("name must not be empty")
        self.name = name
        self.email = email
