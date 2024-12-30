"""Runtime binary specifications."""

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
        "api_url": "https://api.github.com/repos/astral-sh/uv",
        "binary_path": "uv"
    }
}
