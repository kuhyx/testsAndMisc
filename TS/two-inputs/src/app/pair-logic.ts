export function findValidPairs(
  x: number | null,
  y: number | null,
  z: number | null,
  ml: number | null,
): Array<[number, number]> | null {
  if (x === null || y === null || z === null || ml === null) {
    console.error("findValidPairs, some value is null");
    return null;
  }

  const results: Array<[number, number]> = [];

  for (let n1 = y; n1 <= ml - y && n1 <= z; n1 += x) {
    const n2 = ml - n1;
    if (n2 % x === 0 && n2 >= y && n2 <= z) {
      results.push([n1, n2]);
    }
  }

  return results;
}

export function findCorrespondingValue(
  pairs: Array<[number, number]>,
  number: number,
): [number, number] | null {
  for (let index = 0; index < pairs.length; index += 1) {
    if (pairs[index][0] === number) {
      return [pairs[index][1], index];
    } else if (pairs[index][1] === number) {
      return [pairs[index][0], index];
    }
  }
  console.error(
    "No corresponding value found for the provided number in the pairs.",
    pairs,
    number,
  );
  return null;
}

export function changeIndex(
  currentValue: number,
  direction: boolean,
  length: number | undefined,
): number {
  if (typeof length !== "undefined") {
    if (direction) {
      if (currentValue + 1 > length - 1) {
        return 0;
      }
      return currentValue + 1;
    } else {
      if (currentValue - 1 < 0) {
        return length - 1;
      }
      return currentValue - 1;
    }
  } else {
    console.error(
      "appComponent, changeIndex, length is undefined!",
      length,
    );
  }
  return currentValue;
}
