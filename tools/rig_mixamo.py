import bpy, traceback
from mathutils import Vector

RIKKU = r"C:\Users\antho\.grok\plugins\grok-remote\web\model_src.glb"
XBOT = r"C:\Users\antho\.grok\plugins\grok-remote\web\Xbot.glb"
OUT = r"C:\Users\antho\.grok\plugins\grok-remote\web\model_mixamo.glb"
LOG = r"C:\Users\antho\.grok\plugins\grok-remote\web\rig2_log.txt"

def log(m):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(str(m) + "\n")

def world_bounds(objs):
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi

try:
    open(LOG, "w").close()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bpy.ops.import_scene.gltf(filepath=XBOT)
    xbot_arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    xbot_meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    actions_before = set(bpy.data.actions)
    log(f"xbot armature {xbot_arm.name} bones {len(xbot_arm.data.bones)} meshes {len(xbot_meshes)} actions {[a.name for a in bpy.data.actions]}")
    xlo, xhi = world_bounds(xbot_meshes)
    xh = xhi.z - xlo.z
    for o in xbot_meshes:
        bpy.data.objects.remove(o, do_unlink=True)

    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=RIKKU)
    rikku_meshes = [o for o in bpy.data.objects if o.type == "MESH" and o not in pre]
    rlo, rhi = world_bounds(rikku_meshes)
    rh = rhi.z - rlo.z
    s = xh / rh
    log(f"xbot h {xh:.3f} rikku h {rh:.3f} scale {s:.3f}")
    # scale + ground + center in WORLD space on top of the import's axis-fix rotation -
    # resetting matrix_world lays her down (the glTF importer's Y-up correction lives there)
    from mathutils import Matrix
    S = Matrix.Scale(s, 4)
    for o in rikku_meshes:
        o.matrix_world = S @ o.matrix_world
    bpy.context.view_layer.update()
    mlo, mhi = world_bounds(rikku_meshes)
    T = Matrix.Translation(Vector((-(mlo.x + mhi.x) / 2, -(mlo.y + mhi.y) / 2, -mlo.z)))
    for o in rikku_meshes:
        o.matrix_world = T @ o.matrix_world
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for o in rikku_meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rikku_meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    nlo, nhi = world_bounds(rikku_meshes)
    log(f"rikku placed lo {tuple(round(v,3) for v in nlo)} hi {tuple(round(v,3) for v in nhi)}")

    ok, env = 0, 0
    for o in rikku_meshes:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True); xbot_arm.select_set(True)
        bpy.context.view_layer.objects.active = xbot_arm
        try:
            bpy.ops.object.parent_set(type="ARMATURE_AUTO"); ok += 1
        except Exception as e:
            log(f"auto fail {o.name}: {e}")
            try:
                bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE"); env += 1
            except Exception as e2:
                log(f"env fail {o.name}: {e2}")
    log(f"weights auto {ok} envelope {env}")

    # make sure every clip survives export: stash each action on an NLA track
    xbot_arm.animation_data_create()
    for a in bpy.data.actions:
        tr = xbot_arm.animation_data.nla_tracks.new()
        tr.name = a.name
        st = tr.strips.new(a.name, int(a.frame_range[0]) if a.frame_range[0] > 0 else 1, a)
        st.name = a.name
    log("nla stashed " + str(len(xbot_arm.animation_data.nla_tracks)))

    bpy.ops.export_scene.gltf(filepath=OUT, export_yup=True, export_animations=True, export_skins=True)
    log("EXPORT OK")
except Exception:
    log("FATAL\n" + traceback.format_exc())
