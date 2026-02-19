#define _GNU_SOURCE
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#define RECV_BUF 65536
#define SMALL_BUF 4096

static volatile sig_atomic_t g_stop = 0;
static const char* DOC_ROOT = NULL; // current working directory

static void on_sigint(int sig) {
  (void)sig;
  g_stop = 1;
}

static long long now_ms(void) {
  struct timespec ts;
  clock_gettime(CLOCK_REALTIME, &ts);
  return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}

static const char* getenv_default(const char* k, const char* def) {
  const char* v = getenv(k);
  return v && *v ? v : def;
}

// ---- file helpers ----
static int ensure_dir(const char* path) {
  struct stat st;
  if (stat(path, &st) == 0) {
    if (S_ISDIR(st.st_mode)) return 0;
    errno = ENOTDIR;
    return -1;
  }
  if (mkdir(path, 0775) == 0) return 0;
  return -1;
}

static char* path_join(const char* a, const char* b) {
  size_t la = strlen(a), lb = strlen(b);
  size_t n = la + 1 + lb + 1;
  char* r = malloc(n);
  if (!r) return NULL;
  snprintf(r, n, "%s/%s", a, b);
  return r;
}

static char* data_dir(void) {
  const char* env = getenv("ARTICLES_DATA_DIR");
  if (env && *env) {
    ensure_dir(env);
    return strdup(env);
  }
  char* d = path_join(DOC_ROOT ? DOC_ROOT : ".", "data");
  if (d) {
    ensure_dir(d);
  }
  return d;
}

static char* data_file(void) {
  char* d = data_dir();
  if (!d) return NULL;
  char* f = path_join(d, "articles.json");
  free(d);
  return f;
}

// Read entire file into memory (NUL-terminated). Caller frees.
static char* read_file_all(const char* path, size_t* out_len) {
  FILE* f = fopen(path, "rb");
  if (!f) {
    if (out_len) *out_len = 0;
    return NULL;
  }
  fseek(f, 0, SEEK_END);
  long sz = ftell(f);
  if (sz < 0) sz = 0;
  fseek(f, 0, SEEK_SET);
  char* buf = malloc((size_t)sz + 1);
  if (!buf) {
    fclose(f);
    return NULL;
  }
  size_t n = fread(buf, 1, (size_t)sz, f);
  fclose(f);
  buf[n] = '\0';
  if (out_len) *out_len = n;
  return buf;
}

static int write_file_all(const char* path, const char* data, size_t len) {
  FILE* f = fopen(path, "wb");
  if (!f) return -1;
  size_t n = fwrite(data, 1, len, f);
  fclose(f);
  return n == len ? 0 : -1;
}

// removed unused append_file_line (lint)

// ---- JSON helpers (minimal) ----
static size_t json_escaped_len(const char* s) {
  size_t n = 0;
  for (const char* p = s; *p; ++p) {
    if (*p == '"' || *p == '\\' || *p == '\n' || *p == '\r' || *p == '\t') n += 2;
    else n++;
  }
  return n;
}

static inline char* json_append_escaped(char* w, char c) {
  if (c == '"' || c == '\\') {
    *w++ = '\\';
    *w++ = c;
    return w;
  }
  if (c == '\n') {
    *w++ = '\\';
    *w++ = 'n';
    return w;
  }
  if (c == '\r') {
    *w++ = '\\';
    *w++ = 'r';
    return w;
  }
  if (c == '\t') {
    *w++ = '\\';
    *w++ = 't';
    return w;
  }
  *w++ = c;
  return w;
}

static void json_escape_into(char* out, const char* s) {
  char* w = out;
  for (const char* p = s; *p; ++p) w = json_append_escaped(w, *p);
  *w = '\0';
}

static char* json_escape(const char* s) {
  size_t n = json_escaped_len(s);
  char* out = (char*)malloc(n + 1);
  if (!out) return NULL;
  json_escape_into(out, s);
  return out;
}

static const char* skip_ws_commas(const char* p) {
  while (*p == ' ' || *p == '\n' || *p == '\r' || *p == '\t' || *p == ',') p++;
  return p;
}

// Parse a JSON string starting at v (after the opening quote).
// Returns malloc'd string and sets *after_end to the char after closing quote.
static inline char json_unescape_char(char c) {
  switch (c) {
  case '"':
  case '\\':
  case '/': return c;
  case 'n': return '\n';
  case 'r': return '\r';
  case 't': return '\t';
  default: return c;
  }
}

static void parse_json_string_core(const char* v, char* out, size_t* w, const char** after_end) {
  bool esc = false;
  const char* p = v;
  for (; *p; ++p) {
    char c = *p;
    if (esc) {
      out[(*w)++] = json_unescape_char(c);
      esc = false;
      continue;
    }
    if (c == '\\') {
      esc = true;
      continue;
    }
    if (c == '"') {
      *after_end = p + 1;
      break;
    }
    out[(*w)++] = c;
  }
  if (!*after_end) *after_end = p;
}

static char* parse_json_string_value(const char* v, const char** after_end) {
  char* out = (char*)malloc(strlen(v) + 1);
  if (!out) {
    *after_end = v;
    return NULL;
  }
  size_t w = 0;
  *after_end = NULL;
  parse_json_string_core(v, out, &w, after_end);
  out[w] = '\0';
  return out;
}

// NOLINTBEGIN(readability-function-size)
static const char* ensure_quoted_key(const char* key, char** to_free, size_t* out_len) {
  *to_free = NULL;
  size_t klen = strlen(key);
  if (klen == 0) {
    *out_len = 0;
    return key;
  }
  if (key[0] == '"') {
    *out_len = klen;
    return key;
  }
  char* tmp = malloc(klen + 3);
  if (!tmp) {
    *out_len = klen;
    return key;
  }
  tmp[0] = '"';
  memcpy(tmp + 1, key, klen);
  tmp[klen + 1] = '"';
  tmp[klen + 2] = '\0';
  *to_free = tmp;
  *out_len = klen + 2;
  return tmp;
}
// NOLINTEND(readability-function-size)

