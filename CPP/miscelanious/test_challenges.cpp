/* Tests for CPP/miscelanious: all testable functions from 4 source files */

#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

/* -----------------------------------------------------------------------
 * Include headers (not source files) - compiled separately via Makefile
 * ----------------------------------------------------------------------- */
#include "howOftenDoesCharOccur.h"
#include "quickchallenges.h"
#include "reverseString.h"
#include "solveQuadraticEquation.h"

/* -----------------------------------------------------------------------
 * Helper
 * ----------------------------------------------------------------------- */
static bool nearlyEqual(float a, float b, float eps = 1e-4f) {
  return std::fabs(a - b) < eps;
}

/* -----------------------------------------------------------------------
 * quickchallenges: sumStartEnd
 * ----------------------------------------------------------------------- */
static void test_sumStartEnd() {
  assert(sumStartEnd(0, 1000) == 500500);
  assert(sumStartEnd(1, 10) == 55);
  assert(sumStartEnd(0, 0) == 0);
  assert(sumStartEnd(5, 5) == 5);
  assert(sumStartEnd(-3, 3) == 0);
  assert(sumStartEnd(1, 1) == 1);
}

/* -----------------------------------------------------------------------
 * solveQuadraticEquation: getDelta, calculateFirstTerm, calculateSecondTerm
 * ----------------------------------------------------------------------- */
static void test_getDelta() {
  /* x^2 - 5x + 6 = 0: a=1, b=-5, c=6 => delta = 25 - 24 = 1 */
  assert(nearlyEqual(getDelta(1.0f, -5.0f, 6.0f), 1.0f));

  /* x^2 + 2x + 1 = 0: delta = 4 - 4 = 0 */
  assert(nearlyEqual(getDelta(1.0f, 2.0f, 1.0f), 0.0f));

  /* x^2 + x + 1 = 0: delta = 1 - 4 = -3 */
  assert(nearlyEqual(getDelta(1.0f, 1.0f, 1.0f), -3.0f));

  /* 2x^2 - 4x + 0 = 0: delta = 16 - 0 = 16 */
  assert(nearlyEqual(getDelta(2.0f, -4.0f, 0.0f), 16.0f));
}

static void test_calculateFirstTerm() {
  /* x^2 - 5x + 6 = 0: roots 2 and 3 */
  float delta = getDelta(1.0f, -5.0f, 6.0f);
  float x1 = calculateFirstTerm(1.0f, -5.0f, delta);
  float x2 = calculateSecondTerm(1.0f, -5.0f, delta);
  assert(nearlyEqual(x1, 2.0f));
  assert(nearlyEqual(x2, 3.0f));
}

static void test_calculateSecondTerm() {
  /* x^2 + 2x + 1 = 0: double root -1 */
  float delta = getDelta(1.0f, 2.0f, 1.0f);
  float x1 = calculateFirstTerm(1.0f, 2.0f, delta);
  float x2 = calculateSecondTerm(1.0f, 2.0f, delta);
  assert(nearlyEqual(x1, -1.0f));
  assert(nearlyEqual(x2, -1.0f));
}

static void test_quadratic_large() {
  /* 2x^2 - 4x = 0: roots 0 and 2 */
  float delta = getDelta(2.0f, -4.0f, 0.0f);
  float x1 = calculateFirstTerm(2.0f, -4.0f, delta);
  float x2 = calculateSecondTerm(2.0f, -4.0f, delta);
  /* smaller root first */
  assert(nearlyEqual(x1, 0.0f));
  assert(nearlyEqual(x2, 2.0f));
}

/* -----------------------------------------------------------------------
 * reverseString: reverseStringManual
 * ----------------------------------------------------------------------- */
