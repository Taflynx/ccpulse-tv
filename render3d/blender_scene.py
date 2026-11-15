"""Photoreal Cycles renders of a SmallTV-style mini display showing the real ccpulse-tv screens.

  blender -b --factory-startup --python render3d/blender_scene.py -- --shot hero --out docs/renders/hero.jpg
  shots: hero | desk | close | trio      options: --samples 160 --w 1600 --h 1000

Everything is built procedurally (no downloaded assets). Units are metres.
"""
import math, os, sys
import bpy, bmesh
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
opt = {"shot": "hero", "out": "", "samples": "160", "w": "1600", "h": "1000"}
for i in range(0, len(args) - 1, 2):
    opt[args[i].lstrip("-")] = args[i + 1]
SHOT = opt["shot"]
OUT = opt["out"] or os.path.join(ROOT, "docs", "renders", SHOT + ".jpg")
SCREENS = os.path.join(ROOT, "docs", "screens")

# ---------------------------------------------------------------- scene setup
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = int(opt["samples"])
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPENIMAGEDENOISE"
scene.cycles.max_bounces = 8
scene.render.resolution_x, scene.render.resolution_y = int(opt["w"]), int(opt["h"])
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 90
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.render.film_transparent = False
scene.view_settings.exposure = float(opt.get("exp", 0))

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.02, 0.022, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0


def link(nt, a, b):
    nt.links.new(a, b)


