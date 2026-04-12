/*
 * Vocabulary Learning Curve Analyzer - thin driver.
 */

#include "vocabulary.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Print excerpt words */
static void print_excerpt(const VocabContext *ctx, int start, int length)
{
    for (int i = start; i < start + length; i++)
    {
        if (i > start)
            printf(" ");
        printf("%s", ctx->word_sequence[i]->word);
    }
}

/* Print words needed (sorted by rank) */
static void print_words_needed(const VocabContext *ctx, int start, int length)
{
    static WordEntry *unique_entries[MAX_UNIQUE_WORDS];
    static bool       seen_rank[MAX_UNIQUE_WORDS + 1];
    memset(seen_rank, 0, (ctx->num_unique_words + 1) * sizeof(bool));

    int count = 0;
    for (int i = start; i < start + length; i++)
    {
        WordEntry *entry = ctx->word_sequence[i];
        if (!seen_rank[entry->rank])
        {
            seen_rank[entry->rank]  = true;
            unique_entries[count++] = entry;
        }
    }

    for (int i = 0; i < count - 1; i++)
    {
        for (int j = i + 1; j < count; j++)
        {
            if (unique_entries[i]->rank > unique_entries[j]->rank)
            {
                WordEntry *tmp    = unique_entries[i];
                unique_entries[i] = unique_entries[j];
                unique_entries[j] = tmp;
            }
        }
    }

    for (int i = 0; i < count; i++)
    {
        if (i > 0)
            printf(", ");
        printf("%s(#%d)", unique_entries[i]->word, unique_entries[i]->rank);
    }
}

/* Print results */
static void print_results(const VocabContext *ctx, ExcerptResult *results, int max_length)
{
    printf("======================================================================\n");
    printf("VOCABULARY LEARNING CURVE\n");
    printf("======================================================================\n");
    printf("\n");
    printf("For each excerpt length, the minimum number of top-frequency\n");
    printf("words you need to learn to understand 100%%%% of some excerpt.\n");
    printf("\n");
    printf("Total words in text: %d\n", ctx->num_words);
    printf("Unique words: %d\n", ctx->num_unique_words);
    printf("\n");
    printf("----------------------------------------------------------------------\n");

    int prev_vocab = 0;
    int actual_max = max_length;
    if (actual_max > ctx->num_words)
        actual_max = ctx->num_words;

    for (int i = 0; i < actual_max; i++)
    {
        ExcerptResult *r = &results[i];
        printf("\n[Length %d] Vocab needed: %d", r->excerpt_length, r->min_vocab_needed);
        if (r->min_vocab_needed > prev_vocab)
            printf(" (+%d)", r->min_vocab_needed - prev_vocab);
        printf("\n");
        printf("  Excerpt: \"");
        print_excerpt(ctx, r->start_pos, r->excerpt_length);
        printf("\"\n");
        printf("  Words: ");
        print_words_needed(ctx, r->start_pos, r->excerpt_length);
        printf("\n");
        prev_vocab = r->min_vocab_needed;
    }

    printf("\n----------------------------------------------------------------------\n");

    if (actual_max > 0)
    {
        ExcerptResult *final = &results[actual_max - 1];
        printf("\nTo understand a %d-word excerpt,\n", final->excerpt_length);
        printf("you need to learn at minimum %d top words.\n", final->min_vocab_needed);
    }
}

static void dump_vocabulary(const VocabContext *ctx, int max_rank)
{
    printf("VOCAB_DUMP_START\n");
    for (int i = 0; i < ctx->num_unique_words; i++)
    {
        if (ctx->all_entries[i]->rank <= max_rank)
            printf("%s;%d\n", ctx->all_entries[i]->word, ctx->all_entries[i]->rank);
    }
    printf("VOCAB_DUMP_END\n");
}

static void print_longest_excerpt_result(const VocabContext *ctx, int max_vocab, int best_start,
                                         int best_length)
{
    printf("======================================================================\n");
    printf("INVERSE MODE: LONGEST EXCERPT WITH TOP %d WORDS\n", max_vocab);
    printf("======================================================================\n");
    printf("\n");
    printf("Total words in text: %d\n", ctx->num_words);
    printf("Unique words: %d\n", ctx->num_unique_words);
    printf("Vocabulary limit: top %d words\n", max_vocab);
    printf("\n");
    printf("----------------------------------------------------------------------\n");
    printf("\n");

    if (best_length == 0)
    {
        printf("No valid excerpt found with top %d words.\n", max_vocab);
        printf("The text may require rarer words from the very beginning.\n");
    }
    else
    {
        printf("LONGEST EXCERPT: %d words\n", best_length);
        printf("Position: words %d to %d\n", best_start + 1, best_start + best_length);
        printf("\n");
        printf("Excerpt:\n  \"");
        print_excerpt(ctx, best_start, best_length);
        printf("\"\n");
        printf("\n");

        int         max_rank_used = 0;
        const char *rarest_word   = NULL;
        for (int i = best_start; i < best_start + best_length; i++)
        {
            if (ctx->word_sequence[i]->rank > max_rank_used)
            {
                max_rank_used = ctx->word_sequence[i]->rank;
                rarest_word   = ctx->word_sequence[i]->word;
            }
        }
        // cppcheck-suppress nullPointer
        printf("Rarest word used: %s (#%d)\n", rarest_word, max_rank_used);

        static bool seen_rank[MAX_UNIQUE_WORDS + 1];
        memset(seen_rank, 0, (ctx->num_unique_words + 1) * sizeof(bool));
        int unique_count = 0;
        for (int i = best_start; i < best_start + best_length; i++)
        {
            if (!seen_rank[ctx->word_sequence[i]->rank])
            {
                seen_rank[ctx->word_sequence[i]->rank] = true;
                unique_count++;
            }
        }
        printf("Unique words in excerpt: %d\n", unique_count);
    }

    printf("\n----------------------------------------------------------------------\n");
}

