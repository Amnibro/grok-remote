# Companion architecture (as-built, 2026-08-22)

Restart any box alone; every link reconnects itself.

## Processes

| Process | Port | File | Restart behavior |
|---|---|---|---|
| Hub | :2421 | server.py (supervisor cmd loop) | supervisor relaunches in ~20-60s; renderer retries ws |
| Motion service | :2423 | motion_service.py | renderer /pose ws reconnects <4s, base state replays |
| Renderer | browser | web/xr.html + modules | refresh-only; holds last pose through service blips |
| Braid | :8788 | separate product | bridged read-only via hub proxy |

## Renderer modules (web/)

- `xr.html` — core: three scene, point sampler (surface-normal culled shell), GPU skinning,
  render loop, gesture overlay, mode/entry UI, AudioContext. 1139 lines.
- `xr-voice.js` — TTS queue behind `initVoice(ctx)`: serialized speak queue, `/api/xr/tts`
  fetch + decode, speechSynthesis fallback with a length-based timeout so a device with no
  voice engine cannot wedge the queue, speak/idle state transitions. The AudioContext itself
  stays in the shell — it must be created inside the real user gesture from the enter button,
  and a dynamic import would lose that gesture. `voiceV` (`speaking`/`alevel`/`gestureSeed`)
  is shared by reference; the render loop and the gesture overlay read it every frame.
- `xr-brain.js` — hub client behind `initBrain(ctx)`: `/ws` JSON-RPC (initialize →
  session/new), reconnect, `session/update` chunk accumulation, sentence flush, and the
  inline-tag dispatch (`[[motion|emote|gaze|compose:…]]`) into motion/compose. `ask()` stays
  in the shell because it owns the body briefing and the camera-frame attachment.
- `xr-motion.js` — motion client behind `initMotion(ctx)`: `/pose` ws with reconnect, clip
  resolve + lazy fetch from the service, base crossfade vs gesture one-shot, per-action
  fadeOut timers, pending-play queue for pre-mixer calls. Shares `motionState`
  (`gestureHold`/`gazeTarget`/`gazeUntil`/`lastGesture`) with the render loop by object
  reference — those are read every frame in `perform()` and the animation loop.
- `xr-ik.js` — two-bone arm IK behind `initIK(ctx)`; see the Arm IK section.
- `xr-panels.js` — all six UI panels behind `initPanels(ctx)`:
  [h] debug HUD (motion/session/cam/vision state) · [c] camera passthrough · [x] manual
  snapshot · [t] conversation visualizer · [j] clip jukebox · [b] Braid panel · [v] live code
  map. Move rows in the transcript are annotated from `clip_index.json` with tier, energy, and
  a hitch flag, so you can read her choices at a glance:

```
⟡ motion: wave_hello   (moderate 18.5)
⟡ motion: joyful_jump  (explosive 118.5)
⟡ motion: idle_loop    (moderate 15 · hitches)
```

  The conversation panel carries a stats line (turns each way, her word count, moves
  fired, most-used move, session span) over a 60-event bar strip coloured amber/blue/green
  for you/her/move, each bar hover-titled with its text. Bar height normalises to the longest
  message in the window — scaling by absolute length made every bar 4-7px and flat.
- `xr-compose.js` — the move-invention engine behind `initCompose(ctx)`: parses the
  `[[compose:name|ms:Bone=x,y,z ...|ms:rest]]` DSL, bakes a real AnimationClip against the
  rig rest pose, plays it, uploads it to the motion service, snapshots her performance to
  companion_view.jpg for the self-refinement loop.
- Module imports are cache-busted (`?t=`) — /static caches for a day otherwise.

## Pose harvest (`/static/pose-harvest.html`)

Video in, playable clip out. MediaPipe PoseLandmarker (lite, float16) runs over the video at
a chosen fps; each frame's 33 world landmarks retarget onto eight limb bones by aiming each
bone's rest direction at the landmark-pair direction, then the frames slerp-smooth over a
window and bake into an AnimationClip that saves straight to the motion service.

Everything is vendored under `web/vendor/mp/` (15 MB: 5.8 MB task + 9.4 MB wasm), so the
harvester needs no CDN at run time. Landmark space converts to three space as `(x, -y, -z)`.

`__harvest.selfTest(clipName, frames, size)` closes the loop without any footage: it renders
`rikku_mixamo.glb` playing a known take into an offscreen canvas, runs the detector on those
pixels, retargets, and compares the recovered arm directions against the source rig's actual
directions. Measured at 480x640, 12 frames each:

| take | detected | median err | p90 |
|---|---|---|---|
| acknowledging | 12/12 | 15.1° | 19.8° |
| standing_greeting | 12/12 | 11.5° | 41.3° |
| joyful_jump | 12/12 | 13.7° | 40.3° |
| salute | 12/12 | 16.0° | 33.6° |

Median ~14° reads the gesture correctly and is not precision mocap. Retarget math itself is
exact: synthetic landmarks for an arm along +x give bone direction `[1,0,0]`.

MediaPipe demands strictly monotonically increasing timestamps for the landmarker's whole
lifetime, so `detectForVideo` gets a private counter (`nextTs()`), never `performance.now()`.
With wall-clock timestamps a second harvest run on the same page silently detected ZERO poses
— the error only surfaced after the empty `catch` was made to report:
`INVALID_ARGUMENT ... Packet timestamp mismatch on stream "norm_rect"`.

GLTFLoader strips the colon from bone names, so clips bake as `mixamorigLeftArm.quaternion`
while the hand-authored clip store uses `mixamorig:Hips.quaternion`. Both bind, because
three sanitizes the track's node name the same way when resolving.

## Arm IK

`xr-ik.js` solves analytic two-bone IK on `<Side>Arm → <Side>ForeArm → <Side>Hand`. It bends
in the plane the current animation already put the elbow in (bend axis = `cross(AB, BC)`),
then aims the whole chain at the target, so it rides on top of whatever clip is playing
instead of fighting it. `tick()` runs in the render loop between `updateMatrixWorld` and
`skeleton.update()`, so the solve reaches the skin in the same frame.

The AI drives it with `[[reach:SIDE TARGET]]` — SIDE left/right, TARGET one of
user/up/down/front/left/right or `x,y,z` meters — and `[[reach:release]]` to let go. The hand
holds the target across frames until released. `reach()` runs the requested point through
`fit()` first, which pulls it onto a sphere of 0.92 × arm span around the shoulder, so a
far-away target gives a natural bend instead of a locked-straight arm.

Measured on the live rig: right arm L1 0.251 m, L2 0.186 m. With the pose reset between
runs, `sign:-1` lands err 0.000 with the elbow *below* the shoulder line (y 1.201 vs shoulder
1.327); `sign:+1` lands err 0.059 with the elbow level at y 1.32, a chicken-wing. Keep -1.
An out-of-reach target reports the honest shortfall in `state.err` (1.5 m target → err 1.04).

## She can always see her own body

With the camera off, `captureView()` used to just bail. It now falls back to `selfSnap()`,
which writes a `solidShot()` render to `companion_view.jpg`, so she can inspect her own
posture whenever she wants — no webcam required. The prompt note is branched: camera on gives
the "camera eyes are ON" line, camera off gives a line saying it is a render of her own body.
Claiming the camera was on when it was not would have been a straight lie in her context.

Throttled to one self-render per 60 s. The first version fired on every single ask, which the
suite caught immediately — steady-state turn size jumped from 2 chars to 250 and every turn
paid for a full solid render.

## Solid self-view for the compose loop

Her self-refinement snapshot used to be the hologram — 8% lit pixels on near-black, where an
arm clipping the body is invisible. `solidShot()` fixes that: the solid GLB is already in the
scene at `visible=false`, so the shot shows it, hides the pointcloud, swaps in a grey
background and dedicated lights, frames a 38° camera on the model's bounding box, renders one
frame, centre-crops to portrait 480x640, and restores every borrowed piece of state.

Four things had to be right, each found by measuring the image rather than assuming:

| attempt | mean luminance | reads as a person |
|---|---|---|
| hologram pointcloud | 21 | no (0/6) |
| solid, no lights | 0 | no |
| solid + lights, black bg | 3 | no |
| solid + lights + grey bg, framed landscape | 133 | no (0/4) |
| same, centre-cropped to portrait 480x640 | — | **yes (4/4)** |

The scene has no lights at all (the point shader does not need any), so a standard material
renders pure black. And "lit pixel percentage" on a grey backdrop measures the backdrop, not
her — that metric said 99% while MediaPipe still saw nothing. Aspect was the last blocker:
landscape fails, portrait detects, same pixels.

Verified end to end: a `[[compose:…]]` wrote a 480x640 RGB `companion_view.jpg`, and the
camera FOV was back to 58 afterwards.

