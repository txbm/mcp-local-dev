"""Core statistical functions."""

def mean(numbers: list[float]) -> float:
    """Calculate arithmetic mean of numbers."""
    if not numbers:
        raise ValueError("Cannot calculate mean of empty sequence")
    return sum(numbers) / len(numbers)

def median(numbers: list[float]) -> float:
    """Calculate median of numbers."""
    if not numbers:
        raise ValueError("Cannot calculate median of empty sequence")
    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_nums[mid-1] + sorted_nums[mid]) / 2
    return sorted_nums[mid]

def mode(numbers: list[float]) -> float:
    """Find mode (most common value) in numbers."""
    if not numbers:
        raise ValueError("Cannot calculate mode of empty sequence")
    counts = {}
    for n in numbers:
        counts[n] = counts.get(n, 0) + 1
    max_count = max(counts.values())
    modes = [n for n, count in counts.items() if count == max_count]
    if len(modes) > 1:
        raise ValueError("Multiple modes found")
    return modes[0]
