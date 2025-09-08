#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <ctype.h>
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
static const char *DOC_ROOT = NULL; // current working directory

static void on_sigint(int sig){ (void)sig; g_stop = 1; }

static long long now_ms(void){ struct timespec ts; clock_gettime(CLOCK_REALTIME, &ts); return (long long)ts.tv_sec*1000 + ts.tv_nsec/1000000; }

static const char* getenv_default(const char* k, const char* def){ const char* v=getenv(k); return v&&*v? v: def; }

// ---- file helpers ----
static int ensure_dir(const char* path){ struct stat st; if(stat(path,&st)==0){ if(S_ISDIR(st.st_mode)) return 0; errno=ENOTDIR; return -1; } if(mkdir(path,0775)==0) return 0; return -1; }

static char* path_join(const char* a, const char* b){ size_t la=strlen(a), lb=strlen(b); size_t n=la+1+lb+1; char* r=malloc(n); if(!r) return NULL; snprintf(r,n,"%s/%s",a,b); return r; }

static char* data_dir(void){ const char* env = getenv("ARTICLES_DATA_DIR"); if(env && *env){ ensure_dir(env); return strdup(env); } char* d = path_join(DOC_ROOT?DOC_ROOT: ".", "data"); if(d){ ensure_dir(d); } return d; }

static char* data_file(void){ char* d = data_dir(); if(!d) return NULL; char* f = path_join(d, "articles.json"); free(d); return f; }

// Read entire file into memory (NUL-terminated). Caller frees.
static char* read_file_all(const char* path, size_t* out_len){ FILE* f=fopen(path,"rb"); if(!f){ if(out_len) *out_len=0; return NULL; } fseek(f,0,SEEK_END); long sz=ftell(f); if(sz<0) sz=0; fseek(f,0,SEEK_SET); char* buf=malloc((size_t)sz+1); if(!buf){ fclose(f); return NULL; } size_t n=fread(buf,1,(size_t)sz,f); fclose(f); buf[n]='\0'; if(out_len) *out_len=n; return buf; }

static int write_file_all(const char* path, const char* data, size_t len){ FILE* f=fopen(path,"wb"); if(!f) return -1; size_t n=fwrite(data,1,len,f); fclose(f); return n==len?0:-1; }

// removed unused append_file_line (lint)

// ---- JSON helpers (minimal) ----
static char* json_escape(const char* s){ size_t n=0; for(const char* p=s; *p; ++p){ if(*p=='"'||*p=='\\'||*p=='\n'||*p=='\r'||*p=='\t') n+=2; else n++; }
 char* out=malloc(n+1); if(!out) return NULL; char* w=out; for(const char* p=s; *p; ++p){ if(*p=='"'){ *w++='\\'; *w++='"'; } else if(*p=='\\'){ *w++='\\'; *w++='\\'; } else if(*p=='\n'){ *w++='\\'; *w++='n'; } else if(*p=='\r'){ *w++='\\'; *w++='r'; } else if(*p=='\t'){ *w++='\\'; *w++='t'; } else { *w++=*p; } } *w='\0'; return out; }

// Find string field value for key in compact JSON. Returns malloc'd string (unescaped). Empty string if not found.
static char* json_get_string(const char* json, const char* key){
  // Build quoted key pattern if needed
  const char* qkey = key;
  char* tmp = NULL;
  size_t klen = strlen(key);
  if(klen==0) return strdup("");
  if(key[0] != '"'){
    tmp = malloc(klen + 3);
    if(!tmp) return strdup("");
    tmp[0] = '"'; memcpy(tmp+1, key, klen); tmp[klen+1] = '"'; tmp[klen+2] = '\0';
    qkey = tmp; klen += 2;
  }
  const char* p = json;
  while((p = strstr(p, qkey))){
    const char* colon = strchr(p + klen, ':'); if(!colon){ p += klen; continue; }
    const char* v = colon + 1; while(*v==' '||*v=='\t') v++;
    if(*v!='"'){
      if(tmp) free(tmp);
      return strdup("");
    }
    v++; // inside string
    char* out = malloc(strlen(v)+1); if(!out){ if(tmp) free(tmp); return strdup(""); }
    size_t w=0; bool esc=false; for(const char* q=v; *q; ++q){ char c=*q; if(esc){ if(c=='"'||c=='\\'||c=='/'){ out[w++]=c; } else if(c=='n'){ out[w++]='\n'; } else if(c=='r'){ out[w++]='\r'; } else if(c=='t'){ out[w++]='\t'; } else { out[w++]=c; } esc=false; continue; } if(c=='\\'){ esc=true; continue; } if(c=='"'){ out[w]='\0'; if(tmp) free(tmp); return out; } out[w++]=c; }
  free(out);
  if(tmp) free(tmp);
  return strdup("");
  }
  if(tmp) free(tmp);
  return strdup("");
}

static long long json_get_number(const char* json, const char* key){ const char* p = strstr(json, key); if(!p) return 0; const char* colon=strchr(p,':'); if(!colon) return 0; const char* v=colon+1; while(*v==' '||*v=='\t') v++; return atoll(v); }