// NOLINTBEGIN(readability-function-size)
static char* json_get_string(const char* obj, const char* key) {
  char* free_key = NULL;
  size_t qlen = 0;
  const char* qkey = ensure_quoted_key(key, &free_key, &qlen);
  const char* p = strchr(obj, '{');
  if (!p) {
    free(free_key);
    return strdup("");
  }
  p++;
  while (*p) {
    p = skip_ws_commas(p);
    if (*p == '}' || !*p) break;
    if (*p != '"') {
      while (*p && *p != ',' && *p != '}') p++;
      continue;
    }
    const char* ks = p + 1; // start of key text
    size_t klen = 0;
    bool esc = false;
    const char* x = ks;
    for (; *x; ++x) {
      char c = *x;
      if (esc) {
        esc = false;
        continue;
      }
      if (c == '\\') {
        esc = true;
        continue;
      }
      if (c == '"') break;
      klen++;
    }
    if (*x != '"') break; // malformed
    int match = (qlen >= 2) && (klen == qlen - 2) && strncmp(ks, qkey + 1, klen) == 0;
    p = x + 1;
    while (*p == ' ' || *p == '\t') p++;
    if (*p != ':') {
      while (*p && *p != ',' && *p != '}') p++;
      if (*p == ',') p++;
      continue;
    }
    p++;
    while (*p == ' ' || *p == '\t') p++;
    if (*p == '"') {
      p++;
      const char* after = NULL;
      char* val = parse_json_string_value(p, &after);
      p = after;
      if (match) {
        free(free_key);
        return val ? val : strdup("");
      }
      free(val);
    } else {
      int depth = 0; // skip non-string value
      while (*p) {
        char c = *p;
        if (c == '{' || c == '[') depth++;
        else if (c == '}' || c == ']') {
          if (depth == 0) break;
          depth--;
        } else if (c == ',' && depth == 0) break;
        p++;
      }
    }
    if (*p == ',') p++;
  }
  free(free_key);
  return strdup("");
}
// NOLINTEND(readability-function-size)

static long long json_get_number(const char* obj, const char* key) {
  char* free_key = NULL;
  size_t qlen = 0;
  const char* qkey = ensure_quoted_key(key, &free_key, &qlen);
  const char* p = strstr(obj, qkey);
  long long val = 0;
  if (p) {
    p += qlen;
    while (*p && *p != ':') p++;
    if (*p == ':') {
      p++;
      while (*p == ' ' || *p == '\t') p++;
      char* endp = NULL;
      val = strtoll(p, &endp, 10);
    }
  }
  free(free_key);
  return val;
}

static char* json_get_top_string(const char* obj, const char* key) {
  // Top-level object string getter is same as generic one for our simple objects
  return json_get_string(obj, key);
}

// Build object JSON string; caller frees
// NOLINTBEGIN(readability-function-size)
static char* build_article_json(const char* id, const char* title, const char* author,
                                const char* body, const char* thumb, long long createdAt,
                                long long updatedAt) {
  char* et = json_escape(title ? title : "");
  char* eau = json_escape(author ? author : "");
  char* eb = json_escape(body ? body : "");
  char* eth = json_escape(thumb ? thumb : "");
  if (!et || !eau || !eb || !eth) {
    free(et);
    free(eau);
    free(eb);
    free(eth);
    return NULL;
  }
  char createdBuf[64];
  snprintf(createdBuf, sizeof(createdBuf), "%lld", createdAt);
  char updated[96] = "";
  if (updatedAt > 0) {
    snprintf(updated, sizeof(updated), ",\"updatedAt\":%lld", updatedAt);
  }
  size_t need = strlen(id) + strlen(et) + strlen(eau) + strlen(eb) + strlen(eth) +
                strlen(createdBuf) + strlen(updated) + 80;
  char* out = malloc(need);
  if (!out) {
    free(et);
    free(eau);
    free(eb);
    free(eth);
    return NULL;
  }
  snprintf(out, need,
           "{\"id\":\"%s\",\"title\":\"%s\",\"author\":\"%s\",\"body\":\"%s\""
           " ,\"thumb\":\"%s\",\"createdAt\":%s%s}",
           id, et, eau, eb, eth, createdBuf, updated);
  free(et);
  free(eau);
  free(eb);
  free(eth);
  return out;
}
// NOLINTEND(readability-function-size)

static char* gen_id(void) {
  char* out = malloc(17);
  if (!out) return NULL;
  unsigned int r = (unsigned int)rand();
  long long t = now_ms();
  snprintf(out, 17, "%08x%08x", (unsigned int)(t & 0xffffffff), r);
  return out;
}

// ---- data URL handling ----
static int b64val(int c) {
  if (c >= 'A' && c <= 'Z') return c - 'A';
  if (c >= 'a' && c <= 'z') return c - 'a' + 26;
  if (c >= '0' && c <= '9') return c - '0' + 52;
  if (c == '+') return 62;
  if (c == '/') return 63;
  return -1;
}
// NOLINTBEGIN(readability-function-size)
static unsigned char* base64_decode(const char* s, size_t len, size_t* out_len) {
  size_t pad = 0;
  if (len >= 1 && s[len - 1] == '=') pad++;
  if (len >= 2 && s[len - 2] == '=') pad++;
  size_t groups = len / 4;
  size_t outcap = groups * 3;
  if (pad <= outcap) outcap -= pad;
  else outcap = 0;
  if (outcap == 0) outcap = 1; // avoid 0-byte malloc and make room for NUL
  unsigned char* out = malloc(outcap + 1);
  if (!out) return NULL;
  size_t w = 0;
  int val = 0, valb = -8;
  for (size_t i = 0; i < len; i++) {
    int c = s[i];
    if (c == '=' || c == '\r' || c == '\n' || c == ' ' || c == '\t') continue;
    int d = b64val(c);
    if (d < 0) {
      free(out);
      return NULL;
    }
    val = (val << 6) + d;
    valb += 6;
    if (valb >= 0) {
      out[w++] = (unsigned char)((val >> valb) & 0xFF);
      valb -= 8;
    }
  }
  if (out_len) *out_len = w;
  return out;
}
// NOLINTEND(readability-function-size)
static int data_url_header(const char* data_url, char** mime_out, int* is_b64_out,
                           const char** payload_out) {
  if (strncmp(data_url, "data:", 5) != 0) return -1;
  const char* p = data_url + 5;
  const char* semi = strchr(p, ';');
  const char* comma = strchr(p, ',');
  if (!comma) return -1;
  char* mime = NULL;
  int is_b64 = 0;
  if (semi && semi < comma) {
    mime = strndup(p, (size_t)(semi - p));
    if (!strncmp(semi, ";base64", 7)) is_b64 = 1;
  } else {
    mime = strndup(p, (size_t)(comma - p));
  }
  *mime_out = mime;
  *is_b64_out = is_b64;
  *payload_out = comma + 1;
  return 0;
}