def mat_principled(name, color, rough=0.5, metal=0.0, coat=0.0, coat_rough=0.1, bump=0.0, bump_scale=900.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = coat
    p.inputs["Coat Roughness"].default_value = coat_rough
    if bump:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = bump_scale
        nz.inputs["Detail"].default_value = 4
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = bump
        bp.inputs["Distance"].default_value = 0.00005
        link(nt, tc.outputs["Object"], nz.inputs["Vector"])
        link(nt, nz.outputs["Fac"], bp.inputs["Height"])
        link(nt, bp.outputs["Normal"], p.inputs["Normal"])
    return m


def screen_material(img_path, strength=1.75):
    """LCD: emissive image (nearest filtering), faint pixel grid, glass reflections on top."""
    m = bpy.data.materials.new("Screen_" + os.path.basename(img_path))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    uv = nt.nodes.new("ShaderNodeTexCoord")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(img_path)
    tex.interpolation = "Closest"
    link(nt, uv.outputs["UV"], tex.inputs["Vector"])
    # pixel grid mask from UV * 240
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    link(nt, uv.outputs["UV"], sep.inputs[0])

    def grid(axis_out):
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 240
        fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1
        mn = nt.nodes.new("ShaderNodeMath"); mn.operation = "MINIMUM"
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.interpolation_type = "SMOOTHSTEP"
        mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 0.12
        mr.inputs["To Min"].default_value = 0.55; mr.inputs["To Max"].default_value = 1.0
        link(nt, axis_out, mul.inputs[0]); link(nt, mul.outputs[0], fr.inputs[0])
        link(nt, fr.outputs[0], inv.inputs[1]); link(nt, fr.outputs[0], mn.inputs[0]); link(nt, inv.outputs[0], mn.inputs[1])
        link(nt, mn.outputs[0], mr.inputs["Value"])
        return mr.outputs["Result"]
    gx, gy = grid(sep.outputs["X"]), grid(sep.outputs["Y"])
    gm = nt.nodes.new("ShaderNodeMath"); gm.operation = "MULTIPLY"
    link(nt, gx, gm.inputs[0]); link(nt, gy, gm.inputs[1])
    col = nt.nodes.new("ShaderNodeMix"); col.data_type = "RGBA"; col.blend_type = "MULTIPLY"
    col.inputs["Factor"].default_value = 1.0
    link(nt, tex.outputs["Color"], col.inputs[6]); link(nt, gm.outputs[0], col.inputs[7])
    # LCD black level: never fully black
    lift = nt.nodes.new("ShaderNodeMix"); lift.data_type = "RGBA"; lift.blend_type = "ADD"
    lift.inputs["Factor"].default_value = 1.0; lift.inputs[7].default_value = (0.004, 0.004, 0.005, 1)
    link(nt, col.outputs[2], lift.inputs[6])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    link(nt, lift.outputs[2], em.inputs["Color"])
    gl = nt.nodes.new("ShaderNodeBsdfGlossy"); gl.inputs["Roughness"].default_value = 0.03
    fr = nt.nodes.new("ShaderNodeFresnel"); fr.inputs["IOR"].default_value = 1.5
    mix = nt.nodes.new("ShaderNodeMixShader")
    link(nt, fr.outputs[0], mix.inputs[0]); link(nt, em.outputs[0], mix.inputs[1]); link(nt, gl.outputs[0], mix.inputs[2])
    link(nt, mix.outputs[0], out.inputs["Surface"])
    return m


def emission(name, color, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1); e.inputs["Strength"].default_value = strength
    link(nt, e.outputs[0], o.inputs[0]); return m


def add_box(name, size, loc, bevel=0.0, segs=6, mat=None, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    if bevel:
        b = o.modifiers.new("Bevel", "BEVEL"); b.width = bevel; b.segments = segs; b.limit_method = "NONE"
        b.harden_normals = False
    bpy.ops.object.shade_smooth()
    if mat: o.data.materials.append(mat)
    if parent: o.parent = parent
    return o


# ---------------------------------------------------------------- the device
W, H, D = 0.046, 0.038, 0.042  # width, depth, height (m)


def make_device(screen_png, shell="graphite", loc=(0, 0, 0), rot_z=0.0):
    root = bpy.data.objects.new("Device", None); bpy.context.collection.objects.link(root)
    root.location = loc; root.rotation_euler = (0, 0, rot_z)
    shell_col = (0.78, 0.76, 0.72) if shell == "white" else (0.028, 0.028, 0.032)
    shell_m = mat_principled("Shell_" + shell, shell_col, rough=0.42 if shell == "white" else 0.48,
                             coat=0.15, coat_rough=0.35, bump=0.08)
    z0 = 0.0016  # feet height
    add_box("Body", (W, H, D), (0, 0, z0 + D / 2), bevel=0.0045, segs=8, mat=shell_m, parent=root)
    # recessed front frame + glass face (front is -Y)
    face_m = mat_principled("FaceGlass", (0.004, 0.004, 0.005), rough=0.06, coat=1.0, coat_rough=0.02)
    add_box("Face", (W - 0.0062, 0.0012, D - 0.0062), (0, -H / 2 - 0.0002, z0 + D / 2), bevel=0.0012, segs=4,
            mat=face_m, parent=root)
    # screen 27.8 mm square, a hair in front of the face, slightly above centre
    bpy.ops.mesh.primitive_plane_add(size=0.0278, location=(0, -H / 2 - 0.00085, z0 + D / 2 + 0.0012),
                                     rotation=(math.pi / 2, 0, 0))
    scr = bpy.context.active_object; scr.name = "Screen"; scr.parent = root
    scr.data.materials.append(screen_material(os.path.join(SCREENS, screen_png)))
    # status LED
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.00045, location=(0, -H / 2 - 0.0008, z0 + D / 2 - 0.0165))
    led = bpy.context.active_object; led.parent = root
    led.data.materials.append(emission("LED", (1.0, 0.32, 0.12), 2.5))
    # rubber feet
    rubber = mat_principled("Rubber", (0.015, 0.015, 0.016), rough=0.9)
    for x in (-0.015, 0.015):
        for y in (-0.012, 0.012):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.0028, depth=z0 + 0.0004, location=(x, y, (z0 + 0.0004) / 2), vertices=32)
            f = bpy.context.active_object; f.parent = root; f.data.materials.append(rubber); bpy.ops.object.shade_smooth()
    # USB-C on the back
    port_m = mat_principled("Port", (0.01, 0.01, 0.012), rough=0.4, metal=0.8)
    add_box("USB", (0.009, 0.001, 0.0032), (0, H / 2 + 0.0002, z0 + 0.008), bevel=0.0014, segs=4, mat=port_m, parent=root)
    root["screen"] = scr.name
    return root


