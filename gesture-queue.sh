#!/usr/bin/env bash
MS="${MS:-http://127.0.0.1:2423}"
P=0;F=0
ok(){ P=$((P+1)); printf '  PASS  %s\n' "$1"; }
no(){ F=$((F+1)); printf '  FAIL  %s\n' "$1"; }
chk(){ [ "$2" = "$3" ] && ok "$1 ($3)" || no "$1 (want $3, got $2)"; }
play(){ curl -s -m 6 -X POST -H "content-type: application/json" -d "$1" "$MS/motion/play"; }
lay(){ printf '%s' "$1" | python -c 'import sys,json;print(json.load(sys.stdin).get("layer"))'; }
sleep 24
A=$(play '{"clip":"salute"}')
chk "first gesture plays" "$(lay "$A")" "gesture"
B=$(play '{"clip":"point"}')
chk "second gesture queues behind it" "$(lay "$B")" "queued"
C=$(play '{"clip":"point"}')
chk "the same queued gesture is not queued twice" "$(lay "$C")" "skipped"
D=$(play '{"clip":"clap"}'); E=$(play '{"clip":"bow"}'); G=$(play '{"clip":"angry"}')
chk "queue stops at its cap" "$(lay "$G")" "dropped"
QN=$(curl -s -m 6 "$MS/motion/state" | python -c 'import sys,json;print(json.load(sys.stdin).get("queued"))')
[ "$QN" -ge 2 ] && ok "state reports the queue depth (queued=$QN)" || no "state reports the queue depth (got $QN)"
sleep 14
H=$(play '{"clip":"salute"}')
chk "a repeat inside the window is refused" "$(lay "$H")" "skipped"
I=$(play '{"clip":"salute","force":true}')
chk "force overrides the repeat guard" "$(lay "$I")" "gesture"
curl -s -m 6 "$MS/motion/state" | grep -q gesture_until && no "gesture_until hidden from api" || ok "gesture_until hidden from api"
sleep 26
J=$(play '{"clip":"salute"}')
chk "the same gesture plays again once the window passes" "$(lay "$J")" "gesture"
K=$(play '{"clip":"walk"}')
chk "base clips ignore the gesture queue" "$(lay "$K")" "base"
curl -s -m 6 -X POST -H "content-type: application/json" -d '{"clip":"standing_w_briefcase_idle"}' "$MS/motion/play" >/dev/null
printf 'RESULT  %d passed, %d failed\n' "$P" "$F"
[ "$F" = 0 ]
