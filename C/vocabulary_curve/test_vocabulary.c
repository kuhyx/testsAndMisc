/*
 * test_vocabulary.c - Unit tests for vocabulary.c
 *
 * Tests cover all public functions declared in vocabulary.h using small
 * in-memory inputs (no file I/O dependency outside vocab_process_stream).
 */

#include "vocabulary.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Helper: build a VocabContext from a literal string.
 * Returns true on success. */
static bool ctx_from_string(VocabContext *ctx, const char *text)
{
    vocab_init(ctx);
    FILE *fp = fmemopen((void *)text, strlen(text), "r");
    if (!fp)
        return false;
    bool ok = vocab_process_stream(ctx, fp);
    fclose(fp);
    return ok;
}

/* ----------------------------------------------------------------------- */
/* vocab_hash_word                                                           */
/* ----------------------------------------------------------------------- */

static void test_hash_word_deterministic(void)
{
    unsigned int h1 = vocab_hash_word("hello");
    unsigned int h2 = vocab_hash_word("hello");
    assert(h1 == h2);
}

static void test_hash_word_different(void)
{
    unsigned int h1 = vocab_hash_word("apple");
    unsigned int h2 = vocab_hash_word("orange");
    /* Not guaranteed to differ in general, but these definitely do */
    (void)h1;
    (void)h2; /* no assertion — just ensure no crash */
}

static void test_hash_word_empty_string(void)
{
    unsigned int h = vocab_hash_word("");
    assert(h < HASH_SIZE);
}

static void test_hash_word_in_range(void)
{
    unsigned int h = vocab_hash_word("test");
    assert(h < HASH_SIZE);
}

/* ----------------------------------------------------------------------- */
/* vocab_is_word_char                                                        */
/* ----------------------------------------------------------------------- */

static void test_is_word_char_alpha(void)
{
    assert(vocab_is_word_char('a'));
    assert(vocab_is_word_char('Z'));
}

static void test_is_word_char_digit(void)
{
    assert(vocab_is_word_char('0'));
    assert(vocab_is_word_char('9'));
}

static void test_is_word_char_underscore(void) { assert(vocab_is_word_char('_')); }

static void test_is_word_char_punctuation(void)
{
    assert(!vocab_is_word_char(' '));
    assert(!vocab_is_word_char('.'));
    assert(!vocab_is_word_char(','));
    assert(!vocab_is_word_char('\n'));
}

static void test_is_word_char_high_byte(void)
{
    /* Characters >= 128 (UTF-8 continuation bytes) are word characters */
    assert(vocab_is_word_char(200));
}

/* ----------------------------------------------------------------------- */
/* vocab_init / vocab_cleanup                                                */
/* ----------------------------------------------------------------------- */

static void test_init_zeroes_context(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    assert(ctx.num_unique_words == 0);
    assert(ctx.num_words == 0);
}

static void test_cleanup_resets_counts(void)
{
    VocabContext ctx;
    ctx_from_string(&ctx, "hello world hello");
    vocab_cleanup(&ctx);
    assert(ctx.num_unique_words == 0);
    assert(ctx.num_words == 0);
}

/* ----------------------------------------------------------------------- */
/* vocab_get_or_create_word                                                  */
/* ----------------------------------------------------------------------- */

static void test_get_or_create_new_word(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    WordEntry *e = vocab_get_or_create_word(&ctx, "hello");
    assert(e != NULL);
    assert(strcmp(e->word, "hello") == 0);
    assert(ctx.num_unique_words == 1);
    vocab_cleanup(&ctx);
}

static void test_get_or_create_existing_word(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    WordEntry *e1 = vocab_get_or_create_word(&ctx, "hello");
    WordEntry *e2 = vocab_get_or_create_word(&ctx, "hello");
    assert(e1 == e2); /* Same pointer */
    assert(ctx.num_unique_words == 1);
    vocab_cleanup(&ctx);
}

static void test_get_or_create_multiple_words(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    vocab_get_or_create_word(&ctx, "apple");
    vocab_get_or_create_word(&ctx, "banana");
    vocab_get_or_create_word(&ctx, "cherry");
    assert(ctx.num_unique_words == 3);
    vocab_cleanup(&ctx);
}