static unsigned char* percent_decode_alloc(const char* s, size_t* out_len) {
  size_t L = strlen(s);
  unsigned char* bytes = (unsigned char*)malloc(L + 1);
  if (!bytes) return NULL;
  size_t w = 0;
  for (size_t i = 0; i < L; i++) {
    if (s[i] == '%' && i + 2 < L) {
      const char h[3] = {s[i + 1], s[i + 2], '\0'};
      bytes[w++] = (unsigned char)strtol(h, NULL, 16);
      i += 2;
    } else if (s[i] == '+') {
      bytes[w++] = ' ';
    } else {
      bytes[w++] = (unsigned char)s[i];
    }
  }
  if (out_len) *out_len = w;
  return bytes;
}

static int parse_data_url(const char* data_url, char** out_mime, unsigned char** out_bytes,
                          size_t* out_len) {
  char* mime = NULL;
  int is_b64 = 0;
  const char* payload = NULL;
  if (data_url_header(data_url, &mime, &is_b64, &payload) != 0) return -1;
  unsigned char* bytes = NULL;
  size_t blen = 0;
  if (is_b64) {
    bytes = base64_decode(payload, strlen(payload), &blen);
  } else {
    bytes = percent_decode_alloc(payload, &blen);
  }
  if (!bytes) {
    free(mime);
    return -1;
  }
  *out_mime = mime;
  *out_bytes = bytes;
  if (out_len) *out_len = blen;
  return 0;
}
static const char* ext_from_mime(const char* mime) {
  if (!mime) return NULL;
  if (strstr(mime, "image/png")) return "png";
  if (strstr(mime, "image/jpeg")) return "jpg";
  if (strstr(mime, "image/webp")) return "webp";
  if (strstr(mime, "image/gif")) return "gif";
  return NULL;
}

// ---- JSON array utilities ----
// NOLINTBEGIN(readability-function-size)
static int find_next_json_object(const char* t, size_t len, size_t* idx, char** out) {
  size_t i = *idx;
  int depth = 0;
  size_t start = 0;
  for (; i < len; ++i) {
    char c = t[i];
    if (c == '{') {
      if (depth == 0) start = i;
      depth++;
    } else if (c == '}') {
      depth--;
      if (depth == 0) {
        size_t end = i;
        size_t L = end - start + 1;
        char* obj = malloc(L + 1);
        if (!obj) return -1;
        memcpy(obj, t + start, L);
        obj[L] = '\0';
        *out = obj;
        *idx = i + 1;
        return 1;
      }
    }
  }
  return 0;
}
// NOLINTEND(readability-function-size)

static int push_str(char*** arr, size_t* cap, size_t* count, char* s) {
  if (*count == *cap) {
    size_t ncap = (*cap == 0) ? 8 : (*cap * 2);
    void* tmp = realloc(*arr, ncap * sizeof(char*));
    if (!tmp) return -1;
    *arr = (char**)tmp;
    *cap = ncap;
  }
  (*arr)[(*count)++] = s;
  return 0;
}

// NOLINTBEGIN(readability-function-size)
static int assemble_array(char** objs, size_t count, char** out, size_t* out_len) {
  size_t total = 2;
  for (size_t k = 0; k < count; ++k) {
    total += strlen(objs[k]);
    if (k + 1 < count) total++;
  }
  char* buf = (char*)malloc(total + 1);
  if (!buf) return -1;
  size_t w = 0;
  buf[w++] = '[';
  for (size_t k = 0; k < count; ++k) {
    size_t L = strlen(objs[k]);
    memcpy(buf + w, objs[k], L);
    w += L;
    if (k + 1 < count) buf[w++] = ',';
  }
  buf[w++] = ']';
  buf[w] = '\0';
  *out = buf;
  if (out_len) *out_len = w;
  return 0;
}
// NOLINTEND(readability-function-size)

static int write_array_to_file(const char* file, char** objs, size_t count) {
  char* out = NULL;
  size_t w = 0;
  if (assemble_array(objs, count, &out, &w)) return -1;
  int rc = write_file_all((char*)file, out, w);
  free(out);
  return rc;
}

static char* save_bytes_with_ext(const unsigned char* bytes, size_t blen, const char* ext) {
  if (!bytes || !blen) return NULL;
  const char* updir = "uploads";
  ensure_dir(updir);
  char* name = gen_id();
  if (!name) return NULL;
  const char* e = (ext && *ext) ? ext : "bin";
  size_t need = strlen(updir) + 1 + strlen(name) + 1 + strlen(e) + 1;
  char* path = malloc(need);
  if (!path) {
    free(name);
    return NULL;
  }
  snprintf(path, need, "%s/%s.%s", updir, name, e);
  free(name);
  if (write_file_all(path, (const char*)bytes, blen) != 0) {
    free(path);
    return NULL;
  }
  return path;
}

static int ensure_capacity(char** out, size_t* cap, size_t need) {
  if (need <= *cap) return 0;
  size_t newcap = need + 64;
  void* tmp = realloc(*out, newcap);
  if (!tmp) return -1;
  *out = tmp;
  *cap = newcap;
  return 0;
}

static void buf_copy(char* out, size_t* w, const char* src, size_t len) {
  memcpy(out + *w, src, len);
  *w += len;
}

static int write_saved_url(char** out, size_t* cap, size_t* w, const char* saved) {
  const char* rel = saved;
  size_t need = *w + 1 + strlen(rel) + 1;
  if (ensure_capacity(out, cap, need)) return -1;
  (*out)[(*w)++] = '/';
  memcpy((*out) + *w, rel, strlen(rel));
  *w += strlen(rel);
  return 0;
}

// NOLINTBEGIN(readability-function-size)
static int process_data_url_segment(const char* url_start, size_t url_len, char** out, size_t* cap,
                                    size_t* w, int* did) {
  char* mime = NULL;
  unsigned char* bytes = NULL;
  size_t bl = 0;
  char* urlbuf = strndup(url_start, url_len);
  if (!urlbuf) return -1;
  int rc = 0;
  if (parse_data_url(urlbuf, &mime, &bytes, &bl) == 0) {
    const char* ext = ext_from_mime(mime);
    char* saved = save_bytes_with_ext(bytes, bl, ext);
    if (saved) {
      if (write_saved_url(out, cap, w, saved) == 0) {
        *did = 1;
      } else {
        rc = -1;
      }
      free(saved);
    }
  }
  free(bytes);
  free(mime);
  free(urlbuf);
  return rc;
}
// NOLINTEND(readability-function-size)