// Parse a top-level JSON object and return the string value for a given key (unquoted key name). Caller frees.
static char* json_get_top_string(const char* json, const char* key){
  size_t keylen = strlen(key);
  const char* p = json;
  // seek to first '{'
  while(*p && *p!='{') p++;
  if(*p!='{') return strdup("");
  p++;
  while(*p){
    while(*p==' '||*p=='\n'||*p=='\r'||*p=='\t'||*p==',') p++;
    if(*p=='}' || !*p) break;
    if(*p!='"'){ // invalid
      // skip token to next comma or end
      while(*p && *p!=',' && *p!='}') {
        p++;
      }
      if(*p==',') {
        p++;
        continue;
      } else {
        break;
      }
    }
    // parse key string
    p++; const char* ks=p; size_t klen=0; bool esc=false; for(; *p; ++p){ char c=*p; if(esc){ esc=false; continue; } if(c=='\\'){ esc=true; continue; } if(c=='"'){ break; } klen++; }
  const char* key_start=ks; if(*p=='"') p++; while(*p==' '||*p=='\t') p++; if(*p!=':') { // malformed
      while(*p && *p!=',' && *p!='}') {
        p++;
      }
      if(*p==',') {
        p++;
        continue;
      } else {
        break;
      }
    }
    p++; while(*p==' '||*p=='\t') p++;
    int key_match = (klen==keylen) && (strncmp(key_start, key, keylen)==0);
    if(*p=='"'){
      p++; // read string value
  char* out = malloc(strlen(p)+1); if(!out) return strdup(""); size_t w=0; bool e=false; for(; *p; ++p){ char c=*p; if(e){ if(c=='"'||c=='\\'||c=='/'){ out[w++]=c; } else if(c=='n'){ out[w++]='\n'; } else if(c=='r'){ out[w++]='\r'; } else if(c=='t'){ out[w++]='\t'; } else { out[w++]=c; } e=false; continue; } if(c=='\\'){ e=true; continue; } if(c=='"'){ out[w]='\0'; p++; break; } out[w++]=c; }
      if(key_match){ return out; } else { free(out); }
    } else {
      // non-string value: skip until comma or end (simple)
      while(*p && *p!=',' && *p!='}') p++;
    }
    if(*p==','){ p++; }
  }
  return strdup("");
}

// Build object JSON string; caller frees
static char* build_article_json(const char* id, const char* title, const char* author, const char* body, const char* thumb, long long createdAt, long long updatedAt){
  char *et=json_escape(title?title:""), *eau=json_escape(author?author:""), *eb=json_escape(body?body:""), *eth=json_escape(thumb?thumb:"");
  if(!et||!eau||!eb||!eth){ free(et); free(eau); free(eb); free(eth); return NULL; }
  char createdBuf[64]; snprintf(createdBuf,sizeof(createdBuf),"%lld",createdAt);
  char updated[96]=""; if(updatedAt>0){ snprintf(updated,sizeof(updated),",\"updatedAt\":%lld",updatedAt); }
  size_t need = strlen(id)+strlen(et)+strlen(eau)+strlen(eb)+strlen(eth)+strlen(createdBuf)+strlen(updated)+80;
  char* out=malloc(need);
  if(!out){ free(et); free(eau); free(eb); free(eth); return NULL; }
  snprintf(out, need, "{\"id\":\"%s\",\"title\":\"%s\",\"author\":\"%s\",\"body\":\"%s\",\"thumb\":\"%s\",\"createdAt\":%s%s}", id, et, eau, eb, eth, createdBuf, updated);
  free(et); free(eau); free(eb); free(eth); return out;
}

static char* gen_id(void){ char* out=malloc(17); if(!out) return NULL; unsigned int r = (unsigned int)rand(); long long t=now_ms(); snprintf(out,17,"%08x%08x", (unsigned int)(t&0xffffffff), r); return out; }

// ---- data URL handling ----
static int b64val(int c){ if(c>='A'&&c<='Z') return c-'A'; if(c>='a'&&c<='z') return c-'a'+26; if(c>='0'&&c<='9') return c-'0'+52; if(c=='+') return 62; if(c=='/') return 63; return -1; }
static unsigned char* base64_decode(const char* s, size_t len, size_t* out_len){
  size_t pad=0;
  if(len>=1 && s[len-1]=='=') pad++;
  if(len>=2 && s[len-2]=='=') pad++;
  size_t groups = len/4;
  size_t outcap = groups*3;
  if(pad <= outcap) outcap -= pad; else outcap = 0;
  if(outcap==0) outcap=1; // avoid 0-byte malloc and make room for NUL
  unsigned char* out = malloc(outcap+1);
  if(!out) return NULL;
  size_t w=0; int val=0, valb=-8;
  for(size_t i=0;i<len;i++){
    int c=s[i];
    if(c=='='||c=='\r'||c=='\n'||c==' '||c=='\t') continue;
    int d=b64val(c); if(d<0){ free(out); return NULL; }
    val = (val<<6) + d; valb += 6;
    if(valb>=0){ out[w++] = (unsigned char)((val>>valb)&0xFF); valb-=8; }
  }
  if(out_len) *out_len=w;
  return out;
}
static int parse_data_url(const char* data_url, char** out_mime, unsigned char** out_bytes, size_t* out_len){ const char* p=data_url; if(strncmp(p,"data:",5)!=0) return -1; p+=5; const char* semi=strchr(p,';'); const char* comma=strchr(p,','); if(!comma) return -1; char* mime=NULL; int is_b64=0; if(semi && semi<comma){ mime = strndup(p, (size_t)(semi-p)); if(!strncmp(semi, ";base64",7)) is_b64=1; } else { mime = strndup(p, (size_t)(comma-p)); }
  const char* payload = comma+1; unsigned char* bytes=NULL; size_t blen=0;
  if(is_b64){ bytes = base64_decode(payload, strlen(payload), &blen); if(!bytes){ free(mime); return -1; } }
  else { // percent-decoded
  size_t L=strlen(payload); bytes=malloc(L+1); if(!bytes){ free(mime); return -1; } size_t w=0; for(size_t i=0;i<L;i++){ if(payload[i]=='%' && i+2<L){ const char h[3]={payload[i+1],payload[i+2],'\0'}; bytes[w++]=(unsigned char)strtol(h,NULL,16); i+=2; } else if(payload[i]=='+'){ bytes[w++]=' '; } else { bytes[w++]=(unsigned char)payload[i]; } } blen=w; }
  *out_mime=mime; *out_bytes=bytes; if(out_len) *out_len=blen; return 0; }