## Look-at (she turns toward the person)

Her gaze was random — the alive loop picked `user/left/right/up/down` out of a hat. With the
camera on, `xr-look.js` runs the vendored PoseLandmarker on a 256x192 downscale of the feed
every 600 ms, takes the nose position blended 60/40 with the shoulder midpoint, maps it to a
yaw and writes `motionState.lookYaw` plus a 2.5 s `lookUntil`. The render loop prefers that
over the random wander while it holds, so she tracks whoever is in frame and drifts back to
idle wandering when they leave.

Mapping verified with synthetic landmarks, symmetric about centre:

| person at frame x | yaw |
|---|---|
| 0.2 | +0.42 |
| 0.5 | 0.00 |
| 0.8 | −0.42 |

Live on the fake camera: 24 frames processed, 24 misses, no errors — correct, since Chrome's
fake device is a colour pattern with no person in it. End-to-end with a real human in frame is
UNVERIFIED, same boundary as the pose harvester.

Pointing the detector at her own `/xr` canvas does NOT close that gap, and it is worth knowing
why. The harvester's self-test detects her at 100% because it renders the **solid, lit GLB on
a grey background**. The `/xr` hologram is a sparse pointcloud on near-black — measured at 8%
lit pixels, mean luminance 21/255 — and MediaPipe found a person in 0 of 6 frames of it. She
cannot see herself through her own eyes; only a real camera or a video with a human in it will
verify look-at. The same fact explains why judging a composed pose from `companion_view.jpg`
is hard when the snapshot is the hologram rather than a lab render.

Two traps: `FilesetResolver.forVisionTasks(path)` resolves against the **page** URL, not the
module's, so `/xr` was looking for `/vendor/mp/` (404) while the harvester at
`/static/pose-harvest.html` worked — the vendor paths are absolute now. And MediaPipe writes
`INFO: Created TensorFlow Lite XNNPACK delegate` to `console.error`, which the error bus was
dutifully recording as a fault; it filters `INFO:`/XNNPACK/TensorFlow Lite now.

## Rig limits on this avatar

`rikku_mixamo.glb` has **no morph targets** on any of its 15 meshes and **no eye, eyelid, or
jaw bones** — 81 nodes, the only head-ish ones being `mixamorig:Head` and `HeadTop_End`.
Blinking, eye darts, and visemes are all impossible without new geometry. Life has to come
from the neck, spine, arms, and the procedural breath already in `perform()`.

## Vision loop

The 8 s watchdog and the compose self-view both write `companion_view.jpg`, so with the
camera on, her pose snapshot was being overwritten by a camera frame within 8 seconds — long
before she could look at it on her next reply. Composing now sets `vision.hold` 20 s out and
the watchdog skips while that holds.

Verified with the fake camera running: compose at 16:24:18 wrote a 6011-byte pose frame,
frame count stayed put through 16:24:28 with the hold active, and at 16:24:30 the loop
resumed and wrote an 8450-byte camera frame.

`captureView(src)` in the shell grabs a 640px frame from the passthrough camera and POSTs it
to `/api/xr/see`, which writes `companion_view.jpg` into the hub's cwd. It runs three ways:
on every `ask()` (and appends a line to the prompt telling her the frame is fresh), from a
4s watchdog that re-captures whenever the last frame is older than 8s, and on the `[x]` key
for a manual snap. `vision {on,frames,last,err,src}` is surfaced in the debug HUD and the
code map, so a stale or failing eye is visible instead of silent.

Testing it needs Chrome's fake camera: `--use-fake-device-for-media-stream
--use-fake-ui-for-media-stream`. Key handlers are bound to `window`, so a CDP-dispatched
`KeyboardEvent` must set `bubbles:true` or it never reaches them.

## Mic can hang, so it has a guard now

Auditing the voice path, two suspicions were wrong and one real risk was left. Space **does**
have a matching `keyup` handler, so hold-to-talk is symmetric with the button. And the second
`let rec` at the top of `localAvatarUrl` is an IndexedDB record, not the SpeechRecognition
object — harmless today, renamed to `recd` because a later `rec.stop()` in that function would
have hit the wrong thing entirely.

The real risk: `recOn` only clears in `onend` and `onerror`. If neither fires, the flag stays
true forever, the talk button stops responding (`if(!recOn)startRec()`), and the mic is dead
until reload. `rec.start()` was also unguarded, so a throw would strand the same flag.

Both fixed: `start()` is wrapped, and a 25 s watchdog clears `recOn`, drops the `rec` class,
stops recognition and returns to idle.

Reproduced naturally rather than simulated. Headless Chrome exposes `webkitSpeechRecognition`
with no microphone behind it, so recognition started and never ended — no result, no error, no
`onend`. The guard fired, `recOn` went false, state returned to `idle`, and the error bus
recorded `mic: recognition never ended - clearing stuck listen state`.

## Avatar dropdown verified end to end

The local-file path had assertions; the dropdown path never did. Exercised for real —
selecting an entry, letting it reload, and reading what actually loaded:

| step | file | bones | rig | driven | stored |
|---|---|---|---|---|---|
| start | rikku_mixamo.glb | 65 | 100% | 49 | null |
| pick model.glb | model.glb | 65 | 100% | 36 | "model.glb" |
| reset to default | rikku_mixamo.glb | 65 | 100% | 42 | null |

Zero errors throughout, and the drive probe follows the avatar — it reports
`Armature|mixamo.com|Layer0` on `model.glb` (its only embedded take) versus `acknowledging`
on the Mixamo build.

No suite assertion added. It shares the same `companionModel` → `loadModel()` path the local
avatar assertions already cover, and a second reload would add ~35 s to a run that is already
long enough that skipping it becomes tempting.

## Bring your own .glb from disk

The selector only listed files already sitting in `web/`. The landing page now takes a file
picker: the .glb is read to an ArrayBuffer, stored in IndexedDB (`companionAvatar` → store
`f` → key `avatar`) with its filename, and `companionModel` is set to `__local`. On every
later load the renderer pulls it back out, wraps it in a Blob URL, and loads that ahead of
the static fallbacks. A `clear` button drops the record. Capped at 120 MB, `.glb` only, no
server changes.

Two traps, both of which hid behind the loader's silent fallback:

- The cache-buster. `loadAsync(url + "?t=" + Date.now())` exists because `/static` caches for
  a day, and it produces `blob:http://host/uuid?t=123`, which is not a valid blob URL. The
  load failed and quietly fell through to `rikku_mixamo.glb`, so everything looked fine while
  the custom avatar was ignored. Blob URLs now skip the cache-buster.
- `idbGet()` swallowed its errors and returned null, which made the fallback look like normal
  behaviour. It reports to the error bus now.

End to end after the fix: `rig.file` reads `my_custom_avatar.glb (local)`, 65 bones, rig 100%,
clips drive 41 bones, zero errors, and `performance.getEntriesByType("resource")` shows **no
.glb request at all** — the body came out of the browser store.

Three suite assertions guard it: the suite stores `model.glb` into IndexedDB under
`suite_avatar.glb`, reloads, checks `rig.file`, drive count, and a clean error log, then
deletes the record. Proven to fail — re-injecting the cache-buster gives
`{"f":"rikku_mixamo.glb","d":40,"e":0}`: the file assertion fails while drive and error-count
still pass, which is exactly why the bug was invisible by eye.

Assertions on counts use a numeric `gt` helper, not substring matching. A `has ... '"d":4'`
check passed only by accident on 41/49 and broke the moment `model.glb` reported 36.

## Drive probe (the right way to verify binding)

Following the `findNode` dead end below, `driveProbe()` measures the thing that actually
matters: it snapshots every bone quaternion, builds a throwaway mixer on the model root,
plays a real clip at mid-duration through three's own binding path, counts how many bones
changed, then restores the pose. It runs 2.5 s after the skeleton is ready and records
`driven` and `probe` on `rigInfo`; the code map shows `clips drive 49/65 bones`.

On `rikku_mixamo.glb` the probe clip `acknowledging` drives 49 of 65 bones. Proven to catch a
dead rig: renaming every bone dropped it to 0 and pushed
`clip "acknowledging" drove 0 bones - this avatar will not animate` onto the error bus;
renaming back restored it to 52 (the higher figure is the base animation having advanced).

## Track binding: do not try to verify it with findNode

An attempt to show "N/66 tracks bound" in the code map reported **0/66 for `wave_hello` on a
rig that visibly plays it**. The cause: GLTFLoader strips the colon, so bones are named
`mixamorigHips`, while the stored track is `mixamorig:Hips.quaternion` and
`THREE.PropertyBinding.parseTrackName` treats `mixamorig:` as a separator, returning
`nodeName: "Hips"`. `findNode(root,"Hips")` finds nothing, yet three still binds and animates
through its own resolution path.