static const char* find_src_attr(const char* p, char* quote_out) {
  const char* m = strstr(p, "src=\"");
  const char* m2 = strstr(p, "src='");
  if (m && (!m2 || m < m2)) {
    *quote_out = '"';
    return m;
  }
  if (m2) {
    *quote_out = '\'';
    return m2;
  }
  return NULL;
}

// NOLINTBEGIN(readability-function-size)
static int handle_src_segment(const char** p_in, const char* hit, char quote, char** out,
                              size_t* outcap, size_t* w, int* did) {
  size_t prefix_len = (size_t)(hit - *p_in);
  if (ensure_capacity(out, outcap, *w + prefix_len + 6)) return -1;
  buf_copy(*out, w, *p_in, prefix_len);
  memcpy(*out + *w, "src=\"", 5);
  *w += 5;
  const char* url_start = hit + 5;
  if (*url_start == '\'' || *url_start == '"') url_start++;
  const char endq = (quote == '\'') ? '\'' : '"';
  const char* url_end = strchr(url_start, endq);
  if (!url_end) {
    size_t L = strlen(url_start);
    if (ensure_capacity(out, outcap, *w + L + 1)) return -1;
    buf_copy(*out, w, url_start, L);
    *p_in = url_start + L;
    return 0;
  }
  size_t url_len = (size_t)(url_end - url_start);
  if (url_len > 5 && strncmp(url_start, "data:", 5) == 0) {
    if (process_data_url_segment(url_start, url_len, out, outcap, w, did)) return -1;
  } else {
    if (ensure_capacity(out, outcap, *w + url_len + 1)) return -1;
    buf_copy(*out, w, url_start, url_len);
  }
  if (ensure_capacity(out, outcap, *w + 1)) return -1;
  (*out)[(*w)++] = '"';
  *p_in = url_end + 1;
  return 0;
}
// NOLINTEND(readability-function-size)

// NOLINTBEGIN(readability-function-size)
static char* migrate_inline_images_in_body(const char* body, bool* changed) {
  if (!body) return NULL;
  const char* p = body;
  size_t outcap = strlen(body) + 1;
  char* out = malloc(outcap);
  if (!out) return NULL;
  size_t w = 0;
  int did = 0;
  while (*p) {
    char quote = '\0';
    const char* hit = find_src_attr(p, &quote);
    if (!hit) {
      size_t L = strlen(p);
      if (ensure_capacity(&out, &outcap, w + L + 1)) {
        free(out);
        return NULL;
      }
      buf_copy(out, &w, p, L);
      break;
    }
    if (handle_src_segment(&p, hit, quote, &out, &outcap, &w, &did)) {
      free(out);
      return NULL;
    }
  }
  out[w] = '\0';
  if (changed) *changed = did;
  return out;
}
// NOLINTEND(readability-function-size)

// ---- HTTP helpers ----
// removed unused send_str (lint)

static void send_response(int c, int code, const char* status, const char* ctype, const char* body,
                          size_t blen, bool cors) {
  char head[SMALL_BUF];
  int n = snprintf(head, sizeof(head),
                   "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\n%s\r\n", code,
                   status, ctype ? ctype : "text/plain", blen,
                   cors ? "Access-Control-Allow-Origin: *\r\n"
                          "Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS\r\n"
                          "Access-Control-Allow-Headers: Content-Type\r\n"
                        : "");
  send(c, head, (size_t)n, 0);
  if (body && blen) send(c, body, blen, 0);
}

static const char* guess_mime(const char* path) {
  const char* ext = strrchr(path, '.');
  if (!ext) return "application/octet-stream";
  ext++;
  if (!strcmp(ext, "html")) return "text/html; charset=utf-8";
  if (!strcmp(ext, "css")) return "text/css";
  if (!strcmp(ext, "js")) return "application/javascript";
  if (!strcmp(ext, "png")) return "image/png";
  if (!strcmp(ext, "jpg") || !strcmp(ext, "jpeg")) return "image/jpeg";
  if (!strcmp(ext, "webp")) return "image/webp";
  if (!strcmp(ext, "gif")) return "image/gif";
  if (!strcmp(ext, "svg")) return "image/svg+xml";
  if (!strcmp(ext, "mp4")) return "video/mp4";
  if (!strcmp(ext, "webm")) return "video/webm";
  return "application/octet-stream";
}

// ---- Data operations (NDJSON-style internal), exposed as JSON array ----
static char* ltrim_dup(const char* s) {
  while (*s && isspace((unsigned char)*s)) s++;
  return strdup(s);
}

// removed unused list_articles_json (lint)

static bool object_id_matches(const char* obj, const char* id) {
  char* got = json_get_string(obj, "\"id\"");
  bool ok = got && strcmp(got, id) == 0;
  free(got);
  return ok;
}

static char* scan_array_for_id(char* t, const char* id) {
  size_t len = strlen(t);
  size_t i = 1;
  while (1) {
    char* obj = NULL;
    int r = find_next_json_object(t, len, &i, &obj);
    if (r <= 0) break;
    if (object_id_matches(obj, id)) {
      free(t);
      return obj;
    }
    free(obj);
  }
  free(t);
  return NULL;
}

static char* find_article_by_id(const char* id) {
  char* file = data_file();
  if (!file) return NULL;
  size_t n = 0;
  char* content = read_file_all(file, &n);
  free(file);
  if (!content) return NULL;
  char* t = ltrim_dup(content);
  free(content);
  if (!t || t[0] != '[') {
    free(t);
    return NULL;
  }
  return scan_array_for_id(t, id);
}

