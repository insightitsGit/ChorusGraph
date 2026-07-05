#!/usr/bin/env python3
"""Apply GitHub security settings: branch protection + owner-only rulesets."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

ACCOUNTS: dict[str, list[str]] = {
    "insightitsGit": [
        "ChorusGraph",
        "PrismCortex",
        "chorus-fabric",
        "prismlibplusapi",
        "prismlib",
        "InsightPlugIn",
        "chorusmesh",
        "prismrag",
        "prismresonance",
        "vectorbridge",
        "prismlang",
    ],
    "aminparva84": [
        "InsightitsAIAgent",
        "prismlib",
        "InsightPrismRAG",
        "prismlang",
        "InsightHospital",
        "InsightShop",
        "InsightGym",
        "Insight-hotel",
        "Insight-Real-State",
        "LifewithAI",
        "xperiai.com",
        "InsightGymUSA",
        "Insighttools",
        "CustomVPN",
        "InsightResturant",
        "MonaSoleimani",
        "tbulletinb",
        "tbulletinn",
        "tbulletin",
    ],
}

RULESET_NAME = "Owner-only writes"
ADMIN_ROLE_ID = 5


def gh(*args: str, account: str | None = None) -> Any:
    cmd = ["gh"]
    if account:
        cmd.extend(["auth", "switch", "--user", account])
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        cmd = ["gh"]
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def repo_info(owner: str, repo: str) -> dict[str, Any]:
    return gh(
        "api",
        f"repos/{owner}/{repo}",
        "--jq",
        "{default_branch: .default_branch, has_issues: .has_issues, allow_forking: .allow_forking}",
    )


def list_collaborators(owner: str, repo: str) -> list[str]:
    try:
        data = gh("api", f"repos/{owner}/{repo}/collaborators", "--paginate")
        return [c["login"] for c in data]
    except RuntimeError:
        return []


def remove_collaborator(owner: str, repo: str, login: str) -> None:
    gh("api", "-X", "DELETE", f"repos/{owner}/{repo}/collaborators/{login}")
    print(f"  removed collaborator: {login}")


def ensure_issues_enabled(owner: str, repo: str, has_issues: bool) -> None:
    if has_issues:
        return
    gh("api", "-X", "PATCH", f"repos/{owner}/{repo}", "-f", "has_issues=true")
    print("  enabled issues (public comments)")


def branch_protection_payload() -> dict[str, Any]:
    return {
        "required_status_checks": None,
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": 1,
        },
        "restrictions": None,
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "required_conversation_resolution": True,
    }


def apply_branch_protection(owner: str, repo: str, branch: str) -> None:
    payload = json.dumps(branch_protection_payload())
    gh_with_input(
        [
            "api",
            "-X",
            "PUT",
            f"repos/{owner}/{repo}/branches/{branch}/protection",
            "--input",
            "-",
        ],
        payload,
    )


def gh_with_input(args: list[str], payload: str) -> Any:
    result = subprocess.run(
        ["gh", *args],
        input=payload,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def existing_ruleset_id(owner: str, repo: str) -> int | None:
    try:
        rulesets = gh("api", f"repos/{owner}/{repo}/rulesets")
    except RuntimeError:
        return None
    for rs in rulesets:
        if rs.get("name") == RULESET_NAME:
            return rs["id"]
    return None


def ruleset_payload() -> dict[str, Any]:
    return {
        "name": RULESET_NAME,
        "target": "branch",
        "enforcement": "active",
        "conditions": {
            "ref_name": {
                "include": ["~ALL"],
                "exclude": [],
            }
        },
        "rules": [
            {"type": "creation"},
            {
                "type": "update",
                "parameters": {"update_allows_fetch_and_merge": True},
            },
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "required_linear_history"},
            {
                "type": "pull_request",
                "parameters": {
                    "allowed_merge_methods": ["merge", "squash", "rebase"],
                    "dismiss_stale_reviews_on_push": True,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_approving_review_count": 1,
                    "required_review_thread_resolution": True,
                },
            },
        ],
        "bypass_actors": [
            {
                "actor_id": ADMIN_ROLE_ID,
                "actor_type": "RepositoryRole",
                "bypass_mode": "always",
            }
        ],
    }


def apply_ruleset(owner: str, repo: str) -> None:
    payload = json.dumps(ruleset_payload())
    ruleset_id = existing_ruleset_id(owner, repo)
    if ruleset_id is None:
        gh_with_input(
            ["api", "-X", "POST", f"repos/{owner}/{repo}/rulesets", "--input", "-"],
            payload,
        )
        print("  created owner-only ruleset")
    else:
        gh_with_input(
            [
                "api",
                "-X",
                "PUT",
                f"repos/{owner}/{repo}/rulesets/{ruleset_id}",
                "--input",
                "-",
            ],
            payload,
        )
        print("  updated owner-only ruleset")


def secure_repo(owner: str, repo: str) -> None:
    print(f"\n[{owner}/{repo}]")
    info = repo_info(owner, repo)
    branch = info["default_branch"]
    ensure_issues_enabled(owner, repo, info["has_issues"])

    collaborators = list_collaborators(owner, repo)
    for login in collaborators:
        if login.lower() != owner.lower():
            remove_collaborator(owner, repo, login)

    try:
        apply_branch_protection(owner, repo, branch)
        print(f"  branch protection on {branch}")
    except RuntimeError as exc:
        print(f"  branch protection skipped: {exc}")

    try:
        apply_ruleset(owner, repo)
    except RuntimeError as exc:
        print(f"  ruleset skipped: {exc}")


def main() -> int:
    errors: list[str] = []
    for account, repos in ACCOUNTS.items():
        print(f"\n========== Account: {account} ==========")
        subprocess.run(
            ["gh", "auth", "switch", "--user", account],
            check=True,
            capture_output=True,
            text=True,
        )
        for repo in repos:
            try:
                secure_repo(account, repo)
            except Exception as exc:  # noqa: BLE001 - collect and continue
                msg = f"{account}/{repo}: {exc}"
                print(f"  ERROR: {msg}")
                errors.append(msg)

    print("\n========== Summary ==========")
    if errors:
        print(f"Completed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("All repositories secured.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
