import asyncio, time, json, os, random, re
from aiohttp import web, WSMsgType
PORT = 2423
CLIP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips")
os.makedirs(CLIP_DIR, exist_ok=True)
def custom_clips():
    return [f[:-5] for f in os.listdir(CLIP_DIR) if f.endswith(".json")]
CLIPS = ["idle", "agree", "headshake", "walk", "run", "sad_pose", "sneak_pose"]
BASE = {"guitar_playing", "standing_w_briefcase_idle", "talking_on_phone"}
EMOTES = {"excited": "joyful_jump", "bounce": "joyful_jump", "yes": "agree", "nod": "agree", "wave": "wave_hello", "hello": "wave_hello", "hi": "wave_hello", "greet": "standing_greeting", "no": "dismissing_gesture", "sad": "sad_pose", "sneaky": "crawling", "apology": "bow_apology", "sorry": "bow_apology", "bow": "bow_apology", "kiss": "blow_kiss", "point": "point_ahead", "salute": "salute", "squat": "squat_down", "clap": "standing_clap", "phone": "talking_on_phone", "talk": "chin_think", "guitar": "guitar_playing", "dance": "dance_loop", "angry": "angry", "surprised": "surprised", "come": "beckoning", "go": "dismissing_gesture", "walk": "walk", "run": "run", "jog": "jogging", "jump": "joyful_jump", "punch": "punch_jab", "idle": "standing_w_briefcase_idle"}
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
REPEAT_WINDOW = 16.0
QUEUE_MAX = 3
def clip_dur(name):
    if name in DUR_CACHE:return DUR_CACHE[name]
    v = DEFAULT_DUR
    try:
        with open(os.path.join(CLIP_DIR, name + ".json"), encoding="utf-8") as f:
            v = float(json.load(f).get("duration") or DEFAULT_DUR)
    except Exception:pass
    v = max(0.6, min(8.0, v))
    DUR_CACHE[name] = v
    return v
recent = {}
pending = []
async def fire(clip, layer, fade, note=""):
    state["seq"] += 1
    if layer == "base":state.update(base=clip, base_at=time.time())
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
    if clip in TRAVEL or any(x in clip for x in ("sit", "lay", "crouch", "plank", "walk", "run", "jog", "sprint", "dance", "twerk", "shuffle")):
        return cors(web.json_response({"ok": True, "clip": clip, "layer": "skipped", "note": "ground/travel clips leave the standing stage - stay standing"}))
    fade = d.get("fade", 0.4)
    now = time.time()
    if layer == "base" and now < state.get("gesture_until", 0) and not d.get("force"):
        state["follow_base"] = clip
        state["follow_at"] = state.get("gesture_until", now)
        return cors(web.json_response({"ok": True, "clip": clip, "layer": "queued", "note": "idle after gesture"}))
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
IDLES = ["standing_w_briefcase_idle", "talking_on_phone", "guitar_playing"]
IDLE_W = {"standing_w_briefcase_idle": 6, "talking_on_phone": 1, "guitar_playing": 1}
IDLE_DWELL = {"standing_w_briefcase_idle": 32.0, "talking_on_phone": 16.0, "guitar_playing": 14.0}
LIFE = ["look_over_shoulder", "agree", "waist_side_stretch", "surprised", "dismissing_gesture", "point_ahead", "salute", "module_check", "sun_salute", "bow_apology", "excited_bounce", "machinamachina_spark", "chin_think", "blow_kiss", "hand_on_heart", "standing_clap", "wave_hello"]
LIFE_W = [2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 2, 2, 1, 2, 1, 1]
LIFE_SOFT = ["look_over_shoulder", "agree", "module_check", "machinamachina_spark", "surprised"]
LIFE_HEAD = ["look_over_shoulder", "module_check", "machinamachina_spark"]
FAM = {"look_over_shoulder": "look", "agree": "nod", "chin_think": "nod", "salute": "arm_up", "sun_salute": "arm_up", "standing_clap": "arm_up", "wave_hello": "arm_up", "waist_side_stretch": "stretch", "point_ahead": "point", "dismissing_gesture": "point", "module_check": "soft", "machinamachina_spark": "soft", "surprised": "soft", "hand_on_heart": "heart", "bow_apology": "heart", "blow_kiss": "heart", "excited_bounce": "bounce"}
def extra_life():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "clip_index.json")
    if not os.path.isfile(p):
        return
    try:
        idx = (json.load(open(p, encoding="utf-8")) or {}).get("clips") or {}
    except Exception:
        return
    skip = set(IDLES) | set(LIFE) | {"standing_greeting", "idle", "headshake", "beckoning", "angry", "acknowledging", "walk", "female_walk"}
    bad = ("sit", "lay", "crouch", "run", "jog", "dance", "pistol", "sword", "swim", "crawl", "roll", "kneel", "plank", "pray", "squat", "jump", "punch", "hit_", "walk")
    for name, m in idx.items():
        if name in skip or any(b in name for b in bad):
            continue
        if not m.get("loops") or (m.get("seam") or 0) > 1:
            continue
        if (m.get("tier") or "") not in ("calm", "moderate"):
            continue
        if (m.get("energy") or 99) > 32 or (m.get("dur") or 0) > 6 or (m.get("dur") or 0) < 1.2:
            continue
        LIFE.append(name)
        LIFE_W.append(1)