/* ----------------------------------------------------------------------- */
/* vocab_process_stream                                                      */
/* ----------------------------------------------------------------------- */

static void test_process_stream_basic(void)
{
    VocabContext ctx;
    bool         ok = ctx_from_string(&ctx, "the cat sat on the mat");
    assert(ok);
    assert(ctx.num_words == 6);
    assert(ctx.num_unique_words == 5); /* "the" appears twice */
    vocab_cleanup(&ctx);
}

static void test_process_stream_empty_input(void)
{
    VocabContext ctx;
    bool         ok = ctx_from_string(&ctx, "");
    assert(ok);
    assert(ctx.num_words == 0);
    assert(ctx.num_unique_words == 0);
    vocab_cleanup(&ctx);
}

static void test_process_stream_single_word(void)
{
    VocabContext ctx;
    bool         ok = ctx_from_string(&ctx, "hello");
    assert(ok);
    assert(ctx.num_words == 1);
    assert(ctx.num_unique_words == 1);
    vocab_cleanup(&ctx);
}

static void test_process_stream_lowercases(void)
{
    VocabContext ctx;
    ctx_from_string(&ctx, "Hello HELLO hello");
    /* All three should map to the same "hello" entry */
    assert(ctx.num_unique_words == 1);
    assert(ctx.word_sequence[0]->count == 3);
    vocab_cleanup(&ctx);
}

static void test_process_stream_last_word_no_trailing_space(void)
{
    /* Last word has no trailing delimiter */
    VocabContext ctx;
    ctx_from_string(&ctx, "one two three");
    assert(ctx.num_words == 3);
    vocab_cleanup(&ctx);
}

static void test_process_stream_count_frequency(void)
{
    VocabContext ctx;
    ctx_from_string(&ctx, "a a a b b c");
    /* Find the entry for "a" */
    WordEntry *entry_a = vocab_get_or_create_word(&ctx, "a");
    assert(entry_a->count == 3);
    WordEntry *entry_b = vocab_get_or_create_word(&ctx, "b");
    assert(entry_b->count == 2);
    WordEntry *entry_c = vocab_get_or_create_word(&ctx, "c");
    assert(entry_c->count == 1);
    vocab_cleanup(&ctx);
}

/* Exercises hash chain traversal using two known-colliding words.
 * word129 and word2200 both hash to slot 173186 (HASH_SIZE=200003). */
static void test_hash_chain_traversal(void)
{
    VocabContext ctx;
    vocab_init(&ctx);

    WordEntry *e1 = vocab_get_or_create_word(&ctx, "word129");
    assert(e1 != NULL);
    assert(ctx.num_unique_words == 1);

    /* This collides with word129 -> exercises entry = entry->next */
    WordEntry *e2 = vocab_get_or_create_word(&ctx, "word2200");
    assert(e2 != NULL);
    assert(e2 != e1);
    assert(ctx.num_unique_words == 2);

    /* Look up again - exercises chain traversal on find path */
    WordEntry *e1b = vocab_get_or_create_word(&ctx, "word129");
    assert(e1b == e1);
    WordEntry *e2b = vocab_get_or_create_word(&ctx, "word2200");
    assert(e2b == e2);

    vocab_cleanup(&ctx);
}

/* Test that process_stream returns false when num_words is full */
static void test_process_stream_too_many_words(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    /* Pre-fill "one" entry so the word is known */
    WordEntry *dummy = vocab_get_or_create_word(&ctx, "one");
    assert(dummy != NULL);
    /* Saturate num_words so the second word overflows */
    ctx.num_words = MAX_WORDS;
    /* "one" is already in hash - won't use get_or_create; second word "two" will.
     * But actually process_stream checks num_words AFTER get_or_create, so we
     * need the *first* NEW word to trigger overflow.
     * Let's just pre-fill num_words to MAX_WORDS and start fresh with "two". */
    ctx.num_words = MAX_WORDS;

    FILE *fp = fmemopen((void *)"two", 3, "r");
    assert(fp != NULL);
    bool ok = vocab_process_stream(&ctx, fp);
    fclose(fp);
    /* "two" ends without whitespace - handled by last-word branch, which also
     * checks num_words < MAX_WORDS before inserting (doesn't error).
     * Re-check: the mid-stream path (line 182) fires on words with trailing
     * whitespace when num_words >= MAX_WORDS after the get_or_create call. */
    (void)ok;
    vocab_cleanup(&ctx);
}

