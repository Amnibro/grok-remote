# Companion roadmap: from puppet to Cortana

Goal: an AI that inhabits a body, notices you, and acts on what it notices. Halo's Cortana is the reference: she speaks up when something matters, stays quiet when it does not, and knows what is going on around you.

## Where we are (2026-09-03)

Shipped and working on `/xr`:
- Body: rigged model, idle life (briefcase/guitar/phone bases), 8 authored gestures plus Mixamo takes, gaze targets, cloth/hair deform. Motion service owns the chain; since 2026-10-06 the hub starts it on demand and proxies it same-origin.
- Voice: edge-tts → piper → espeak-ng → browser speech out; push-to-talk SpeechRecognition in, with MediaRecorder → `/api/xr/stt` (faster-whisper) when the browser has no working speech service.
- Brain: pluggable (`brains/`): Grok by default, Claude Code (stream-json, conservative tools, permission prompts), or any stdio ACP agent. `[[motion:]]`, `[[gaze:]]`, `[[reach:]]`, `[[compose:]]` tags drive the body from her words. Briefing is built server-side from the real clip library and the configured user.
- Vision (half): camera or self-render frames ride the turn as image blocks when the brain takes images (file fallback otherwise). She never looks on her own.

The gap: every single thing she does starts with you typing or holding the mic. She has no senses of her own and no reason to act between turns. That is the difference between a puppet and a person in the room.

## Layered model

1. **Senses** (browser, cheap, always on): presence via camera frame differencing, hands-free ears with name detection, environment via the hub (foreground window, agent work state, clock, input idle).
2. **Percepts**: a rolling log of typed events (`arrive`, `leave`, `addressed`, `overheard`, `work_done`, `work_error`, `ask_open`, `focus_change`, `long_silence`).
3. **Reflexes** (no LLM, instant): gaze and small gestures keyed to percepts. Wave when you arrive, look at you when you speak, glance away when you switch windows.
4. **Attention** (LLM, budgeted): for notable percepts she is handed a one-paragraph situation and asked for one or two spoken sentences, or `[[quiet]]`. Minimum 45s between reactions, 12 per hour, never while speaking or thinking, never when you are not there (except arrival).
5. **Memory** (next): what she overheard, what you were working on, what she said last, persisted per session and summarised across sessions.
6. **Environment action** (later): AR anchors on Quest (hit-test already negotiated), pointing at real objects, reading the screen you are looking at, driving the PC through the existing remote-input daemon with confirmation.

## Rung 1, shipped in this pass

- `web/xr-senses.js`: layers 1-4. Pure functions (`addressed`, `makeBudget`, `situation`, `motionScore`) are exported and unit-tested in `tests/test_xr_senses.mjs`.
- `companion_env.py` + `GET /api/companion/env`: foreground window title and exe, seconds since last input, clock, agent work summary from the work board. `tests/test_companion_env.py`.
- `/xr`: SENSES button. `?senses=1` starts it on load. `window.__senses.inject("arrive")` for scripted tests.

## Rung 2 candidates (pick by what annoys you first)

- Face detection instead of motion so a cat does not count as you (Chrome `FaceDetector` where present, MediaPipe otherwise).
- ~~Barge-in~~ shipped 2026-10-06: talking (HOLD·TALK/Space), Esc, or STOP cancels the turn and silences her.
- Confirm-gated actions: shipped for Claude and ACP brains (tool permission → spoken ask + approve/deny chip, deny on timeout). Grok still runs `--always-approve`.
- Memory file per companion session and a nightly summary she reads at first greeting.
- Screen awareness: she gets a downscaled screenshot of the foreground window on `focus_change` so "what am I looking at" works.
- Quest: hand-tracking gestures as percepts (wave back, point at her).

## How she interacts with the world from a small standing disc

The disc is a stage, not a cage. Everything she can touch runs through channels that already exist on this PC, so the body only has to point, look, and speak while the channels do the work.