extra_life()
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
def pick_chain(cur):
    if cur != HOME:
        state["last_prop"] = cur
        return HOME
    alts = [c for c in IDLES if c != HOME and c != state.get("last_prop")]
    if not alts:
        alts = [c for c in IDLES if c != HOME]
    return weighted(alts, [IDLE_W.get(c, 1) for c in alts]) if alts else HOME
async def get_alive(req):
    return cors(web.json_response({"home": HOME, "idles": IDLES, "life": LIFE, "life_soft": LIFE_SOFT, "life_head": LIFE_HEAD, "idle_w": IDLE_W}))
async def alive_loop(app):
    nxt = random.uniform(22, 42)
    since = 0.0
    while True:
        nap = random.uniform(12, 28)
        await asyncio.sleep(nap)
        if not clients:
            since = 0.0
            continue
        since += nap
        busy = time.time() < state.get("gesture_until", 0)
        if since < nxt:
            if not busy:
                g = random.choices(["user", "user", "user", "left", "right", "down", "up", "away"], k=1)[0]
                await bcast({"type": "gaze", "target": g, "seq": state["seq"]})
            continue
        since = 0.0
        if busy:
            nxt = min(nxt, max(2.0, state.get("gesture_until", 0) - time.time() + 0.4))
            continue
        if state.get("follow_base"):
            if pending or time.time() < state.get("gesture_until", 0):
                wait = 0.8 if pending else max(1.2, state.get("gesture_until", 0) - time.time() + 0.4)
                nxt = min(nxt, wait)
                continue
            if time.time() >= state.get("follow_at", 0):
                nb = state.pop("follow_base", None)
                state.pop("follow_at", None)
                if nb:
                    await fire(nb, "base", 1.1, "idle chain")
                nxt = random.uniform(14, 26)
                continue
        if state.get("base") not in IDLES:
            if time.time() - state.get("base_at", 0) > 8:
                await fire(HOME, "base", 1.1, "idle recover")
                nxt = random.uniform(14, 26)
            else:
                nxt = random.uniform(6, 12)
            continue
        quiet = time.time() - state.get("gesture_at", 0)
        pool = LIFE_HEAD if state.get("base") == "guitar_playing" else (LIFE_SOFT if state.get("base") != HOME else LIFE)
        did = False
        if quiet > 8 and random.random() < 0.48:
            lasts = sorted(recent, key=recent.get, reverse=True)[:2]
            last_fam = FAM.get(state.get("gesture") or "")
            def ok(c, fam=True, rec=True):
                if c == state.get("gesture") or (rec and c in lasts) or (rec and time.time() - recent.get(c, 0) <= REPEAT_WINDOW):
                    return False
                return not (fam and last_fam and FAM.get(c) == last_fam)
            fresh = [c for c in pool if ok(c)]
            if not fresh:
                fresh = [c for c in pool if ok(c, rec=False)]
            if not fresh:
                fresh = [c for c in pool if ok(c, fam=False, rec=False)]
            w = [LIFE_W[LIFE.index(c)] if c in LIFE else 1 for c in fresh]
            if fresh:
                clip = weighted(fresh, w)
                await fire(clip, "gesture", 0.55, "life beat")
                if not str(clip).startswith("look"):
                    await bcast({"type": "gaze", "target": "user", "seq": state["seq"]})
                did = True
                if random.random() < 0.35:
                    nxtb = pick_chain(state.get("base"))
                    dwell0 = time.time() - state.get("base_at", 0)
                    need0 = IDLE_DWELL.get(state.get("base"), 20)
                    if nxtb == HOME or dwell0 >= need0:
                        state["follow_base"] = nxtb
                        state["follow_at"] = state.get("gesture_until", time.time())
        if not did:
            cur = state.get("base")
            dwell = time.time() - state.get("base_at", 0)
            need = IDLE_DWELL.get(cur, 20)
            if dwell < need:
                nxt = random.uniform(8, 16)
                continue
            pick = pick_chain(cur)
            await fire(pick, "base", 1.1, "idle home" if pick == HOME else "idle chain")
            did = True
        nxt = random.uniform(14, 26) if did else random.uniform(22, 42)
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
app.router.add_get("/motion/alive", get_alive)
app.router.add_post("/motion/clip", save_clip)
app.router.add_get("/motion/clipdata/{name}", clip_data)
app.router.add_route("OPTIONS", "/motion/{tail:.*}", opt)
web.run_app(app, port=PORT)