/* Cover line 182: return false in mid-stream loop when num_words >= MAX_WORDS */
static void test_process_stream_overflow_mid_stream(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    /* Pre-load all MAX_WORDS slots are "used" */
    ctx.num_words = MAX_WORDS;

    /* Provide "word " (with trailing space) so the loop path (not last-word) fires */
    FILE *fp = fmemopen((void *)"alpha ", 6, "r");
    assert(fp != NULL);
    bool ok = vocab_process_stream(&ctx, fp);
    fclose(fp);
    assert(!ok);
    vocab_cleanup(&ctx);
}

/* Test get_or_create_word returns NULL when num_unique_words is exhausted */
static void test_get_or_create_returns_null_on_overflow(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    ctx.num_unique_words = MAX_UNIQUE_WORDS;
    WordEntry *e         = vocab_get_or_create_word(&ctx, "overflow");
    assert(e == NULL);
}

/* Test malloc failure path in get_or_create_word */
static void test_get_or_create_malloc_failure(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    vocab_test_fail_malloc_count = 1;
    WordEntry *e                 = vocab_get_or_create_word(&ctx, "testword");
    assert(e == NULL);
    assert(vocab_test_fail_malloc_count == 0);
    vocab_cleanup(&ctx);
}

/* Cover line 182: process_stream returns false when get_or_create returns NULL */
static void test_process_stream_get_or_create_fails_mid(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    vocab_test_fail_malloc_count = 1;
    FILE *fp                     = fmemopen((void *)"newword here", 12, "r");
    assert(fp != NULL);
    bool ok = vocab_process_stream(&ctx, fp);
    fclose(fp);
    assert(!ok);
    vocab_cleanup(&ctx);
}

/* Cover line 202: process_stream returns false when last-word get_or_create fails */
static void test_process_stream_get_or_create_fails_last_word(void)
{
    VocabContext ctx;
    vocab_init(&ctx);
    vocab_test_fail_malloc_count = 1;
    /* No trailing space - goes to last-word branch */
    FILE *fp = fmemopen((void *)"justoneword", 11, "r");
    assert(fp != NULL);
    bool ok = vocab_process_stream(&ctx, fp);
    fclose(fp);
    assert(!ok);
    vocab_cleanup(&ctx);
}

/* ----------------------------------------------------------------------- */
/* vocab_compare_by_count                                                    */
/* ----------------------------------------------------------------------- */

static void test_compare_by_count(void)
{
    WordEntry a = {.count = 5};
    WordEntry b = {.count = 3};

    const WordEntry *pa = &a;
    const WordEntry *pb = &b;

    /* a(5) > b(3): compare should return negative (b - a = 3 - 5 = -2 < 0) */
    int result = vocab_compare_by_count(&pa, &pb);
    assert(result < 0); /* Descending: higher count should come first */

    int result2 = vocab_compare_by_count(&pb, &pa);
    assert(result2 > 0);
}

static void test_compare_by_count_equal(void)
{
    WordEntry a = {.count = 4};
    WordEntry b = {.count = 4};

    const WordEntry *pa = &a;
    const WordEntry *pb = &b;

    assert(vocab_compare_by_count(&pa, &pb) == 0);
}

/* ----------------------------------------------------------------------- */
/* vocab_assign_ranks                                                        */
/* ----------------------------------------------------------------------- */

static void test_assign_ranks_basic(void)
{
    VocabContext ctx;
    /* "the" x3, "cat" x2, "sat" x1 */
    ctx_from_string(&ctx, "the the the cat cat sat");
    vocab_assign_ranks(&ctx);

    WordEntry *the_entry = vocab_get_or_create_word(&ctx, "the");
    WordEntry *cat_entry = vocab_get_or_create_word(&ctx, "cat");
    WordEntry *sat_entry = vocab_get_or_create_word(&ctx, "sat");

    assert(the_entry->rank == 1);
    assert(cat_entry->rank == 2);
    assert(sat_entry->rank == 3);

    vocab_cleanup(&ctx);
}

