from vispy import app
import display
import world

def main():

    w = world.World(50, 50, [])
    c = display.get_canvas(w)
    app.run()

if __name__ == "__main__":
    main()
