import numpy as np
from vispy import app, gloo
from world import Tile_State
from goomba import Goomba

CANVAS = None 

def get_canvas(world=None):
    global CANVAS
    if not CANVAS:
        CANVAS = Canvas(world)
        return CANVAS
    
    if not world:
        return CANVAS
    
    CANVAS.set_world(world)
    return CANVAS

boundary_vertex_shader = """
attribute vec2 a_position;
uniform vec4 u_color;
uniform vec2 u_offset;
uniform float u_scale;
varying vec4 v_color;
void main()
{
    gl_Position = vec4((u_scale*a_position) + u_offset, 0.0, 1.0);
    v_color = u_color;
}"""

boundary_fragment_shader = """
varying vec4 v_color;
void main()
{
    gl_FragColor = v_color;
}"""


dirty_vertex_shader = """
attribute vec2 a_position;
attribute float a_pointsize;
uniform vec4 u_color;
uniform vec2 u_offset;
uniform float u_scale;
varying vec4 v_color;
void main()
{
    gl_Position = vec4((u_scale*a_position) + u_offset, 0.0, 1.0);
    gl_PointSize = a_pointsize;
    v_color = u_color;

}"""

goomba_vertex_shader = """
attribute vec2 a_position;
attribute vec4 a_color;
uniform vec2 u_offset;
uniform float u_scale;
varying vec4 v_color;
void main()
{
    gl_Position = vec4((u_scale*a_position) + u_offset, 0.0, 1.0);
    v_color = a_color;
}"""



