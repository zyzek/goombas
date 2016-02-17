"""Main entry point for pitting goomba against goomba."""

from collections import OrderedDict

import cProfile
import re

from vispy import app
import display
import world
import genome

def main():
    """Set up the world and run it."""
    metadesc = OrderedDict([("colors", "0.3 0.8 0.8  0.3 0.8 0.8  0.8 0.3 0.8  0.8 0.3 0.8"),
                            ("fuzziness", "1.0"),
                            ("const_bounds", "-5.0 5.0"),
                            ("fun_gen_depth", "3"),
                            ("incr_range", "5.0"),
                            ("mult_range", "2.0")])
    muterates = OrderedDict([("mute", "0.1"),
                             ("genome", "0.2"),
                             ("gene_action", "0.5"),
                             ("struct_mod", "0.5"),
                             ("leaf_type", "0.3"),
                             ("genome_rel", "2 1 1 1 2"),
                             ("const_rel", "1 1 1 1"),
                             ("leaf_rel", "1 1 4 4"),
                             ("enum_rel", "1 1 1"),
                             ("struct_rel", "1 1 1")])

    meta1 = " ".join(metadesc.values()) + " " + " ".join(muterates.values())
    metadesc["colors"] = "1.0 0.0 0.0  1.0 0.0 0.0  1.0 0.0 0.0  1.0 0.0 0.0"
    meta2 = " ".join(metadesc.values()) + " " + " ".join(muterates.values())
    gen = " 12 + 1 $10 | 4 * = 0 % $10 23 * 100 $1 | " \
             " 5 * 100 $2 | " \
             " 4 * 90 $4 | 3 * 90 $3 | 1 * 100 $5 | " \
             " 3 * * 80 $1 $0 | 4 * * 80 $1 - 1 $0 | " \
             " 1 20 " 
            # Increment state per step, random turn
            # Suck up stuff if it's present underneath bot
            # Turn towards food
            # If bumped, turn away from obstacle
            # Baseline instinct to move forward


    #gen = " | 1 1 | 3 * 2 $0 | 4 * 3 $1 | 5 * 4 $2 | 12 + 1 $10 | 5 * = 0 % $10 7 * 100 $1"


    print("Generating Goombas")
    gen2 = [genome.Genome(*genome.cross_genome_sequences((meta2, gen), (meta1, gen))) for _ in range(30)]
    for g in gen2:
        g.mutate()
    gen2 = [g.sequences() for g in gen2]
   
    
    print("Building World")
    #wrld = world.World.random_goombas(40, 40, 10, meta1, [3, 10])
    wrld = world.World(100, 100, gen2, meta1, [3, 10], 1000)
	
    print("Constructing geometry (can take a bit because I'm a retard)")
    canv = display.get_canvas(wrld)
    canv.title = "Genetic Roombas!"

    canv.show()
    app.run()


if __name__ == "__main__":
    main()
    #cProfile.run('main()')
