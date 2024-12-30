"""Runtime binary specifications and API constants."""

# GitHub API URL structure
GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPOS_PATH = "repos"
RELEASES_PATH = "releases"
ASSETS_PATH = "assets"
LATEST_PATH = "latest"

# UV repository constants
UV_OWNER = "astral-sh"
UV_REPO = "uv"
UV_API_BASE = f"{GITHUB_API_BASE}/{GITHUB_REPOS_PATH}/{UV_OWNER}/{UV_REPO}"

RUNTIME_BINARIES = {
    "node": {
        "version": "20.10.0",
        "url_template": "https://nodejs.org/dist/v{version}/node-v{version}-{platform}-{arch}.tar.gz",
        "checksum_template": "https://nodejs.org/dist/v{version}/SHASUMS256.txt",
        "binary_path": "bin/node",
        "npx_path": "bin/npx"
    },
    "bun": {
        "version": "1.0.21",
        "url_template": "https://github.com/oven-sh/bun/releases/download/bun-v{version}/bun-{platform}-{arch}.zip",
        "checksum_template": "https://github.com/oven-sh/bun/releases/download/bun-v{version}/SHASUMS.txt",
        "binary_path": "bun"
    },
    "uv": {
        "version": None,  # Will be fetched dynamically
        "binary_path": "uv"
    }
}