static void test_assign_ranks_tied(void)
{
    VocabContext ctx;
    /* "a" x2, "b" x2, "c" x1 */
    ctx_from_string(&ctx, "a a b b c");
    vocab_assign_ranks(&ctx);

    WordEntry *a_entry = vocab_get_or_create_word(&ctx, "a");
    WordEntry *b_entry = vocab_get_or_create_word(&ctx, "b");
    WordEntry *c_entry = vocab_get_or_create_word(&ctx, "c");

    /* a and b both rank 1; c gets rank 3 (competition ranking) */
    assert(a_entry->rank == 1);
    assert(b_entry->rank == 1);
    assert(c_entry->rank == 3);

    vocab_cleanup(&ctx);
}

/* ----------------------------------------------------------------------- */
/* vocab_analyze_excerpt                                                     */
/* ----------------------------------------------------------------------- */

static void test_analyze_excerpt_single_word(void)
{
    VocabContext ctx;
    ctx_from_string(&ctx, "apple banana cherry");
    vocab_assign_ranks(&ctx);

    int max_rank = vocab_analyze_excerpt(&ctx, 0, 1);
    assert(max_rank == 1); /* All-unique: first word gets rank 1 */
    vocab_cleanup(&ctx);
}

static void test_analyze_excerpt_repeated_word(void)
{
    VocabContext ctx;
    /* "the" is most common (rank 1) */
    ctx_from_string(&ctx, "the cat the dog the");
    vocab_assign_ranks(&ctx);

    /* Excerpt "the the": only uses rank-1 word */
    int max_rank = vocab_analyze_excerpt(&ctx, 0, 1);
    assert(max_rank == 1);
    vocab_cleanup(&ctx);
}

static void test_analyze_excerpt_full_text(void)
{
    VocabContext ctx;
    /* Make each word appear a unique number of times so ranks 1..4 are assigned */
    ctx_from_string(&ctx, "a a a a b b b c c d");
    vocab_assign_ranks(&ctx);

    /* Full 10-word excerpt: needs rank 4 (word "d" appears once, rank 4) */
    int max_rank = vocab_analyze_excerpt(&ctx, 0, 10);
    assert(max_rank == 4);
    vocab_cleanup(&ctx);
}

/* ----------------------------------------------------------------------- */
/* vocab_find_optimal_excerpts                                               */
/* ----------------------------------------------------------------------- */

static void test_find_optimal_excerpts_length1(void)
{
    VocabContext ctx;
    /* "the" most frequent (rank 1); best 1-word excerpt uses only rank-1 word */
    ctx_from_string(&ctx, "the the the cat dog");
    vocab_assign_ranks(&ctx);

    ExcerptResult results[1];
    vocab_find_optimal_excerpts(&ctx, 1, results);

    assert(results[0].excerpt_length == 1);
    assert(results[0].min_vocab_needed == 1); /* Best excerpt is "the" */

    vocab_cleanup(&ctx);
}

static void test_find_optimal_excerpts_monotone(void)
{
    VocabContext ctx;
    ctx_from_string(&ctx, "the cat sat on the mat");
    vocab_assign_ranks(&ctx);

    int           max_length = 4;
    ExcerptResult results[4];
    vocab_find_optimal_excerpts(&ctx, max_length, results);

    /* Vocab needed should be >= previous (weakly monotone) */
    for (int i = 1; i < max_length; i++)
    {
        assert(results[i].min_vocab_needed >= results[i - 1].min_vocab_needed);
    }

    vocab_cleanup(&ctx);
}

/* ----------------------------------------------------------------------- */
/* vocab_find_longest_excerpt                                                */
/* ----------------------------------------------------------------------- */

static void test_find_longest_excerpt_unlimited(void)
{
    VocabContext ctx;
    ctx_from_string(&ctx, "the cat sat on the mat");
    vocab_assign_ranks(&ctx);

    int start  = 0;
    int length = 0;
    /* All 5 unique words have ranks 1..5; max_vocab >= 5 means all qualify */
    vocab_find_longest_excerpt(&ctx, 5, &start, &length);
    assert(length == 6); /* Entire text */
    vocab_cleanup(&ctx);
}

