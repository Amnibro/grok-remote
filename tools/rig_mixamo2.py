import bpy, traceback
from math import radians
from mathutils import Vector, Matrix

RIKKU = r"C:\Users\antho\.grok\plugins\grok-remote\web\model_src.glb"
XBOT = r"C:\Users\antho\.grok\plugins\grok-remote\web\Xbot.glb"
OUT = r"C:\Users\antho\.grok\plugins\grok-remote\web\model_mixamo2.glb"
LOG = r"C:\Users\antho\.grok\plugins\grok-remote\web\rig3_log.txt"
REND = r"C:\Users\antho\.grok\plugins\grok-remote\web\rig3_render_"

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
    for o in [o for o in bpy.data.objects if o.type == "MESH"]:
        bpy.data.objects.remove(o, do_unlink=True)
    # do NOT bake the armature object transform - the clips' hip root keys are authored in
    # its original frame and baking pitches every animation backward. The mesh-side bake
    # below is what actually fixes the lying-down bind.
    # rest-pose sanity: where do the arm bones sit?
    lb = xbot_arm.data.bones.get("mixamorig:LeftArm") or next((b for b in xbot_arm.data.bones if "LeftArm" in b.name), None)
    lh = xbot_arm.data.bones.get("mixamorig:LeftHand") or next((b for b in xbot_arm.data.bones if "LeftHand" in b.name), None)
    if lb: log(f"rest LeftArm head {tuple(round(v,2) for v in (xbot_arm.matrix_world @ lb.head_local))}")
    if lh: log(f"rest LeftHand head {tuple(round(v,2) for v in (xbot_arm.matrix_world @ lh.head_local))}")
    # armature object bound_box is garbage - measure the SKELETON from bone joints
    # transform_apply inflates imported bone TAILS (z up to 45) while heads stay true -
    # measure from heads only, and leave use_deform alone (heat binds fine regardless)
    zs = [(xbot_arm.matrix_world @ b.head_local).z for b in xbot_arm.data.bones]
    zs = [v for v in zs if -0.5 < v < 3.0]
    azmin, azmax = min(zs), max(zs)
    ah = azmax - min(0.0, azmin)
    log(f"skeleton z {azmin:.2f}..{azmax:.2f} height {ah:.3f}")

    pre = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=RIKKU)
    rikku_meshes = [o for o in bpy.data.objects if o.type == "MESH" and o not in pre]
    # ONE mesh: bone heat on 14 loose shells binds islands to wrong bones; joined it solves globally
    bpy.ops.object.select_all(action="DESELECT")
    for o in rikku_meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rikku_meshes[0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = "RikkuBody"
    rlo, rhi = world_bounds([body])
    rh = rhi.z - rlo.z
    s = ah / rh
    log(f"armature h {ah:.3f} rikku h {rh:.3f} scale {s:.3f}")
    S = Matrix.Scale(s, 4)
    body.matrix_world = S @ body.matrix_world
    bpy.context.view_layer.update()
    mlo, mhi = world_bounds([body])
    T = Matrix.Translation(Vector((-(mlo.x + mhi.x) / 2, -(mlo.y + mhi.y) / 2, -mlo.z)))
    body.matrix_world = T @ body.matrix_world
    bpy.context.view_layer.update()
    flo, fhi = world_bounds([body])
    log(f"placed lo {tuple(round(v,2) for v in flo)} hi {tuple(round(v,2) for v in fhi)}")

    # bake HER transform flat too - reparenting away from the Sketchfab empty chain drops
    # its axis-fix rotation and lays her down
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # FULL-DENSITY weighting: heat needs the cleanup (dedup+normals) but the cleanup eats
    # half her verts - so heat-weight a cleaned DUPLICATE, then transfer weights back to
    # the untouched full mesh by nearest vertex
    bpy.ops.object.duplicate()
    proxy = bpy.context.view_layer.objects.active
    proxy.name = "WeightProxy"
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    log(f"proxy verts {len(proxy.data.vertices)} full verts {len(body.data.vertices)}")
    bpy.ops.object.select_all(action="DESELECT")
    proxy.select_set(True); xbot_arm.select_set(True)
    bpy.context.view_layer.objects.active = xbot_arm
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    npw = sum(1 for v in proxy.data.vertices if v.groups)
    log(f"proxy weighted {npw}/{len(proxy.data.vertices)}")
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    dt = body.modifiers.new("wxfer", "DATA_TRANSFER")
    dt.object = proxy
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.datalayout_transfer(modifier="wxfer")
    bpy.ops.object.modifier_apply(modifier="wxfer")
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True); xbot_arm.select_set(True)
    bpy.context.view_layer.objects.active = xbot_arm
    bpy.ops.object.parent_set(type="ARMATURE")
    nw = sum(1 for v in body.data.vertices if v.groups)
    log(f"bound vgroups {len(body.vertex_groups)} modifiers {[m.type for m in body.modifiers]} weighted {nw}/{len(body.data.vertices)}")
    if nw < len(body.data.vertices):
        # transfer gaps get the FULL smooth weight dict of the nearest proxy vert - one-hot
        # nearest-bone snapping shreds the surface into rigid chunks
        import mathutils
        kd = mathutils.kdtree.KDTree(len(proxy.data.vertices))
        for v in proxy.data.vertices:
            kd.insert(proxy.matrix_world @ v.co, v.index)
        kd.balance()
        pgnames = {g.index: g.name for g in proxy.vertex_groups}
        bgroups = {g.name: g for g in body.vertex_groups}
        mw = body.matrix_world
        fixed = 0
        for v in body.data.vertices:
            if v.groups:
                continue
            _, idx, _ = kd.find(mw @ v.co)
            for g in proxy.data.vertices[idx].groups:
                nm = pgnames[g.group]
                if nm not in bgroups:
                    bgroups[nm] = body.vertex_groups.new(name=nm)
                bgroups[nm].add([v.index], g.weight, "REPLACE")
            fixed += 1
        log(f"orphans kd-copied {fixed}")
    bpy.data.objects.remove(proxy, do_unlink=True)
    if nw < len(body.data.vertices) * 0.5:
        # heat failed silently (background warnings vanish) - weight by capsule distance to
        # the deform bone segments, top-2 blend. Deterministic and plenty for a hologram.
        log("heat sparse - manual capsule weighting")
        import mathutils
        segs = []
        for b in xbot_arm.data.bones:
            if not b.use_deform:
                continue
            h = xbot_arm.matrix_world @ b.head_local
            t = xbot_arm.matrix_world @ b.tail_local
            r = max(0.03, (t - h).length * 0.45)
            segs.append((b.name, h, t, r))
        for g in list(body.vertex_groups):
            body.vertex_groups.remove(g)
        groups = {}
        for name, h, t, r in segs:
            groups[name] = body.vertex_groups.new(name=name)
        mw = body.matrix_world
        for v in body.data.vertices:
            p = mw @ v.co
            best = []
            for name, h, t, r in segs:
                ab = t - h
                l2 = ab.length_squared or 1.0
                tt = max(0.0, min(1.0, (p - h).dot(ab) / l2))
                d = (p - (h + ab * tt)).length
                w = (r / (d + r * 0.35)) ** 3
                best.append((w, name))
            best.sort(reverse=True)
            top = best[:2]
            s = sum(w for w, _ in top) or 1.0
            for w, name in top:
                groups[name].add([v.index], w / s, "REPLACE")
        nw2 = sum(1 for v in body.data.vertices if v.groups)
        log(f"manual weights done {nw2}/{len(body.data.vertices)}")
    # bleed sweep: a vert whose STRONGEST bone sits far from it (heat leaked across space,
    # e.g. ribbon points grabbing forearm weights) rebinds to its nearest bone segment
    segs2 = {}
    for b in xbot_arm.data.bones:
        if b.use_deform:
            segs2[b.name] = (xbot_arm.matrix_world @ b.head_local, xbot_arm.matrix_world @ b.tail_local)
    def segd(p, h, t):
        ab = t - h
        l2 = ab.length_squared or 1.0
        tt = max(0.0, min(1.0, (p - h).dot(ab) / l2))
        return (p - (h + ab * tt)).length
    gname = {g.index: g.name for g in body.vertex_groups}
    mw2 = body.matrix_world
    rebound = 0
    for v in body.data.vertices:
        if not v.groups:
            continue
        top = max(v.groups, key=lambda g: g.weight)
        nm = gname.get(top.group)
        if nm not in segs2:
            continue
        p = mw2 @ v.co
        h, t = segs2[nm]
        lim = max(0.12, (t - h).length * 0.9)
        if segd(p, h, t) <= lim:
            continue
        best = min(((segd(p, sh, st), n) for n, (sh, st) in segs2.items()), key=lambda x: x[0])
        if best[1] != nm:
            for gi in [g.group for g in v.groups]:
                body.vertex_groups[gi].remove([v.index])
            body.vertex_groups[best[1]].add([v.index], 1.0, "REPLACE")
            rebound += 1
    log(f"bleed rebound {rebound}")
    log("scene objects: " + ", ".join(o.name + ":" + o.type for o in bpy.data.objects))
    blo, bhi = world_bounds([body])
    log(f"body world lo {tuple(round(v,2) for v in blo)} hi {tuple(round(v,2) for v in bhi)}")
    for m in bpy.data.materials:
        try:
            m.blend_method = "OPAQUE"
        except Exception:
            pass

    # proof renders: rest + idle frame 30, BEFORE any export
    scene = bpy.context.scene
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    cam.location = (0, -3.1, ah * 0.52)
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
    # unambiguous deformation test: crank the left arm down 70 degrees and look
    pb = xbot_arm.pose.bones.get("mixamorig:LeftArm")
    if pb:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, radians(-70))
    bpy.context.view_layer.update()
    snap("armtest")
    if pb:
        pb.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()

    # stash all clips, export
    for a in bpy.data.actions:
        tr = xbot_arm.animation_data.nla_tracks.new()
        tr.name = a.name
        tr.strips.new(a.name, max(1, int(a.frame_range[0])), a)
    bpy.ops.export_scene.gltf(filepath=OUT, export_yup=True, export_animations=True, export_skins=True)
    log("EXPORT OK")
except Exception:
    log("FATAL\n" + traceback.format_exc())