// NOLINTBEGIN(readability-function-size)
static int rewrite_articles_map(char** out_json_updated, const char* match_id,
                                const char* patch_json, bool is_delete) {
  char* file = data_file();
  if (!file) return -1;
  size_t n = 0;
  char* content = read_file_all(file, &n);
  if (!content) {
    free(file);
    return -1;
  }
  char* t = ltrim_dup(content);
  free(content);
  if (!t) {
    free(file);
    return -1;
  }
  if (t[0] != '[') {
    FILE* f = fopen(file, "wb");
    if (f) {
      fputs("[]", f);
      fclose(f);
    }
    free(file);
    free(t);
    return -1;
  }
  size_t i = 1;
  size_t len = strlen(t);
  char** objs = NULL;
  size_t cap = 0, count = 0;
  bool found = false;
  char* updated_copy = NULL;
  while (i < len) {
    char* obj = NULL;
    int r = find_next_json_object(t, len, &i, &obj);
    if (r < 0) {
      // free accumulated objs
      for (size_t z = 0; z < count; ++z) free(objs[z]);
      free(objs);
      free(file);
      free(t);
      free(updated_copy);
      return -1;
    }
    if (r == 0) break;
    char* id = json_get_string(obj, "id");
    bool isMatch = id && strcmp(id, match_id) == 0;
    free(id);
    if (isMatch) {
      found = true;
      if (!is_delete) {
        char* title = json_get_string(obj, "title");
        char* author = json_get_string(obj, "author");
        char* body = json_get_string(obj, "body");
        char* thumb = json_get_string(obj, "thumb");
        char* ptitle = json_get_top_string(patch_json, "title");
        if (ptitle && *ptitle) {
          free(title);
          title = ptitle;
        } else free(ptitle);
        char* pauthor = json_get_top_string(patch_json, "author");
        if (pauthor && *pauthor) {
          free(author);
          author = pauthor;
        } else free(pauthor);
        char* pbody = json_get_top_string(patch_json, "body");
        if (pbody && *pbody) {
          free(body);
          body = pbody;
        } else free(pbody);
        char* pthumb = json_get_top_string(patch_json, "thumb");
        if (pthumb && *pthumb) {
          free(thumb);
          thumb = pthumb;
        } else free(pthumb);
        long long createdAt = json_get_number(obj, "\"createdAt\"");
        long long updatedAt = now_ms();
        char* obj2 = build_article_json(match_id, title, author, body, thumb, createdAt, updatedAt);
        free(title);
        free(author);
        free(body);
        free(thumb);
        free(updated_copy);
        updated_copy = strdup(obj2);
        free(obj);
        obj = obj2;
      }
    }
    if (!(isMatch && is_delete)) {
      if (push_str(&objs, &cap, &count, obj)) {
        free(obj);
        for (size_t z = 0; z < count; ++z) free(objs[z]);
        free(objs);
        free(file);
        free(t);
        free(updated_copy);
        return -1;
      }
    } else {
      free(obj);
    }
  }
  int rc = write_array_to_file(file, objs, count);
  for (size_t z = 0; z < count; ++z) free(objs[z]);
  free(objs);
  free(file);
  free(t);
  if (found && !is_delete && out_json_updated)
    *out_json_updated = updated_copy ? updated_copy : strdup("");
  else free(updated_copy);
  return found && rc == 0 ? 0 : -1;
}
// NOLINTEND(readability-function-size)

// NOLINTBEGIN(readability-function-size)
static char* create_article_from_body(const char* body_json) {
  char* title = json_get_top_string(body_json, "title");
  char* author = json_get_top_string(body_json, "author");
  char* b = json_get_top_string(body_json, "body");
  char* th = json_get_top_string(body_json, "thumb");
  char* id = gen_id();
  long long t = now_ms();
  char* obj = build_article_json(id, title, author, b, th, t, 0);
  free(title);
  free(author);
  free(b);
  free(th);
  if (!id || !obj) {
    free(id);
    free(obj);
    return NULL;
  }
  char* file = data_file();
  if (!file) {
    free(id);
    free(obj);
    return NULL;
  }
  size_t n = 0;
  char* content = read_file_all(file, &n);
  char* out = NULL;
  size_t w = 0;
  if (!content || n == 0) {
    free(content);
    char* arr_items[1] = {obj};
    assemble_array(arr_items, 1, &out, &w);
  } else {
    char* tcontent = ltrim_dup(content);
    free(content);
    if (tcontent && tcontent[0] == '[') {
      // Prepend new object
      size_t i = 1, len = strlen(tcontent);
      char** items = NULL;
      size_t cap = 0, cnt = 0;
      {
        char* dup = strdup(obj);
        if (!dup || push_str(&items, &cap, &cnt, dup)) {
          free(dup);
          free(tcontent);
          free(file);
          free(id);
          free(obj);
          return NULL;
        }
      }
      while (1) {
        char* one = NULL;
        int r = find_next_json_object(tcontent, len, &i, &one);
        if (r <= 0) {
          // if negative error, free any allocated 'one'
          if (r < 0) free(one);
          break;
        }
        if (push_str(&items, &cap, &cnt, one)) {
          free(one);
          for (size_t z = 0; z < cnt; ++z) free(items[z]);
          free(items);
          free(tcontent);
          free(file);
          free(id);
          free(obj);
          return NULL;
        }
      }
      assemble_array(items, cnt, &out, &w);
      for (size_t z = 0; z < cnt; ++z) free(items[z]);
      free(items);
    } else {
      char* arr_items[1] = {obj};
      assemble_array(arr_items, 1, &out, &w);
    }
    free(tcontent);
  }
  if (out) write_file_all(file, out, w);
  free(out);
  free(file);
  free(id);
  return obj;
}
// NOLINTEND(readability-function-size)

// ---- request handling ----
static const char* ext_from_content_type(const char* ct) {
  if (!ct) return NULL;
  if (strstr(ct, "image/png")) return "png";
  if (strstr(ct, "image/jpeg")) return "jpg";
  if (strstr(ct, "image/jpg")) return "jpg";
  if (strstr(ct, "image/webp")) return "webp";
  if (strstr(ct, "image/gif")) return "gif";
  return NULL;
}

static const char* get_qparam(const char* path, const char* key) {
  const char* q = strchr(path, '?');
  if (!q) return NULL;
  q++;
  size_t klen = strlen(key);
  while (*q) {
    if (!strncmp(q, key, klen) && q[klen] == '=') {
      return q + klen + 1;
    }
    while (*q && *q != '&') q++;
    if (*q == '&') q++;
  }
  return NULL;
}

static char* strndup_local(const char* s, size_t n) {
  char* r = malloc(n + 1);
  if (!r) return NULL;
  memcpy(r, s, n);
  r[n] = '\0';
  return r;
}

static char* save_upload(const char* body, size_t blen, const char* ext_hint) {
  if (!body || blen == 0) return NULL;
  const char* updir = "uploads";
  ensure_dir(updir);
  char* name = gen_id();
  if (!name) return NULL;
  const char* ext = (ext_hint && *ext_hint) ? ext_hint : "bin";
  size_t need = strlen(updir) + 1 + strlen(name) + 1 + strlen(ext) + 1;
  char* path = malloc(need);
  if (!path) {
    free(name);
    return NULL;
  }
  snprintf(path, need, "%s/%s.%s", updir, name, ext);
  free(name);
  if (write_file_all(path, body, blen) != 0) {
    free(path);
    return NULL;
  }
  return path;
}