Measured directly instead: playing `wave_hello` swung the right arm from
`[-0.894,-0.365,0.26]` to `[-0.215,-0.672,0.708]`. The clips bind.

That check was reverted rather than shipped — a permanent red 0/66 on a healthy rig is worse
than no indicator. If binding ever needs verifying, measure bone deviation before and after a
play; never infer it from `findNode`. `window.__xr.THREE` is exposed for this kind of probing.

## Tool pages match the live avatar

The lab and the harvester both loaded `model.glb` while the renderer showed
`rikku_mixamo.glb`, so authoring happened against a body that was not hers. Both now read the
same `localStorage.companionModel` the renderer honours, defaulting to `rikku_mixamo.glb` and
falling back to `model.glb` if that fails. Confirmed by reading the page's own resource
timing: `glbLoaded: ["rikku_mixamo.glb"]`, error log empty, 65 bones.

Both also carry the renderer's error bus now, writing straight into the `#msg` line, so a
throw while authoring shows up instead of leaving a dead button. Verified by firing
`null.boom()` into the lab: `msg` became `ERR js: Uncaught TypeError…`.

## Motion lab (`/static/motion-lab.html`)

Live loop-seam readout under the key list, using the same first-vs-last-key angle as the
offline tools, so a base authored here closes properly instead of shipping a hitch:

```
seam 50.0 deg HITCHES hard    (RightArm -60 then -10)
seam  0.0 deg loops clean     (returned to -60)
```

Colour-coded green under 8°, amber under 40°, red above. Two suite assertions drive it by
authoring an open loop then closing it.


Practice range on `model.glb`. Bone sliders + snap-key authoring, plus a timeline strip:
drag a key marker to retime, click to select and load that pose, update/dup/delete, scrub
the built clip frame-accurate, layer any library clip underneath at a blend weight, and
`bake blend` samples the blended result at 20fps into a new saved clip.

## Idle drift and life beats

Her base had been `standing_w_briefcase_idle` on infinite loop — the alive loop only wandered
her gaze, so the body underneath never changed. `alive_loop` now also drifts the base every
70-150 s among `IDLES = [standing_w_briefcase_idle, idle_loop, idle_talking_loop]`, and only
when the current base is already one of those, so it never overrides a base the AI chose
(walking, sitting, dancing) or interrupts a gesture.

Watched live for 3.5 minutes: base held at `standing_w_briefcase_idle` through t+90 s, swapped
to `idle_loop` at t+105 s with seq stepping by 2 (gaze plus base play), and the renderer HUD
followed to `idle_loop`. Restarting the service resets `seq` to 0 and the renderer reconnects
within 4 s.

On the same tick, if nothing has gestured for 150 s, half the time it fires a life beat from
`LIFE = [look_over_shoulder, acknowledging]` instead of swapping the base, so long silences
get a small movement rather than a frozen loop.

Polling `/motion/state` cannot see those beats — the gesture field self-clears after 12 s and
a 20 s poll steps right over it. Read the renderer instead: `document.title` and
`motionState.lastGesture` both recorded `acknowledging` after a 5-minute watch showed only
`seq` climbing.

`state["gesture"]` used to stick forever, so the HUD claimed she was saluting minutes after
she stopped. Plays now stamp `gesture_at`, `/motion/state` blanks a gesture older than 12 s,
and `gesture_at` is stripped from the response rather than leaking into the API.

## Move pacing feedback

Her briefing tells her to be sparing with moves, and nothing ever told her whether she was.
`moveStats()` reads the convo log for the last 24 entries and returns turns, move count, the
most-used move and its count. `ask()` appends a one-line body note when she is over-moving,
worded as a pacing nudge she is told not to voice:

- moves/replies above 0.6 → "you have used 9 moves across your last 10 replies…"
- any single move used 3+ times → "joyful_jump has come up 5 times lately…"

Silent otherwise, so a well-paced conversation costs nothing. Verified both branches: five
clean exchanges produce no note; five repeats of `joyful_jump` trip the repeat branch; nine
varied moves over ten replies trip the rate branch.

## Conversation recap across reloads

Refreshing `/xr` mints a new brain session, so she used to come back with no idea you had
been mid-conversation while the transcript panel still showed every word of it. The first
`ask()` after a load now prepends a recap built from the persisted convo log: up to six
non-move lines, 180 chars each, only if the newest is under six hours old, with an
instruction to pick up naturally rather than greet him fresh or recite it back.

Order matters — the recap is captured *before* `panels.addConvo("you", text)`, otherwise the
message being sent lands in its own recap. Fires once per page load.

Verified: fresh log gives no recap (4863-char prompt); seed four exchanges, reload, and the
first turn carries `[You and Anthony were already talking 0 minutes ago…]` ending at her last
line, while the second turn has none.

## Landscape clipped the code map

Rotating with the panels open found the same class of bug one layer deeper. On 844x390 the
code map rendered 424 px tall from `top:44px` — 78 px hanging off the bottom of a 390 px
screen with no scroll, because the panel had no `max-height` or `overflow`.

Everything else survived rotation: hud 144 px, transcript and jukebox 226 px (the jukebox
already scrolled), Braid 56 px, and the touch bar at y=351 clear of all of them.

Capped at `calc(100vh - 96px)` with `overflow-y:auto` and `max-width:96vw`. Landscape now
gives 318 px scrollable at 844x390 and 303 px at 667x375, and portrait is unchanged at
384 px wide with nothing clipped.

## Landscape phone cut off the landing page

Portrait is fine at every height down to 500 px. Landscape is not: `#land` is
`position:fixed;inset:0` with `overflow-y:visible`, so content taller than the viewport is
simply unreachable — no scroll.

| viewport | content hidden below the fold |
|---|---|
| 844x390 | 4 px |
| 667x375 | 12 px |
| 568x320 | 39 px |

One CSS change — `overflow-y:auto` plus `overscroll-behavior:contain` and a little padding.
All three landscape sizes now scroll and reach the bottom of the content.

## Phone layout verified at 390x844

With the panels finally reachable by touch, the question was whether they fit. Measured under
a real CDP viewport override (`tests/xr-mobile.mjs`, `Emulation.setDeviceMetricsOverride`):

| panel | width | fits 390px |
|---|---|---|
| hud | 165 | yes |
| jukebox | 230 | yes |
| transcript | 290 | yes |
| braid | 310 | yes |
| code map | 384 | yes, 6px to spare |

No change needed. Three assertions lock it, including `widest < 391`, so a future panel that
outgrows a phone fails the suite.

Two traps worth remembering. `--window-size=390,844` on headless gave a 487x699 viewport —
only the CDP override produces a true phone size. And the first measurement returned all-zero
rects reading as "fits", because `doKey` toggles and the panels were already open from an
earlier probe; the assertion now reports `seen` so a hidden panel cannot pass as fitting.

Test-order coupling bit again: this probe opens five panels and shows the touch bar, which
broke the touch-bar assertions running after it. It restores state before returning now.

## Strands instead of a slab

Every loose point shared one lag texture, so the whole ponytail moved as a single piece.
There are two now — a fast one and one at `SLOWMUL = 0.42` of its rate — and the shader picks
per point:

```
float hv=fract(aRnd.z*7.13);
pNow=mix(pNow,mix(pLag,pLag2,hv),clamp(cw*(0.65+0.5*hv),0.0,0.85));
```

`hv` varies both which texture a point leans on and how strongly it lags, so neighbouring
points sit at different places along the trail. One extra texture, one extra 4-bone skin for
the ~1600 loose points.

Measured live by skinning each loose point with both matrix sets and taking the distance:

| | worst | mean |
|---|---|---|
| at rest | 22 mm | 13 mm |
| mid-salute | 30 mm | 20 mm |

A first attempt at that metric compared the translation columns of the two bone textures
directly and reported 725 mm, which is not a distance in the world — the skinning matrix
carries the bind inverse, so its translation column is not a position. That version came back
out rather than shipping a number that reads like millimetres of hair and isn't.

## Headless coverage for the lag loop

`tests/lag.mjs` drives the whole lag path against a stub 18-bone texture, so it costs no GPU
and can run while someone is wearing the headset:

| check | value |
|---|---|
| lag rate, calm | 6.96 |
| lag rate, 1-second burst | 2.12 |
| rate after the burst ends | 7.00 |
| strand separation while moving | 5 mm |
| strand separation once settled | 1 mm |

