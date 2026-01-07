/*
 * Vocabulary Learning Curve Analyzer
 *
 * For each excerpt length (1, 2, 3, ... N words), finds the excerpt that
 * requires the minimum number of top-frequency words to understand 100%.
 *
 * Usage:
 *   ./vocabulary_curve <file.txt> [max_length]
 *   ./vocabulary_curve test.txt 50
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdbool.h>

#define MAX_WORD_LEN 64
#define MAX_WORDS 500000
#define MAX_UNIQUE_WORDS 100000
#define HASH_SIZE 200003  /* Prime number for better distribution */

/* Word entry for hash table */
typedef struct WordEntry {
    char word[MAX_WORD_LEN];
    int count;
    int rank;  /* 1-indexed rank by frequency (1 = most common) */
    struct WordEntry *next;
} WordEntry;

/* Hash table for word lookup */
static WordEntry *hash_table[HASH_SIZE];
static WordEntry *all_entries[MAX_UNIQUE_WORDS];
static int num_unique_words = 0;

/* All words in order of appearance - store POINTERS not indices */
static WordEntry *word_sequence[MAX_WORDS];
static int num_words = 0;

/* Result for each excerpt length */
typedef struct {
    int excerpt_length;
    int min_vocab_needed;
    int start_pos;  /* Start position in word_sequence */
} ExcerptResult;

/* Simple hash function */
static unsigned int hash_word(const char *word) {
    unsigned int hash = 5381;
    int c;
    while ((c = *word++)) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash % HASH_SIZE;
}

/* Find or create word entry */
static WordEntry *get_or_create_word(const char *word) {
    unsigned int h = hash_word(word);
    WordEntry *entry = hash_table[h];

    while (entry) {
        if (strcmp(entry->word, word) == 0) {
            return entry;
        }
        entry = entry->next;
    }

    /* Create new entry */
    if (num_unique_words >= MAX_UNIQUE_WORDS) {
        fprintf(stderr, "Too many unique words\n");
        exit(1);
    }

    entry = malloc(sizeof(WordEntry));
    if (!entry) {
        fprintf(stderr, "Memory allocation failed\n");
        exit(1);
    }

    strncpy(entry->word, word, MAX_WORD_LEN - 1);
    entry->word[MAX_WORD_LEN - 1] = '\0';
    entry->count = 0;
    entry->rank = 0;
    entry->next = hash_table[h];
    hash_table[h] = entry;

    all_entries[num_unique_words++] = entry;

    return entry;
}

/* Compare function for sorting by frequency (descending) */
static int compare_by_count(const void *a, const void *b) {
    const WordEntry *wa = *(const WordEntry **)a;
    const WordEntry *wb = *(const WordEntry **)b;
    return wb->count - wa->count;  /* Descending */
}

/* Check if character is part of a word */
static bool is_word_char(int c) {
    return isalnum(c) || c == '_' || (unsigned char)c >= 128;
}

/* Read and process file */
static bool process_file(const char *filename) {
    FILE *fp = fopen(filename, "r");
    if (!fp) {
        fprintf(stderr, "Cannot open file: %s\n", filename);
        return false;
    }

    char word[MAX_WORD_LEN];
    int word_len = 0;
    int c;

    while ((c = fgetc(fp)) != EOF) {
        if (is_word_char(c)) {
            if (word_len < MAX_WORD_LEN - 1) {
                word[word_len++] = tolower(c);
            }
        } else if (word_len > 0) {
            word[word_len] = '\0';

            WordEntry *entry = get_or_create_word(word);
            entry->count++;

            if (num_words >= MAX_WORDS) {
                fprintf(stderr, "Too many words in file\n");
                fclose(fp);
                return false;
            }

            /* Store pointer directly - survives sorting */
            word_sequence[num_words++] = entry;

            word_len = 0;
        }
    }

    /* Handle last word if file doesn't end with whitespace */
    if (word_len > 0) {
        word[word_len] = '\0';
        WordEntry *entry = get_or_create_word(word);
        entry->count++;

        if (num_words < MAX_WORDS) {
            word_sequence[num_words++] = entry;
        }
    }

    fclose(fp);
    return true;
}

