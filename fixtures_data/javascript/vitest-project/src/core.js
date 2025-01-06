export function mean(numbers) {
  if (!numbers.length) {
    throw new Error("Cannot calculate mean of empty sequence");
  }
  return numbers.reduce((sum, n) => sum + n, 0) / numbers.length;
}

export function median(numbers) {
  if (!numbers.length) {
    throw new Error("Cannot calculate median of empty sequence");
  }
  const sorted = [...numbers].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

export function mode(numbers) {
  if (!numbers.length) {
    throw new Error("Cannot calculate mode of empty sequence");
  }
  const counts = new Map();
  numbers.forEach(n => counts.set(n, (counts.get(n) || 0) + 1));
  const maxCount = Math.max(...counts.values());
  const modes = [...counts.entries()]
    .filter(([_, count]) => count === maxCount)
    .map(([n, _]) => n);
  if (modes.length > 1) {
    throw new Error("Multiple modes found");
  }
  return modes[0];
}