static const char* ext_from_mime(const char* mime){ if(!mime) return NULL; if(strstr(mime,"image/png")) return "png"; if(strstr(mime,"image/jpeg")) return "jpg"; if(strstr(mime,"image/webp")) return "webp"; if(strstr(mime,"image/gif")) return "gif"; return NULL; }

static char* save_bytes_with_ext(const unsigned char* bytes, size_t blen, const char* ext){ if(!bytes||!blen) return NULL; const char* updir="uploads"; ensure_dir(updir); char* name=gen_id(); if(!name) return NULL; const char* e = (ext&&*ext)? ext: "bin"; size_t need=strlen(updir)+1+strlen(name)+1+strlen(e)+1; char* path=malloc(need); if(!path){ free(name); return NULL; } snprintf(path,need,"%s/%s.%s", updir, name, e); free(name); if(write_file_all(path,(const char*)bytes,blen)!=0){ free(path); return NULL; } return path; }

static char* migrate_inline_images_in_body(const char* body, bool* changed){
  if(!body) return NULL;
  const char* p = body;
  size_t outcap = strlen(body) + 1;
  char* out = malloc(outcap);
  if(!out) return NULL;
  size_t w = 0; int did = 0;
  while(*p){
    const char* m = strstr(p, "src=\"");
    const char* m2 = strstr(p, "src='");
    const char* hit = NULL; char quote='\0';
    if(m && (!m2 || m < m2)){ hit = m; quote='\"'; }
    else if(m2){ hit = m2; quote='\''; }
    if(!hit){
      size_t L = strlen(p);
      if(w + L + 1 > outcap){
        size_t newcap = w + L + 1;
        void* tmp = realloc(out, newcap);
        if(!tmp){ free(out); return NULL; }
        out = tmp;
      }
      memcpy(out + w, p, L);
      w += L;
      break;
    }
    // copy up to src=
    size_t prefix_len = (size_t)(hit - p);
    if(w + prefix_len + 6 > outcap){
      size_t newcap = w + prefix_len + 64;
      void* tmp = realloc(out, newcap);
      if(!tmp){ free(out); return NULL; }
      out = tmp; outcap = newcap;
    }
    memcpy(out + w, p, prefix_len);
    w += prefix_len;
    memcpy(out + w, "src=\"", 5);
    w += 5; // normalize to double quote
  const char* url_start = hit + 5;
  if(*url_start=='\'' || *url_start=='"') url_start++;
  const char endq = (quote=='\'') ? '\'' : '"';
    const char* url_end = strchr(url_start, endq);
  if(!url_end){ // malformed; copy rest
      size_t L = strlen(url_start);
      if(w + L + 1 > outcap){
        size_t newcap = w + L + 1;
        void* tmp = realloc(out, newcap);
        if(!tmp){ free(out); return NULL; }
    out = tmp;
      }
      memcpy(out + w, url_start, L);
      w += L;
      break;
    }
    size_t url_len = (size_t)(url_end - url_start);
    if(url_len>5 && strncmp(url_start, "data:", 5)==0){
      char* mime = NULL; unsigned char* bytes = NULL; size_t bl = 0; char* urlbuf = strndup(url_start, url_len);
      if(parse_data_url(urlbuf,&mime,&bytes,&bl)==0){
        const char* ext = ext_from_mime(mime);
        char* saved = save_bytes_with_ext(bytes, bl, ext);
        if(saved){
          const char* rel = saved;
          size_t need = 1 + strlen(rel);
          if(w + need + 1 > outcap){
            size_t newcap = w + need + 64;
            void* tmp = realloc(out, newcap);
            if(!tmp){ free(saved); free(bytes); free(mime); free(urlbuf); free(out); return NULL; }
            out = tmp; outcap = newcap;
          }
          out[w++] = '/';
          memcpy(out + w, rel, strlen(rel));
          w += strlen(rel);
          did = 1;
          free(saved);
        }
      }
      free(bytes); free(mime); free(urlbuf);
    } else {
      if(w + url_len + 1 > outcap){
        size_t newcap = w + url_len + 64;
        void* tmp = realloc(out, newcap);
        if(!tmp){ free(out); return NULL; }
        out = tmp; outcap = newcap;
      }
      memcpy(out + w, url_start, url_len);
      w += url_len;
    }
    // closing quote
    if(w + 1 > outcap){
      size_t newcap = w + 64;
      void* tmp = realloc(out, newcap);
      if(!tmp){ free(out); return NULL; }
      out = tmp; outcap = newcap;
    }
    out[w++] = '"';
    p = url_end + 1;
  }
  out[w] = '\0';
  if(changed) *changed = did;
  return out;
}

