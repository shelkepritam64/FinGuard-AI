"""
FinGuard AI — Initial Administrator Bootstrap & Access Management Tool
=====================================================================
Securely provisions or resets administrator accounts in FinGuard AI.
Adheres strictly to zero-trust principles:
- Uses existing bcrypt password-hashing and user-storage services.
- Never hardcodes passwords, tokens, or hashes.
- Prompts for passwords securely via getpass (no terminal echo).
- Enforces strict password complexity (min 8 chars, uppercase, lowercase, digit).
- Prevents accidental creation of multiple initial administrators.
- Never silently changes user roles without explicit elevation intent.
- Records all bootstrap and reset actions to the immutable audit log.

Exact Commands:
---------------
1. Create the initial administrator:
   python scripts/seed_admin.py --email admin123@gmail.com --name "FinGuard Lead Admin"

2. Safely reset administrator password:
   python scripts/seed_admin.py --email admin123@gmail.com --reset-password

3. Explicitly promote an existing standard user to administrator:
   python scripts/seed_admin.py --email existing_user@gmail.com --promote

4. Provision an additional administrator (bypassing single-admin initial lock):
   python scripts/seed_admin.py --email second_admin@gmail.com --allow-multiple
"""

import sys
import getpass
import argparse
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

# Add backend directory to sys.path so app modules can be imported
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.user_store import user_store
from app.core.auth import hash_password


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password complexity against FinGuard AI security policy.
    Requirements:
      - Minimum 8 characters
      - At least one uppercase letter [A-Z]
      - At least one lowercase letter [a-z]
      - At least one numeric digit [0-9]

    Returns:
      (is_valid, list_of_error_reasons)
    """
    issues: List[str] = []
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        issues.append("Password must contain at least one uppercase letter (A-Z).")
    if not re.search(r"[a-z]", password):
        issues.append("Password must contain at least one lowercase letter (a-z).")
    if not re.search(r"[0-9]", password):
        issues.append("Password must contain at least one numeric digit (0-9).")

    return (len(issues) == 0, issues)


def bootstrap_admin(
    email: str,
    password: Optional[str] = None,
    full_name: str = "System Administrator",
    reset_password: bool = False,
    promote: bool = False,
    allow_multiple: bool = False,
    store = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Programmatic entrypoint to provision, elevate, or reset an administrator account.
    Safe for unit tests and automated tooling.
    """
    active_store = store or user_store
    clean_email = email.strip().lower()

    if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        return False, "Invalid email address format.", None

    existing_user = active_store.get_user_by_email(clean_email)
    admin_count = active_store.count_admin_users()

    # Case 1: Account already exists as an administrator
    if existing_user and existing_user.get("role") == "admin":
        if not reset_password:
            return (
                False,
                f"Administrator '{clean_email}' already exists. Pass --reset-password to safely update credentials.",
                existing_user
            )

        # Resetting password for existing admin
        if not password:
            return False, "New password is required to perform password reset.", None

        valid, issues = validate_password_strength(password)
        if not valid:
            return False, "Password strength validation failed: " + "; ".join(issues), None

        new_hash = hash_password(password)
        updated = active_store.update_user(
            user_id=existing_user["id"],
            password_hash=new_hash,
            status="active"
        )
        active_store.record_audit_log(
            actor_email="system:bootstrap",
            action="reset_admin_password",
            target_email=clean_email,
            details="Administrator password reset via bootstrap CLI"
        )
        return True, f"Successfully reset password for administrator '{clean_email}'.", updated

    # Case 2: Account already exists with a non-admin role
    if existing_user and existing_user.get("role") != "admin":
        if not promote:
            return (
                False,
                f"Account '{clean_email}' already exists with role '{existing_user.get('role')}'. "
                f"To prevent silent role elevation, specify --promote explicitly.",
                existing_user
            )

        # Optional password update during promotion if provided
        update_kwargs: Dict[str, Any] = {
            "user_id": existing_user["id"],
            "role": "admin",
            "status": "active"
        }
        if password:
            valid, issues = validate_password_strength(password)
            if not valid:
                return False, "Password strength validation failed: " + "; ".join(issues), None
            update_kwargs["password_hash"] = hash_password(password)

        updated = active_store.update_user(**update_kwargs)
        active_store.record_audit_log(
            actor_email="system:bootstrap",
            action="promote_user_to_admin",
            target_email=clean_email,
            details="Existing user promoted to administrator via bootstrap CLI"
        )
        return True, f"Successfully promoted user '{clean_email}' to administrator.", updated

    # Case 3: Brand-new administrator account
    # Guard: Prevent accidental creation of multiple initial administrators
    if admin_count > 0 and not allow_multiple:
        return (
            False,
            f"An administrator already exists in the system (Current count: {admin_count}). "
            f"To prevent accidental creation of multiple initial administrators, pass --allow-multiple.",
            None
        )

    if not password:
        return False, "Password is required to create a new administrator.", None

    valid, issues = validate_password_strength(password)
    if not valid:
        return False, "Password strength validation failed: " + "; ".join(issues), None

    pwd_hash = hash_password(password)
    user = active_store.create_user(
        email=clean_email,
        password_hash=pwd_hash,
        full_name=full_name.strip() or "System Administrator",
        role="admin",
        status="active"
    )

    active_store.record_audit_log(
        actor_email="system:bootstrap",
        action="seed_initial_admin",
        target_email=clean_email,
        details="Initial administrator account created via secure CLI"
    )

    return True, f"Administrator '{clean_email}' successfully created.", user


