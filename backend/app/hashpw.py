"""Generate the APP_PASSWORD_HASH and SESSION_SECRET values for .env.

    python -m app.hashpw
"""
import getpass
import secrets
import sys

from argon2 import PasswordHasher


def main() -> int:
    pw = getpass.getpass('New app password: ')
    if len(pw) < 8:
        print('Use at least 8 characters.', file=sys.stderr)
        return 1
    if getpass.getpass('Repeat: ') != pw:
        print('Passwords did not match.', file=sys.stderr)
        return 1
    print('\nAdd these lines to .env:\n')
    # Single quotes keep the hash's '$' literal for both docker compose and python-dotenv.
    print(f"APP_PASSWORD_HASH='{PasswordHasher().hash(pw)}'")
    print(f'SESSION_SECRET={secrets.token_urlsafe(32)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