// ---- HTTP helpers ----
// removed unused send_str (lint)

static void send_response(int c, int code, const char* status, const char* ctype, const char* body, size_t blen, bool cors){
  char head[SMALL_BUF];
  int n=snprintf(head,sizeof(head),
    "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\n%s\r\n",
    code, status, ctype?ctype:"text/plain", blen,
    cors? "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n":"");
  send(c, head, (size_t)n, 0);
  if(body && blen) send(c, body, blen, 0);
}

static const char* guess_mime(const char* path){ const char* ext=strrchr(path,'.'); if(!ext) return "application/octet-stream"; ext++; if(!strcmp(ext,"html")) return "text/html; charset=utf-8"; if(!strcmp(ext,"css")) return "text/css"; if(!strcmp(ext,"js")) return "application/javascript"; if(!strcmp(ext,"png")) return "image/png"; if(!strcmp(ext,"jpg")||!strcmp(ext,"jpeg")) return "image/jpeg"; if(!strcmp(ext,"webp")) return "image/webp"; if(!strcmp(ext,"gif")) return "image/gif"; if(!strcmp(ext,"svg")) return "image/svg+xml"; if(!strcmp(ext,"mp4")) return "video/mp4"; if(!strcmp(ext,"webm")) return "video/webm"; return "application/octet-stream"; }

// ---- Data operations (NDJSON-style internal), exposed as JSON array ----
static char* ltrim_dup(const char* s){ while(*s && isspace((unsigned char)*s)) s++; return strdup(s); }

// removed unused list_articles_json (lint)

static char* find_article_by_id(const char* id){
  char* file=data_file(); if(!file) return NULL;
  size_t n=0; char* content=read_file_all(file,&n); free(file); if(!content) return NULL;
  char* t=ltrim_dup(content); free(content); if(!t) return NULL; if(t[0] != '['){ free(t); return NULL; }
  // iterate objects
  size_t len=strlen(t); size_t i=1; int depth=0; size_t start=0; for(; i<len; ++i){ char c=t[i]; if(c=='{'){ if(depth==0) start=i; depth++; } else if(c=='}'){ depth--; if(depth==0){ size_t end=i; size_t obj_len=end-start+1; char* obj=malloc(obj_len+1); if(!obj){ free(t); return NULL; } memcpy(obj, t+start, obj_len); obj[obj_len]='\0'; char* got=json_get_string(obj, "\"id\""); int match=got && strcmp(got,id)==0; free(got); if(match){ free(t); return obj; } free(obj); }
    }
  }
  free(t); return NULL;
}

static int rewrite_articles_map(char** out_json_updated, const char* match_id, const char* patch_json, bool is_delete){
  char* file=data_file(); if(!file) return -1; size_t n=0; char* content=read_file_all(file,&n); if(!content){ free(file); return -1; }
  char* t=ltrim_dup(content); free(content); if(!t){ free(file); return -1; }
  if(t[0] != '['){ // nothing to do
    FILE* f=fopen(file,"wb"); if(!f){ free(file); free(t); return -1; }
    fputs("[]", f); fclose(f); free(file); free(t); return -1;
  }
  // collect objects
  size_t len=strlen(t); size_t i=1; int depth=0; size_t start=0; size_t count=0, cap=8; char** objs=malloc(cap*sizeof(char*)); if(!objs){ free(t); free(file); return -1; } bool found=false; char* updated_copy=NULL;
  for(; i<len; ++i){ char c=t[i]; if(c=='{'){ if(depth==0) start=i; depth++; } else if(c=='}'){ depth--; if(depth==0){ size_t end=i; size_t obj_len=end-start+1; char* obj=malloc(obj_len+1); if(!obj){ for(size_t z=0; z<count; ++z) free(objs[z]); free(objs); free(file); free(t); return -1; } memcpy(obj, t+start, obj_len); obj[obj_len]='\0';
  char* id=json_get_string(obj, "id"); bool isMatch=id && strcmp(id,match_id)==0; if(isMatch){ found=true; if(!is_delete){ char* title=json_get_string(obj, "title"); char* author=json_get_string(obj, "author"); char* body=json_get_string(obj, "body"); char* thumb=json_get_string(obj, "thumb"); char* ptitle=json_get_top_string(patch_json, "title"); if(ptitle&&*ptitle){ free(title); title=ptitle; } else free(ptitle); char* pauthor=json_get_top_string(patch_json, "author"); if(pauthor&&*pauthor){ free(author); author=pauthor; } else free(pauthor); char* pbody=json_get_top_string(patch_json, "body"); if(pbody&&*pbody){ free(body); body=pbody; } else free(pbody); char* pthumb=json_get_top_string(patch_json, "thumb"); if(pthumb&&*pthumb){ free(thumb); thumb=pthumb; } else free(pthumb); long long createdAt=json_get_number(obj, "\"createdAt\""); long long updatedAt=now_ms(); char* obj2=build_article_json(id,title,author,body,thumb,createdAt,updatedAt); free(title); free(author); free(body); free(thumb);
              free(updated_copy); updated_copy=strdup(obj2); free(obj); obj=obj2; }
          }
          free(id);
          if(!(isMatch && is_delete)){
            if(count==cap){ cap*=2; void* tmp=realloc(objs, cap*sizeof(char*)); if(!tmp){ for(size_t z=0; z<count; ++z) free(objs[z]); free(objs); free(obj); free(file); free(t); return -1; } objs=(char**)tmp; }
            objs[count++]=obj;
          } else {
            free(obj);
          }
        }
      }
  }
  // write back array
  size_t total_len=2; for(size_t k=0;k<count;k++){ total_len+=strlen(objs[k]); if(k+1<count) total_len++; }
  char* out=malloc(total_len+1); if(!out){ for(size_t z=0; z<count; ++z) free(objs[z]); free(objs); free(file); free(t); return -1; } size_t w=0; out[w++]='['; for(size_t k=0;k<count;k++){ size_t L=strlen(objs[k]); memcpy(out+w, objs[k], L); w+=L; if(k+1<count) out[w++]=','; } out[w++]=']'; out[w]='\0';
  int rc = write_file_all(file, out, w);
  for(size_t k=0;k<count;k++) free(objs[k]);
  free(objs);
  free(out);
  free(file);
  free(t);
  if(found && !is_delete && out_json_updated){ *out_json_updated = updated_copy ? updated_copy : strdup(""); } else { free(updated_copy); }
  return found && rc==0 ? 0 : -1;
}

