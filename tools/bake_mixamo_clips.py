import bpy, json, os, re, traceback
from math import radians
from mathutils import Vector
WEB = r"C:\Users\antho\Documents\ai\grok-remote\web"
CLIP_DIR = r"C:\Users\antho\Documents\ai\grok-remote\clips"
OUT = os.path.join(WEB, "rikku_mixamo.glb")
OUT2 = r"C:\Users\antho\.grok\plugins\grok-remote\web\rikku_mixamo.glb"
LOG = os.path.join(WEB, "bake_clips_log.txt")
CHAR = os.path.join(WEB, "rikku.fbx")
os.makedirs(CLIP_DIR, exist_ok=True)
def log(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(str(m) + "\n")
def slug(name):
    n = re.sub(r"\s*\(\d+\)\s*", " ", name)
    n = re.sub(r"[^a-z0-9]+", "_", n.lower()).strip("_")
    return n or "clip"
def world_bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi
def scale_selected(s):
    bpy.ops.transform.resize(value=(s, s, s))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
def wipe(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
def sample_clip(arm, action, name, fps=30):
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = action
    fr0, fr1 = [int(round(v)) for v in action.frame_range]
    if fr1 < fr0:
        fr1 = fr0
    times = []
    qmap = {b.name: [] for b in arm.pose.bones}
    pmap = {}
    hips = next((b for b in arm.pose.bones if b.name.endswith("Hips") or b.name == "Hips"), None)
    if hips:
        pmap[hips.name] = []
    scene = bpy.context.scene
    scene.render.fps = fps
    for fr in range(fr0, fr1 + 1):
        scene.frame_set(fr)
        bpy.context.view_layer.update()
        times.append((fr - fr0) / float(fps))
        for b in arm.pose.bones:
            q = b.matrix_basis.to_quaternion()
            qmap[b.name].extend([q.x, q.y, q.z, q.w])
        if hips:
            p = hips.matrix_basis.to_translation()
            pmap[hips.name].extend([p.x, p.y, p.z])
    tracks = []
    for bn, vals in qmap.items():
        tracks.append({"name": bn + ".quaternion", "type": "quaternion", "times": times, "values": vals})
    for bn, vals in pmap.items():
        tracks.append({"name": bn + ".position", "type": "vector", "times": times, "values": vals})
    dur = times[-1] if times else 0
    path = os.path.join(CLIP_DIR, name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"name": name, "duration": dur, "tracks": tracks}, f, separators=(",", ":"))
    return dur, path
ALIASES = {
    "female_standing_pose": "idle",
    "female_walk": "walk",
    "jogging": "run",
    "standing_greeting": "wave_hello",
    "kneeling_pointing": "point_ahead",
    "female_laying_pose": "lay_down",
    "female_laying_pose_1": "lay_down",
    "jab_cross": "punch_jab",
    "acknowledging": "agree",
    "dancing_twerk": "dance_loop",
    "rumba_dancing": "dance_loop",
    "silly_dancing": "dance_loop",
    "defeated": "sad_pose",
}
try:
    open(LOG, "w").close()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=CHAR, automatic_bone_orientation=False, ignore_leaf_bones=False)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    lo, hi = world_bounds(meshes)
    h = max(1e-6, hi.z - lo.z)
    s = 1.7 / h
    log("char height " + str(round(h, 5)) + " scale " + str(round(s, 4)))
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = arms[0]
    scale_selected(s)
    char = arms[0]
    char.name = "RikkuArm"
    if char.animation_data is None:
        char.animation_data_create()
    seen = set()
    files = []
    for fn in sorted(os.listdir(WEB)):
        if not fn.lower().endswith(".fbx"):
            continue
        if fn.lower() == "rikku.fbx":
            continue
        files.append(fn)
    for fn in files:
        name = slug(os.path.splitext(fn)[0])
        if name in seen:
            log("skip dup " + fn)
            continue
        pre = set(bpy.data.objects)
        pre_act = set(bpy.data.actions)
        try:
            bpy.ops.import_scene.fbx(filepath=os.path.join(WEB, fn), automatic_bone_orientation=False, ignore_leaf_bones=False)
        except Exception as e:
            log("import fail " + fn + " " + str(e))
            continue
        new_objs = [o for o in bpy.data.objects if o not in pre]
        new_arms = [o for o in new_objs if o.type == "ARMATURE"]
        bpy.ops.object.select_all(action="DESELECT")
        for o in new_objs:
            o.select_set(True)
        if new_objs:
            bpy.context.view_layer.objects.active = new_objs[0]
            scale_selected(s)
        src = new_arms[0] if new_arms else None
        acts = []
        if src and src.animation_data and src.animation_data.action:
            acts.append(src.animation_data.action)
        for a in bpy.data.actions:
            if a not in pre_act:
                acts.append(a)
        uniq = []
        for a in acts:
            if a not in uniq:
                uniq.append(a)
        if not uniq:
            log("no action " + fn)
            wipe(new_objs)
            continue
        a = uniq[0]
        a.name = name
        seen.add(name)
        dur, path = sample_clip(char, a, name)
        alias = ALIASES.get(name)
        if alias and alias not in seen:
            dst = os.path.join(CLIP_DIR, alias + ".json")
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            d["name"] = alias
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(d, f, separators=(",", ":"))
            seen.add(alias)
            log("alias " + name + " -> " + alias)
        tr = char.animation_data.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, 1, a)
        wipe(new_objs)
        log("baked " + name + " dur " + str(round(dur, 3)) + " from " + fn)
    bpy.ops.object.select_all(action="DESELECT")
    char.select_set(True)
    bpy.context.view_layer.objects.active = char
    bpy.ops.export_scene.gltf(filepath=OUT, export_yup=True, export_animations=True, export_skins=True, export_nla_strips=True, export_apply=False)
    log("EXPORT " + OUT)
    try:
        bpy.ops.export_scene.gltf(filepath=OUT2, export_yup=True, export_animations=True, export_skins=True, export_nla_strips=True, export_apply=False)
        log("EXPORT " + OUT2)
    except Exception as e:
        log("plugin export skip " + str(e))
    log("clips " + str(sorted(seen)))
    log("OK")
except Exception:
    log("FATAL\n" + traceback.format_exc())