Writing it exposed a design property worth stating out loud. My first version shook the rig for
five straight seconds and the rate never moved, which looked like a dead feature. The floor had
simply learned that shaking was the new normal — which is the intent, since an avatar with a
busy idle clip should not sit at maximum trail forever. A gesture is a transient, so the test
models a transient.

## Hair that reacts to how fast she moves

A fixed lag rate gives the same trail whether she nods or throws a salute, so the rate now
tracks rig speed. `lagAuto` sums the per-frame change in the translation column of every bone
matrix, divides by `dt`, and eases the result:

```
rate = clamp(base / (1 + slowK * excess), minA, maxA)
excess = max(0, speed - floor * headroom)
```

`floor` is a self-calibrating baseline that falls at 0.25/s and rises at 0.12/s, so it settles
onto whatever her current idle costs and treats anything above it as a real move. No per-avatar
tuning constant, and a busier idle clip raises its own floor instead of permanently maxing the
trail.

Measured live across a calm window and a salute:

| | calm | salute |
|---|---|---|
| rig speed | 0.67 | 16.64 |
| lag rate | 6.83 | 1.60 |

Lower rate means longer trail, so a fast gesture buys **4.3x** more hair lag than her idle. The
`restRate > 2.5` assertion is the other half of that — hair that never settles reads as broken
just as badly as hair that never moves.

Finding the speed signal took one wrong turn: the first version summed every 4th float in the
bone texture, which lands on the `(0,0,0,1)` bottom row of each affine matrix and reads exactly
zero forever. Stride 16, offsets 12 through 14.

## Her hair swings

The verlet cloth sim was the wrong tool. It needs CPU-side world positions, and the real
avatar skins on the GPU, so there was nothing to simulate against.

What shipped instead is lag skinning. Every frame the bone texture gets copied into a second
texture that eases toward it at `dt*7`, so `uBoneTexLag` holds the pose from a few frames ago.
The vertex shader skins each point twice and mixes:

```
float cw=aFlex*uCloth;
pNow=mix(pNow,pLag,clamp(cw,0.0,0.85));
```

A loose point renders at a slightly older pose, so it trails when the head turns and settles
when she stops. It can never detach, because both positions are legitimate skinned positions of
the same vertex.

### Finding the loose points

`flex` only ever got filled on the `!skinned` branch, which the real avatar never takes. The
mesh-name heuristics were dead anyway — every mesh in `rikku_mixamo.glb` is named
`7_mesh12_1_0_0`, so `/hair|ponytail|tail/` was never going to match, and `localToWorld` on a
skinned mesh returns bind-space coordinates that put every mesh centroid at the model's feet.

`hairFlex` in `xr-deform.js` ignores meshes entirely and reads the rig. A point whose dominant
skin weight belongs to a bone matching `/head|hair|ponytail|braid|scarf|cloth|skirt|coat|cape|
tail/i` gets `flex = (down/span)^1.4 * 0.55`, where `down` is how far it hangs below that
joint. Zero at the attachment, maximum at the free end.

On the live avatar:

| measure | value |
|---|---|
| loose points found | **1678** of 115 000 |
| owning bone | `mixamorigHead` |
| hang span below the joint | 435 mm |
| peak flex weight | 0.55 |
| pose-lag drift, idle | 86 163 |
| pose-lag drift, during a salute | **182 127** |

The drift pair is the proof the mix has something to trail toward — the lagged pose diverges
2.1x further from the live pose while a gesture plays.

### The static imports were serving day-old code

Three cycles of new modules came in as static imports with no cache-buster, while the older
dynamic ones carry `?t=Date.now()`. `/static` was `max-age=86400`, so the browser held the old
`xr-deform.js` and the page died on `does not provide an export named 'LOOSE'` against a file
that had exported it for ten minutes.

`server.py` now sends `no-cache` for `xr-*.js` and leaves everything else on the day-long
cache. Two assertions pin both halves, since flipping the whole `/static` route to `no-cache`
would drag `three.module.js` over the wire on every load.

## xr-deform.js, and the cloth sim that never ran

Going after the per-frame hot path, I found `stepPhysics` — a 55-line verlet cloth simulator
with wind, gravity, damping, and an elastic stray-radius clamp. Nothing calls it. `physState`
is declared `null` on line 421 and never assigned anywhere in the file.

It gets worse upstream. `samplePoints` computes a per-point `flex` array: scarf points get
`0.6 * down^1.8` so looseness is zero at the attachment edge and only the free end swings, hair
gets a falloff below 55% height. That array is returned as `res.flex` and then read by nothing.
Her hair and scarf have never moved.

`web/xr-deform.js` now holds both halves — `skinFrame` (the live CPU-skinning path) and
`clothStep` (the sim), with the tuning constants lifted into an exported `CLOTH` object and a
`strayRadius(state)` reporter. `xr.html` keeps five lines: the temp matrices, a context builder,
and two one-line wrappers. `physState` is still null, so the cloth call is a no-op today.

Benched headless against a stub THREE (this measures loop structure, not real matrix math):

| path | points | per-call |
|---|---|---|
| cpu skin | 20 000 | 0.22 ms |
| cloth step | 4 000 | 0.13 ms |

Over 120 steps the worst stray point sits **6 mm** from its target against a **26 mm** elastic
limit, so the clamp does hold and no piece can visibly detach.

Both functions stopped trusting their callers. `skinFrame` returns `null` on any of six missing
inputs (all three probed) and skips bone indices outside the matrix array instead of reading
`undefined.elements`. `clothStep` returns `null` on missing state or a zero-length cloud.

Wiring `physState` is the next job, and it needs a decision first: the CPU skin path only runs
on the synthetic fallback body, while the normal GLB path skins on the GPU, where the CPU has
no cheap read of where the hair currently is.

## xr-skin.js: the synthetic rig came out

The earlier dependency scan said `bindSynthetic` writes fifteen globals and I left it alone.
Reading it properly, it writes three — `skelRoot`, `skeleton`, `sampledMeshMatrix` — and reads
`uniforms`. The scan was over-inclusive because it swept the whole 87-line span including the
neighbours.

So it came out. `web/xr-skin.js` exports the joint table, the twelve capsules, `buildSkeleton`,
`skinWeights`, and `dominantBone`. What stayed in `xr.html` is nine lines that assign the three
globals and reset the bind matrices.

Pulling the capsule table out of the function body is what made the rig testable. Twelve probe
points, one at each joint's own position:

| check | value |
|---|---|
| bones built | 12 |
| capsules bound to a bone | 12 of 12 |
| joints whose own point picks their own bone | **12 of 12** |
| weight sum per point, min and max | 1.000000 / 1.000000 |
| body points blending 2+ bones | **100%** |
| same meter on a rigid one-bone bind | **0%** |
| bind time, 1000 points | 4 ms |

That 100% is the one I wanted. The comment in the original code says capsule weights exist so
hard height bands don't razor-cut the body into rigid sections at every threshold, and nothing
had ever checked it. The rigid control at 0% is what makes the 100% mean something.

`skinWeights` also stopped trusting its inputs: a capsule naming a bone that isn't in the rig
gets filtered out and `bindSynthetic` logs it to the error bus, an empty cloud returns
zero-length arrays, and a boneless rig returns all zeros instead of `undefined` indices.

## xr-body.js: the pure geometry came out

`reposeStatic` and `meterize` were the only two functions in the synthetic-body block that
touch zero module globals — I mapped reads and writes across all three candidates first, and
`bindSynthetic` writes fifteen of them, so it stayed put.

The two pure ones are now `web/xr-body.js`, imported statically. Both return a summary object
instead of nothing, which is what let me assert on them:

| check | value |
|---|---|
| scaled height | 1700 mm |
| feet on floor | y=0 |
| x centered | 0 |
| forward-most point ends up rearmost (z mirror) | yes |
| leg points given flex weight | 544 of 544 |
| arm points moved by repose | 56 |
| largest single point move | 370 mm |

`tests/body-geom.mjs` runs it headless on a synthetic 600-point cloud. Two dead locals came
out on the way — `knotY` and `zAtt` were computed every call and never read.

Writing the harness surfaced a trap worth naming: `flex[i]=0.2` into a `Float32Array` and then
`v===0.2` against a double is always false, so the flex assertion read 0 of 544 and looked like
a real bug. The comparison needs a tolerance.

### The code map was hiding a module

`body` sat in the panel's SKIP list because no such file existed — `modUp("body")` meant "rig
is ready". Now that `xr-body.js` is real, SKIP drops to `{core:1}` and the marker fires when
the module loads, so the visualizer stops under-reporting its own stack.

Moving that `modUp("body")` call to the top level of the script blew up the entire renderer:
58 assertions failed with `__xr is not defined`, because `modUp` closes over a `const` declared
600 lines below it. Same TDZ shape as the previous three. It belongs inside the import's
`.then`, where the whole module body has already evaluated.

