#!/usr/bin/env bash
# black-metal-preview.sh — MAIN + ALT palettes (truecolor + correct 256-code)
set -u
RESET=$'\e[0m'; BOLD=$'\e[1m'

# --- your palettes -----------------------------------------------------------
# MAIN
m_alt="#5f8787"; m_alt_bg="#060b12"; m_bg="#000000"; m_comment="#505050"
m_constant="#aaaaaa"; m_fg="#c1c1c1"; m_func="#888888"; m_keyword="#999999"
m_line="#000000"; m_number="#aaaaaa"; m_operator="#9b99a3"; m_property="#c1c1c1"
m_string="#a5aaa7"; m_type="#626b67"; m_visual="#333333"
m_diag_red="#5f8787"; m_diag_blue="#999999"; m_diag_yellow="#5f8787"; m_diag_green="#6e4c4c"

# ALT
a_alt="#5f8787"; a_alt_bg="#4d2020"; a_bg="#000000"; a_comment="#505050"
a_constant="#aaaaaa"; a_fg="#c1c1c1"; a_func="#888888"; a_keyword="#999999"
a_line="#000000"; a_number="#aaaaaa"; a_operator="#9b99a3"; a_property="#c1c1c1"
a_string="#f3ecd4"; a_type="#eecc6c"; a_visual="#333333"
a_diag_red="#5f8787"; a_diag_blue="#999999"; a_diag_yellow="#5f8787"; a_diag_green="#6e4c4c"

# --- helpers -----------------------------------------------------------------
hex2rgb() { local h="${1#\#}"; printf '%d;%d;%d' "0x${h:0:2}" "0x${h:2:2}" "0x${h:4:2}"; }
bg()  { local rgb; rgb=$(hex2rgb "$1"); printf '\e[48;2;%sm' "$rgb"; }
fg()  { local rgb; rgb=$(hex2rgb "$1"); printf '\e[38;2;%sm' "$rgb"; }
blk() { printf '        '; } # 8-wide block

# map component 0..255 -> 0..5 using *true* midpoints between {0,95,135,175,215,255}
to6() {
  local c=$1
  if   (( c < 48 ));  then echo 0
  elif (( c < 115 )); then echo 1
  elif (( c < 155 )); then echo 2
  elif (( c < 195 )); then echo 3
  elif (( c < 235 )); then echo 4
  else                     echo 5
  fi
}

rgb_to_256() {
  local r=$1 g=$2 b=$3
  local r6=$(to6 "$r") g6=$(to6 "$g") b6=$(to6 "$b")
  local map=(0 95 135 175 215 255)
  local rc=${map[$r6]} gc=${map[$g6]} bc=${map[$b6]}
  local code_cube=$((16 + 36*r6 + 6*g6 + b6))
  local dr=$((r-rc)); local dg=$((g-gc)); local db=$((b-bc))
  local dist_cube=$((dr*dr + dg*dg + db*db))
  # grayscale candidate 232..255 (levels: 8+10*i)
  local avg=$(( (r + g + b) / 3 ))
  local i=$(( (avg - 8 + 5) / 10 )); (( i < 0 )) && i=0; (( i > 23 )) && i=23
  local gray=$((8 + 10*i))
  local dgr=$((r-gray)); local dgg=$((g-gray)); local dgb=$((b-gray))
  local dist_gray=$((dgr*dgr + dgg*dgg + dgb*dgb))
  local code_gray=$((232 + i))
  if (( dist_gray < dist_cube )); then echo "$code_gray"; else echo "$code_cube"; fi
}

sw_true_bg() { local r g b; IFS=';' read -r r g b < <(hex2rgb "$1"); printf '\e[48;2;%s;%s;%sm    \e[0m' "$r" "$g" "$b"; }
sw256_bg()   { printf '\e[48;5;%sm    \e[0m' "$1"; }

print_header() {
  printf '\n%b%s%b\n' "$BOLD" "$1" "$RESET"
  printf "%-18s %-10s %-12s %-18s\n" "Role" "Hex" "Truecolor" "256-color (code)"
  printf -- "-----------------------------------------------------------------\n"
}
show_row() { # "Role|#hex"
  local role hex r g b code
  IFS='|' read -r role hex <<<"$1"
  IFS=';' read -r r g b < <(hex2rgb "$hex")
  code="$(rgb_to_256 "$r" "$g" "$b")"
  printf "%-18s %-10s " "$role" "$hex"
  sw_true_bg "$hex"; printf "  "
  sw256_bg "$code";  printf "  (%3s)\n" "$code"
}
show_theme() { local title="$1"; shift; print_header "$title"; while IFS= read -r L; do [[ -z "$L" || "$L" =~ ^# ]] && continue; show_row "$L"; done; }

clear
printf "Env: COLORTERM=%s, TERM=%s\n" "${COLORTERM-}" "${TERM-}"

# MAIN
show_theme "Black Metal — MAIN" <<'ROWS'
alt|#5f8787
alt_bg|#060b12
bg|#000000
comment|#505050
constant|#aaaaaa
fg|#c1c1c1
func|#888888
keyword|#999999
line|#000000
number|#aaaaaa
operator|#9b99a3
property|#c1c1c1
string|#a5aaa7
type|#626b67
visual|#333333
diag_red|#5f8787
diag_blue|#999999
diag_yellow|#5f8787
diag_green|#6e4c4c
# colormap (useful when forcing 256-color)
colormap.black|#060b12
colormap.grey|#505050
colormap.red|#5f8787
colormap.orange|#aaaaaa
colormap.green|#c1c1c1
colormap.yellow|#888888
colormap.blue|#aaaaaa
colormap.purple|#999999
colormap.magenta|#626b67
colormap.cyan|#a5aaa7
colormap.white|#c1c1c1
ROWS

# ALT
show_theme "Black Metal — ALT" <<'ROWS'
alt|#5f8787
alt_bg|#4d2020
bg|#000000
comment|#505050
constant|#aaaaaa
fg|#c1c1c1
func|#888888
keyword|#999999
line|#000000
number|#aaaaaa
operator|#9b99a3
property|#c1c1c1
string|#f3ecd4
type|#eecc6c
visual|#333333
diag_red|#5f8787
diag_blue|#999999
diag_yellow|#5f8787
diag_green|#6e4c4c
# colormap (useful when forcing 256-color)
colormap.black|#4d2020
colormap.grey|#505050
colormap.red|#5f8787
colormap.orange|#aaaaaa
colormap.green|#c1c1c1
colormap.yellow|#888888
colormap.blue|#aaaaaa
colormap.purple|#999999
colormap.magenta|#eecc6c
colormap.cyan|#f3ecd4
colormap.white|#c1c1c1
ROWS

printf "\nSanity checks (expected -> actual):\n"
printf "  #5f8787  -> code 66 : "; sw256_bg 66; printf "  (should match Truecolor teal above)\n"
printf "  #4d2020  -> code 52 : "; sw256_bg 52; printf "  (ALT maroon)\n\n"

