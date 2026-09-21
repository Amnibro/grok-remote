import bpy, sys, traceback
from math import radians, sin, pi
from mathutils import Matrix, Vector

IN = r"C:\Users\antho\.grok\plugins\grok-remote\web\model_src.glb"
OUT = r"C:\Users\antho\.grok\plugins\grok-remote\web\model_rigged.glb"
LOG = r"C:\Users\antho\.grok\plugins\grok-remote\web\rig_log.txt"

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(str(msg) + "\n")

try:
    open(LOG, "w").close()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=IN)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    log(f"meshes {len(meshes)}")
    lo = Vector((1e9, 1e9, 1e9)); hi = Vector((-1e9, -1e9, -1e9))
    for o in meshes:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    H = hi.z - lo.z
    cx = (lo.x + hi.x) / 2
    # gltf importer maps glTF +Y up to Blender +Z up; model-forward stays on Blender Y.
    # body plane sits forward of origin (measured z~0.14 of 0.5 in glTF = Blender -Y).
    cy = (lo.y + hi.y) / 2
    log(f"H {H:.3f} cx {cx:.3f} cy {cy:.3f} lo {tuple(round(v,3) for v in lo)} hi {tuple(round(v,3) for v in hi)}")
    z0 = lo.z
    def J(x, zf):  # joint helper: lateral x, height fraction -> Blender coords
        return Vector((cx + x * H, cy, z0 + zf * H))
    hips = J(0, 0.54); spine = J(0, 0.64); chest = J(0, 0.74); neck = J(0, 0.83); headtip = J(0, 1.00)
    shL = J(-0.11, 0.80); elL = J(-0.23, 0.68); haL = J(-0.31, 0.57); haLt = J(-0.34, 0.53)
    shR = J(0.11, 0.80); elR = J(0.23, 0.68); haR = J(0.31, 0.57); haRt = J(0.34, 0.53)
    legL = J(-0.09, 0.52); knL = J(-0.10, 0.29); ftL = J(-0.10, 0.02)
    legR = J(0.09, 0.52); knR = J(0.10, 0.29); ftR = J(0.10, 0.02)

    bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
    arm = bpy.context.object
    arm.name = "CompanionRig"
    eb = arm.data.edit_bones
    root = eb[0]; root.name = "Hips"; root.head = hips; root.tail = spine
    def add(name, parent, head, tail, connect=True):
        b = eb.new(name); b.head = head; b.tail = tail; b.parent = parent; b.use_connect = connect
        return b
    sp = add("Spine", root, spine, chest)
    ch = add("Spine2", sp, chest, neck)
    nk = add("Neck", ch, neck, J(0, 0.90))
    add("Head", nk, J(0, 0.90), headtip)
    ual = add("LeftArm", ch, shL, elL, False)
    fal = add("LeftForeArm", ual, elL, haL)
    add("LeftHand", fal, haL, haLt)
    uar = add("RightArm", ch, shR, elR, False)
    far = add("RightForeArm", uar, elR, haR)
    add("RightHand", far, haR, haRt)
    ull = add("LeftUpLeg", root, legL, knL, False)
    lll = add("LeftLeg", ull, knL, ftL)
    ulr = add("RightUpLeg", root, legR, knR, False)
    llr = add("RightLeg", ulr, knR, ftR)
    bpy.ops.object.mode_set(mode="OBJECT")
    log("armature built bones " + str(len(arm.data.bones)))

    ok, fail = 0, 0
    for o in meshes:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True); arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        try:
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")
            ok += 1
        except Exception as e:
            log(f"auto-weight fail {o.name}: {e}")
            try:
                bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")
                fail += 1
            except Exception as e2:
                log(f"envelope fail {o.name}: {e2}")
    log(f"weights auto {ok} envelope {fail}")

    # Idle action: arms already at the model's natural slope; add gentle life. 4s loop @24fps.
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    act = bpy.data.actions.new("Idle")
    arm.animation_data_create()
    arm.animation_data.action = act
    try:
        if hasattr(act, "slots"):
            slot = act.slots.new(id_type='OBJECT', name="Idle")
            arm.animation_data.action_slot = slot
    except Exception as e:
        log(f"slot note: {e}")
    pb = arm.pose.bones
    def key(bone, frame, eul):
        b = pb[bone]
        b.rotation_mode = "XYZ"
        b.rotation_euler = eul
        b.keyframe_insert("rotation_euler", frame=frame)
    F = 96
    for f in range(0, F + 1, 12):
        t = f / F * 2 * pi
        sway = sin(t); breathe = sin(2 * t); drift = sin(t + 1.3)
        key("Spine", f, (radians(1.2 * breathe), radians(1.5 * sway), 0))
        key("Spine2", f, (radians(1.5 * breathe), radians(1.2 * sway), radians(0.8 * drift)))
        key("Neck", f, (radians(1.5 * drift), radians(-1.2 * sway), 0))
        key("Head", f, (radians(1.2 * sin(t + 2.1)), radians(2.0 * sway), radians(0.8 * breathe)))
        key("LeftArm", f, (radians(2.0 * drift), 0, radians(3.0 + 1.5 * sway)))
        key("RightArm", f, (radians(2.0 * sin(t + 0.9)), 0, radians(-3.0 - 1.5 * sway)))
        key("LeftForeArm", f, (radians(2.5 + 1.5 * breathe), 0, 0))
        key("RightForeArm", f, (radians(2.5 + 1.5 * sin(2 * t + 1.1)), 0, 0))
        key("Hips", f, (0, radians(1.0 * sway), radians(0.6 * drift)))
    bpy.ops.object.mode_set(mode="OBJECT")
    log("idle action keyed")

    bpy.ops.export_scene.gltf(filepath=OUT, export_yup=True, export_animations=True, export_skins=True)
    log("EXPORT OK")
except Exception:
    log("FATAL\n" + traceback.format_exc())