static char* create_article_from_body(const char* body_json){
  char* title=json_get_top_string(body_json, "title"); char* author=json_get_top_string(body_json, "author"); char* b=json_get_top_string(body_json, "body"); char* th=json_get_top_string(body_json, "thumb"); char* id=gen_id(); long long t=now_ms(); char* obj=build_article_json(id,title,author,b,th,t,0);
  free(title); free(author); free(b); free(th); if(!id||!obj){ free(id); free(obj); return NULL; }
  char* file=data_file(); if(!file){ free(id); free(obj); return NULL; }
  size_t n=0; char* content=read_file_all(file,&n);
  if(!content || n==0){ // write new array
    if(content) { free(content); }
    size_t L=strlen(obj); size_t tot=L+2; char* arr=malloc(tot+1); if(arr){ size_t w=0; arr[w++]='['; memcpy(arr+w,obj,L); w+=L; arr[w++]=']'; arr[w]='\0'; write_file_all(file, arr, w); free(arr); }
  } else {
  char* tcontent=ltrim_dup(content); free(content); if(tcontent && tcontent[0]=='['){ size_t clen=strlen(tcontent); if(clen>=2 && tcontent[clen-1]==']'){
        // insert at front
  bool empty = (clen==2);
  size_t Lobj=strlen(obj);
  size_t newlen = 1 + Lobj + (empty?0:1) + (clen-2) + 1;
  char* out=malloc(newlen+1); if(out){ size_t w=0; out[w++]='['; memcpy(out+w,obj,Lobj); w+=Lobj; if(!empty){ out[w++]=','; memcpy(out+w, tcontent+1, clen-2); w+=(clen-2); } out[w++]=']'; out[w]='\0'; write_file_all(file, out, w); free(out); }
      } else { // corrupt; overwrite
  size_t L=strlen(obj); size_t tot=L+2; char* arr=malloc(tot+1); if(arr){ size_t w=0; arr[w++]='['; memcpy(arr+w,obj,L); w+=L; arr[w++]=']'; arr[w]='\0'; write_file_all(file, arr, w); free(arr); }
      }
    } else {
      // not an array; overwrite
  size_t L=strlen(obj); size_t tot=L+2; char* arr=malloc(tot+1); if(arr){ size_t w=0; arr[w++]='['; memcpy(arr+w,obj,L); w+=L; arr[w++]=']'; arr[w]='\0'; write_file_all(file, arr, w); free(arr); }
    }
    free(tcontent);
  }
  // persist done; return created object JSON
  free(file);
  free(id);
  return obj;
}

// ---- request handling ----
static const char* ext_from_content_type(const char* ct){ if(!ct) return NULL; if(strstr(ct,"image/png")) return "png"; if(strstr(ct,"image/jpeg")) return "jpg"; if(strstr(ct,"image/jpg")) return "jpg"; if(strstr(ct,"image/webp")) return "webp"; if(strstr(ct,"image/gif")) return "gif"; return NULL; }

static const char* get_qparam(const char* path, const char* key){ const char* q=strchr(path,'?'); if(!q) return NULL; q++; size_t klen=strlen(key); while(*q){ if(!strncmp(q,key,klen) && q[klen]=='='){ return q+klen+1; } while(*q && *q!='&') q++; if(*q=='&') q++; }
  return NULL; }

