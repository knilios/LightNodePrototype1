from __future__ import annotations

import argparse
import getpass

from src.core.auth import (
    create_user,
    issue_access_token_for_user,
    list_tokens,
    list_users,
    reset_password,
    revoke_token_by_id,
    revoke_user_tokens,
    set_user_active,
)
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

    token_create_cmd = subparsers.add_parser("create-access-token", help="Create host-issued access token")
    token_create_cmd.add_argument("username")
    token_create_cmd.add_argument("--days", type=int, default=30)
    token_create_cmd.add_argument("--extension-id", default=None)

    token_list_cmd = subparsers.add_parser("list-tokens", help="List tokens")
    token_list_cmd.add_argument("--username", default=None)

    token_revoke_cmd = subparsers.add_parser("revoke-token", help="Revoke token by id")
    token_revoke_cmd.add_argument("token_id")

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
        return

    if args.command == "create-access-token":
        token = issue_access_token_for_user(
            username=args.username,
            extension_id=args.extension_id,
            days_valid=args.days,
        )
        print(f"Token ID: {token['token_id']}")
        print(f"Access Token: {token['access_token']}")
        print(f"Expires At: {token['expires_at']}")
        return

    if args.command == "list-tokens":
        tokens = list_tokens(username=args.username)
        if not tokens:
            print("No tokens")
            return
        for token in tokens:
            status = "revoked" if token["revoked_at"] else "active"
            print(
                f"{token['id']} | {token['username']} | {status} | "
                f"issued={token['issued_at']} | expires={token['expires_at']} | ext={token['extension_id']}"
            )
        return

    if args.command == "revoke-token":
        if not revoke_token_by_id(args.token_id):
            raise SystemExit("Token not found or already revoked")
        print("Token revoked")
        return


if __name__ == "__main__":
    main()