## xr-pose.js: the fallback body came out

`xr.html` shipped 41 lines of `if(n==="Hips")return [...]` chains generating the synthetic
body's idle and talk clips. Those only run when the GLB fails to load, so they were the
least-exercised code in the renderer and the easiest to break unnoticed.

They're now `web/xr-pose.js` behind `initPose({THREE,getSkeleton})`, with the if-chains
rewritten as two lookup tables keyed by bone name. `makeBodyClip` returns `null` when the
skeleton is missing instead of throwing halfway through a `.map`.

The module also exports `seamOf(clip)`, which walks every quaternion track and returns the
angular distance between the first and last keyframe. Both fallback clips measure **0.000°** —
their poses are pure sin/cos over exactly one period, so the endpoints coincide by
construction. A ramp pose that climbs 0.6 rad and never comes back measures **34.378°**, which
is what stops the zero from being a rubber stamp.

`tests/pose-seam.mjs` runs all of it headless against a stub THREE, so the least-exercised path
in the renderer now has five assertions without needing a browser.

The code map panel picks the module up automatically: its row list comes from live readiness
markers, so the count went 7 to 8 the moment `modUp("pose")` fired. The suite assertion that
hardcoded 7 caught the change and now checks `rows == mods` instead of a fixed number.

## Overlap matrix for the persistent chrome

Having shipped one control on top of another, the sweep got generalised: measure every
always-present element and test all pairs for intersection. Five elements — caption, exit,
talk, type row, touch bar — across three viewports:

| viewport | overlaps | offscreen |
|---|---|---|
| 390x844 | none | none |
| 844x390 | none | none |
| 360x640 | none | none |

Clean, so nothing shipped from it beyond three assertions that run the matrix at 360x640, the
tightest case. `n > 4` guards the empty-sample trap: an all-hidden UI would otherwise report
zero overlaps and pass.

## The touch bar was covering the talk button

The bar I added to make panels reachable on phones was `position:fixed;bottom:8px` — straight
on top of the composer it was meant to sit beside. Measured:

| viewport | bar | type row | talk | verdict |
|---|---|---|---|---|
| 390x844 | 729-836 | 700-740 | from 750 | covers both |
| 844x390 | 351-382 | 246-286 | from 296 | covers the talk button |

On a phone the primary control was sitting under my new toolbar. Shipping a feature that
blocks the main input is worse than not shipping it.

It is now a child of `#hud` (a flex column) with `order:-1`, so layout places it above the
composer and it can never collide: 589-658 in portrait with the type row at 700, 173-204 in
landscape with the type row at 246. Being inside `#hud` also means it inherits the landing-page
hide for free. `#hud` is `pointer-events:none`, so the bar sets `pointer-events:auto` — the
existing "touch button opens its panel" assertion proves the buttons still respond.

Three more assertions: renders at real width on a phone, clear of the text input, clear of the
talk button.

## Touch bar (the panels were desktop-only)

All seven panel actions were bound to `keydown` and nothing else, so on a phone or in the
Quest browser there was no way to open the HUD, transcript, jukebox, Braid panel, code map,
camera, or snapshot. Six features and a headset target, unreachable without a keyboard.

The keydown body moved into `doKey(k)`; the keyboard listener and a pill-button bar both call
it, so there is one implementation. The bar shows on touch-primary devices and stays out of
the way on desktop.

Gating took two tries. `navigator.maxTouchPoints > 0` showed it on desktop — headless Chrome
reports `maxTouchPoints: 2` alongside `pointer:fine`, and laptops with touchscreens do the
same. The working test is `(pointer:coarse) && !(any-hover:hover)`, plus a one-shot
`touchstart` listener so a real touch reveals it anywhere.

Four assertions: hidden on desktop, appears on touchstart, has all seven buttons, and a
button press actually opens its panel.

## TTS latency is variance, not length (no change shipped)

Probing `/api/xr/tts`, a 1296-char sentence took **16.1 s**. That looked superlinear against
287 chars at 2.9 s and 575 at 3.2 s, and the obvious fix was to chunk long text so audio
starts sooner.

Re-timing killed it. The **same** 1295-char text then took 2.2 s and 3.2 s, while 863 chars
took 7.4 s. Latency is dominated by round-trip variance to the edge-tts service, with no
usable relationship to text length. Chunking would have added round trips, each with its own
variance, to solve a phantom.

Nothing shipped. Two facts worth keeping: the endpoint is robust on content (unicode,
em-dashes, emoji and Al Bhed all return 200; empty text is correctly rejected 400), and
`pump()` calls `say(text)` **before** the fetch, so her words appear on screen immediately and
only the audio lags during a slow synthesis.

## Braid backend is down (diagnosis, 2026-08-22)

The `/api/xr/braid` bridge has been returning `live:false` for several cycles. Facts gathered:

- `Amni-Delve/dist/Braid.exe` exists — 21 MB, built 08-19 00:14
- nothing is LISTENING on `:8788`
- the Braid **desktop shell is still open** and retrying: an `msedgewebview2.exe` (the Tauri
  webview) holds repeated `SYN_SENT` sockets to `127.0.0.1:8788`

So the window is alive and its backend died underneath it. Starting it is a separate
product's call, so nothing was launched from here.

The companion degrades correctly meanwhile, verified live: `[b]` panel reads "Braid offline",
the code map dot goes red, the prompt note is skipped rather than sent empty, and the suite
SKIPs its Braid assertion instead of failing.

## Visibility sweep across every added element

After the badge, I checked whether anything else I had shipped was invisible. Every UI element
added this session, measured by real `getBoundingClientRect()` rather than by its inline
style:

| page | elements checked | rendered |
|---|---|---|
| motion-lab | 17 | 16 |
| pose-harvest | 10 | 10 |
| xr panels | 6 | 4 |

The three zero-size cases are all legitimately empty containers, confirmed by populating them:
`#keys` in the lab goes to 29 px tall after two snapped keys, `#clog` to 38x270 after two
messages, and `#blines` is empty only because Braid is offline. The badge remains the only
element that was genuinely hidden.

## The companion badge was never visible

Chasing phone layout found that the badge I added to `<header>` has never rendered. The hub
runs a `layout-braid` UI with `body.class = "layout-braid bordered can-hover page-chat"` and
`header { display:none }` — at **both** 1280x800 and 390x844. The element existed, its inline
style said `inline-flex`, and its bounding rect was 0x0.

My own assertions passed the whole time because they checked `badge.style.display`, the value
I had set myself, rather than whether anything rendered. Exactly the empty-sample class
documented above, in my own test.

The badge is now created in JS and appended to `document.body` as `position:fixed` bottom-left
with `z-index:9999`, so no layout mode can hide it. Verified as a real box: 170x25 at left 10,
inside the viewport at both widths. The assertions check `getBoundingClientRect()` and require
width over 40 px.

## Companion badge in the hub chat

From the desktop chat there was no way to tell whether she was running, so the header now
carries a small pill that polls `/motion/state` every 10 s and links straight to `/xr`
(carrying the key through). Three states, all verified live:

| condition | badge |
|---|---|
| motion service down | hidden entirely |
| service up, no renderer | amber dot, `idle · standing_w_briefcase` |
| renderer attached | green dot, `1 live · standing_w_briefcase · salute` |

Killing the service hid it; restarting brought it back to `1 live` on the next poll without a
page reload, because the renderer reconnects on its own.

## Body tags never reach the chat UIs

`[[motion:…]]`, `[[emote:…]]`, `[[gaze:…]]`, `[[compose:…]]`, `[[reach:…]]`, and bare
`[[wave]]` forms mean something only to the renderer. The hub chat strips them in
`takeAgentRx()` (the same choke point that already consumed `[[rx:…]]`, and the only place
agent text passes through for streaming, history repaint, and replay). The watch page strips
them in `stripBody()` on the way to `setLine`.

The bare-tag pattern is `[[a-z0-9_]{2,40}]]`, so wiki-style links survive: `[[MyWiki]]` and
`[[two words]]` pass through untouched, and `arr[[0]]` is below the two-character floor.
Verified against the live hub UI, calling the real `takeAgentRx` in the page.

Four suite assertions cover this, driven by opening a second tab on the already-running test
Chrome: `curl -X PUT ":$PORT/json/new?<url-encoded hub url>"`, then evaluating with
`CDP_PAGE="2421/?key"`. Proven to fail — disabling the colon-form replace let
`[[motion:agree]]` through while the bare-tag line still stripped `[[wave]]`, which is exactly
the split the two assertions distinguish.

The `/xr` conversation panel still shows moves as `⟡` rows — that is where they belong.

