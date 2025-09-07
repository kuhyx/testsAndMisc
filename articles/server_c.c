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
static long long g_boot_ms = 0; // server start time for live-reload token

static void on_sigint(int sig){ (void)sig; g_stop = 1; }

static long long now_ms(){ struct timespec ts; clock_gettime(CLOCK_REALTIME, &ts); return (long long)ts.tv_sec*1000 + ts.tv_nsec/1000000; }

static const char* getenv_default(const char* k, const char* def){ const char* v=getenv(k); return v&&*v? v: def; }

// ---- file helpers ----
static int ensure_dir(const char* path){ struct stat st; if(stat(path,&st)==0){ if(S_ISDIR(st.st_mode)) return 0; errno=ENOTDIR; return -1; } if(mkdir(path,0775)==0) return 0; return -1; }

static char* path_join(const char* a, const char* b){ size_t la=strlen(a), lb=strlen(b); size_t n=la+1+lb+1; char* r=malloc(n); if(!r) return NULL; snprintf(r,n,"%s/%s",a,b); return r; }

static char* data_dir(){ const char* env = getenv("ARTICLES_DATA_DIR"); if(env && *env){ ensure_dir(env); return strdup(env); } char* d = path_join(DOC_ROOT?DOC_ROOT: ".", "data"); if(d){ ensure_dir(d); } return d; }

static char* data_file(){ char* d = data_dir(); if(!d) return NULL; char* f = path_join(d, "articles.json"); free(d); return f; }

// Read entire file into memory (NUL-terminated). Caller frees.
static char* read_file_all(const char* path, size_t* out_len){ FILE* f=fopen(path,"rb"); if(!f){ if(out_len) *out_len=0; return NULL; } fseek(f,0,SEEK_END); long sz=ftell(f); if(sz<0) sz=0; fseek(f,0,SEEK_SET); char* buf=malloc((size_t)sz+1); if(!buf){ fclose(f); return NULL; } size_t n=fread(buf,1,(size_t)sz,f); fclose(f); buf[n]='\0'; if(out_len) *out_len=n; return buf; }

static int write_file_all(const char* path, const char* data, size_t len){ FILE* f=fopen(path,"wb"); if(!f) return -1; size_t n=fwrite(data,1,len,f); fclose(f); return n==len?0:-1; }

