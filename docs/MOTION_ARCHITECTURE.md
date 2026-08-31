# Companion Motion Architecture — the AI inhabits the body

Goal (Anthony, 2026-08-21): the hologram is a BODY the AI inhabits. Motion is part of the
model's action space — think "scream" and the body screams, think "run" and it runs. That
requires (1) a controllable skeleton, (2) a motion vocabulary the AI can compose, (3) modular
processes so any piece restarts without touching the rest (no more whole-stack restarts).

## Process split (restart independence)

| Module | Form | Restart cost |
|---|---|---|
| Hub (grok-remote server) | existing :2421 | untouched by motion work |
| Renderer (`/xr`) | thin three.js page: receives POSE FRAMES, draws points | browser refresh only |
| Motion service | NEW process, own port + supervisor: skeleton state, clip library, layered blender, IK | restart alone; renderer holds last pose and reconnects |
| Acquisition tools | offline scripts (Blender factory, video→pose harvester, practice range) | run ad hoc, never live |

Renderer subscribes to the motion service (`ws://…/pose`, 30–60Hz bone quaternions). The brain
never computes poses — it emits INTENTS.

## The AI's control surface

1. **Intent tags in speech** (same pattern as the rx-meter tags): the model writes
   `[[motion:wave]]`, `[[emote:excited]]`, `[[gaze:user]]` inline; the pipeline strips them
   from TTS and forwards to the motion service. Thinking IS doing.
2. **Direct API** for tools/agents: `POST /motion/play {clip, layer, blend}`,
   `POST /motion/ik {bone, target, seconds}`, `POST /motion/gaze {x,y,z}`.
3. **Layered blending** (motion service, not renderer): base idle loop · gesture layer
   (clips/IK, additive) · gaze/head layer · audio-reactive micro layer. A scream =
   gesture(arms_up_fast) + head(back) + audio spike, composed at runtime.

## Motion acquisition — three feeders, one format

Canonical clip = JSON: `{bones:[names], fps, tracks:{bone:[quat…]}, meta}` on the standard
(Mixamo-name) bone set. Everything below emits this.

1. **Ready-made libraries** (seed vocabulary): Xbot.glb clips (idle/agree/headShake/walk, MIT,
   already in web/), Mixamo exports (Anthony's Adobe login), Quaternius CC0 packs. Convert
   with a Blender/three script to clip JSON.
2. **Practice range** (`/motion-lab`): skeleton view + designated TARGETS ("right hand here in
   0.4s", "look there"). Two-bone analytic IK proposes the motion; a human (or vision model)
   rates; accepted takes are recorded as clips. This is where NEW motions get trained and
   where the AI learns composable primitives.
3. **Video→pose harvester**: grok-imagine (or any) motion video → pose estimation
   (MediaPipe/MoveNet, the amni-ai PT-trainer pattern) → 33-landmark tracks → retarget to the
   bone set → clip JSON. Batch tool, offline. Mass-produces natural presets.

## Body pipeline state (2026-08-21)

- WORKS, live: CC-BY Rikku pointcloud, synthetic 12-bone + capsule-blend weights, cloth verlet,
  voice/brain loop. Known flaws (bent wrists, lean, twist loop) are the synth path's ceiling.
- BUILT, parked: Blender factory (`tools/rig_companion.py`, `tools/rig_mixamo.py`) — bone-heat
  weights bind clean; the Xbot fusion deforms wrong (rest-pose mismatch suspected). RULE: debug
  fusion with headless bpy test RENDERS before any browser round-trip.
- Renderer glTF path is spec-pure (identity binds, joints carry placement) and cache-busts
  model fetches (`?t=` — /static caches a day, swapped models resurrected stale).

## Build order

1. Fix the Xbot fusion in Blender (posed-frame render as proof) → her mesh on the Mixamo rig
   playing pro clips — kills wrists/lean/twist in one move.
2. Extract motion service from xr.html (pose-frame WS, clip JSON, layer blender) + thin the
   renderer. Own port, own supervisor.
3. Intent tags through the speech pipeline.
4. clip-from-GLB converter → seed library from Xbot/Mixamo.
5. /motion-lab practice range with IK targets.
6. Video→pose harvester (PT-trainer pattern).