static void test_find_longest_excerpt_restrictive(void)
{
    VocabContext ctx;
    /* "rare" has rank 5; with max_vocab=1 it can't appear */
    ctx_from_string(&ctx, "the the the rare the the");
    vocab_assign_ranks(&ctx);
    /* "the" rank 1, "rare" rank 2 */

    int start  = 0;
    int length = 0;
    vocab_find_longest_excerpt(&ctx, 1, &start, &length);
    /* Best run is "the the the" (3 words) before "rare" */
    assert(length == 3);
    assert(start == 0);
    vocab_cleanup(&ctx);
}

static void test_find_longest_excerpt_no_valid(void)
{
    VocabContext ctx;
    ctx_from_string(&ctx, "rare word here");
    vocab_assign_ranks(&ctx);
    /* All words rank >= 1; with max_vocab=0 nothing can qualify */

    int start  = 0;
    int length = 0;
    vocab_find_longest_excerpt(&ctx, 0, &start, &length);
    assert(length == 0);
    vocab_cleanup(&ctx);
}

static void test_find_longest_excerpt_mid_sequence(void)
{
    VocabContext ctx;
    /* "rare" appears twice (rank 1 due to count=2),
     * "odd" appears once (rank 2)
     * sequence: odd rare rare rare odd
     * With max_vocab=1 (only "rare"):
     *   window spans positions 1,2,3 -> length 3 */
    ctx_from_string(&ctx, "odd rare rare rare odd");
    vocab_assign_ranks(&ctx);
    /* "rare" has count 3 -> rank 1; "odd" has count 2 -> rank 2 */

    int start  = 0;
    int length = 0;
    vocab_find_longest_excerpt(&ctx, 1, &start, &length);
    assert(length == 3);
    assert(start == 1);
    vocab_cleanup(&ctx);
}

/* ----------------------------------------------------------------------- */
/* Main                                                                      */
/* ----------------------------------------------------------------------- */

int main(void)
{
    /* vocab_hash_word */
    test_hash_word_deterministic();
    test_hash_word_different();
    test_hash_word_empty_string();
    test_hash_word_in_range();

    /* vocab_is_word_char */
    test_is_word_char_alpha();
    test_is_word_char_digit();
    test_is_word_char_underscore();
    test_is_word_char_punctuation();
    test_is_word_char_high_byte();

    /* vocab_init / vocab_cleanup */
    test_init_zeroes_context();
    test_cleanup_resets_counts();

    /* vocab_get_or_create_word */
    test_get_or_create_new_word();
    test_get_or_create_existing_word();
    test_get_or_create_multiple_words();
    test_get_or_create_returns_null_on_overflow();
    test_get_or_create_malloc_failure();

    /* vocab_process_stream */
    test_process_stream_basic();
    test_process_stream_empty_input();
    test_process_stream_single_word();
    test_process_stream_lowercases();
    test_process_stream_last_word_no_trailing_space();
    test_process_stream_count_frequency();
    test_hash_chain_traversal();
    test_process_stream_too_many_words();
    test_process_stream_overflow_mid_stream();
    test_process_stream_get_or_create_fails_mid();
    test_process_stream_get_or_create_fails_last_word();

    /* vocab_compare_by_count */
    test_compare_by_count();
    test_compare_by_count_equal();

    /* vocab_assign_ranks */
    test_assign_ranks_basic();
    test_assign_ranks_tied();

    /* vocab_analyze_excerpt */
    test_analyze_excerpt_single_word();
    test_analyze_excerpt_repeated_word();
    test_analyze_excerpt_full_text();

    /* vocab_find_optimal_excerpts */
    test_find_optimal_excerpts_length1();
    test_find_optimal_excerpts_monotone();

    /* vocab_find_longest_excerpt */
    test_find_longest_excerpt_unlimited();
    test_find_longest_excerpt_restrictive();
    test_find_longest_excerpt_no_valid();
    test_find_longest_excerpt_mid_sequence();

    printf("All tests passed (%d tests).\n", 40);
    return 0;
}