## Code map derives its own module list

The map held a hardcoded array of six module filenames. Adding `xr-look.js` left it stale
immediately — a code visualizer that had stopped showing all the code. It now derives the
list from the live readiness markers (`__xr.mods()` minus `body`, `core`, and the session id),
so a new module appears the moment it registers.

Three assertions lock it: row count equals module count, and no row reports `0 lines` (which
would mean a module the map names but cannot fetch).

## Code map measures itself

The `[v]` map used to be a hand-drawn tree that could drift from reality. It now fetches each
module and reports real line counts and sizes, so the picture cannot lie:

```
   · xr-panels.js    186 lines  11.7kb
   · xr-brain.js      67 lines  3kb
   · xr-motion.js     66 lines  3.2kb
   · xr-voice.js      52 lines  1.6kb
   · xr-ik.js         86 lines  3.4kb
   · xr-compose.js    93 lines  4.3kb
```

Measured once per panel open and cached.

## Jukebox sorted by energy

The `[j]` list is ordered calm → moderate → lively → explosive using `clip_index.json`, each
row coloured by tier, showing its deg/s, hover-titled with tier, energy, and duration.
Unrated clips sink to the bottom.

`/motion/clips` returns 101 entries containing 97 unique names — `agree`, `walk`, `run`, and
`sad_pose` each appear twice, since the service merges the `clips/` files with GLB-embedded
aliases without deduping. The jukebox and the briefing both dedupe on read, which is why the
list shows 97; fixing the service itself would need a restart.

## She feels her own faults

The renderer knew when the motion link dropped or the camera was failing; she did not, so a
broken body read as a mood. `ask()` now builds an ailment list — motion ws down, vision
capture erroring, rig under 80%, any renderer error inside the last five minutes — and when
it is non-empty appends a note telling her to say plainly what is broken if asked, without
apologising in circles or inventing a cause. A healthy renderer appends nothing, so it costs
zero tokens in the normal case.

Verified both directions: healthy gives a 4882-char prompt with no note; one synthetic
`noteErr` and the next prompt carries `1 renderer error(s), latest console: …`. Both are
suite assertions.

## Runtime error bus

Two failures this build were invisible: a `codeMapRefresh` that threw on an undefined helper
and rendered a blank panel, and a TDZ ReferenceError that killed every dynamic import while
the page still looked alive. Nothing surfaced either one.

`errLog` now sits at the top of the module — before any import, so it catches module failures
too. It hooks `window.onerror`, `unhandledrejection`, and wraps `console.error`, keeping the
last 30 entries with repeat-collapsing (`x4` rather than four rows). The debug HUD carries an
`errors` line and the code map shows a red dot the moment anything throws.

Verified by firing all three kinds at a live renderer — `null.boom()` in a timer, a rejected
promise, an explicit `console.error` — and all three landed as `js`, `promise`, `console`.
The bus reads empty at boot, which is itself the assertion the suite makes.

## Braid context in her prompt

The `[b]` panel showed Braid to the human while she stayed blind to it. `ask()` now hits
`/api/xr/braid` (a local proxy, measured 55 ms) and, when the room is live, appends a compact
note: session count plus the last two transcript lines truncated to 140 chars each, with an
instruction to raise it only when asked and never recite it unprompted. Adds roughly 400
characters per turn.

## Hub wedge: aiohttp request factory goes None

The hub can reach a state where the socket still accepts and every request dies in the
protocol handler:

```
TypeError: 'NoneType' object is not callable   aiohttp/web_protocol.py start()
```

`self._request_factory` is None, meaning the app started shutting down while the listener
stayed open. `/health` and `/xr` both hang to timeout, `netstat` shows LISTENING plus a pile
of CLOSE_WAIT, and the supervisor never intervenes because it only respawns on process exit.

Why nothing caught it: the supervisor actually running is `logs/cmd-supervise-*.cmd`, a plain
loop that spawns `server.py` and waits for it to **exit**. A wedged-but-alive process blocks
that wait forever, so the loop never iterates. `scripts/supervise-ui.ps1` does poll health,
and it was not the one running — the live supervisor process was created *after* the recovery.

Worse, `motion_service.py` has **no supervisor at all** — nothing in `start.ps1`, the scripts,
or `server.py` launches or restarts it. If her body service dies it stays dead.

`scripts/hub-watchdog.ps1` fills both gaps without touching the launch chain: poll `/health`
every 10 s (5 s timeout), and after 3 consecutive failures force-kill whatever holds the
LISTENING socket so the cmd supervisor sees an exit and respawns. Run it alongside:

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hub-watchdog.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hub-watchdog.ps1 `
  -Name motion -Port 2423 -HealthPath /motion/state -FailsBeforeKill 2 `
  -RespawnExe <python> -RespawnArgs <plugin>\motion_service.py
```

`scripts/watchdogs.ps1` wraps both into one command and is idempotent — running it twice
reports "already running" instead of stacking duplicates:

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/watchdogs.ps1          # start both
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/watchdogs.ps1 -Status  # list
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/watchdogs.ps1 -Stop    # stop both
```

Neither survives a reboot; drop that start line into autostart if you want them permanent.

The 3-fail threshold is not arbitrary. During a suite run the hub logged
`health fail 1/3` at 17:15:32 and `health recovered after 1 fail(s)` ten seconds later —
headless browsers hammering it produced a transient miss. At `FailsBeforeKill=1` that would
have killed a perfectly healthy hub mid-test.

It takes `-HealthPath` (any endpoint that returns JSON), and `-RespawnExe`/`-RespawnArgs` for
services nothing else restarts. With no respawn command it only kills, leaving the cmd
supervisor to bring the process back; with one, it starts the service itself.

Motion respawn proven by killing the service outright:

```
health fail 1/2 listener pid=0
health fail 2/2 listener pid=0
respawning: python.exe ...\motion_service.py
after respawn: listener pid=119116
```

`/motion/state` answered again 14 s after the kill.

Tested against a deliberately wedged listener rather than the live hub — a python socket that
accepts and never replies on port 2499. The watchdog logged three failures, killed it, and
confirmed `pid alive=0`, then correctly reported "no listener on port" once it was gone.

Recovery, confirmed on 2026-08-22: `Stop-Process -Force` reported the process still alive and
the LISTENING row persisted, `taskkill /F` then said "process not found" and `Get-Process`
confirmed 0 — the netstat row was stale. The supervisor respawned 40 s later. Verify through
`/health` for `ready:true` **and** `agent_listening:true`, never a bare 200.

Trigger here was almost certainly repeated headless renderers being killed mid-websocket
during testing. Kill test browsers between phases rather than leaving sockets half-closed.

## Soak result (leaving her running)

Every check up to this point was short-lived, so the renderer got a real soak: 120 gesture
plays across ~8 minutes on a headless instance launched with `--js-flags="--expose-gc"`.

| point | heap | clips in memory |
|---|---|---|
| baseline | 34.7 MB | 42 |
| after 40 distinct clips | 36.2 MB | 57 |
| after 80 more replays | 36.3 MB | 57 |

The 1.5 MB rise is the 15 newly fetched clips, roughly 100 KB each. Replaying clips already in
memory moved the heap 0.1 MB across 80 plays, so nothing accumulates per play — the mixer
action cache, the `gestureOut` timer map, and `fetchedClips` all stay bounded. Error bus
empty throughout, `/pose` websocket still linked, and the arm still swung on a fresh
`joyful_jump` at the end.

To repeat it: launch with `--expose-gc`, call `gc()` before each `performance.memory` read,
and fire clips through `POST /motion/play` rather than in-page so the whole path is exercised.

## Prompt budget

Five separate injections had accumulated without anyone measuring the total, so I measured
before touching anything: first turn 4862 chars, steady state **555** — of which 544 was the
Braid block riding on every single turn.

Braid now carries a signature (`sessions|last two lines`) and only re-sends when that
changes. Steady-state overhead dropped from 555 to **2 chars**. Verified by stubbing
`window.fetch` for `/api/xr/braid` to return a different transcript: the note re-fired with
the new session count, then suppressed again on the following identical turn.

First turn is 5119 (the body briefing dominates and is gated by `__bodyPrimed` to once per
page load). The conditional blocks — recap, pacing nudge, body faults, compose metrics — are
all zero-cost when their condition is false.

## Prompt composition check

The whole briefing is assembled at `ask()` time from four live sources, so the suite verifies
the real outgoing prompt without spending an agent turn: stub `brain.req`, call `__ask()`,
read what the stub captured, restore. A green run confirms a 4830-char prompt carrying the
tier-grouped clip library, the `[[reach:…]]` documentation, and the Braid context.

## Bring-your-own avatar (rig check)