/* Assign ranks based on frequency */
static void assign_ranks(void) {
    /* Sort all_entries by frequency (this doesn't affect word_sequence) */
    qsort(all_entries, num_unique_words, sizeof(WordEntry *), compare_by_count);

    /* Assign 1-indexed ranks using competition ranking:
     * Words with same frequency get same rank.
     * Next rank is current_position + 1 (skipping numbers).
     * Example: counts 5,3,3,2 -> ranks 1,2,2,4 (not 1,2,3,4) */
    for (int i = 0; i < num_unique_words; i++) {
        if (i == 0) {
            all_entries[i]->rank = 1;
        } else if (all_entries[i]->count == all_entries[i-1]->count) {
            /* Same frequency as previous word - same rank */
            all_entries[i]->rank = all_entries[i-1]->rank;
        } else {
            /* Different frequency - rank is position + 1 */
            all_entries[i]->rank = i + 1;
        }
    }
}

/* Analyze excerpt and return max rank needed */
static int analyze_excerpt(int start, int length) {
    /* Track which entries we've seen using a simple visited array */
    /* We use the rank field is already assigned, so we can check uniqueness */
    static bool seen_rank[MAX_UNIQUE_WORDS + 1];
    memset(seen_rank, 0, (num_unique_words + 1) * sizeof(bool));

    int max_rank = 0;

    for (int i = start; i < start + length; i++) {
        WordEntry *entry = word_sequence[i];
        int rank = entry->rank;

        if (!seen_rank[rank]) {
            seen_rank[rank] = true;
            if (rank > max_rank) {
                max_rank = rank;
            }
        }
    }

    return max_rank;
}

/* Find optimal excerpts for each length */
static void find_optimal_excerpts(int max_length, ExcerptResult *results) {
    for (int length = 1; length <= max_length && length <= num_words; length++) {
        int best_vocab = num_unique_words + 1;
        int best_start = 0;

        /* Slide window through text */
        for (int start = 0; start <= num_words - length; start++) {
            int vocab_needed = analyze_excerpt(start, length);

            if (vocab_needed < best_vocab) {
                best_vocab = vocab_needed;
                best_start = start;
            }
        }

        results[length - 1].excerpt_length = length;
        results[length - 1].min_vocab_needed = best_vocab;
        results[length - 1].start_pos = best_start;
    }
}

/* Print excerpt words */
static void print_excerpt(int start, int length) {
    for (int i = start; i < start + length; i++) {
        if (i > start) printf(" ");
        printf("%s", word_sequence[i]->word);
    }
}

/* Print words needed (sorted by rank) */
static void print_words_needed(int start, int length) {
    /* Collect unique entries */
    static WordEntry *unique_entries[MAX_UNIQUE_WORDS];
    static bool seen_rank[MAX_UNIQUE_WORDS + 1];
    memset(seen_rank, 0, (num_unique_words + 1) * sizeof(bool));

    int count = 0;
    for (int i = start; i < start + length; i++) {
        WordEntry *entry = word_sequence[i];
        if (!seen_rank[entry->rank]) {
            seen_rank[entry->rank] = true;
            unique_entries[count++] = entry;
        }
    }

    /* Sort by rank (simple bubble sort - small arrays) */
    for (int i = 0; i < count - 1; i++) {
        for (int j = i + 1; j < count; j++) {
            if (unique_entries[i]->rank > unique_entries[j]->rank) {
                WordEntry *tmp = unique_entries[i];
                unique_entries[i] = unique_entries[j];
                unique_entries[j] = tmp;
            }
        }
    }

    /* Print */
    for (int i = 0; i < count; i++) {
        if (i > 0) printf(", ");
        printf("%s(#%d)", unique_entries[i]->word, unique_entries[i]->rank);
    }
}