static void test_reverseStringManual() {
  assert(reverseStringManual("hello") == "olleh");
  assert(reverseStringManual("abcde") == "edcba");
  assert(reverseStringManual("abcd") == "dcba");
  assert(reverseStringManual("a") == "a");
  assert(reverseStringManual("") == "");
  assert(reverseStringManual("ab") == "ba");
  assert(reverseStringManual("racecar") == "racecar");
}

/* -----------------------------------------------------------------------
 * howOftenDoesCharOccur: computeCharOccurences, printCharOccurenceVector
 * ----------------------------------------------------------------------- */
static void test_computeCharOccurences_basic() {
  auto v = computeCharOccurences("aaaabbbcca");
  assert(v.size() == 4);
  assert(v[0].c == 'a' && v[0].occurrence == 4);
  assert(v[1].c == 'b' && v[1].occurrence == 3);
  assert(v[2].c == 'c' && v[2].occurrence == 2);
  assert(v[3].c == 'a' && v[3].occurrence == 1);
}

static void test_computeCharOccurences_single() {
  auto v = computeCharOccurences("x");
  assert(v.size() == 1);
  assert(v[0].c == 'x' && v[0].occurrence == 1);
}

static void test_computeCharOccurences_empty() {
  auto v = computeCharOccurences("");
  assert(v.empty());
}

static void test_computeCharOccurences_all_same() {
  auto v = computeCharOccurences("zzzz");
  assert(v.size() == 1);
  assert(v[0].c == 'z' && v[0].occurrence == 4);
}

static void test_computeCharOccurences_alternating() {
  auto v = computeCharOccurences("ababab");
  assert(v.size() == 6);
  for (auto &e : v) {
    assert(e.occurrence == 1);
  }
}

static void test_printCharOccurenceVector_output() {
  auto v = computeCharOccurences("aab");
  /* Capture stdout */
  std::streambuf *old = std::cout.rdbuf();
  std::ostringstream oss;
  std::cout.rdbuf(oss.rdbuf());
  printCharOccurenceVector(v);
  std::cout.rdbuf(old);
  std::string out = oss.str();
  assert(out.find("\"a\"") != std::string::npos);
  assert(out.find("\"b\"") != std::string::npos);
  assert(out.find('[') != std::string::npos);
  assert(out.find(']') != std::string::npos);
}

static void test_printCharOccurenceVector_single() {
  std::vector<charOccurence> v;
  charOccurence e;
  e.c = 'x';
  e.occurrence = 3;
  v.push_back(e);
  std::streambuf *old = std::cout.rdbuf();
  std::ostringstream oss;
  std::cout.rdbuf(oss.rdbuf());
  printCharOccurenceVector(v);
  std::cout.rdbuf(old);
  std::string out = oss.str();
  assert(out.find("\"x\"") != std::string::npos);
  assert(out.find("3") != std::string::npos);
}

static void test_print_function() {
  /* print() is called inside main() - test it directly via output capture */
  std::streambuf *old = std::cout.rdbuf();
  std::ostringstream oss;
  std::cout.rdbuf(oss.rdbuf());
  print("hello test");
  print("Enter quadratic equation constants: a, b, c as in: ax^2 + bx + c = 0");
  std::cout.rdbuf(old);
  assert(oss.str().find("hello test") != std::string::npos);
  assert(oss.str().find("Enter quadratic equation constants") !=
         std::string::npos);
}

/* -----------------------------------------------------------------------
 * main
 * ----------------------------------------------------------------------- */
int main() {
  test_sumStartEnd();
  test_getDelta();
  test_calculateFirstTerm();
  test_calculateSecondTerm();
  test_quadratic_large();
  test_reverseStringManual();
  test_computeCharOccurences_basic();
  test_computeCharOccurences_single();
  test_computeCharOccurences_empty();
  test_computeCharOccurences_all_same();
  test_computeCharOccurences_alternating();
  test_printCharOccurenceVector_output();
  test_printCharOccurenceVector_single();
  test_print_function();

  std::cout << "All tests passed!\n";
  return 0;
}
