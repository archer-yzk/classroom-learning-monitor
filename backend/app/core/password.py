"""密码散列与校验工具。

这里只保存不可直接还原的密码散列，不把用户密码明文写入数据库。
"""

import hashlib
import hmac
import secrets


ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """为密码生成随机盐并计算安全散列。"""

    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        ITERATIONS,
    ).hex()
    return f"{ALGORITHM}${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    """判断用户输入的密码是否与数据库散列一致。"""

    try:
        algorithm, iterations_text, salt, expected_digest = stored_hash.split("$", 3)
        if algorithm != ALGORITHM:
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations_text),
        ).hex()
        return hmac.compare_digest(digest, expected_digest)
    except (TypeError, ValueError):
        return False
