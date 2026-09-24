"""Print a HAP admin password hash without putting the password in shell history."""

from getpass import getpass
from hashlib import pbkdf2_hmac
from secrets import token_bytes

password = getpass("HAP admin password: ")
confirmation = getpass("Confirm password: ")
if len(password) < 12 or password != confirmation:
    raise SystemExit("Passwords must match and contain at least 12 characters")
salt = token_bytes(16)
digest = pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
print(f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}")