A GLB with the wrong bone names used to load silently and simply never move — the clips bind
to `mixamorig:*` names, so a mismatched rig is a mannequin. `rigReport(url)` runs the moment
the skeleton is built: it strips the `mixamorig:` prefix, compares against 20 required bones,
and records `{file,bones,matched,missing,pct}`. Under 80% it says so on screen, naming the
first few missing bones. The result caches to `localStorage` per file, so the landing dropdown
shows `· rig 100%` next to any avatar that has been loaded once. The code map carries the
same line.

`rikku_mixamo.glb` reports 65 bones, 20/20, 100%. `Soldier.glb` also passes at 100% (49
bones) — three.js's Soldier is itself a Mixamo export, so it is NOT a negative test. To prove
the failure path, rename five bones on the live skeleton and re-run: matched drops to 15/20,
pct 75, and `missing` lists exactly the five renamed.

Note the name collision hazard: `rig` was already the XR `THREE.Group`. The rig report object
is `rigInfo`.

## Empty-sample guards (a check that checks nothing passes)

Two measurements this session reported perfect scores while measuring nothing: the pop A/B
read 0.06 cm because the arm was frozen, and the rest-pose probe read 0° for every clip
because `restQ` was not exposed so every bone was skipped. Same shape both times — a loop
whose filter drops everything leaves the accumulator at its initial value, which reads as
success.

The three offline auditors had the same hole. `brief-audit`, `service-audit`, and
`clip-invariants` all reported empty "missing" lists and exited 0 if their regex failed to
find the list they were supposed to scan. Each now emits `parsed_ok` (and counts) and exits
nonzero when it found nothing to check, with a suite assertion per tool.

Proven: renaming `IDLES` to `IDLES_RENAMED` in `motion_service.py` used to give clean empty
output and exit 0 from both tools that read it. It now gives `"counts": {"IDLES": 0},
"parsed_ok": false` and `"idles_checked": 0, "parsed_ok": false`, both exit 1.

Rule for any new check here: report the sample count and fail on zero. A green light from an
empty loop is worse than no light.

## Null result: distance-from-rest says nothing about gesture harshness

Chasing residual pop, I measured how far each clip's first keyframe sits from the rig's rest
pose, expecting the outliers to be the clips that yank her into position. Median 175°, with
177-180° on hips and legs for **every** clip — including `standing_w_briefcase_idle`, which
plays constantly and looks fine.

