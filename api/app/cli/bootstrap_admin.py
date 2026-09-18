"""`bootstrap-admin` — one-time, out-of-band creation of the first admin
clerk account (FR-015, AC-019, backend-architecture.md §12).

Interactive by default: prompts for a username and (via `getpass`) a
password, never echoing either. Refuses to run when stdin is not a TTY
unless `--from-env` is given, in which case the credentials are read from
two environment variables (backend-architecture.md §12 names the flag but
not the exact variable names; this task's interpretation, chosen to match
the command's own name — see the two constants below) and
`must_change_password` is forced `True` — a reminder to delete both
variables is printed once the run completes.

Idempotent: if any admin clerk already exists, this is a deliberate no-op
(exit 0, nothing written) — never a second/conflicting admin account
(AC-019's third bullet). Never a migration, never a fixture, no credential
ever committed to the repo.

`bootstrap_admin()` is the callable core T-006a's seeded-account fixtures
(`admin_test`/`clerk_test`, test-strategy.md §3) call directly against a
test session — `main()` below is only the argparse/getpass/stdin wrapper
around it, so both paths go through the identical validation/creation code
(never a raw INSERT).

Exit codes: `0` created, `0` no-op (admin already exists), `1`
validation/DB error, `2` refused (non-TTY, no `--from-env`).
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core import hashing, validation
from app.core.clock import now as clock_now
from app.core.errors import DomainError, UsernameTaken
from app.db.models.clerk_account import ClerkAccount
from app.db.repositories import user as user_repo
from app.db.session import get_session

# Env var names read by `--from-env`. Not named in infrastructure.md/
# backend-architecture.md §12 beyond "reads credentials from env vars";
# these are this task's chosen names, matching the command's own name.
_USERNAME_ENV_VAR = "BOOTSTRAP_ADMIN_USERNAME"
_PASSWORD_ENV_VAR = "BOOTSTRAP_ADMIN_PASSWORD"  # noqa: S105 - env var name, not a credential

# Fixed, arbitrary 64-bit key for `pg_advisory_xact_lock` (review F2):
# check-then-insert on `any_admin_clerk_exists()` is otherwise a race under
# READ COMMITTED between two concurrent `bootstrap-admin` invocations. This
# is a transaction-scoped lock (released automatically at COMMIT/ROLLBACK),
# so it only serialises concurrent calls to this function, never blocks
# ordinary request traffic. Value has no meaning beyond being stable and
# unlikely to collide with another advisory-lock user in this codebase (none
# exists yet); derived from spelling "BOOTSTRAPADMIN" is not necessary, it
# is simply a fixed constant reserved for this one call site.
_ADVISORY_LOCK_KEY = 70150190001

_REFUSAL_MESSAGE = (
    "bootstrap-admin: refusing to run - stdin is not a TTY and --from-env "
    "was not given. Pass --from-env with the two environment variables "
    "named in this module set for a non-interactive run."
)


@dataclass(frozen=True)
class BootstrapResult:
    """Outcome of one `bootstrap_admin()` call.

    `created=False` means the idempotent no-op path was taken (an admin
    clerk already existed) — `clerk_id`/`username` are `None` in that case
    since nothing was read or written about the existing row.
    """

    created: bool
    clerk_id: int | None
    username: str | None


def bootstrap_admin(
    session: Session,
    username: str,
    password: str,
    *,
    must_change_password: bool,
) -> BootstrapResult:
    """Create the first admin clerk account, or no-op if one already exists.

    Does not commit — the caller owns the transaction boundary (`main()`
    below uses `app.db.session.get_session()`'s machinery; a test uses the
    per-test rollback `db_session` fixture instead).
    """
    # F2: serialise concurrent invocations before the existence check below
    # — otherwise two processes can both observe "no admin yet" under READ
    # COMMITTED and both insert. Released automatically at COMMIT/ROLLBACK.
    session.execute(sa.text("SELECT pg_advisory_xact_lock(:key)"), {"key": _ADVISORY_LOCK_KEY})

    if user_repo.any_admin_clerk_exists(session):
        return BootstrapResult(created=False, clerk_id=None, username=None)

    validation.validate_username(username)
    validation.validate_password(password, username=username)

    # Defensive only: the advisory lock above is what actually prevents the
    # real race (two concurrent bootstraps); nothing in this task's scope can
    # otherwise reach here with a taken username, but a clear `UsernameTaken`
    # is a better failure than a raw `IntegrityError` if it ever does.
    if user_repo.get_by_username(session, username) is not None:
        raise UsernameTaken(
            "That username is already taken.", fields={"username": "username_taken"}
        )

    # TODO(T-033): once FR-017's in-app account-creation service exists,
    # consider whether it should own this row-construction logic too — this
    # bootstrap path writes the ORM row directly since it predates that
    # service and only ever creates the very first admin account (FR-015).
    clerk = ClerkAccount(
        username=username,
        password_hash=hashing.hash_password(password),
        is_admin_clerk=True,
        must_change_password=must_change_password,
        password_is_otp=False,
        password_set_at=clock_now(),
    )
    session.add(clerk)
    session.flush()
    return BootstrapResult(created=True, clerk_id=clerk.id, username=clerk.username)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bootstrap-admin",
        description="Create the first admin clerk account (one-time, out-of-band, FR-015).",
    )
    parser.add_argument(
        "--from-env",
        action="store_true",
        help=(
            f"Read credentials from {_USERNAME_ENV_VAR}/{_PASSWORD_ENV_VAR} "
            "instead of prompting; forces must_change_password=True. Required "
            "when stdin is not a TTY."
        ),
    )
    return parser


def _read_env_credentials() -> tuple[str, str] | None:
    """Return `(username, password)` from the environment, or `None` (and
    print a one-line usage error) if either is unset/blank.

    Pops both variables out of `os.environ` immediately after reading them
    (review F1/F3) — cheap belt-and-braces so this process's own environment
    no longer carries the credential a moment after it is no longer needed;
    it does not reach the parent shell/session, which is why `main()` still
    prints the "delete them" reminder below.
    """
    env_username = os.environ.pop(_USERNAME_ENV_VAR, None)
    env_password = os.environ.pop(_PASSWORD_ENV_VAR, None)
    if not env_username or not env_password:
        print(
            f"bootstrap-admin: --from-env requires both {_USERNAME_ENV_VAR} and "
            f"{_PASSWORD_ENV_VAR} to be set.",
            file=sys.stderr,
        )
        return None
    return env_username, env_password


def _print_from_env_reminder() -> None:
    print(
        f"bootstrap-admin: reminder - delete {_USERNAME_ENV_VAR} and "
        f"{_PASSWORD_ENV_VAR} from the environment now."
    )


def _prompt_credentials() -> tuple[str, str]:
    entered_username = input("Admin username: ").strip()
    entered_password = getpass.getpass("Admin password: ")
    return entered_username, entered_password


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    from_env = args.from_env

    if from_env:
        credentials = _read_env_credentials()
        if credentials is None:
            # Review F1: print the reminder regardless of outcome, including
            # this early usage-error return.
            _print_from_env_reminder()
            return 1
        username, password = credentials
        must_change_password = True
    else:
        if not sys.stdin.isatty():
            print(_REFUSAL_MESSAGE, file=sys.stderr)
            return 2
        username, password = _prompt_credentials()
        must_change_password = False

    try:
        with contextlib.contextmanager(get_session)() as session:
            result = bootstrap_admin(
                session, username, password, must_change_password=must_change_password
            )
    except DomainError as exc:
        print(f"bootstrap-admin: {exc.message}", file=sys.stderr)
        if from_env:
            _print_from_env_reminder()
        return 1
    except Exception:  # noqa: BLE001 - never surface DB internals (may echo bound values)
        print(
            "bootstrap-admin: a database error occurred; no account was created.",
            file=sys.stderr,
        )
        if from_env:
            _print_from_env_reminder()
        return 1

    if from_env:
        _print_from_env_reminder()

    if result.created:
        print(f"bootstrap-admin: created admin clerk {result.username!r}.")
    else:
        print("bootstrap-admin: an admin clerk already exists; no action taken.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
