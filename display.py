from vispy import app, gloo
import numpy as np
import sys

canvas = None
def get_canvas():
    if not canvas:
        canvas = Canvas()

    return canvas


vertex_shader = """
attribute vec2 position;
attribute vec4 color;
varying vec4 v_color;

void main()
{
    gl_Position = vec4(position, 0.0, 1.0);
    v_color = color;
}"""

fragment_shader = """
varying vec4 v_color;
void main()
{
    gl_FragColor = v_color;
}"""

class Canvas(app.Canvas):
    def __init__(self, world=None):
        self.world = world


        app.Canvas.__init__(self, keys='interactive', size=(800, 600))

        self.program = gloo.Program(vertex_shader, fragment_shader)
        
        pos = np.array([(-0.3, -0.2), (-0.5, 0.5), (0.0, 0.0),
                        (0.5, -0.8), (0.2, 0.3), (0.6, -0.2)], np.float32)
        cols = np.array([(1.0,0.0,0.0,1.0), (0.0,1.0,0.0,1.0), (0.0,0.0,1.0,1.0),
                         (1.0, 0.0, 1.0, 1.0),(0.4, 1.0, 0.2, 1.0),(0.1, 1.0, 0.1, 1.0)], np.float32)


        self.program['position'] = pos
        self.program['color'] = cols

        self.show()

    def on_resize(self, event):
        width, height = event.size
        gloo.set_viewport(0, 0, width, height)

    def on_draw(self, event):
        gloo.clear()
        self.program.draw('triangles')

    def set_world(self, world):
        self.world = world

    def update_world_geom(self):
        pass


if __name__ == '__main__':
    c = Canvas()
    if sys.flags.interactive != 1:
        app.run()