class Canvas(app.Canvas):
    def __init__(self, world=None):
        self.b_int_col = (0.5, 0.1, 0.1, 1.0)
        self.b_out_col = (0.9, 0.3, 0.3, 1.0)
        self.dirt_col = (0.2, 0.8, 0.2, 1.0)
        self.dirt_size = 5.0
        self.goomba_col = (0.2, 0.7, 0.7, 1.0)


        self.boundary_verts = None
        self.boundary_interior = None
        self.dirty_verts = None
        self.dirty_indices = None
        self.goomba_verts = None
        self.goomba_colors = None
        self.set_world(world)

        app.Canvas.__init__(self, keys='interactive', size=(1200, 1200))

        self.boundary_program = gloo.Program(boundary_vertex_shader, boundary_fragment_shader)
        self.boundary_program["a_position"] = self.boundary_verts
        self.boundary_program["u_color"] = (1.0, 0.0, 1.0, 1.0)
        self.boundary_program["u_scale"] = 2.0/len(self.world.state)
        self.boundary_program["u_offset"] = (-1, -1)

        self.dirty_program = gloo.Program(dirty_vertex_shader, boundary_fragment_shader)
        self.dirty_program["a_position"] = self.dirty_verts
        self.dirty_program["a_pointsize"] = self.dirt_size #* (self.pixel_scale)
        self.dirty_program["u_color"] = self.dirt_col
        self.dirty_program["u_scale"] = 2.0/len(self.world.state)
        self.dirty_program["u_offset"] = (-1, -1)

        self.goomba_program = gloo.Program(goomba_vertex_shader, boundary_fragment_shader)
        self.goomba_program["a_position"] = self.goomba_verts
        self.goomba_program["a_color"] = self.goomba_colors
        self.goomba_program["u_scale"] = 2.0/len(self.world.state)
        self.goomba_program["u_offset"] = (-1, -1)

        self._timer = app.Timer('auto', connect=self.update, start=True)

    def on_resize(self, event):
        width, height = event.size
        gloo.set_viewport(0, 0, width, height)

    def on_draw(self, event):
        self.world.step()
        self.update_dirties()
        self.update_goombas()
        
        self.goomba_program["a_position"] = self.goomba_verts

        gloo.clear()
        self.boundary_program["u_color"] = self.b_int_col
        self.boundary_program.draw('triangles', self.boundary_interior)
        self.boundary_program["u_color"] = self.b_out_col
        self.boundary_program.draw('lines', self.boundary_outline)
        self.dirty_program.draw('points', self.dirty_indices)
        self.goomba_program.draw('triangles')

    def set_world(self, world):
        # Generate point set for boundaries, dirt, goombas
        self.world = world

        if not world:
            return

        boundaries = []
        boundary_verts = []
        boundary_interior = []
        boundary_outline = []
        
        dirty_verts = []
        dirty_offset = 0.5

        # obtain list of all boundaries and dirty cell points
        for y in range(len(world.state)):
            for x in range(len(world.state[y])):
                dirty_verts.append((x + dirty_offset, y + dirty_offset))
                if world.get_tile(x, y) == Tile_State.boundary:
                    boundaries.append((x, y))

        #generate vert list for corners of boundaries
        for x, y in boundaries:
            xy = 0
            x1y = 0
            xy1 = 0
            x1y1 = 0

            try:
                xy = boundary_verts.index((x, y))
            except ValueError:
                xy = len(boundary_verts)
                boundary_verts.append((x, y))

            try:
                x1y = boundary_verts.index((x + 1, y))
            except ValueError:
                x1y = len(boundary_verts)
                boundary_verts.append((x + 1, y))

            try:
                xy1 = boundary_verts.index((x, y + 1))
            except ValueError:
                xy1 = len(boundary_verts)
                boundary_verts.append((x, y + 1))

            try:
                x1y1 = boundary_verts.index((x + 1, y + 1))
            except ValueError:
                x1y1 = len(boundary_verts)
                boundary_verts.append((x + 1, y + 1))

            if (x, y) not in boundary_verts:
                boundary_verts.append((x, y))
            if (x + 1, y) not in boundary_verts:
                boundary_verts.append((x + 1, y))
            if (x, y + 1) not in boundary_verts:
                boundary_verts.append((x, y + 1))
            if (x + 1, y + 1) not in boundary_verts:
                boundary_verts.append((x + 1, y + 1))

            # boundary interiors
            boundary_interior.extend([xy, xy1, x1y, x1y, xy1, x1y1])

            # boundary outlines: edges of boundary tiles abutting non-boundary tiles
            if world.get_tile(x - 1, y) != Tile_State.boundary:
                boundary_outline.extend([xy, xy1])
            if world.get_tile(x + 1, y) != Tile_State.boundary:
                boundary_outline.extend([x1y, x1y1])
            if world.get_tile(x, y - 1) != Tile_State.boundary:
                boundary_outline.extend([xy, x1y])
            if world.get_tile(x, y + 1) != Tile_State.boundary:
                boundary_outline.extend([xy1, x1y1])

            self.boundary_verts = gloo.VertexBuffer(np.array(boundary_verts, np.float32))
            self.boundary_interior = gloo.IndexBuffer(np.array(boundary_interior, np.uint32))
            self.boundary_outline = gloo.IndexBuffer(np.array(boundary_outline, np.uint32))

            self.dirty_verts = gloo.VertexBuffer(np.array(dirty_verts, np.float32))

            self.update_dirties()
            self.update_goombas()

    def update_dirties(self):
        if not self.world:
            return

        dirty_coords = []
        h = len(self.world.state)
        w = len(self.world.state[0])

        for y in range(h):
            for x in range(w):
                if self.world.get_tile(x, y) == Tile_State.dirty:
                    dirty_coords.append(x + y*w)

        self.dirty_indices = gloo.IndexBuffer(np.array(dirty_coords, np.uint32))

    def update_goombas(self):
        if not self.world:
            return

        verts = []
        colors = []
        gs = Goomba.SHAPE

        for goomba in self.world.goombas:
            for vert in [gs[0], gs[1], gs[2], gs[0], gs[2], gs[3]]:
                rot = rotated(vert, goomba.ori)
                verts.append((goomba.pos[0] + rot[0] + 0.5, goomba.pos[1] + rot[1] + 0.5))

            gc = goomba.genome.colors
            colors.extend([gc[0], gc[1], gc[2], gc[0], gc[2], gc[3]])

        self.goomba_verts = gloo.VertexBuffer(np.array(verts, np.float32))
        self.goomba_colors = np.array(colors, np.float32)

def rotated(point, rotation):
    if rotation == [0, 1]:
        return point
    elif rotation == [0, -1]:
        return [-point[0], -point[1]]
    elif rotation == [1, 0]:
        return [point[1], -point[0]]
    else:
        return [-point[1], point[0]]

