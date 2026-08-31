import asyncio, time, json, os, random, re
from aiohttp import web, WSMsgType
PORT = 2423
CLIP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips")
os.makedirs(CLIP_DIR, exist_ok=True)
def custom_clips():
    return [f[:-5] for f in os.listdir(CLIP_DIR) if f.endswith(".json")]
CLIPS = ["idle", "agree", "headshake", "walk", "run", "sad_pose", "sneak_pose"]
BASE = {"idle", "walk", "run", "jogging", "female_walk", "sitting", "guitar_playing", "standing_w_briefcase_idle", "sitting_talking", "talking_on_phone"}
EMOTES = {"excited": "joyful_jump", "bounce": "joyful_jump", "yes": "agree", "nod": "agree", "wave": "wave_hello", "hello": "wave_hello", "hi": "wave_hello", "greet": "standing_greeting", "no": "dismissing_gesture", "sad": "sad_pose", "sneaky": "crawling", "apology": "praying", "sorry": "defeated", "bow": "praying", "kiss": "beckoning", "point": "point_ahead", "salute": "salute", "squat": "squat_down", "lie": "sitting", "laydown": "sitting", "rest": "sitting", "clap": "standing_clap", "phone": "talking_on_phone", "talk": "sitting_talking", "guitar": "guitar_playing", "dance": "dance_loop", "angry": "angry", "surprised": "surprised", "come": "beckoning", "go": "dismissing_gesture", "walk": "walk", "run": "run", "jog": "jogging", "jump": "joyful_jump", "punch": "punch_jab", "idle": "standing_w_briefcase_idle"}
state = {"base": "standing_w_briefcase_idle", "gesture": None, "gaze": None, "seq": 0, "gesture_at": 0.0}
clients = set()
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "content-type"
    return r
async def bcast(msg):
    dead = [w for w in clients if w.closed]
    for w in dead:
        clients.discard(w)
    for w in list(clients):
        try:
            await w.send_json(msg)
        except Exception:
            clients.discard(w)
async def pose_ws(req):
    w = web.WebSocketResponse(heartbeat=20)
    await w.prepare(req)
    clients.add(w)
    await w.send_json({"type": "state", **state})
    async for m in w:
        if m.type == WSMsgType.ERROR:
            break
    clients.discard(w)
    return w
DUR_CACHE = {}
DEFAULT_DUR = 2.2
REPEAT_WINDOW = 22.0
QUEUE_MAX = 3
def clip_dur(name):
    if name in DUR_CACHE:return DUR_CACHE[name]
    v = DEFAULT_DUR
    try:
        with open(os.path.join(CLIP_DIR, name + ".json"), encoding="utf-8") as f:
            v = float(json.load(f).get("duration") or DEFAULT_DUR)
    except Exception:pass
    v = max(0.6, min(6.0, v))
    DUR_CACHE[name] = v
    return v
recent = {}
pending = []
async def fire(clip, layer, fade, note=""):
    state["seq"] += 1
    if layer == "base":state.update(base=clip)
    else:
        state.update(gesture=clip, gesture_at=time.time())
        state["gesture_until"] = time.time() + clip_dur(clip)
        recent[clip] = time.time()
    await bcast({"type": "play", "clip": clip, "layer": layer, "fade": fade, "seq": state["seq"]})
    return {"ok": True, "clip": clip, "layer": layer, "note": note}
async def drain_loop(app):
    while True:
        await asyncio.sleep(0.25)
        if not pending or time.time() < state.get("gesture_until", 0):continue
        clip, layer, fade = pending.pop(0)
        await fire(clip, layer, fade, "queued")
async def play(req):
    d = await req.json()
    print(f"play {d.get('clip')} from {req.remote} ua={req.headers.get('User-Agent','?')[:60]}", flush=True)
    clip = EMOTES.get((d.get("clip") or "").strip().lower(), (d.get("clip") or "").strip().lower())
    if clip not in CLIPS and clip not in custom_clips():
        return cors(web.json_response({"ok": False, "err": "unknown clip", "clips": CLIPS + custom_clips()}, status=400))
    TRAVEL = {"start_walking", "walk_strafe_left", "jumping_down", "jump_loop", "jump_land", "crouch_to_stand", "crouch_turn_to_stand", "standing_up", "situp_to_idle", "sitting_enter", "sitting_exit", "roll", "crawling", "push_loop", "swim_fwd_loop", "sprint_loop", "driving_loop", "punch_enter", "spell_simple_enter", "spell_simple_exit"}
    layer = d.get("layer") or ("base" if clip in BASE else "gesture")
    if clip in TRAVEL and layer == "gesture":
        return cors(web.json_response({"ok": True, "clip": clip, "layer": "skipped", "note": "travel/transition clips distort the stage - pick an in-place move instead"}))
    fade = d.get("fade", 0.4)
    now = time.time()
    if layer == "gesture":
        if not d.get("force") and now - recent.get(clip, 0) < REPEAT_WINDOW:
            return cors(web.json_response({"ok": True, "clip": clip, "layer": "skipped", "note": "just played %.0fs ago - repeating it reads as a twitch" % (now - recent[clip])}))
        if now < state.get("gesture_until", 0):
            if any(q[0] == clip for q in pending):
                return cors(web.json_response({"ok": True, "clip": clip, "layer": "skipped", "note": "already queued"}))
            if len(pending) >= QUEUE_MAX:
                return cors(web.json_response({"ok": True, "clip": clip, "layer": "dropped", "note": "gesture queue full", "queued": len(pending)}))
            pending.append((clip, layer, fade))
            return cors(web.json_response({"ok": True, "clip": clip, "layer": "queued", "queued": len(pending), "waitMs": int((state["gesture_until"] - now) * 1000)}))
    return cors(web.json_response(await fire(clip, layer, fade)))