Two independent methods agreed (offline from the GLB node rotations, and in-page against the
renderer's authoritative `restQ` with all 65 bones matched), so the number is real and the
interpretation was wrong. The rest pose is the **bind** pose, not the pose she stands in; a
leg sitting ~180° from bind is simply what animated legs look like. Distance from rest is
therefore not a quality signal for anything.

What does measure gesture harshness is the runtime frame-to-frame jump at the transition,
already covered above (42 cm before the weight-easing fix, 6-7 cm after). No change shipped
from this line of inquiry beyond exposing `__xr.restQ()` for probing.

## Loop seams: the UAL `*_loop` clips do not loop

Chasing the gesture-start pop turned up a bigger one. Sampling the hand during **pure idle,
no gesture at all**, showed a displaced frame every ~2.5 s — and `idle_loop` is 2.5 s long.
Switching the base to `standing_w_briefcase_idle` (14.3 s) gave **zero** big jumps in 9 s.

Measuring the seam directly — angular distance between each track's first and last keyframe:

| clip | seam | 
|---|---|
| standing_w_briefcase_idle | 0.05° |
| idle_loop | 70.3° |
| idle_torch_loop | 74.5° |
| sitting_idle_loop / sitting_talking_loop | 86.9° |
| idle_talking_loop | 91.6° |
| crouch_idle_loop | 128.9° |

Every UAL clip named `*_loop` is a one-shot segment despite the name; playing it on repeat
snaps 70-129° at the wrap, once per cycle. All 33 seamless clips in the library are
Mixamo-baked (~0.04°).

`IDLES` is `["standing_w_briefcase_idle", "talking_on_phone", "guitar_playing"]` — all Mixamo, seam ~0°. After a prop idle, `pick_chain` hops to the other unused prop 28% of the time, else HOME. `IDLE_DWELL` is 16s briefcase / 16s phone / 14s guitar. Additive gaze is skipped while `gestureHold` is live so Mixamo head motion is not overwritten.
The idle-drift feature had been making her *worse* since it was added, twitching every 2.5 s
whenever it drifted to `idle_loop`.

Across the whole library, **45 of 94 clips loop seamlessly and 49 do not**. Nine of the 22
`BASE` entries are in the broken half, so the AI could still pick one by name and leave it
hitching. Rather than change playback (removing them from `BASE` would turn them back into
one-shot gestures, the bug fixed above), the measurement now travels with the data:
`clip_index.json` carries `seam` and `loops` per clip, and the briefing gains a line naming
every base that hitches above 40°, telling her to use those as a one-off beat and never leave
one running.

`tools/clip-invariants.py` checks every `IDLES` entry seams under 8°. Proven to fail: putting
`idle_loop` back gave `"idles_with_loop_seam": [["idle_loop", 70.29]]` and exit 1.

## Gesture-start pop (measured, then fixed)

Every gesture started with a visible snap and nobody had measured it. Sampling the right
hand's world position each frame across a `wave_hello` start showed a **42 cm jump in a single
39 ms frame** — roughly 10 m/s, impossible for a wave.

The cause was in the render loop: the gesture action fades in over 0.4 s while the idle layer's
weight was **stepped** from 1.0 to 0.12 in one frame. For the first frames total weight
collapsed toward 0.12, the pose sagged to rest, then recovered.

Both layer weights now ease toward their target at `dt*5.5` instead of snapping. Measured from
a settled idle, four consecutive runs:

| build | max single-frame hand jump |
|---|---|
| stepped weights | 42.2 cm |
| eased weights | 6.0, 6.2, 6.8, 7.1 cm |

Two assertions guard it: max frame jump under 200 mm, and total path over 100 mm so a frozen
arm cannot pass by not moving at all. That second one matters — during the A/B the old build
produced three readings of 0.06 cm, which looked like a perfect score and actually meant the
arm never moved.

## Clip invariants (root motion stays frozen)

"All baked clips are root-motion-frozen (Hips X/Z pinned)" had been written down and never
checked. `python tools/clip-invariants.py` scans every clip in `clips/` for a Hips position
track whose X or Z travels more than 2 cm, plus empty/unparseable files and absurd durations.

The invariant holds: **0 of 94 clips carry root motion.** Worth locking anyway, because the
motion lab's `buildClip` emits a `Hips.position` track whenever the hips moved, and
`window.lab.setHips()` lets you move them — so a lab-authored clip can break it. The pose
harvester is safe by construction, writing quaternions only.

Proven to fail: planting a clip with 1.2 m of hip travel gave
`"root_motion": [["__invtest.json", 1.2]]` and exit 1.

## Compose bone whitelist

The compose engine resolved any short bone name that existed on the rig, so
`[[compose:x|400:Hips=0,80,0|1200:rest]]` baked and played an 80° hip spin — contradicting the
root-motion-frozen rule that keeps her performing in place. The documented list of 19 bones
was guidance she could simply ignore.

`ALLOWED` in `xr-compose.js` now enforces exactly that list. Illegal bones are dropped,
collected into `skipped`, and reported back in her next prompt:

> `IGNORED bones you are not allowed to drive: Hips - only Spine/Spine1/Spine2/Neck/Head/
> Shoulder/Arm/ForeArm/Hand/UpLeg/Leg/Foot are legal, Hips stays pinned so you do not slide
> off the stage.`

Verified before and after: the same spec baked `peakBone: "Hips"` at 80° beforehand, and
afterwards gives `skipped: ["Hips"]` with `peakBone: "LeftArm"` at 50° — the legal half of the
move still works.

All 19 documented bones resolve exactly against the live skeleton (no fuzzy fallbacks), and
every gaze direction `alive_loop` emits is known to the renderer's `GZ` table.

The suite deletes its own scratch clips now. A `suitehold.json` from an earlier run had been
sitting in the library since 18:11, which is how the count read 102 instead of 101.

## Service list audit (and a real classification bug)

`motion_service.py` carries four hardcoded clip-name sets — `BASE`, `TRAVEL`, `IDLES`,
`LIFE` — plus the `EMOTES` alias map, none of them validated against the library. Auditing
them found `female_standing_pose` in `BASE` with no such clip (inert, since unknown clips are
rejected before that line), and one genuine bug:

**`idle_loop` and `idle_talking_loop` were not in `BASE`.** A play with no explicit layer
falls back to `"base" if clip in BASE else "gesture"`, so the AI sending
`[[motion:idle_loop]]` got a one-shot gesture that faded out, rather than a looping base.
The idle-drift feature only worked because `alive_loop` passes `layer="base"` itself.

Added the in-place idle loops (`idle_loop`, `idle_talking_loop`, `idle_torch_loop`,
`sitting_talking_loop`, `crouch_idle_loop`). Confirmed against the live API:

```
idle_loop          -> base
idle_talking_loop  -> base
sitting_talking_loop -> base
wave_hello         -> gesture
salute             -> gesture
```

Locomotion loops (`jog_fwd_loop`, `sprint_loop`, `swim_fwd_loop`, `driving_loop`,
`push_loop`, `crouch_fwd_loop`) were left out deliberately — they carry root motion.

`python tools/service-audit.py` checks all five lists plus "every IDLES entry is also in
BASE", and two suite assertions run it. Restarting the service to pick up the fix also
demonstrated the motion watchdog for real: killed at 18:00:44, respawned automatically.

## Briefing drift audit

Her body briefing names clips in prose — a mood guide, a base-clip guide, and a hardcoded
fallback list used when `/motion/clips` fails. Nothing kept those in sync with the actual
library, and two had rotted: `laughing` and `lay_down` do not exist. She was being told about
moves that would silently do nothing.

Replaced with `sitting_laughing` and `laying_breathless`, both real.

`python tools/brief-audit.py` extracts every snake_case name from the briefing and the
fallback list, checks each against `/motion/clips` and its emote aliases, prints a JSON
summary and exits nonzero on any miss. Two suite assertions run it. Proven to fail: injecting
`sitting_XXlaughing` gave `"fallback_missing": ["sitting_XXlaughing"]` and exit 1.

## Clip energy index

`node tools/clip-index.mjs` walks `clips/*.json` and writes `web/clip_index.json`, keyed by
FILENAME (the motion service lists filenames, and a clip's internal `name` often differs —
`crouch_fwd_loop.json` holds `Crouch_Fwd_Loop`). Per clip it records peak deviation, the
dominant bone, mover count, duration, and motion energy = mean per-key angular travel across
major bones per second. Fingers and toes are excluded.

Energy, rather than peak angle, is what separates a small beat from a showy one. Peak angle
rated 45 of 94 clips "big" because a 14-second idle loop swings a forearm 90° eventually, and
`salute` peaked on `RightHandMiddle3`. Energy sorts the way a person would:

| clip | deg/s | tier |
|---|---|---|
| standing_w_briefcase_idle | 7.4 | calm |
| agree | 7.6 | calm |
| salute | 14.6 | moderate |
| wave_hello | 18.5 | moderate |
| dance_loop | 92.6 | explosive |
| joyful_jump | 118.5 | explosive |

The session briefing groups her library into those four tiers instead of dumping one flat
list, so she picks amplitude to match the moment. Rebuild the index after adding clips.

## Compose feedback metric

Composing used to be judged only by eye, off `companion_view.jpg`. `xr-compose.js` now runs
`measure()` on every clip it bakes: it applies the clip's own first key, records the hand
positions, then walks every key measuring peak angular deviation from rest (which bone, how
many degrees) and the furthest the hands travel. The result rides into her NEXT prompt as a
line she can act on, alongside the snapshot.

Measured ladder on the live rig (RightArm, 3 keys, 1.2 s):

| DSL angle | peak reported | hand travel |
|---|---|---|
| 8° | 8.0° | 6.1 cm |
| 60° | 60.0° | 42.6 cm |
| 150° | 150.0° | 82.6 cm |

Anchor travel to the clip's own first key, never to the live animated pose. Measuring against
the live pose reported 28.3 cm for an 8° move, because key 0 snaps the arm from wherever the
base animation had it back to rest, and that snap dominated the number.

## Verification

`bash tests/companion-suite.sh` is the whole-stack check — 158 assertions in one run: hub and
motion service up, all six renderer modules serving 200, every file md5-identical across the
plugin tree and the repo mirror, both static pages booting, then a live headless renderer
where it asserts the brain negotiated a session, the renderer attached to the pose ws, a
`[[motion:…]]` tag actually changed the service gesture, the TTS queue drained to idle, arm
IK solved to err 0, and the vision loop captured a frame off the fake camera. Exits nonzero
on any failure and kills its own Chrome on the way out.

Runs in ~100 s with per-phase timings printed. The Braid assertion SKIPs rather than fails
when `:8788` is offline — Braid is a separate product, and the companion suite should not go
red because it is down.

Assertions that call `__ask()` have to be order-independent now that Braid and the recap
only fire once. Two of them broke by consuming another assertion's first turn; the fix is
`__xr.resetBraidSig()` and zeroing `__xr.vision().last` inside the assertion that needs a
fresh one. `QUICK=1` skips the local-avatar phase (71 s).

The timings paid for themselves immediately: the first measured run took 131 s, of which 56 s
was the live-renderer phase and 40 s the local-avatar phase — almost all of it fixed `sleep`
padding. Both now poll for readiness (`waitfor` on `brain().ready()` and on `rig.file`) and
print a note if the wait times out, which cut those phases to 35 s and 8 s. Measure before
optimising: the assumption going in was that the suite took several minutes, and it never did.

Proven to fail before being trusted: hiding `xr-ik.js` turned a green run into 3 failures
(module 404, mirror mismatch, IK null).

`bash tests/page-smoke.sh <page.html> "<title sentinel>"` loads the page in headless Chrome
and asserts the module reached its sentinel (`document.title`). Confirmed to FAIL on a
deliberately broken build before being trusted.

`document.title` is the readiness bus. The renderer reports `xr ok [body,compose,core,motion,
panels] 65 bones`, appending ` | <clip>` on every gesture — so a headless run plus a
`POST /motion/play` proves the whole broadcast→resolve→play round trip, not just page load.
Chrome for tests lives at `.cache/puppeteer/chrome/win64-*`; always launch with a throwaway
`--user-data-dir` and kill by matching that dir, since the MCP browser shares the binary.

`--dump-dom` HANGS on `/xr?auto=1` — the open hub websocket stops virtual time from
expiring. For any page that holds a live socket, launch with `--remote-debugging-port` and
drive it with `CDP_PORT=<port> CDP_PAGE=<url-fragment> node tests/xr-live.mjs '<expression>'`, which evaluates in the live page via
CDP (node's global WebSocket, no dependencies). `window.__xr` exposes `mods() brain()
motion() motionState clips() state()` for exactly this.

Full-pipeline check without spending an agent turn: set `__xr.brain().B.accum` to text
containing a `[[motion:…]]` tag, call `flushSentences(true)`, then read `/motion/state` and
confirm the gesture changed.

## Hub endpoints (server.py)

- `/xr` — renderer page (no-store)
- `/api/xr/tts` — edge-tts voice (rate +12%, pitch +16Hz)
- `/api/xr/see` — saves a jpeg to `<cwd>/companion_view.jpg` (camera eyes + compose self-view)
- `/api/xr/models` — GLB list for the avatar selector (any Mixamo-rigged GLB in web/ appears)
- `/api/xr/braid` — proxies Braid :8788 /api/state + /api/sessions

## Motion service (:2423)

- clips/ store: ~100 clip JSONs (three AnimationClip.toJSON format). Baked Mixamo set +
  hand-authored gestures + her own compose inventions.
- `POST /motion/play {clip,layer,fade}` — emote aliases resolve; travel/transition clips
  are refused as gestures (root yaw = rotate-freeze-teleport); base set loops.
- `ws /pose` — broadcast play/gaze/state to renderers; alive-loop wanders her gaze 18-40s.
- All baked clips are root-motion-frozen (Hips X/Z pinned) — she performs in place.

## The AI's control surface

Inline tags in her speech, stripped before TTS: `[[motion:clip]]`, `[[emote:name]]`,
`[[gaze:dir]]`, `[[compose:...]]`. Session briefing (first prompt) carries the library,
a mood guide, restraint rules, and the feedback-loop instructions (view companion_view.jpg
at the start of the next reply after composing; re-compose under the same name to refine).

## Known rules

- Only real mocap loops as bases; single-frame pose bakes crumple (rest-frame mismatch).
- The GLB's embedded take is never used as idle fallback.
- Meter-scale rig (hips rest y≈1.0); lab setHips uses meters.
- Judge torso in the lab, hair on the body (cloth physics owns hair; raw wireframe lies).
- The speech "talk" layer must never bind a seated/travel clip — it rides at full weight while
  she speaks and averages against any gesture. It is forced to 0 during a gesture hold.
- Replaying the same gesture clip clears its pending fadeOut timer (gestureOut map), otherwise
  the first play's fadeOut cuts the second mid-move.