// Convert a data: URL into a newly-allocated absolute URL string ("/uploads/...")
// Returns NULL on failure.
static int parse_and_save_data_url(const char* data_url, char** out_saved) {
  char* mime = NULL;
  unsigned char* bytes = NULL;
  size_t bl = 0;
  if (parse_data_url(data_url, &mime, &bytes, &bl) != 0) {
    free(mime);
    free(bytes);
    return -1;
  }
  const char* ext = ext_from_mime(mime);
  char* saved = save_bytes_with_ext(bytes, bl, ext);
  free(mime);
  free(bytes);
  if (!saved) return -1;
  *out_saved = saved;
  return 0;
}

static char* saved_to_abs_url(char* saved) {
  size_t L = strlen(saved) + 2;
  char* url = (char*)malloc(L);
  if (!url) {
    free(saved);
    return NULL;
  }
  snprintf(url, L, "/%s", saved);
  free(saved);
  return url;
}

static char* data_url_to_abs_url(const char* data_url) {
  char* saved = NULL;
  if (parse_and_save_data_url(data_url, &saved) != 0) return NULL;
  return saved_to_abs_url(saved);
}

static int migrate_thumb_if_data_url(char** pthumb) {
  char* thumb = *pthumb;
  if (!thumb || strncmp(thumb, "data:", 5) != 0) return 0;
  char* url = data_url_to_abs_url(thumb);
  if (!url) return 0;
  free(thumb);
  *pthumb = url;
  return 1;
}

// Replace inline images inside body HTML in-place. Returns 1 if changed.
static int migrate_body_inplace(char** pbody) {
  bool bchanged = false;
  char* new_body = migrate_inline_images_in_body(*pbody, &bchanged);
  if (new_body && bchanged) {
    free(*pbody);
    *pbody = new_body;
    return 1;
  }
  free(new_body);
  return 0;
}

static char* rebuild_updated_article(char* old_obj, const char* id, const char* title,
                                     const char* author, const char* body, const char* thumb,
                                     long long createdAt) {
  free(old_obj);
  return build_article_json(id ? id : "", title ? title : "", author ? author : "",
                            body ? body : "", thumb ? thumb : "", createdAt, 0);
}

static char* migrate_one_obj_if_needed(char* obj, int* changed_any) {
  char* id = json_get_string(obj, "id");
  char* title = json_get_string(obj, "title");
  char* author = json_get_string(obj, "author");
  char* body_s = json_get_string(obj, "body");
  char* thumb = json_get_string(obj, "thumb");
  long long createdAt = json_get_number(obj, "\"createdAt\"");
  int obj_changed = 0;
  obj_changed |= migrate_thumb_if_data_url(&thumb);
  obj_changed |= migrate_body_inplace(&body_s);
  if (obj_changed) {
    *changed_any = 1;
    obj = rebuild_updated_article(obj, id, title, author, body_s, thumb, createdAt);
  }
  free(id);
  free(title);
  free(author);
  free(body_s);
  free(thumb);
  return obj;
}

// NOLINTBEGIN(readability-function-size)
static void api_get_articles_array(int c) {
  char* file = data_file();
  if (!file) {
    send_response(c, 200, "OK", "application/json", "[]", 2, true);
    return;
  }
  size_t n = 0;
  char* content = read_file_all(file, &n);
  if (!content) {
    free(file);
    send_response(c, 200, "OK", "application/json", "[]", 2, true);
    return;
  }
  char* t = ltrim_dup(content);
  free(content);
  if (!t) {
    free(file);
    send_response(c, 200, "OK", "application/json", "[]", 2, true);
    return;
  }
  if (t[0] != '[') {
    free(file);
    free(t);
    send_response(c, 200, "OK", "application/json", "[]", 2, true);
    return;
  }
  size_t i = 1, len = strlen(t);
  char** objs = NULL;
  size_t cap = 0, count = 0;
  int changed = 0;
  while (1) {
    char* obj = NULL;
    int r = find_next_json_object(t, len, &i, &obj);
    if (r < 0) {
      for (size_t z = 0; z < count; ++z) free(objs[z]);
      free(objs);
      free(file);
      free(t);
      send_response(c, 500, "Internal Server Error", "application/json", "", 0, true);
      return;
    }
    if (r == 0) break;
    obj = migrate_one_obj_if_needed(obj, &changed);
    if (push_str(&objs, &cap, &count, obj)) {
      free(obj);
      for (size_t z = 0; z < count; ++z) free(objs[z]);
      free(objs);
      free(file);
      free(t);
      send_response(c, 500, "Internal Server Error", "application/json", "", 0, true);
      return;
    }
  }
  char* out = NULL;
  size_t w = 0;
  if (assemble_array(objs, count, &out, &w)) {
    for (size_t z = 0; z < count; ++z) free(objs[z]);
    free(objs);
    free(file);
    free(t);
    send_response(c, 500, "Internal Server Error", "application/json", "", 0, true);
    return;
  }
  if (changed) write_file_all(file, out, w);
  send_response(c, 200, "OK", "application/json", out, w, true);
  for (size_t z = 0; z < count; ++z) free(objs[z]);
  free(objs);
  free(out);
  free(file);
  free(t);
}
// NOLINTEND(readability-function-size)

static void persist_article_update(const char* obj, const char* title, const char* author,
                                   const char* body_s, const char* thumb, long long createdAt) {
  char* id_copy = json_get_string(obj, "id");
  char* updated =
      build_article_json(id_copy ? id_copy : "", title ? title : "", author ? author : "",
                         body_s ? body_s : "", thumb ? thumb : "", createdAt, 0);
  if (updated) {
    rewrite_articles_map(NULL, id_copy, updated, false);
    free(updated);
  }
  free(id_copy);
}

static int migrate_fields_if_needed(char** obj, char** title, char** author, char** body_s,
                                    char** thumb, long long createdAt) {
  int obj_changed = 0;
  obj_changed |= migrate_thumb_if_data_url(thumb);
  obj_changed |= migrate_body_inplace(body_s);
  if (obj_changed) {
    persist_article_update(*obj, *title, *author, *body_s, *thumb, createdAt);
    free(*obj);
    *obj = NULL;
    return 1;
  }
  return 0;
}

typedef struct {
  char* title;
  char* author;
  char* body;
  char* thumb;
  long long createdAt;
} ArticleFields;

static void load_fields(const char* obj, ArticleFields* f) {
  f->title = json_get_string(obj, "title");
  f->author = json_get_string(obj, "author");
  f->body = json_get_string(obj, "body");
  f->thumb = json_get_string(obj, "thumb");
  f->createdAt = json_get_number(obj, "\"createdAt\"");
}