# ---------------------------------------------------------------- environments
def area(name, loc, target, size, power, color=(1, 1, 1), shape="RECTANGLE", size_y=None):
    l = bpy.data.lights.new(name, "AREA"); l.energy = power; l.color = color; l.shape = shape
    l.size = size; l.size_y = size_y or size
    o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc
    d = Vector(target) - Vector(loc); o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return o


def sweep(color=(0.5, 0.48, 0.45)):
    """Seamless photo backdrop: floor curving up into a wall behind the product."""
    bm = bmesh.new()
    prof = []
    for i in range(41):
        t = i / 40
        if t < 0.5:
            y, z = -0.6 + t / 0.5 * 0.7, 0.0
        else:
            a = (t - 0.5) / 0.5 * math.pi / 2
            y, z = 0.1 + math.sin(a) * 0.25, (1 - math.cos(a)) * 0.25
        prof.append((y, z))
    prof.append((0.35, 0.8))
    verts = []
    for x in (-1.0, 1.0):
        verts.append([bm.verts.new((x, y, z)) for y, z in prof])
    for i in range(len(prof) - 1):
        bm.faces.new((verts[0][i], verts[1][i], verts[1][i + 1], verts[0][i + 1]))
    me = bpy.data.meshes.new("Sweep"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("Sweep", me); bpy.context.collection.objects.link(o)
    for p in me.polygons: p.use_smooth = True
    o.data.materials.append(mat_principled("Paper", color, rough=0.92))
    return o


def wood_material():
    m = bpy.data.materials.new("Oak"); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 22.0, 1.0)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 6; nz.inputs["Detail"].default_value = 8
    nz.inputs["Distortion"].default_value = 1.2
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.inputs["Scale"].default_value = 3.5
    wv.inputs["Distortion"].default_value = 9; wv.inputs["Detail"].default_value = 6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.16, 0.075, 0.03, 1)
    ramp.color_ramp.elements[1].color = (0.42, 0.22, 0.10, 1)
    link(nt, tc.outputs["Object"], mp.inputs["Vector"]); link(nt, mp.outputs[0], wv.inputs["Vector"])
    link(nt, mp.outputs[0], nz.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY_ADD"; mx.inputs[1].default_value = 0.6; mx.inputs[2].default_value = 0.2
    link(nt, wv.outputs["Fac"], mx.inputs[0])
    ad = nt.nodes.new("ShaderNodeMath"); ad.operation = "ADD"
    link(nt, mx.outputs[0], ad.inputs[0]); link(nt, nz.outputs["Fac"], ad.inputs[1])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.5; mr.inputs["From Max"].default_value = 1.4
    link(nt, ad.outputs[0], mr.inputs["Value"]); link(nt, mr.outputs[0], ramp.inputs["Fac"])
    link(nt, ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.45; p.inputs["Coat Weight"].default_value = 0.3; p.inputs["Coat Roughness"].default_value = 0.25
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.15
    link(nt, wv.outputs["Fac"], bp.inputs["Height"]); link(nt, bp.outputs["Normal"], p.inputs["Normal"])
    return m


def desk():
    add_box("Desk", (1.6, 0.8, 0.03), (0, 0.1, -0.015), mat=wood_material())
    wall = add_box("Wall", (3, 0.02, 1.5), (0, 0.55, 0.7), mat=mat_principled("Wall", (0.09, 0.085, 0.08), rough=0.95))
    # keyboard
    kb_m = mat_principled("KB", (0.025, 0.025, 0.028), rough=0.55)
    key_m = mat_principled("Keys", (0.05, 0.05, 0.056), rough=0.5)
    add_box("Keyboard", (0.30, 0.11, 0.012), (-0.25, 0.02, 0.006), bevel=0.004, segs=4, mat=kb_m)
    for i in range(15):
        for j in range(5):
            add_box("Key", (0.0165, 0.0165, 0.007), (-0.383 + i * 0.019, -0.022 + j * 0.019, 0.0145), bevel=0.0025, segs=3, mat=key_m)
    # mug
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.095, location=(0.19, 0.17, 0.0475), vertices=96)
    mug = bpy.context.active_object
    s = mug.modifiers.new("Sol", "SOLIDIFY"); s.thickness = 0.004
    bm = mug.modifiers.new("Bev", "BEVEL"); bm.width = 0.0015; bm.segments = 3
    bpy.ops.object.shade_smooth()
    # remove top cap so it's a cup
    me = mug.data
    for p in me.polygons:
        if p.normal.z > 0.9: p.select = True
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    bm2 = bmesh.new(); bm2.from_mesh(me)
    tops = [f for f in bm2.faces if f.normal.z > 0.9]
    bmesh.ops.delete(bm2, geom=tops, context="FACES"); bm2.to_mesh(me); bm2.free()
    mug.data.materials.append(mat_principled("Ceramic", (0.62, 0.20, 0.10), rough=0.25, coat=0.6, coat_rough=0.05))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0365, depth=0.001, location=(0.19, 0.17, 0.082), vertices=96)
    bpy.context.active_object.data.materials.append(mat_principled("Coffee", (0.03, 0.012, 0.005), rough=0.08))
    # window light from the left + practical warm fill
    area("Window", (-0.9, -0.3, 0.7), (0, 0.05, 0.02), 0.9, 28, (1.0, 0.97, 0.92), size_y=1.2)
    area("Fill", (0.5, -0.7, 0.35), (0, 0, 0.02), 0.5, 2.2, (1.0, 0.85, 0.7))
    area("Rim", (0.35, 0.45, 0.4), (0, 0, 0.02), 0.3, 3, (0.75, 0.85, 1.0))