async def gaze(req):
    d = await req.json()
    state["gaze"] = d.get("target") or d
    state["seq"] += 1
    await bcast({"type": "gaze", "target": state["gaze"], "seq": state["seq"]})
    return cors(web.json_response({"ok": True}))
async def get_state(req):
    st = dict(state)
    if st.get("gesture") and time.time() - st.get("gesture_at", 0) > 12:
        st["gesture"] = None
    st.pop("gesture_at", None)
    st.pop("gesture_until", None)
    st["queued"] = len(pending)
    return cors(web.json_response({**st, "clients": len(clients)}))
async def get_clips(req):
    return cors(web.json_response({"clips": CLIPS + custom_clips(), "emotes": EMOTES}))
async def save_clip(req):
    d = await req.json()
    name = re.sub(r"[^a-z0-9_]", "", (d.get("name") or "").lower())
    if not name or not d.get("data"):
        return cors(web.json_response({"ok": False, "err": "need name+data"}, status=400))
    with open(os.path.join(CLIP_DIR, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(d["data"], f)
    return cors(web.json_response({"ok": True, "name": name, "clips": CLIPS + custom_clips()}))
async def clip_data(req):
    name = re.sub(r"[^a-z0-9_]", "", req.match_info["name"].lower())
    p = os.path.join(CLIP_DIR, name + ".json")
    if not os.path.exists(p):
        return cors(web.json_response({"ok": False, "err": "no such clip"}, status=404))
    with open(p, encoding="utf-8") as f:
        return cors(web.json_response(json.load(f)))
async def opt(req):
    return cors(web.Response())
HOME = "standing_w_briefcase_idle"
IDLES = ["standing_w_briefcase_idle", "talking_on_phone"]
IDLE_W = {"standing_w_briefcase_idle": 5, "talking_on_phone": 1}
LIFE = ["look_over_shoulder", "agree", "acknowledging", "waist_side_stretch", "surprised"]
LIFE_W = [3, 3, 2, 2, 1]
def weighted(names, weights):
    use = [(n, weights[i] if i < len(weights) else 1) for i, n in enumerate(names)]
    tot = sum(w for _, w in use) or 1
    x = random.random() * tot
    acc = 0.0
    for n, w in use:
        acc += w
        if x <= acc:
            return n
    return use[-1][0]
async def alive_loop(app):
    nxt = random.uniform(22, 42)
    since = 0.0
    while True:
        nap = random.uniform(12, 28)
        await asyncio.sleep(nap)
        if not clients:
            continue
        state["seq"] += 1
        g = random.choices(["user", "user", "user", "left", "right", "down"], k=1)[0]
        await bcast({"type": "gaze", "target": g, "seq": state["seq"]})
        since += nap
        if since < nxt:
            continue
        since = 0.0
        nxt = random.uniform(22, 42)
        if time.time() < state.get("gesture_until", 0):
            continue
        if state.get("base") not in IDLES:
            continue
        quiet = time.time() - state.get("gesture_at", 0)
        if quiet > 8 and random.random() < 0.62:
            fresh = [c for c in LIFE if time.time() - recent.get(c, 0) > REPEAT_WINDOW]
            w = [LIFE_W[LIFE.index(c)] for c in fresh]
            if fresh:
                await fire(weighted(fresh, w), "gesture", 0.55, "life beat")
                continue
        if state.get("base") != HOME and random.random() < 0.7:
            await fire(HOME, "base", 1.1, "idle home")
            continue
        alts = [c for c in IDLES if c != state.get("base")]
        if not alts:
            continue
        pick = weighted(alts, [IDLE_W.get(c, 1) for c in alts])
        await fire(pick, "base", 1.1, "idle chain")
async def start_bg(app):
    app["alive"] = asyncio.create_task(alive_loop(app))
    app["drain"] = asyncio.create_task(drain_loop(app))
app = web.Application()
app.on_startup.append(start_bg)
app.router.add_get("/pose", pose_ws)
app.router.add_post("/motion/play", play)
app.router.add_post("/motion/gaze", gaze)
app.router.add_get("/motion/state", get_state)
app.router.add_get("/motion/clips", get_clips)
app.router.add_post("/motion/clip", save_clip)
app.router.add_get("/motion/clipdata/{name}", clip_data)
app.router.add_route("OPTIONS", "/motion/{tail:.*}", opt)
web.run_app(app, port=PORT)