int main(int argc, char *argv[])
{
    if (argc < 2)
    {
        fprintf(stderr, "Usage: %s <file.txt> [options]\n", argv[0]);
        fprintf(stderr, "\nModes:\n");
        fprintf(stderr, "  (default)         Find minimum vocab needed for each excerpt length\n");
        fprintf(stderr,
                "  --max-vocab N     INVERSE: Find longest excerpt using only top N words\n");
        fprintf(stderr, "\nOptions:\n");
        fprintf(stderr, "  max_length        Maximum excerpt length to analyze (default: 30)\n");
        fprintf(stderr, "  --dump-vocab [N]  Output all words with ranks up to N\n");
        fprintf(stderr, "\nExamples:\n");
        fprintf(stderr, "  %s book.txt 50              # Analyze excerpts up to 50 words\n",
                argv[0]);
        fprintf(stderr, "  %s book.txt --max-vocab 500 # Find longest excerpt with top 500 words\n",
                argv[0]);
        return 1;
    }

    const char *filename       = argv[1];
    int         max_length     = 30;
    bool        dump_vocab     = false;
    int         dump_max_rank  = 0;
    int         max_vocab_mode = 0;

    for (int i = 2; i < argc; i++)
    {
        if (strcmp(argv[i], "--dump-vocab") == 0)
        {
            dump_vocab = true;
            if (i + 1 < argc && argv[i + 1][0] != '-')
                dump_max_rank = atoi(argv[++i]);
        }
        else if (strcmp(argv[i], "--max-vocab") == 0)
        {
            if (i + 1 < argc)
            {
                max_vocab_mode = atoi(argv[++i]);
                if (max_vocab_mode < 1)
                {
                    fprintf(stderr, "Error: --max-vocab requires a positive number\n");
                    return 1;
                }
            }
            else
            {
                fprintf(stderr, "Error: --max-vocab requires a number\n");
                return 1;
            }
        }
        else if (argv[i][0] != '-')
        {
            max_length = atoi(argv[i]);
            if (max_length < 1)
                max_length = 1;
            if (max_length > 1000)
                max_length = 1000;
        }
    }

    VocabContext ctx;
    vocab_init(&ctx);

    FILE *fp = fopen(filename, "r");
    if (!fp)
    {
        fprintf(stderr, "Cannot open file: %s\n", filename);
        return 1;
    }

    bool ok = vocab_process_stream(&ctx, fp);
    fclose(fp);

    if (!ok)
    {
        vocab_cleanup(&ctx);
        return 1;
    }

    if (ctx.num_words == 0)
    {
        fprintf(stderr, "No words found in file\n");
        vocab_cleanup(&ctx);
        return 1;
    }

    vocab_assign_ranks(&ctx);

    if (max_vocab_mode > 0)
    {
        int best_start  = 0;
        int best_length = 0;
        vocab_find_longest_excerpt(&ctx, max_vocab_mode, &best_start, &best_length);
        print_longest_excerpt_result(&ctx, max_vocab_mode, best_start, best_length);

        if (dump_vocab)
        {
            if (dump_max_rank == 0)
                dump_max_rank = max_vocab_mode;
            dump_vocabulary(&ctx, dump_max_rank);
        }

        vocab_cleanup(&ctx);
        return 0;
    }

    ExcerptResult *results = malloc(max_length * sizeof(ExcerptResult));
    if (!results)
    {
        fprintf(stderr, "Memory allocation failed\n");
        vocab_cleanup(&ctx);
        return 1;
    }

    vocab_find_optimal_excerpts(&ctx, max_length, results);
    print_results(&ctx, results, max_length);

    if (dump_vocab)
    {
        if (dump_max_rank == 0 && max_length > 0)
            dump_max_rank = results[max_length - 1].min_vocab_needed;
        if (dump_max_rank > 0)
            dump_vocabulary(&ctx, dump_max_rank);
    }

    free(results);
    vocab_cleanup(&ctx);

    return 0;
}