static void free_fields(ArticleFields* f) {
  free(f->title);
  free(f->author);
  free(f->body);
  free(f->thumb);
}

static char* maybe_migrate_and_refresh(const char* id, char* obj) {
  ArticleFields f;
  load_fields(obj, &f);
  if (migrate_fields_if_needed(&obj, &f.title, &f.author, &f.body, &f.thumb, f.createdAt)) {
    free_fields(&f);
    return find_article_by_id(id);
  }
  free_fields(&f);
  return obj;
}

static void api_get_article_by_id(int c, const char* id) {
  char* obj = find_article_by_id(id);
  if (!obj) {
    send_response(c, 404, "Not Found", "application/json", "", 0, true);
    return;
  }
  obj = maybe_migrate_and_refresh(id, obj);
  send_response(c, 200, "OK", "application/json", obj, strlen(obj), true);
  free(obj);
}

static void api_post_article(int c, const char* body) {
  char* obj = create_article_from_body(body ? body : "");
  if (!obj) {
    send_response(c, 400, "Bad Request", "application/json", "", 0, true);
    return;
  }
  size_t L = strlen(obj);
  send_response(c, 201, "Created", "application/json", obj, L, true);
  free(obj);
}
static void api_put_article(int c, const char* id, const char* body) {
  char* updated = NULL;
  if (rewrite_articles_map(&updated, id, body ? body : "", false) == 0) {
    size_t L = strlen(updated);
    send_response(c, 200, "OK", "application/json", updated, L, true);
    free(updated);
  } else {
    send_response(c, 404, "Not Found", "application/json", "", 0, true);
  }
}
static void api_delete_article(int c, const char* id) {
  if (rewrite_articles_map(NULL, id, NULL, true) == 0) {
    send_response(c, 204, "No Content", "application/json", "", 0, true);
  } else {
    send_response(c, 404, "Not Found", "application/json", "", 0, true);
  }
}

static char* choose_ext_from(const char* path, const char* content_type) {
  const char* ext_q = get_qparam(path, "ext");
  const char* ext_from_ct = ext_from_content_type(content_type);
  const char* ext = ext_from_ct ? ext_from_ct : (ext_q ? ext_q : "bin");
  size_t elen = 0;
  while (elen < 4 && ext[elen] && isalnum((unsigned char)ext[elen])) elen++;
  return strndup_local(ext, elen ? elen : 3);
}

static void respond_saved_upload(int c, char* saved) {
  size_t L = strlen(saved) + 20;
  char* res = (char*)malloc(L);
  if (!res) {
    free(saved);
    send_response(c, 500, "Internal Server Error", "application/json", "", 0, true);
    return;
  }
  snprintf(res, L, "{\"url\":\"/%s\"}", saved);
  send_response(c, 201, "Created", "application/json", res, strlen(res), true);
  free(res);
  free(saved);
}

static void api_post_upload(int c, const char* path, const char* body, size_t blen,
                            const char* content_type) {
  char* ext_safe = choose_ext_from(path, content_type);
  if (!ext_safe) {
    send_response(c, 500, "Internal Server Error", "application/json", "", 0, true);
    return;
  }
  char* saved = save_upload(body, blen, ext_safe);
  free(ext_safe);
  if (!saved) {
    send_response(c, 500, "Internal Server Error", "application/json", "", 0, true);
    return;
  }
  respond_saved_upload(c, saved);
}

static bool path_has_id_suffix(const char* path, size_t base_len) {
  return path[base_len] == '/' && strlen(path) > base_len + 1;
}

static bool is_method(const char* m, const char* want) { return strcmp(m, want) == 0; }

static void dispatch_articles_get(int c, const char* path) {
  const char* base = "/api/articles";
  size_t bl = strlen(base);
  if (strcmp(path, base) == 0) api_get_articles_array(c);
  else if (path_has_id_suffix(path, bl)) api_get_article_by_id(c, path + bl + 1);
  else send_response(c, 404, "Not Found", "application/json", "", 0, true);
}

static void dispatch_articles_mut(int c, const char* method, const char* path, const char* body) {
  const char* base = "/api/articles";
  size_t bl = strlen(base);
  if (is_method(method, "POST") && strcmp(path, base) == 0) api_post_article(c, body);
  else if (is_method(method, "PUT") && path_has_id_suffix(path, bl))
    api_put_article(c, path + bl + 1, body);
  else if (is_method(method, "DELETE") && path_has_id_suffix(path, bl))
    api_delete_article(c, path + bl + 1);
}

static void dispatch_upload(int c, const char* method, const char* path, const char* body,
                            size_t blen, const char* content_type) {
  if (strncmp(path, "/api/upload", 12) != 0) return;
  if (is_method(method, "POST")) api_post_upload(c, path, body, blen, content_type);
}

static void handle_api(int c, const char* method, const char* path, const char* body, size_t blen,
                       const char* content_type) {
  if (!strncmp(method, "OPTIONS", 7)) {
    send_response(c, 204, "No Content", "application/json", "", 0, true);
    return;
  }
  const char* base = "/api/articles";
  size_t bl = strlen(base);
  if (strncmp(path, base, bl) == 0) {
    if (is_method(method, "GET")) dispatch_articles_get(c, path);
    else dispatch_articles_mut(c, method, path, body);
  }
  dispatch_upload(c, method, path, body, blen, content_type);
  if (strncmp(path, "/api/", 5) == 0)
    send_response(c, 404, "Not Found", "text/plain", "Not Found", 9, true);
}

static bool safe_path(const char* p) {
  if (strstr(p, "..")) return false;
  return true;
}