/* Print results */
static void print_results(ExcerptResult *results, int max_length) {
    printf("======================================================================\n");
    printf("VOCABULARY LEARNING CURVE\n");
    printf("======================================================================\n");
    printf("\n");
    printf("For each excerpt length, the minimum number of top-frequency\n");
    printf("words you need to learn to understand 100%% of some excerpt.\n");
    printf("\n");
    printf("Total words in text: %d\n", num_words);
    printf("Unique words: %d\n", num_unique_words);
    printf("\n");
    printf("----------------------------------------------------------------------\n");

    int prev_vocab = 0;
    int actual_max = max_length;
    if (actual_max > num_words) actual_max = num_words;

    for (int i = 0; i < actual_max; i++) {
        ExcerptResult *r = &results[i];

        printf("\n[Length %d] Vocab needed: %d", r->excerpt_length, r->min_vocab_needed);
        if (r->min_vocab_needed > prev_vocab) {
            printf(" (+%d)", r->min_vocab_needed - prev_vocab);
        }
        printf("\n");

        printf("  Excerpt: \"");
        print_excerpt(r->start_pos, r->excerpt_length);
        printf("\"\n");

        printf("  Words: ");
        print_words_needed(r->start_pos, r->excerpt_length);
        printf("\n");

        prev_vocab = r->min_vocab_needed;
    }

    printf("\n----------------------------------------------------------------------\n");

    if (actual_max > 0) {
        ExcerptResult *final = &results[actual_max - 1];
        printf("\nTo understand a %d-word excerpt,\n", final->excerpt_length);
        printf("you need to learn at minimum %d top words.\n", final->min_vocab_needed);
    }
}

/* Free memory */
static void cleanup(void) {
    for (int i = 0; i < num_unique_words; i++) {
        free(all_entries[i]);
    }
}

/* Dump all vocabulary with ranks (for Python integration) */
static void dump_vocabulary(int max_rank) {
    printf("VOCAB_DUMP_START\n");
    for (int i = 0; i < num_unique_words; i++) {
        if (all_entries[i]->rank <= max_rank) {
            printf("%s;%d\n", all_entries[i]->word, all_entries[i]->rank);
        }
    }
    printf("VOCAB_DUMP_END\n");
}