static char* strndup_local(const char* s, size_t n){ char* r=malloc(n+1); if(!r) return NULL; memcpy(r,s,n); r[n]='\0'; return r; }

static char* save_upload(const char* body, size_t blen, const char* ext_hint){ if(!body||blen==0) return NULL; const char* updir = "uploads"; ensure_dir(updir); char* name=gen_id(); if(!name) return NULL; const char* ext = (ext_hint&&*ext_hint)? ext_hint: "bin"; size_t need=strlen(updir)+1+strlen(name)+1+strlen(ext)+1; char* path=malloc(need); if(!path){ free(name); return NULL; } snprintf(path,need,"%s/%s.%s", updir, name, ext); free(name); if(write_file_all(path, body, blen)!=0){ free(path); return NULL; } return path; }

static void handle_api(int c, const char* method, const char* path, const char* body, size_t blen, const char* content_type){
  if(!strncmp(method,"OPTIONS",7)){
    send_response(c, 204, "No Content", "application/json", "", 0, true); return;
  }
  // /api/articles or /api/articles/<id>
  const char* base = "/api/articles";
  size_t bl = strlen(base);
  if(!strncmp(path, base, bl)){
    if(!strcmp(method,"GET")){
      if(!strcmp(path, base)){
        // Load, migrate thumbs/body inline images to files if needed, persist, then return
        char* file=data_file(); if(!file){ send_response(c,200,"OK","application/json","[]",2,true); return; }
        size_t n=0; char* content=read_file_all(file,&n); if(!content){ free(file); send_response(c,200,"OK","application/json","[]",2,true); return; }
        char* t=ltrim_dup(content); free(content); if(!t){ free(file); send_response(c,200,"OK","application/json","[]",2,true); return; }
  if(t[0] != '['){ free(file); send_response(c,200,"OK","application/json","[]",2,true); free(t); return; }
        // iterate and rebuild array
  size_t len=strlen(t); size_t i=1; int depth=0; size_t start=0; size_t count=0, cap=8; char** objs=malloc(cap*sizeof(char*)); if(!objs){ free(t); free(file); send_response(c,500,"Internal Server Error","application/json","",0,true); return; } int changed=0;
    for(; i<len; ++i){ char ch=t[i]; if(ch=='{'){ if(depth==0) start=i; depth++; } else if(ch=='}'){ depth--; if(depth==0){ size_t end=i; size_t obj_len=end-start+1; char* obj=malloc(obj_len+1); if(!obj){ for(size_t z=0; z<count; ++z) free(objs[z]); free(objs); free(t); free(file); send_response(c,500,"Internal Server Error","application/json","",0,true); return; } memcpy(obj, t+start, obj_len); obj[obj_len]='\0';
              // check thumb
              char* id=json_get_string(obj, "id"); char* title=json_get_string(obj, "title"); char* author=json_get_string(obj, "author"); char* body_s=json_get_string(obj, "body"); char* thumb=json_get_string(obj, "thumb"); long long createdAt=json_get_number(obj, "\"createdAt\"");
              int obj_changed=0;
              // migrate thumb if data URL
      if(thumb && strncmp(thumb, "data:",5)==0){ char* mime=NULL; unsigned char* bytes=NULL; size_t bl2=0; if(parse_data_url(thumb,&mime,&bytes,&bl2)==0){ const char* ext=ext_from_mime(mime); char* saved=save_bytes_with_ext(bytes,bl2,ext); if(saved){ size_t urlL=strlen(saved)+2; char* newthumb=malloc(urlL); if(newthumb){ snprintf(newthumb,urlL,"/%s",saved); free(thumb); thumb=newthumb; obj_changed=1; } free(saved); } free(mime); free(bytes); }
              }
              // migrate inline images in body
              bool bchanged=false; char* new_body=migrate_inline_images_in_body(body_s,&bchanged); if(new_body && bchanged){ free(body_s); body_s=new_body; obj_changed=1; } else { free(new_body); }
              if(obj_changed){ changed=1; free(obj); char* obj2=build_article_json(id?id:"",title?title:"",author?author:"",body_s?body_s:"",thumb?thumb:"",createdAt,0); obj=obj2; }
              free(id); free(title); free(author); free(body_s); free(thumb);
              if(count==cap){ cap*=2; void* tmp=realloc(objs, cap*sizeof(char*)); if(!tmp){ for(size_t z=0; z<count; ++z) free(objs[z]); free(objs); free(t); free(file); send_response(c,500,"Internal Server Error","application/json","",0,true); return; } objs=(char**)tmp; }
              objs[count++]=obj;
            }
          }
        }
        // build array string
        size_t total_len=2; for(size_t k=0;k<count;k++){ total_len+=strlen(objs[k]); if(k+1<count) total_len++; }
  char* out=malloc(total_len+1); if(!out){ for(size_t z=0; z<count; ++z) free(objs[z]); free(objs); free(t); free(file); send_response(c,500,"Internal Server Error","application/json","",0,true); return; } size_t w=0; out[w++]='['; for(size_t k=0;k<count;k++){ size_t Lx=strlen(objs[k]); memcpy(out+w, objs[k], Lx); w+=Lx; if(k+1<count) out[w++]=','; } out[w++]=']'; out[w]='\0';
        if(changed){ write_file_all(file, out, w); }
  send_response(c,200,"OK","application/json",out,w,true);
  for(size_t k=0;k<count;k++) free(objs[k]);
  free(objs);
  free(out);
  free(file);
  free(t);
  return;
      } else if(path[bl]=='/' && strlen(path)>bl+1){
        const char* id=path+bl+1; char* obj=find_article_by_id(id); if(!obj){ send_response(c,404,"Not Found","application/json","",0,true); return;}
        // migrate this object if needed
  char* title=json_get_string(obj, "title"); char* author=json_get_string(obj, "author"); char* body_s=json_get_string(obj, "body"); char* thumb=json_get_string(obj, "thumb"); long long createdAt=json_get_number(obj, "\"createdAt\""); int obj_changed=0;
  if(thumb && strncmp(thumb, "data:",5)==0){ char* mime=NULL; unsigned char* bytes=NULL; size_t bl2=0; if(parse_data_url(thumb,&mime,&bytes,&bl2)==0){ const char* ext=ext_from_mime(mime); char* saved=save_bytes_with_ext(bytes,bl2,ext); if(saved){ size_t urlL=strlen(saved)+2; char* newthumb=malloc(urlL); if(newthumb){ snprintf(newthumb,urlL,"/%s",saved); free(thumb); thumb=newthumb; obj_changed=1; } free(saved); } free(mime); free(bytes); } }
        bool bchanged=false; char* new_body=migrate_inline_images_in_body(body_s,&bchanged); if(new_body && bchanged){ free(body_s); body_s=new_body; obj_changed=1; } else { free(new_body); }
        if(obj_changed){ char* id_copy=json_get_string(obj, "id"); char* updated=build_article_json(id_copy?id_copy:"", title?title:"", author?author:"", body_s?body_s:"", thumb?thumb:"", createdAt, 0); // persist
          if(updated){ rewrite_articles_map(NULL, id_copy, updated, false); free(updated); }
          free(id_copy);
          free(obj); obj=build_article_json(json_get_string("",""), title?title:"", author?author:"", body_s?body_s:"", thumb?thumb:"", createdAt, 0); // rebuild for response
          // Above line uses placeholder; simpler: rebuild from previously updated string parsing is heavy; instead send the updated we built
          // But rewrite_articles_map returned updated; safer to just re-find
          free(obj); obj=find_article_by_id(id);
        }
        free(title); free(author); free(body_s); free(thumb);
        size_t L=strlen(obj); send_response(c,200,"OK","application/json",obj,L,true); free(obj); return;
      }
    } else if(!strcmp(method,"POST") && !strcmp(path, base)){
      char* obj=create_article_from_body(body?body:""); if(!obj){ send_response(c,400,"Bad Request","application/json","",0,true); return;} size_t L=strlen(obj); send_response(c,201,"Created","application/json",obj,L,true); free(obj); return;
    } else if(!strcmp(method,"PUT") && path[bl]=='/' && strlen(path)>bl+1){
      const char* id=path+bl+1; char* updated=NULL; if(rewrite_articles_map(&updated,id,body?body:"",false)==0){ size_t L=strlen(updated); send_response(c,200,"OK","application/json",updated,L,true); free(updated); } else { send_response(c,404,"Not Found","application/json","",0,true);} return;
    } else if(!strcmp(method,"DELETE") && path[bl]=='/' && strlen(path)>bl+1){
      const char* id=path+bl+1; if(rewrite_articles_map(NULL,id,NULL,true)==0){ send_response(c,204,"No Content","application/json","",0,true);} else { send_response(c,404,"Not Found","application/json","",0,true);} return;
    }
  }
  // /api/upload for binary image upload
  if(!strncmp(path, "/api/upload", 12)){
    if(!strcmp(method,"POST")){
  const char* ext_q = get_qparam(path, "ext"); const char* ext_from_ct = ext_from_content_type(content_type);
      const char* ext = ext_from_ct ? ext_from_ct : (ext_q ? ext_q : "bin");
      // trim ext to safe token
  size_t elen=0; while(elen<4 && ext[elen] && isalnum((unsigned char)ext[elen])) elen++; char* ext_safe=strndup_local(ext,elen?elen:3); if(!ext_safe){ send_response(c,500,"Internal Server Error","application/json","",0,true); return; }
      char* saved = save_upload(body, blen, ext_safe); free(ext_safe);
      if(!saved){ send_response(c,500,"Internal Server Error","application/json","",0,true); return; }
      // build URL
      const char* rel = saved; // saved like "uploads/.."
      size_t L = strlen(rel)+20; char* res=malloc(L); if(!res){ free(saved); send_response(c,500,"Internal Server Error","application/json","",0,true); return; }
      snprintf(res, L, "{\"url\":\"/%s\"}", rel);
      send_response(c,201,"Created","application/json",res,strlen(res),true);
      free(res); free(saved); return;
    }
  }
  send_response(c,404,"Not Found","text/plain","Not Found",9,true);
}