static void normalize_rel_path(const char* path, char* rel, size_t relsz) {
  if (!strcmp(path, "/")) snprintf(rel, relsz, "%s", "/index.html");
  else snprintf(rel, relsz, "%s", path);
}
static int read_file_to_buf(const char* full, char** out, size_t* n) {
  FILE* f = fopen(full, "rb");
  if (!f) return -1;
  fseek(f, 0, SEEK_END);
  long sz = ftell(f);
  fseek(f, 0, SEEK_SET);
  char* buf = malloc((size_t)sz);
  if (!buf) {
    fclose(f);
    return -1;
  }
  *n = fread(buf, 1, (size_t)sz, f);
  fclose(f);
  *out = buf;
  return 0;
}
static void send_cached_or_plain(int c, const char* rel, const char* mime, const char* buf,
                                 size_t n) {
  int is_upload = (strncmp(rel, "/uploads/", 9) == 0);
  if (is_upload) {
    char head[SMALL_BUF];
    int hlen = snprintf(head, sizeof(head),
                        "HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: "
                        "%zu\r\nCache-Control: public, max-age=31536000, immutable\r\n\r\n",
                        mime, (size_t)n);
    send(c, head, (size_t)hlen, 0);
    if (n) send(c, buf, n, 0);
  } else {
    send_response(c, 200, "OK", mime, buf, n, false);
  }
}
static void handle_static(int c, const char* path) {
  char rel[SMALL_BUF];
  normalize_rel_path(path, rel, sizeof(rel));
  if (!safe_path(rel)) {
    send_response(c, 403, "Forbidden", "text/plain", "Forbidden", 9, false);
    return;
  }
  char full[SMALL_BUF * 2];
  snprintf(full, sizeof(full), "%s%s", DOC_ROOT ? DOC_ROOT : ".", rel);
  char* buf = NULL;
  size_t n = 0;
  if (read_file_to_buf(full, &buf, &n) != 0) {
    send_response(c, 404, "Not Found", "text/plain", "Not Found", 9, false);
    return;
  }
  const char* mime = guess_mime(full);
  send_cached_or_plain(c, rel, mime, buf, n);
  free(buf);
}

// removed unused read_headers_into
static void parse_request_line(const char* buf, char* method, char* path) {
  if (sscanf(buf, "%15s %4095s", method, path) < 2) {
    method[0] = '\0';
    path[0] = '\0';
  }
}
static void parse_headers(const char* buf, size_t* content_length, char* ctype, size_t ctype_sz) {
  *content_length = 0;
  ctype[0] = '\0';
  const char* cl = strcasestr(buf, "Content-Length:");
  if (cl) *content_length = strtoul(cl + 15, NULL, 10);
  const char* ct = strcasestr(buf, "Content-Type:");
  if (ct) {
    ct += 13;
    while (*ct == ' ' || *ct == '\t') ct++;
    size_t i = 0;
    while (*ct && *ct != '\r' && *ct != '\n' && i < ctype_sz - 1) {
      ctype[i++] = *ct++;
    }
    ctype[i] = '\0';
  }
}
// ---- small helpers to keep functions compact ----
static size_t copy_from_buffer(char* dst, const char* src, size_t available, size_t max_n) {
  size_t cpy = available > max_n ? max_n : available;
  if (cpy) memcpy(dst, src, cpy);
  return cpy;
}

static void recv_remaining_body(int c, char* body, size_t off, size_t total_len) {
  size_t remain = total_len - off;
  while (remain > 0) {
    ssize_t rr = recv(c, body + off, remain, 0);
    if (rr <= 0) break;
    off += (size_t)rr;
    remain -= (size_t)rr;
  }
}
static char* read_body_if_needed(int c, const char* buf, size_t total, size_t content_length) {
  if (!content_length) return NULL;
  const char* hdr_end = strstr(buf, "\r\n\r\n");
  size_t header_bytes = hdr_end ? (size_t)(hdr_end - buf) + 4 : total;
  size_t have_body = total > header_bytes ? total - header_bytes : 0;
  char* body = (char*)malloc(content_length + 1);
  if (!body) return NULL;
  size_t off = 0;
  if (have_body) off = copy_from_buffer(body, buf + header_bytes, have_body, content_length);
  if (off < content_length) recv_remaining_body(c, body, off, content_length);
  body[content_length] = '\0';
  return body;
}
static ssize_t read_request_headers(int c, char* buf, size_t bufsz) {
  ssize_t total = 0;
  while (true) {
    ssize_t rcv = recv(c, buf + total, bufsz - 1 - (size_t)total, 0);
    if (rcv <= 0) break;
    total += rcv;
    buf[total] = '\0';
    if (strstr(buf, "\r\n\r\n")) break;
    if (total >= (ssize_t)bufsz - 1) break;
  }
  return total;
}

static void process_request(int c, const char* buf, ssize_t total) {
  char method[16] = {0}, path[SMALL_BUF] = {0};
  parse_request_line(buf, method, path);
  if (!method[0]) return;
  size_t content_length = 0;
  char ctype[128] = {0};
  parse_headers(buf, &content_length, ctype, sizeof(ctype));
  char* body = read_body_if_needed(c, buf, (size_t)total, content_length);
  if (!strncmp(path, "/api/", 5))
    handle_api(c, method, path, body, content_length, ctype[0] ? ctype : NULL);
  else if (!strcmp(method, "GET")) handle_static(c, path);
  else if (!strcmp(method, "OPTIONS"))
    send_response(c, 204, "No Content", "text/plain", "", 0, false);
  else send_response(c, 405, "Method Not Allowed", "text/plain", "", 0, false);
  free(body);
}

static void handle_client(int c) {
  char buf[RECV_BUF];
  ssize_t total = read_request_headers(c, buf, sizeof(buf));
  if (total > 0) process_request(c, buf, total);
  close(c);
}

static int server_socket_init(const char* host, int port) {
  int s = socket(AF_INET, SOCK_STREAM, 0);
  if (s < 0) return -1;
  int opt = 1;
  setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
  struct sockaddr_in addr = {0};
  addr.sin_family = AF_INET;
  addr.sin_port = htons((uint16_t)port);
  addr.sin_addr.s_addr = inet_addr(host);
  if (bind(s, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
    close(s);
    return -1;
  }
  if (listen(s, 64) < 0) {
    close(s);
    return -1;
  }
  return s;
}

static void server_loop(int s) {
  while (!g_stop) {
    struct sockaddr_in ca;
    socklen_t calen = sizeof(ca);
    int c = accept(s, (struct sockaddr*)&ca, &calen);
    if (c < 0) {
      if (errno == EINTR) break;
      perror("accept");
      continue;
    }
    handle_client(c);
  }
}

static void init_runtime(void) {
  signal(SIGINT, on_sigint);
  srand((unsigned int)time(NULL));
  char cwd[SMALL_BUF];
  if (getcwd(cwd, sizeof(cwd))) DOC_ROOT = strdup(cwd);
}

int main(int argc, char** argv) {
  (void)argc;
  (void)argv;
  init_runtime();
  const char* host = getenv_default("HOST", "127.0.0.1");
  int port = atoi(getenv_default("PORT", "8000"));
  if (port <= 0) port = 8000;
  int s = server_socket_init(host, port);
  if (s < 0) {
    perror("server");
    return 1;
  }
  printf("Serving Mini Articles (C) on http://%s:%d\n", host, port);
  server_loop(s);
  close(s);
  return 0;
}
