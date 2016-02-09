from vispy import app
import display
import world
from genome import Genome
import random

def main():

    gen = " | 1 1 | 3 * 2 $0 | 4 * 3 $1" #| 5 * 4 $2"

    seq = "1.0 | 0.3 0.8 0.8  0.3 0.8 0.8  0.8 0.3 0.8  0.8 0.3 0.8" + gen

    sense = "1.0 | 0.3 0.8 0.8  0.3 0.8 0.8  0.8 0.3 0.8  0.8 0.3 0.8 | 1 $0 | 1 $1 | 1 $2 | 1 $3 | 1 $4 | 1 $5 | 1 $6 | 1 $7 | 1 $8 | 1 $9 | 1 $10 | 1 $11"

    slist = []

    for _ in range(10):
        s = "1.0 | " + " ".join([str(random.random()) for _ in range(12)]) + gen
        slist.append(s)

    slist.append(seq)

    w = world.World(50, 50, [sense])
    c = display.get_canvas(w)
    c.title = "Genetic Roombas!"
    c.show()

    app.run()


if __name__ == "__main__":
    main()