def studio_lights(k=1.0):
    area("Key", (-0.45, -0.45, 0.45), (0, 0, 0.02), 0.6, 11 * k, (1.0, 0.96, 0.9))
    area("Rim", (0.45, 0.35, 0.3), (0, 0, 0.03), 0.35, 6 * k, (0.75, 0.85, 1.0))
    area("Top", (0.0, -0.05, 0.75), (0, 0, 0), 0.8, 4 * k, (1, 1, 1))
    area("Fill", (0.55, -0.5, 0.12), (0, 0, 0.02), 0.4, 1.6 * k, (1, 1, 1))


def camera(loc, target, lens=85, fstop=None, focus=None, focus_on=None):
    c = bpy.data.cameras.new("Cam"); c.lens = lens; c.sensor_width = 36
    o = bpy.data.objects.new("Cam", c); bpy.context.collection.objects.link(o)
    o.location = loc; d = Vector(target) - Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if fstop:
        c.dof.use_dof = True; c.dof.aperture_fstop = fstop
        c.dof.focus_distance = focus or d.length
        if focus_on is not None:
            c.dof.focus_object = bpy.data.objects[focus_on["screen"]]
    scene.camera = o
    return o


# ---------------------------------------------------------------- shots
if SHOT == "hero":
    sweep((0.42, 0.40, 0.37)); studio_lights()
    dv = make_device("usage.png", rot_z=math.radians(2))
    camera((0.20, -0.30, 0.11), (0.004, 0, 0.021), lens=85, fstop=8, focus_on=dv)
elif SHOT == "close":
    sweep((0.035, 0.034, 0.033)); studio_lights(0.7)
    dv = make_device("clawd_think.png", rot_z=math.radians(-6))
    camera((-0.15, -0.24, 0.085), (0.0, -0.005, 0.023), lens=100, fstop=4, focus_on=dv)
elif SHOT == "trio":
    sweep((0.05, 0.048, 0.046)); studio_lights(1.1)
    make_device("clock.png", "white", loc=(-0.058, 0.012, 0), rot_z=math.radians(16))
    dv = make_device("usage.png", "graphite", loc=(0, -0.006, 0))
    make_device("clawd_jump.png", "white", loc=(0.058, 0.012, 0), rot_z=math.radians(-16))
    camera((0.0, -0.42, 0.13), (0, 0, 0.022), lens=70, fstop=11, focus_on=dv)
elif SHOT == "desk":
    desk()
    dv = make_device("clock.png", rot_z=math.radians(6), loc=(0.0, 0.0, 0))
    camera((0.17, -0.27, 0.085), (0.0, 0.0, 0.024), lens=70, fstop=2.8, focus_on=dv)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("WROTE", OUT)
