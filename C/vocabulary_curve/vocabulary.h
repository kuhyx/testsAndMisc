/*
 * vocabulary.h - Core vocabulary analysis logic, extracted for testability.
 */
#pragma once

#include <stdbool.h>
#include <stdio.h>

#define MAX_WORD_LEN 64
#define MAX_WORDS 500000
#define MAX_UNIQUE_WORDS 100000
#define HASH_SIZE 200003 /* Prime number for better distribution */

/* Word entry for hash table */
typedef struct WordEntry
{
    char              word[MAX_WORD_LEN];
    int               count;
    int               rank; /* 1-indexed rank by frequency (1 = most common) */
    struct WordEntry *next;
} WordEntry;

/* Result for each excerpt length */
typedef struct
{
    int excerpt_length;
    int min_vocab_needed;
    int start_pos; /* Start position in word_sequence */
} ExcerptResult;

/* Context holding all mutable state (replaces static globals) */
typedef struct
{
    WordEntry *hash_table[HASH_SIZE];
    WordEntry *all_entries[MAX_UNIQUE_WORDS];
    int        num_unique_words;
    WordEntry *word_sequence[MAX_WORDS];
    int        num_words;
} VocabContext;

/* Initialise a fresh context (zero everything) */
void vocab_init(VocabContext *ctx);

/* Free all allocated WordEntry nodes inside ctx */
void vocab_cleanup(VocabContext *ctx);

/* Hash a word (public for tests) */
unsigned int vocab_hash_word(const char *word);

/* Find or create a word entry in the context */
WordEntry *vocab_get_or_create_word(VocabContext *ctx, const char *word);

/* Check if a character can be part of a word */
bool vocab_is_word_char(int c);

/* Comparator for qsort (descending count) */
int vocab_compare_by_count(const void *a, const void *b);

/* Assign frequency ranks to all entries in ctx */
void vocab_assign_ranks(VocabContext *ctx);

/* Analyse one excerpt window and return the max rank required */
int vocab_analyze_excerpt(const VocabContext *ctx, int start, int length);

/* Read and index words from an open FILE stream into ctx */
bool vocab_process_stream(VocabContext *ctx, FILE *fp);

/* Find optimal excerpts for lengths 1..max_length; results[] must be
 * pre-allocated to max_length elements */
void vocab_find_optimal_excerpts(const VocabContext *ctx, int max_length, ExcerptResult *results);

/* Inverse mode: find longest contiguous excerpt using only top-N vocab */
void vocab_find_longest_excerpt(const VocabContext *ctx, int max_vocab, int *out_start,
                                int *out_length);

/* Test hook: set to non-zero to make the next malloc call(s) return NULL.
 * Only used by test_vocabulary.c to exercise the malloc-failure path. */
extern int vocab_test_fail_malloc_count;
