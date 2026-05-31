"""Convert browser cookie exports to Playwright storage_state format.

Usage:
    python convert_cookies.py cookies.json twitter_auth.json
"""
import json
import sys
from pathlib import Path


def convert(raw: list[dict]) -> dict:
    cookies = []
    for c in raw:
        expires = c.get("expirationDate") or c.get("expires") or c.get("expiry") or -1
        same_site = c.get("sameSite") or "Lax"
        # Normalise sameSite values
        same_site_map = {
            "no_restriction": "None",
            "unspecified": "Lax",
            "lax": "Lax",
            "strict": "Strict",
            "none": "None",
        }
        same_site = same_site_map.get(same_site.lower(), same_site.capitalize())

        cookies.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "expires": int(expires) if expires != -1 else -1,
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "sameSite": same_site,
        })
    return {"cookies": cookies, "origins": []}


def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_cookies.py <input.json> <output.json>")
        sys.exit(1)

    raw_text = Path(sys.argv[1]).read_text()
    data = json.loads(raw_text)

    # Handle different export formats
    cookies = None

    if isinstance(data, list):
        cookies = data
    elif isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, list):
            cookies = inner
        elif isinstance(inner, dict):
            cookies = []
            for v in inner.values():
                if isinstance(v, list):
                    cookies.extend(v)

    if cookies is None:
        print("Could not parse cookie format. Top-level structure:")
        if isinstance(data, dict):
            print(f"  Keys: {list(data.keys())}")
            for k, v in data.items():
                print(f"  {k!r}: {type(v).__name__} — {str(v)[:80]}")
        else:
            print(f"  Type: {type(data).__name__}")
        sys.exit(1)

    result = convert(cookies)
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2))
    print(f"Converted {len(result['cookies'])} cookies → {sys.argv[2]}")


if __name__ == "__main__":
    main()