static int append_file_line(const char* path, const char* line){ FILE* f=fopen(path,"ab"); if(!f) return -1; size_t n=fwrite(line,1,strlen(line),f); n+=fwrite("\n",1,1,f); fclose(f); return (int)n>=0?0:-1; }

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
    if(*v!='"'){ if(tmp) free(tmp); return strdup(""); }
    v++; // inside string
    char* out = malloc(strlen(v)+1); if(!out){ if(tmp) free(tmp); return strdup(""); }
    size_t w=0; bool esc=false; for(const char* q=v; *q; ++q){ char c=*q; if(esc){ if(c=='"'||c=='\\'||c=='/'){ out[w++]=c; } else if(c=='n'){ out[w++]='\n'; } else if(c=='r'){ out[w++]='\r'; } else if(c=='t'){ out[w++]='\t'; } else { out[w++]=c; } esc=false; continue; } if(c=='\\'){ esc=true; continue; } if(c=='"'){ out[w]='\0'; if(tmp) free(tmp); return out; } out[w++]=c; }
    free(out); if(tmp) free(tmp); return strdup("");
  }
  if(tmp) free(tmp); return strdup("");
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
      while(*p && *p!=',' && *p!='}') p++;
      if(*p==',') { p++; continue; } else break;
    }
    // parse key string
    p++; const char* ks=p; size_t klen=0; bool esc=false; for(; *p; ++p){ char c=*p; if(esc){ esc=false; continue; } if(c=='\\'){ esc=true; continue; } if(c=='"'){ break; } klen++; }
    const char* key_start=ks; const char* key_end=p; if(*p=='"') p++; while(*p==' '||*p=='\t') p++; if(*p!=':') { // malformed
      while(*p && *p!=',' && *p!='}') p++; if(*p==',') { p++; continue; } else break;
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
static char* build_article_json(const char* id, const char* title, const char* body, const char* thumb, long long createdAt, long long updatedAt){
  char *et=json_escape(title?title:""), *eb=json_escape(body?body:""), *eth=json_escape(thumb?thumb:"");
  if(!et||!eb||!eth){ free(et); free(eb); free(eth); return NULL; }
  char createdBuf[64]; snprintf(createdBuf,sizeof(createdBuf),"%lld",createdAt);
  char updated[96]=""; if(updatedAt>0){ snprintf(updated,sizeof(updated),",\"updatedAt\":%lld",updatedAt); }
  size_t need = strlen(id)+strlen(et)+strlen(eb)+strlen(eth)+strlen(createdBuf)+strlen(updated)+64;
  char* out=malloc(need);
  if(!out){ free(et); free(eb); free(eth); return NULL; }
  snprintf(out, need, "{\"id\":\"%s\",\"title\":\"%s\",\"body\":\"%s\",\"thumb\":\"%s\",\"createdAt\":%s%s}", id, et, eb, eth, createdBuf, updated);
  free(et); free(eb); free(eth); return out;
}

static char* gen_id(){ char* out=malloc(17); if(!out) return NULL; unsigned int r = (unsigned int)rand(); long long t=now_ms(); snprintf(out,17,"%08x%08x", (unsigned int)(t&0xffffffff), r); return out; }

// ---- HTTP helpers ----
static void send_str(int c, const char* s){ send(c, s, strlen(s), 0); }

static void send_response(int c, int code, const char* status, const char* ctype, const char* body, size_t blen, bool cors){
  char head[SMALL_BUF];
  int n=snprintf(head,sizeof(head),
    "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\n%s\r\n",
    code, status, ctype?ctype:"text/plain", blen,
    cors? "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n":"");
  send(c, head, (size_t)n, 0);
  if(body && blen) send(c, body, blen, 0);
}

static const char* guess_mime(const char* path){ const char* ext=strrchr(path,'.'); if(!ext) return "application/octet-stream"; ext++; if(!strcmp(ext,"html")) return "text/html; charset=utf-8"; if(!strcmp(ext,"css")) return "text/css"; if(!strcmp(ext,"js")) return "application/javascript"; if(!strcmp(ext,"png")) return "image/png"; if(!strcmp(ext,"jpg")||!strcmp(ext,"jpeg")) return "image/jpeg"; if(!strcmp(ext,"svg")) return "image/svg+xml"; return "application/octet-stream"; }

// ---- Data operations (NDJSON-style internal), exposed as JSON array ----
static char* ltrim_dup(const char* s){ while(*s && isspace((unsigned char)*s)) s++; return strdup(s); }

static char* list_articles_json(size_t* out_len){
  char* file=data_file(); if(!file){ return strdup("[]"); }
  size_t n=0; char* content=read_file_all(file,&n); free(file);
  if(!content||n==0){ free(content); if(out_len) *out_len=2; return strdup("[]"); }
  char* t=ltrim_dup(content); free(content);
  if(!t){ if(out_len) *out_len=2; return strdup("[]"); }
  // If already a JSON array, return as-is
  if(t[0]=='['){ if(out_len) *out_len=strlen(t); return t; }
  // Otherwise, treat as empty
  free(t); if(out_len) *out_len=2; return strdup("[]");
}

static char* find_article_by_id(const char* id){
  char* file=data_file(); if(!file) return NULL;
  size_t n=0; char* content=read_file_all(file,&n); free(file); if(!content) return NULL;
  char* t=ltrim_dup(content); free(content); if(!t) return NULL; if(t[0] != '['){ free(t); return NULL; }
  // iterate objects
  size_t len=strlen(t); size_t i=1; int depth=0; size_t start=0; for(; i<len; ++i){ char c=t[i]; if(c=='{'){ if(depth==0) start=i; depth++; } else if(c=='}'){ depth--; if(depth==0){ size_t end=i; size_t obj_len=end-start+1; char* obj=malloc(obj_len+1); memcpy(obj, t+start, obj_len); obj[obj_len]='\0'; char* got=json_get_string(obj, "\"id\""); int match=got && strcmp(got,id)==0; free(got); if(match){ free(t); return obj; } free(obj); }
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
  size_t len=strlen(t); size_t i=1; int depth=0; size_t start=0; size_t count=0, cap=8; char** objs=malloc(cap*sizeof(char*)); bool found=false; char* updated_copy=NULL;
  for(; i<len; ++i){ char c=t[i]; if(c=='{'){ if(depth==0) start=i; depth++; } else if(c=='}'){ depth--; if(depth==0){ size_t end=i; size_t obj_len=end-start+1; char* obj=malloc(obj_len+1); memcpy(obj, t+start, obj_len); obj[obj_len]='\0';
  char* id=json_get_string(obj, "id"); bool isMatch=id && strcmp(id,match_id)==0; if(isMatch){ found=true; if(!is_delete){ char* title=json_get_string(obj, "title"); char* body=json_get_string(obj, "body"); char* thumb=json_get_string(obj, "thumb"); char* ptitle=json_get_top_string(patch_json, "title"); if(ptitle&&*ptitle){ free(title); title=ptitle; } else free(ptitle); char* pbody=json_get_top_string(patch_json, "body"); if(pbody&&*pbody){ free(body); body=pbody; } else free(pbody); char* pthumb=json_get_top_string(patch_json, "thumb"); if(pthumb&&*pthumb){ free(thumb); thumb=pthumb; } else free(pthumb); long long createdAt=json_get_number(obj, "\"createdAt\""); long long updatedAt=now_ms(); char* obj2=build_article_json(id,title,body,thumb,createdAt,updatedAt); free(title); free(body); free(thumb);
              free(updated_copy); updated_copy=strdup(obj2); free(obj); obj=obj2; }
          }
          free(id);
          if(!(isMatch && is_delete)){
            if(count==cap){ cap*=2; objs=realloc(objs, cap*sizeof(char*)); }
            objs[count++]=obj;
          } else {
            free(obj);
          }
        }
      }
  }
  // write back array
  size_t total_len=2; for(size_t k=0;k<count;k++){ total_len+=strlen(objs[k]); if(k+1<count) total_len++; }
  char* out=malloc(total_len+1); size_t w=0; out[w++]='['; for(size_t k=0;k<count;k++){ size_t L=strlen(objs[k]); memcpy(out+w, objs[k], L); w+=L; if(k+1<count) out[w++]=','; } out[w++]=']'; out[w]='\0';
  int rc = write_file_all(file, out, w);
  for(size_t k=0;k<count;k++) free(objs[k]); free(objs); free(out); free(file); free(t);
  if(found && !is_delete && out_json_updated){ *out_json_updated = updated_copy ? updated_copy : strdup(""); } else { free(updated_copy); }
  return found && rc==0 ? 0 : -1;
}

static char* create_article_from_body(const char* body_json){
  char* title=json_get_top_string(body_json, "title"); char* b=json_get_top_string(body_json, "body"); char* th=json_get_top_string(body_json, "thumb"); char* id=gen_id(); long long t=now_ms(); char* obj=build_article_json(id,title,b,th,t,0);
  free(title); free(b); free(th); if(!id||!obj){ free(id); free(obj); return NULL; }
  char* file=data_file(); if(!file){ free(id); free(obj); return NULL; }
  size_t n=0; char* content=read_file_all(file,&n);
  if(!content || n==0){ // write new array
    size_t L=strlen(obj); size_t tot=L+2; char* arr=malloc(tot+1); size_t w=0; arr[w++]='['; memcpy(arr+w,obj,L); w+=L; arr[w++]=']'; arr[w]='\0'; write_file_all(file, arr, w); free(arr);
  } else {
    char* tcontent=ltrim_dup(content); if(tcontent && tcontent[0]=='['){ size_t clen=strlen(tcontent); if(clen>=2 && tcontent[0]=='[' && tcontent[clen-1]==']'){
        // insert at front
        bool empty = (clen==2);
        size_t Lobj=strlen(obj);
        size_t newlen = 1 + Lobj + (empty?0:1) + (clen-2) + 1;
        char* out=malloc(newlen+1); size_t w=0; out[w++]='['; memcpy(out+w,obj,Lobj); w+=Lobj; if(!empty){ out[w++]=','; memcpy(out+w, tcontent+1, clen-2); w+=(clen-2); } out[w++]=']'; out[w]='\0'; write_file_all(file, out, w); free(out);
      } else { // corrupt; overwrite
        size_t L=strlen(obj); size_t tot=L+2; char* arr=malloc(tot+1); size_t w=0; arr[w++]='['; memcpy(arr+w,obj,L); w+=L; arr[w++]=']'; arr[w]='\0'; write_file_all(file, arr, w); free(arr);
      }
    } else {
      // not an array; overwrite
      size_t L=strlen(obj); size_t tot=L+2; char* arr=malloc(tot+1); size_t w=0; arr[w++]='['; memcpy(arr+w,obj,L); w+=L; arr[w++]=']'; arr[w]='\0'; write_file_all(file, arr, w); free(arr);
    }
    free(tcontent);
  }
  free(content); free(file); free(id); return obj; }

// ---- request handling ----
static void handle_api(int c, const char* method, const char* path, const char* body, size_t blen){
  if(!strncmp(method,"OPTIONS",7)){
    send_response(c, 204, "No Content", "application/json", "", 0, true); return;
  }
  // /api/articles or /api/articles/<id>
  const char* base = "/api/articles";
  size_t bl = strlen(base);
  if(!strncmp(path, base, bl)){
    if(!strcmp(method,"GET")){
      if(!strcmp(path, base)){
        size_t L=0; char* arr=list_articles_json(&L); send_response(c, 200, "OK", "application/json", arr, L, true); free(arr); return;
      } else if(path[bl]=='/' && strlen(path)>bl+1){
        const char* id=path+bl+1; char* obj=find_article_by_id(id); if(!obj){ send_response(c,404,"Not Found","application/json","",0,true); return;} size_t L=strlen(obj); send_response(c,200,"OK","application/json",obj,L,true); free(obj); return;
      }
    } else if(!strcmp(method,"POST") && !strcmp(path, base)){
      char* obj=create_article_from_body(body?body:""); if(!obj){ send_response(c,400,"Bad Request","application/json","",0,true); return;} size_t L=strlen(obj); send_response(c,201,"Created","application/json",obj,L,true); free(obj); return;
    } else if(!strcmp(method,"PUT") && path[bl]=='/' && strlen(path)>bl+1){
      const char* id=path+bl+1; char* updated=NULL; if(rewrite_articles_map(&updated,id,body?body:"",false)==0){ size_t L=strlen(updated); send_response(c,200,"OK","application/json",updated,L,true); free(updated); } else { send_response(c,404,"Not Found","application/json","",0,true);} return;
    } else if(!strcmp(method,"DELETE") && path[bl]=='/' && strlen(path)>bl+1){
      const char* id=path+bl+1; if(rewrite_articles_map(NULL,id,NULL,true)==0){ send_response(c,204,"No Content","application/json","",0,true);} else { send_response(c,404,"Not Found","application/json","",0,true);} return;
    }
  }
  send_response(c,404,"Not Found","text/plain","Not Found",9,true);
}

static bool safe_path(const char* p){ if(strstr(p, "..")) return false; return true; }

static void handle_static(int c, const char* path){
  char rel[SMALL_BUF]; if(!strcmp(path,"/")) strncpy(rel,"/index.html",sizeof(rel)); else strncpy(rel,path,sizeof(rel)); rel[sizeof(rel)-1]='\0';
  if(!safe_path(rel)){ send_response(c,403,"Forbidden","text/plain","Forbidden",9,false); return; }
  // build abs path
  char full[SMALL_BUF*2]; snprintf(full,sizeof(full),"%s%s", DOC_ROOT?DOC_ROOT:".", rel);
  FILE* f=fopen(full,"rb"); if(!f){ send_response(c,404,"Not Found","text/plain","Not Found",9,false); return; }
  fseek(f,0,SEEK_END); long sz=ftell(f); fseek(f,0,SEEK_SET); char* buf=malloc((size_t)sz); if(!buf){ fclose(f); send_response(c,500,"Internal Server Error","text/plain","",0,false); return; }
  size_t n=fread(buf,1,(size_t)sz,f); fclose(f);
  const char* mime=guess_mime(full);
  // Inject a tiny live-reload script into index.html at serve-time (does not affect file size on disk)
  if(strstr(mime, "text/html") && (!strcmp(rel, "/index.html"))){
    const char* lr = "<script>setInterval(()=>fetch('/__lr').then(r=>r.text()).then(t=>{if(window.__lr!==t){if(window.__lr)location.reload();window.__lr=t}}),500);</script>";
    size_t ln = strlen(lr);
    char* out = malloc(n + ln);
    if(out){ memcpy(out, buf, n); memcpy(out + n, lr, ln); send_response(c,200,"OK",mime,out,n+ln,false); free(out); free(buf); return; }
  }
  send_response(c,200,"OK",mime,buf,n,false); free(buf);
}

static void handle_client(int c){
  char buf[RECV_BUF]; ssize_t rcv=0, total=0;
  // read headers
  while((rcv=recv(c, buf+total, sizeof(buf)-1-total, 0))>0){ total+=rcv; buf[total]='\0'; if(strstr(buf, "\r\n\r\n")) break; if(total >= (ssize_t)sizeof(buf)-1) break; }
  if(total<=0){ close(c); return; }
  // parse request line
  char method[16]={0}, path[SMALL_BUF]={0};
  sscanf(buf, "%15s %1023s", method, path);
  // headers
  size_t content_length=0; char* cl = strcasestr(buf, "Content-Length:"); if(cl){ content_length = strtoul(cl+15, NULL, 10); }
  // find body start
  char* hdr_end = strstr(buf, "\r\n\r\n"); size_t header_bytes = hdr_end? (size_t)(hdr_end - buf) + 4 : (size_t)total; size_t have_body = total > (ssize_t)header_bytes ? (size_t)total - header_bytes : 0;
  char* body = NULL; if(content_length){ body = malloc(content_length+1); if(!body){ close(c); return; } size_t off=0; if(have_body){ size_t cpy = have_body>content_length?content_length:have_body; memcpy(body, buf+header_bytes, cpy); off = cpy; }
    size_t remain = content_length - off; while(remain>0){ ssize_t rr = recv(c, body+off, remain, 0); if(rr<=0) break; off+=rr; remain-=rr; } body[content_length]='\0'; }

  // Lightweight live-reload timestamp endpoint
  if(!strcmp(method, "GET") && !strcmp(path, "/__lr")){
    char idx[SMALL_BUF*2]; snprintf(idx, sizeof(idx), "%s/index.html", DOC_ROOT?DOC_ROOT:".");
    struct stat st; char out[96]; size_t w=0;
    if(stat(idx, &st)==0){ w=(size_t)snprintf(out, sizeof(out), "%ld-%lld", (long)st.st_mtime, g_boot_ms); }
    else { out[0]='0'; w=1; }
    send_response(c,200,"OK","text/plain",out,w,false);
    free(body); close(c); return;
  }

  if(!strncmp(path, "/api/", 5)){
    handle_api(c, method, path, body, content_length);
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
  signal(SIGINT, on_sigint);
  srand((unsigned int)time(NULL));
  g_boot_ms = now_ms();
  char cwd[SMALL_BUF]; if(getcwd(cwd,sizeof(cwd))) DOC_ROOT=strdup(cwd);
  const char* host = getenv_default("HOST","127.0.0.1");
  int port = atoi(getenv_default("PORT","8000")); if(port<=0) port=8000;

  int s = socket(AF_INET, SOCK_STREAM, 0); if(s<0){ perror("socket"); return 1; }
  int opt=1; setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
  struct sockaddr_in addr; memset(&addr,0,sizeof(addr)); addr.sin_family=AF_INET; addr.sin_port=htons((uint16_t)port); addr.sin_addr.s_addr=inet_addr(host);
  if(bind(s,(struct sockaddr*)&addr,sizeof(addr))<0){ perror("bind"); close(s); return 1; }
  if(listen(s,64)<0){ perror("listen"); close(s); return 1; }
  printf("Serving Mini Articles (C) on http://%s:%d\n", host, port);

  while(!g_stop){ struct sockaddr_in ca; socklen_t calen=sizeof(ca); int c=accept(s,(struct sockaddr*)&ca,&calen); if(c<0){ if(errno==EINTR) break; perror("accept"); continue; } handle_client(c); }
  close(s);
  return 0;
}
