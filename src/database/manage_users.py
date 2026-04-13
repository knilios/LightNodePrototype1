from __future__ import annotations

import argparse
import getpass

from src.core.auth import create_user, list_users, reset_password, revoke_user_tokens, set_user_active
from src.database.db import init_database


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage LightNode users (host-only)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_cmd = subparsers.add_parser("create-user", help="Create a new user")
    create_cmd.add_argument("username")
    create_cmd.add_argument("--role", default="user")

    reset_cmd = subparsers.add_parser("reset-password", help="Reset a user's password")
    reset_cmd.add_argument("username")

    deactivate_cmd = subparsers.add_parser("deactivate-user", help="Deactivate a user and revoke tokens")
    deactivate_cmd.add_argument("username")

    activate_cmd = subparsers.add_parser("activate-user", help="Activate a user")
    activate_cmd.add_argument("username")

    subparsers.add_parser("list-users", help="List all users")

    return parser


def main() -> None:
    init_database()
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "create-user":
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise SystemExit("Passwords do not match")

        user = create_user(args.username, password, role=args.role)
        print(f"Created user: {user['username']} ({user['id']})")
        return

    if args.command == "reset-password":
        new_password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm new password: ")
        if new_password != confirm:
            raise SystemExit("Passwords do not match")

        if not reset_password(args.username, new_password):
            raise SystemExit("User not found")
        print("Password updated")
        return

    if args.command == "deactivate-user":
        if not set_user_active(args.username, False):
            raise SystemExit("User not found")

        users = [u for u in list_users() if u["username"] == args.username.strip().lower()]
        if users:
            revoke_user_tokens(users[0]["id"])
        print("User deactivated and tokens revoked")
        return

    if args.command == "activate-user":
        if not set_user_active(args.username, True):
            raise SystemExit("User not found")
        print("User activated")
        return

    if args.command == "list-users":
        users = list_users()
        if not users:
            print("No users")
            return
        for user in users:
            state = "active" if int(user["is_active"]) == 1 else "inactive"
            print(f"{user['username']} | {user['role']} | {state} | {user['id']}")


if __name__ == "__main__":
    main()
