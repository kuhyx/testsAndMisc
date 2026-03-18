BEGIN{ in_func=0; depth=0; start=0; err=0; prev="" }
{
  line=$0
  # track function start when we see an opening brace at top-level and previous non-empty
  # line looks like a function signature (ends with ')' and not ';', and not a typedef/struct/enum/union)
  for(i=1;i<=length(line);i++){
    c=substr(line,i,1)
    if(c=="{"){
      if(depth==0 && !in_func){
        # Heuristic check on previous non-empty trimmed line
        t=prev
        sub(/^\s+/, "", t); sub(/\s+$/, "", t)
        if(t ~ /\)$/ && t !~ /;\s*$/ && t !~ /^(typedef|struct|enum|union)\b/){
          in_func=1; start=NR
        }
      }
      depth++
    } else if(c=="}"){
      depth--
      if(in_func && depth==0){
        lines=NR-start+1
        if(lines>20){ print FILENAME ":" start " function too long: " lines " lines"; err=1 }
        in_func=0
      }
    }
  }
  # update previous non-empty line
  tmp=line; sub(/^\s+/, "", tmp); sub(/\s+$/, "", tmp)
  if(length(tmp)>0){ prev=tmp }
}
END{ if(err) exit 1 }