static bool safe_path(const char* p){ if(strstr(p, "..")) return false; return true; }

static void handle_static(int c, const char* path){
  char rel[SMALL_BUF];
  if(!strcmp(path,"/")){
    snprintf(rel, sizeof(rel), "%s", "/index.html");
  } else {
    snprintf(rel, sizeof(rel), "%s", path);
  }
  if(!safe_path(rel)){ send_response(c,403,"Forbidden","text/plain","Forbidden",9,false); return; }
  // build abs path
  char full[SMALL_BUF*2]; snprintf(full,sizeof(full),"%s%s", DOC_ROOT?DOC_ROOT:".", rel);
  FILE* f=fopen(full,"rb"); if(!f){ send_response(c,404,"Not Found","text/plain","Not Found",9,false); return; }
  fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET); char* buf=malloc((size_t)sz); if(!buf){ fclose(f); send_response(c,500,"Internal Server Error","text/plain","",0,false); return; }
  size_t n=fread(buf,1,(size_t)sz,f); fclose(f);
  const char* mime=guess_mime(full);
  // Add strong cache for uploaded assets
  int is_upload = (strncmp(rel, "/uploads/", 9)==0);
  if(is_upload){
    char head[SMALL_BUF];
    int hlen=snprintf(head,sizeof(head),
      "HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %zu\r\nCache-Control: public, max-age=31536000, immutable\r\n\r\n",
      mime, (size_t)n);
    send(c, head, (size_t)hlen, 0);
    if(n) send(c, buf, n, 0);
  } else {
    send_response(c,200,"OK",mime,buf,n,false);
  }
  free(buf);
}

