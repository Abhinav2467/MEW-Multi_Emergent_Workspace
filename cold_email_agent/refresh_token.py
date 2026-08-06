import argparse
import json
from pathlib import Path
from agent import get_registration_link, finalize_user_token

TOKEN_PATH = Path("token.json")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a new Gmail OAuth token and save it to token.json."
    )
    parser.add_argument(
        "--code",
        help="Authorization code returned by Google after approving the consent screen.",
    )
    parser.add_argument(
        "--output",
        default="token.json",
        help="Output file for the saved credentials JSON (default: token.json).",
    )
    args = parser.parse_args()

    auth_url = get_registration_link()
    print("Open this URL in your browser and authorize the app:")
    print(auth_url)
    print()

    auth_code = args.code
    if not auth_code:
        auth_code = input("Paste the authorization code here: ").strip()

    if not auth_code:
        raise SystemExit("No authorization code provided.")

    result = finalize_user_token(auth_code)

    if isinstance(result, str) and result.startswith("Error:"):
        raise SystemExit(result)

    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError:
            pass

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Saved refreshed token to {args.output}")
    print("You can now run create_draft.py or use send_outreach(..., send_now=False) directly.")


if __name__ == "__main__":
    main()