def run_interactive_password_prompt() -> str:
    """Prompt for password securely using getpass without echo, confirming match."""
    while True:
        p1 = getpass.getpass("Enter admin password (min 8 chars, upper, lower, digit): ")
        if not p1:
            print("[-] Password cannot be empty.")
            continue
        p2 = getpass.getpass("Confirm admin password: ")
        if p1 != p2:
            print("[-] Passwords do not match. Please try again.\n")
            continue
        return p1


def main():
    parser = argparse.ArgumentParser(
        description="FinGuard AI — Initial Administrator Provisioning & Access Recovery Tool"
    )
    parser.add_argument(
        "--email",
        type=str,
        help="Administrator email address (e.g. admin123@gmail.com)"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="System Administrator",
        help="Administrator display name (default: 'System Administrator')"
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Safely reset the password for an existing administrator account"
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Explicitly elevate an existing non-admin user to administrator"
    )
    parser.add_argument(
        "--allow-multiple",
        action="store_true",
        help="Allow creating an additional administrator if one already exists"
    )
    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="Password argument (reserved for non-interactive test automation; interactive prompt is default)"
    )

    args = parser.parse_args()

    email = args.email
    if not email:
        try:
            email = input("Enter admin email address: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[-] Operation cancelled.")
            sys.exit(1)

    clean_email = (email or "").strip().lower()
    if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        print("[-] Error: A valid email address is required (e.g. admin123@gmail.com).")
        sys.exit(1)

    existing_user = user_store.get_user_by_email(clean_email)
    admin_count = user_store.count_admin_users()

    # Pre-check multiple admin safety when interactive and not flagged
    allow_multiple = args.allow_multiple
    if not existing_user and admin_count > 0 and not allow_multiple:
        print(f"[!] Warning: FinGuard AI already has {admin_count} administrator(s) provisioned.")
        print("    Additional administrators should normally be created via the Admin Portal.")
        if sys.stdin.isatty():
            confirm = input("[?] Do you explicitly want to create an additional administrator? [y/N]: ").strip().lower()
            if confirm in ("y", "yes"):
                allow_multiple = True
            else:
                print("[-] Bootstrap aborted to prevent accidental creation of multiple administrators.")
                sys.exit(1)
        else:
            print("[-] Refusing to create multiple administrators without --allow-multiple.")
            sys.exit(1)

    # Pre-check non-admin existing user promotion safety
    promote = args.promote
    if existing_user and existing_user.get("role") != "admin" and not promote:
        print(f"[!] Warning: User '{clean_email}' already exists with role '{existing_user.get('role')}'.")
        print("    FinGuard AI will NEVER silently elevate user accounts to administrator.")
        if sys.stdin.isatty():
            confirm = input(f"[?] Explicitly promote '{clean_email}' to administrator? [y/N]: ").strip().lower()
            if confirm in ("y", "yes"):
                promote = True
            else:
                print("[-] Elevation cancelled. Role remains unchanged.")
                sys.exit(1)
        else:
            print("[-] Specify --promote to explicitly elevate this account to administrator.")
            sys.exit(1)

    # Pre-check existing admin without --reset-password flag
    reset_password = args.reset_password
    if existing_user and existing_user.get("role") == "admin" and not reset_password:
        print(f"[!] Administrator account '{clean_email}' already exists.")
        if sys.stdin.isatty():
            confirm = input("[?] Would you like to reset this administrator's password? [y/N]: ").strip().lower()
            if confirm in ("y", "yes"):
                reset_password = True
            else:
                print("[*] No changes made. Exiting safely.")
                sys.exit(0)
        else:
            print(f"[*] To safely reset access, run:\n    python scripts/seed_admin.py --email {clean_email} --reset-password")
            sys.exit(0)

    # Prompt for password securely using getpass
    password = args.password
    if not password:
        password = run_interactive_password_prompt()

    # Validate password strength
    valid, issues = validate_password_strength(password)
    if not valid:
        print("\n[-] Password does not satisfy security requirements:")
        for issue in issues:
            print(f"    - {issue}")
        print("\n[-] Please choose a stronger password containing uppercase, lowercase, and digits.\n")
        sys.exit(1)

    # Execute bootstrap action
    success, message, user = bootstrap_admin(
        email=clean_email,
        password=password,
        full_name=args.name,
        reset_password=reset_password,
        promote=promote,
        allow_multiple=allow_multiple
    )

    if not success:
        print(f"\n[-] Bootstrap failed: {message}\n")
        sys.exit(1)

    print(f"\n[+] {message}")
    if user:
        print(f"    User ID: {user['id']}")
        print(f"    Email:   {user['email']}")
        print(f"    Role:    {user['role']}")
        print(f"    Status:  {user['status']}")
    print("")


if __name__ == "__main__":
    main()