static void handle_client(int c){
  char buf[RECV_BUF]; ssize_t rcv=0, total=0;
  // read headers
  while((rcv=recv(c, buf+total, sizeof(buf)-1-total, 0))>0){ total+=rcv; buf[total]='\0'; if(strstr(buf, "\r\n\r\n")) break; if(total >= (ssize_t)sizeof(buf)-1) break; }
  if(total<=0){ close(c); return; }
  // parse request line
  char method[16]={0}, path[SMALL_BUF]={0};
  if(sscanf(buf, "%15s %4095s", method, path) < 2){ close(c); return; }
  // headers
  size_t content_length=0; const char* cl = strcasestr(buf, "Content-Length:"); if(cl){ content_length = strtoul(cl+15, NULL, 10); }
  const char* ct_hdr = strcasestr(buf, "Content-Type:"); char ctype[128]={0}; if(ct_hdr){ ct_hdr+=13; while(*ct_hdr==' '||*ct_hdr=='\t') ct_hdr++; size_t i=0; while(*ct_hdr && *ct_hdr!='\r' && *ct_hdr!='\n' && i<sizeof(ctype)-1){ ctype[i++]=*ct_hdr++; } ctype[i]='\0'; }
  // find body start
  const char* hdr_end = strstr(buf, "\r\n\r\n"); size_t header_bytes = hdr_end? (size_t)(hdr_end - buf) + 4 : (size_t)total; size_t have_body = total > (ssize_t)header_bytes ? (size_t)total - header_bytes : 0;
  char* body = NULL; if(content_length){ body = malloc(content_length+1); if(!body){ close(c); return; } size_t off=0; if(have_body){ size_t cpy = have_body>content_length?content_length:have_body; memcpy(body, buf+header_bytes, cpy); off = cpy; }
    size_t remain = content_length - off; while(remain>0){ ssize_t rr = recv(c, body+off, remain, 0); if(rr<=0) break; off+=rr; remain-=rr; } body[content_length]='\0'; }

  if(!strncmp(path, "/api/", 5)){
    handle_api(c, method, path, body, content_length, ctype[0]?ctype:NULL);
  } else if(!strcmp(method,"GET")){
    handle_static(c, path);
  } else if(!strcmp(method,"OPTIONS")){
    send_response(c,204,"No Content","text/plain","",0,false);
  } else {
    send_response(c,405,"Method Not Allowed","text/plain","",0,false);
  }
  free(body);
  close(c);
}

int main(int argc, char** argv){
  (void)argc; (void)argv;
  signal(SIGINT, on_sigint);
  srand((unsigned int)time(NULL));
  char cwd[SMALL_BUF]; if(getcwd(cwd,sizeof(cwd))) DOC_ROOT=strdup(cwd);
  const char* host = getenv_default("HOST","127.0.0.1");
  int port = atoi(getenv_default("PORT","8000")); if(port<=0) port=8000;

  int s = socket(AF_INET, SOCK_STREAM, 0); if(s<0){ perror("socket"); return 1; }
  int opt=1; setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
  struct sockaddr_in addr = {0}; addr.sin_family=AF_INET; addr.sin_port=htons((uint16_t)port); addr.sin_addr.s_addr=inet_addr(host);
  if(bind(s,(struct sockaddr*)&addr,sizeof(addr))<0){ perror("bind"); close(s); return 1; }
  if(listen(s,64)<0){ perror("listen"); close(s); return 1; }
  printf("Serving Mini Articles (C) on http://%s:%d\n", host, port);

  while(!g_stop){ struct sockaddr_in ca; socklen_t calen=sizeof(ca); int c=accept(s,(struct sockaddr*)&ca,&calen); if(c<0){ if(errno==EINTR) break; perror("accept"); continue; } handle_client(c); }
  close(s);
  return 0;
}
