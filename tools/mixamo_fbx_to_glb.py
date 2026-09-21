import bpy, traceback
from math import radians
from mathutils import Vector
IN = r"C:\Users\antho\Downloads\rikku.fbx"
OUT = r"C:\Users\antho\Documents\ai\grok-remote\web\rikku_mixamo.glb"
OUT2 = r"C:\Users\antho\.grok\plugins\grok-remote\web\rikku_mixamo.glb"
LOG = r"C:\Users\antho\Documents\ai\grok-remote\web\rikku_mixamo_log.txt"
REND = r"C:\Users\antho\Documents\ai\grok-remote\web\rikku_mixamo_"
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
    bpy.ops.import_scene.fbx(filepath=IN, automatic_bone_orientation=False, ignore_leaf_bones=False)
    objs = list(bpy.data.objects)
    log("objects: " + ", ".join(o.name + ":" + o.type for o in objs))
    arms = [o for o in objs if o.type == "ARMATURE"]
    meshes = [o for o in objs if o.type == "MESH"]
    log("actions: " + ", ".join(a.name for a in bpy.data.actions))
    for a in arms:
        log("armature " + a.name + " bones " + str(len(a.data.bones)))
        for b in list(a.data.bones)[:8]:
            log("  bone " + b.name)
    lo, hi = world_bounds(meshes or arms)
    log("raw bounds lo " + str(tuple(round(v, 4) for v in lo)) + " hi " + str(tuple(round(v, 4) for v in hi)))
    h = max(1e-6, hi.z - lo.z)
    s = 1.7 / h
    log("height_z " + str(round(h, 5)) + " scale " + str(round(s, 4)))
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    root = arms[0] if arms else meshes[0]
    bpy.context.view_layer.objects.active = root
    bpy.ops.transform.resize(value=(s, s, s))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.update()
    lo, hi = world_bounds(meshes or arms)
    log("scaled lo " + str(tuple(round(v, 3) for v in lo)) + " hi " + str(tuple(round(v, 3) for v in hi)))
    h = hi.z - lo.z
    arm = arms[0] if arms else None
    scene = bpy.context.scene
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    mid = (lo + hi) * 0.5
    cam.location = (mid.x, lo.y - max(h * 1.6, 2.2), mid.z)
    cam.rotation_euler = (radians(90), 0, 0)
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 900
    def snap(name):
        scene.render.filepath = REND + name + ".png"
        bpy.ops.render.render(write_still=True)
        log("render " + name)
    snap("rest")
    if arm:
        pb = arm.pose.bones.get("mixamorig:LeftArm") or next((b for b in arm.pose.bones if "LeftArm" in b.name), None)
        if pb:
            pb.rotation_mode = "XYZ"
            pb.rotation_euler = (0, 0, radians(-70))
            bpy.context.view_layer.update()
            snap("armtest")
            pb.rotation_euler = (0, 0, 0)
            bpy.context.view_layer.update()
        if arm.animation_data is None:
            arm.animation_data_create()
        for a in bpy.data.actions:
            tr = arm.animation_data.nla_tracks.new()
            tr.name = a.name
            tr.strips.new(a.name, max(1, int(a.frame_range[0])), a)
    bpy.ops.export_scene.gltf(filepath=OUT, export_yup=True, export_animations=True, export_skins=True, export_apply=False)
    log("EXPORT " + OUT)
    try:
        bpy.ops.export_scene.gltf(filepath=OUT2, export_yup=True, export_animations=True, export_skins=True, export_apply=False)
        log("EXPORT " + OUT2)
    except Exception as e:
        log("plugin copy export skip " + str(e))
    log("OK")
except Exception:
    log("FATAL\n" + traceback.format_exc())
