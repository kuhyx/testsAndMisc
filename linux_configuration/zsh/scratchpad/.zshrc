# Minimal rc for the floating scratchpad calculator (i3: Mod+c).
#
# Deliberately tiny: it loads ONLY the live-calc widget, so the popup starts
# instantly instead of paying for the full ~/.zshrc (oh-my-zsh, pyenv, conda,
# nvm). ZDOTDIR points here, so this is the only rc that runs.

PROMPT='%F{cyan}calc ❯%f '
RPROMPT=''
autoload -Uz colors 2>/dev/null && colors 2>/dev/null

# Load the widget from the repo (one level up), independent of the oh-my-zsh
# symlink, so the scratchpad works even if oh-my-zsh is not installed.
source "${ZDOTDIR}/../calc-live.zsh"

print -P '%F{242}Live calculator — type math, see the result as you type. Ctrl-D to close.%f'