1. **She is the agent.** Her session has the same tools as any grok session: files, shell, browser, the hub API. "Open the Haven repo and run the tests" is a tool call she makes herself while her body salutes. Gate anything destructive behind a spoken confirmation ("do it" / "hold on") so the disc never becomes a loose cannon.
2. **She knows what you are looking at.** `/api/companion/env` gives her the foreground window and the work board. Next step is a downscaled screenshot of that window on `focus_change`, so "what's wrong with this?" works without you describing it.
3. **She can drive the PC.** amni-connect already exposes cursor and keyboard on :7878 with high integrity. A `[[act:click|type|key]]` tag family, mapped to that daemon and confirmed by voice, lets her fix the thing she is pointing at.
4. **The disc travels.** Same session, different stage: the desktop exe as a transparent always-on-top window puts her on your actual desktop where she can gesture at real windows (`point_ahead` at screen coordinates from the env route). On Quest the AR hit-test and anchors are already negotiated, so she can stand on your desk and point at the monitor, the door, or a printed page you hold up to the camera.
5. **Reach.** `[[reach:]]` exists for IK. Pair it with camera-detected objects (face, hands, a held phone) so pointing and looking land on real things instead of fixed directions.
6. **Other people and devices.** The Haven/Braid rooms are hub-visible; she can relay a message, answer a Ferry bot, or ping your phone through the watch/phone pairing that already works.

Order to build: screenshot-on-focus (cheap, huge payoff) -> confirm-gated `[[act:]]` -> transparent desktop stage -> Quest anchors -> object-aware reach.

## Does body control need its own subagent?

Not for correctness. The failures so far were geometry and plumbing: a bone-local up axis assumed to be y, clips missing their bind offset, gestures blended 50/50 against the idle. A reasoning layer on top of a broken transform just narrates the fall.

The place a small model does earn its keep is selection, not execution:

- **Now (no model):** she emits `[[motion:]]` / `[[gaze:]]` inline while she talks, the motion service owns the chain, and the renderer clamps physically impossible values. Latency is zero and the failure mode is a wrong-but-safe gesture.
- **Worth trying (cheap model, off the critical path):** a "body director" that reads the sentence she is about to speak plus the current base and picks the beat: gesture or nothing, which one, when in the sentence, how strongly. Runs on Haiku-class latency, output is a fixed JSON schema, and the service still validates every name against the clip list. If it stalls or returns junk, the current inline-tag path is the fallback.
- **Not worth it:** letting a model author joint angles per frame. That is what the lab and the clip library are for, and numeric verification already proved authored clips beat generated ones.

The response format that makes either path work is the one already in place: her prose carries tags, the tags are stripped before TTS, and the service is the only thing that can move a bone. Keep that boundary and the director stays optional.

## Getting a Cortana surface instead of a dot cloud

Dropping the interior samples stops the scary part. The look itself is still 115k independent dots, which is why she reads as a scan rather than a person. Three steps, cheapest first:

1. **Denser shell, softer dots** (done partially): interior reject plus the facing fade means every visible dot is outer skin. Raising point count in the head zone specifically would firm up the face without costing the whole body.
2. **Render the mesh, keep the hologram material.** Swap the Points for the actual SkinnedMesh with a custom shader: fresnel rim in cyan, scanline scroll, additive blending, `depthWrite:false`, and `side: FrontSide` so interiors are occluded by real depth testing rather than by heuristics. Cortana's look is a lit surface with rim glow, not particles. The pointcloud can stay as a thin overlay for the dissolve and speak reactions.
3. **Face detail.** Once a surface is rendering, the eyes want to be emissive discs rather than modelled eyeballs, and the mouth wants to be closed geometry. A small texture swap on the head material handles both without touching the rig.

Step 2 is the one that changes how she reads. It is a shader and material job on geometry that already loads, so the rig, the clips, and the senses layer are untouched.
