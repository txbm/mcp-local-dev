import { mean, median, mode } from '../src/core.js';

const sampleNumbers = [1.0, 2.0, 2.0, 3.0, 4.0];
const emptySequence = [];
const multiModalSequence = [1.0, 1.0, 2.0, 2.0, 3.0];

describe('Statistical functions', () => {
  describe('mean', () => {
    test('calculates mean of numbers correctly', () => {
      expect(mean(sampleNumbers)).toBe(2.4);
    });

    test('throws error for empty sequence', () => {
      expect(() => mean(emptySequence)).toThrow('empty sequence');
    });
  });

  describe('median', () => {
    test('calculates median with odd length sequence', () => {
      expect(median(sampleNumbers)).toBe(2.0);
    });

    test('throws error for empty sequence', () => {
      expect(() => median(emptySequence)).toThrow('empty sequence');
    });
  });

  describe('mode', () => {
    test('finds most common value', () => {
      expect(mode(sampleNumbers)).toBe(2.0);
    });

    test('throws error for multiple modes', () => {
      expect(() => mode(multiModalSequence)).toThrow('Multiple modes');
    });

    test('throws error for empty sequence', () => {
      expect(() => mode(emptySequence)).toThrow('empty sequence');
    });
  });
});
