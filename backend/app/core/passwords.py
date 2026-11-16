from werkzeug.security import check_password_hash, generate_password_hash


class Passwords:
    """PBKDF2 via Werkzeug; avoids native hashing DLLs blocked on this Windows host."""

    @staticmethod
    def hash(password: str) -> str:
        return generate_password_hash(password, method="pbkdf2:sha256:1000000", salt_length=16)

    @staticmethod
    def verify(password: str, stored_hash: str) -> bool:
        return check_password_hash(stored_hash, password)
