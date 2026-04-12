/*
 * vocabulary.c - Core vocabulary analysis logic.
 */
#include "vocabulary.h"

#include <ctype.h>
#include <stdlib.h>
#include <string.h>

/* Test hook: test code can set this to make the next N malloc calls fail */
int vocab_test_fail_malloc_count = 0;

static void *vocab_malloc(size_t size)
{
    if (vocab_test_fail_malloc_count > 0)
    {
        vocab_test_fail_malloc_count--;
        return NULL;
    }
    return malloc(size);
}

/* ----------------------------------------------------------------------- */
/* Initialise / cleanup                                                      */
/* ----------------------------------------------------------------------- */

void vocab_init(VocabContext *ctx)
{
    memset(ctx->hash_table, 0, sizeof(ctx->hash_table));
    ctx->num_unique_words = 0;
    ctx->num_words        = 0;
}

void vocab_cleanup(VocabContext *ctx)
{
    for (int i = 0; i < ctx->num_unique_words; i++)
    {
        free(ctx->all_entries[i]);
    }
    ctx->num_unique_words = 0;
    ctx->num_words        = 0;
}

/* ----------------------------------------------------------------------- */
/* Hash table helpers                                                        */
/* ----------------------------------------------------------------------- */

unsigned int vocab_hash_word(const char *word)
{
    unsigned int hash = 5381;
    int          c;
    while ((c = *word++))
    {
        hash = ((hash << 5) + hash) + (unsigned int)c;
    }
    return hash % HASH_SIZE;
}

WordEntry *vocab_get_or_create_word(VocabContext *ctx, const char *word)
{
    unsigned int h     = vocab_hash_word(word);
    WordEntry   *entry = ctx->hash_table[h];

    while (entry)
    {
        if (strcmp(entry->word, word) == 0)
        {
            return entry;
        }
        entry = entry->next;
    }

    /* Create new entry */
    if (ctx->num_unique_words >= MAX_UNIQUE_WORDS)
    {
        fprintf(stderr, "Too many unique words\n");
        return NULL;
    }

    entry = vocab_malloc(sizeof(WordEntry));
    if (!entry)
    {
        fprintf(stderr, "Memory allocation failed\n");
        return NULL;
    }

    strncpy(entry->word, word, MAX_WORD_LEN - 1);
    entry->word[MAX_WORD_LEN - 1] = '\0';
    entry->count                  = 0;
    entry->rank                   = 0;
    entry->next                   = ctx->hash_table[h];
    ctx->hash_table[h]            = entry;

    ctx->all_entries[ctx->num_unique_words++] = entry;

    return entry;
}

/* ----------------------------------------------------------------------- */
/* Character classification                                                  */
/* ----------------------------------------------------------------------- */

bool vocab_is_word_char(int c) { return isalnum(c) || c == '_' || (unsigned char)c >= 128; }

/* ----------------------------------------------------------------------- */
/* Sorting / ranking                                                         */
/* ----------------------------------------------------------------------- */

int vocab_compare_by_count(const void *a, const void *b)
{
    const WordEntry *wa = *(const WordEntry **)a;
    const WordEntry *wb = *(const WordEntry **)b;
    return wb->count - wa->count; /* Descending */
}

void vocab_assign_ranks(VocabContext *ctx)
{
    qsort(ctx->all_entries, ctx->num_unique_words, sizeof(WordEntry *), vocab_compare_by_count);

    for (int i = 0; i < ctx->num_unique_words; i++)
    {
        if (i == 0)
        {
            ctx->all_entries[i]->rank = 1;
        }
        else if (ctx->all_entries[i]->count == ctx->all_entries[i - 1]->count)
        {
            ctx->all_entries[i]->rank = ctx->all_entries[i - 1]->rank;
        }
        else
        {
            ctx->all_entries[i]->rank = i + 1;
        }
    }
}

/* ----------------------------------------------------------------------- */
/* Sliding-window analysis                                                   */
/* ----------------------------------------------------------------------- */

int vocab_analyze_excerpt(const VocabContext *ctx, int start, int length)
{
    static bool seen_rank[MAX_UNIQUE_WORDS + 1];
    memset(seen_rank, 0, (ctx->num_unique_words + 1) * sizeof(bool));

    int max_rank = 0;

    for (int i = start; i < start + length; i++)
    {
        WordEntry *entry = ctx->word_sequence[i];
        int        rank  = entry->rank;

        if (!seen_rank[rank])
        {
            seen_rank[rank] = true;
            if (rank > max_rank)
            {
                max_rank = rank;
            }
        }
    }

    return max_rank;
}

/* ----------------------------------------------------------------------- */
/* File I/O                                                                  */
/* ----------------------------------------------------------------------- */

bool vocab_process_stream(VocabContext *ctx, FILE *fp)
{
    char word[MAX_WORD_LEN];
    int  word_len = 0;
    int  c;

    while ((c = fgetc(fp)) != EOF)
    {
        if (vocab_is_word_char(c))
        {
            if (word_len < MAX_WORD_LEN - 1)
            {
                word[word_len++] = tolower(c);
            }
        }
        else if (word_len > 0)
        {
            word[word_len] = '\0';

            WordEntry *entry = vocab_get_or_create_word(ctx, word);
            if (!entry)
                return false;
            entry->count++;

            if (ctx->num_words >= MAX_WORDS)
            {
                fprintf(stderr, "Too many words in file\n");
                return false;
            }

            ctx->word_sequence[ctx->num_words++] = entry;
            word_len                             = 0;
        }
    }

    /* Handle last word if file doesn't end with whitespace */
    if (word_len > 0)
    {
        word[word_len]   = '\0';
        WordEntry *entry = vocab_get_or_create_word(ctx, word);
        if (!entry)
            return false;
        entry->count++;

        if (ctx->num_words < MAX_WORDS)
        {
            ctx->word_sequence[ctx->num_words++] = entry;
        }
    }

    return true;
}

/* ----------------------------------------------------------------------- */
/* Optimal-excerpt search                                                    */
/* ----------------------------------------------------------------------- */

void vocab_find_optimal_excerpts(const VocabContext *ctx, int max_length, ExcerptResult *results)
{
    for (int length = 1; length <= max_length && length <= ctx->num_words; length++)
    {
        int best_vocab = ctx->num_unique_words + 1;
        int best_start = 0;

        for (int start = 0; start <= ctx->num_words - length; start++)
        {
            int vocab_needed = vocab_analyze_excerpt(ctx, start, length);

            if (vocab_needed < best_vocab)
            {
                best_vocab = vocab_needed;
                best_start = start;
            }
        }

        results[length - 1].excerpt_length   = length;
        results[length - 1].min_vocab_needed = best_vocab;
        results[length - 1].start_pos        = best_start;
    }
}

/* ----------------------------------------------------------------------- */
/* Inverse mode                                                              */
/* ----------------------------------------------------------------------- */

void vocab_find_longest_excerpt(const VocabContext *ctx, int max_vocab, int *out_start,
                                int *out_length)
{
    int best_start  = 0;
    int best_length = 0;

    int left = 0;
    for (int right = 0; right < ctx->num_words; right++)
    {
        if (ctx->word_sequence[right]->rank > max_vocab)
        {
            left = right + 1;
        }
        else
        {
            int length = right - left + 1;
            if (length > best_length)
            {
                best_length = length;
                best_start  = left;
            }
        }
    }

    *out_start  = best_start;
    *out_length = best_length;
}
