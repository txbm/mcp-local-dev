import pytest
from mcp_local_dev.sandboxes.git import normalize_github_url

@pytest.mark.parametrize("input_url,expected", [
    ("git@github.com:user/repo.git", "https://github.com/user/repo.git"),
    ("http://github.com/user/repo", ValueError),
    ("user/repo", "https://github.com/user/repo"),
    ("https://github.com/user/repo", "https://github.com/user/repo"),
    ("", ValueError),
])
def test_normalize_github_url(input_url, expected):
    if expected is ValueError:
        with pytest.raises(ValueError):
            normalize_github_url(input_url)
    else:
        assert normalize_github_url(input_url) == expected