/* Find longest excerpt using only top N words (inverse mode) */
static void find_longest_excerpt(int max_vocab) {
    /* Sliding window: find longest contiguous sequence where all words have rank <= max_vocab */
    int best_start = 0;
    int best_length = 0;

    int left = 0;
    for (int right = 0; right < num_words; right++) {
        /* If current word is outside our vocabulary, move left past it */
        if (word_sequence[right]->rank > max_vocab) {
            left = right + 1;
        } else {
            /* Current window [left, right] is valid */
            int length = right - left + 1;
            if (length > best_length) {
                best_length = length;
                best_start = left;
            }
        }
    }

    /* Print results */
    printf("======================================================================\n");
    printf("INVERSE MODE: LONGEST EXCERPT WITH TOP %d WORDS\n", max_vocab);
    printf("======================================================================\n");
    printf("\n");
    printf("Total words in text: %d\n", num_words);
    printf("Unique words: %d\n", num_unique_words);
    printf("Vocabulary limit: top %d words\n", max_vocab);
    printf("\n");
    printf("----------------------------------------------------------------------\n");
    printf("\n");

    if (best_length == 0) {
        printf("No valid excerpt found with top %d words.\n", max_vocab);
        printf("The text may require rarer words from the very beginning.\n");
    } else {
        printf("LONGEST EXCERPT: %d words\n", best_length);
        printf("Position: words %d to %d\n", best_start + 1, best_start + best_length);
        printf("\n");
        printf("Excerpt:\n  \"");
        print_excerpt(best_start, best_length);
        printf("\"\n");
        printf("\n");

        /* Find the rarest word in the excerpt */
        int max_rank_used = 0;
        const char *rarest_word = NULL;
        for (int i = best_start; i < best_start + best_length; i++) {
            if (word_sequence[i]->rank > max_rank_used) {
                max_rank_used = word_sequence[i]->rank;
                rarest_word = word_sequence[i]->word;
            }
        }
        printf("Rarest word used: %s (#%d)\n", rarest_word, max_rank_used);

        /* Count unique words in excerpt */
        static bool seen_rank[MAX_UNIQUE_WORDS + 1];
        memset(seen_rank, 0, (num_unique_words + 1) * sizeof(bool));
        int unique_count = 0;
        for (int i = best_start; i < best_start + best_length; i++) {
            if (!seen_rank[word_sequence[i]->rank]) {
                seen_rank[word_sequence[i]->rank] = true;
                unique_count++;
            }
        }
        printf("Unique words in excerpt: %d\n", unique_count);
    }

    printf("\n----------------------------------------------------------------------\n");
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <file.txt> [options]\n", argv[0]);
        fprintf(stderr, "\nModes:\n");
        fprintf(stderr, "  (default)         Find minimum vocab needed for each excerpt length\n");
        fprintf(stderr, "  --max-vocab N     INVERSE: Find longest excerpt using only top N words\n");
        fprintf(stderr, "\nOptions:\n");
        fprintf(stderr, "  max_length        Maximum excerpt length to analyze (default: 30)\n");
        fprintf(stderr, "  --dump-vocab [N]  Output all words with ranks up to N\n");
        fprintf(stderr, "\nExamples:\n");
        fprintf(stderr, "  %s book.txt 50              # Analyze excerpts up to 50 words\n", argv[0]);
        fprintf(stderr, "  %s book.txt --max-vocab 500 # Find longest excerpt with top 500 words\n", argv[0]);
        return 1;
    }

    const char *filename = argv[1];
    int max_length = 30;
    bool dump_vocab = false;
    int dump_max_rank = 0;
    int max_vocab_mode = 0;  /* 0 = normal mode, >0 = inverse mode with this vocab limit */

    /* Parse arguments */
    for (int i = 2; i < argc; i++) {
        if (strcmp(argv[i], "--dump-vocab") == 0) {
            dump_vocab = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') {
                dump_max_rank = atoi(argv[++i]);
            }
        } else if (strcmp(argv[i], "--max-vocab") == 0) {
            if (i + 1 < argc) {
                max_vocab_mode = atoi(argv[++i]);
                if (max_vocab_mode < 1) {
                    fprintf(stderr, "Error: --max-vocab requires a positive number\n");
                    return 1;
                }
            } else {
                fprintf(stderr, "Error: --max-vocab requires a number\n");
                return 1;
            }
        } else if (argv[i][0] != '-') {
            max_length = atoi(argv[i]);
            if (max_length < 1) max_length = 1;
            if (max_length > 1000) max_length = 1000;
        }
    }

    /* Initialize hash table */
    memset(hash_table, 0, sizeof(hash_table));

    /* Process file */
    if (!process_file(filename)) {
        return 1;
    }

    if (num_words == 0) {
        fprintf(stderr, "No words found in file\n");
        return 1;
    }

    /* Assign ranks by frequency */
    assign_ranks();

    /* Inverse mode: find longest excerpt with limited vocabulary */
    if (max_vocab_mode > 0) {
        find_longest_excerpt(max_vocab_mode);

        /* Dump vocabulary if requested */
        if (dump_vocab) {
            if (dump_max_rank == 0) dump_max_rank = max_vocab_mode;
            dump_vocabulary(dump_max_rank);
        }

        cleanup();
        return 0;
    }

    /* Normal mode: find optimal excerpts */
    ExcerptResult *results = malloc(max_length * sizeof(ExcerptResult));
    if (!results) {
        fprintf(stderr, "Memory allocation failed\n");
        cleanup();
        return 1;
    }

    find_optimal_excerpts(max_length, results);

    /* Print results */
    print_results(results, max_length);

    /* Dump vocabulary if requested */
    if (dump_vocab) {
        /* If no max_rank specified, use the max from the excerpt */
        if (dump_max_rank == 0 && max_length > 0) {
            dump_max_rank = results[max_length - 1].min_vocab_needed;
        }
        if (dump_max_rank > 0) {
            dump_vocabulary(dump_max_rank);
        }
    }

    /* Cleanup */
    free(results);
    cleanup();

    return 0;
}
