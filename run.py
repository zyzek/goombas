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
                             ("genome", "0.1"),
                             ("gene_action", "0.3"),
                             ("struct_mod", "0.5"),
                             ("leaf_type", "0.3"),
                             ("genome_rel", "1 1 1 1 1"),
                             ("const_rel", "1 1 1 1"),
                             ("enum_rel", "1 1 1"),
                             ("struct_rel", "1 1 1")])

    #meta = "1.0  -5.0 5.0  3  5.0 2.0   0.3 0.8 0.8  0.3 0.8 0.8  0.8 0.3 0.8  0.8 0.3 0.8 " \
    #       "0.1  0.1  1 1 1 1 1  1 1 1 1  1 1 2 2"

    meta = " ".join(metadesc.values()) + " " + " ".join(muterates.values())
    gen = " 12 + 1 $10 | 4 * = 0 % $10 23 * 100 $1 | " \
             " 5 * 100 $2 | " \
             " 4 * 90 $4 | 3 * 90 $3 | 1 * 100 $5 | " \
             " 3 * * 80 $1 $0 | 4 * * 80 $1 - 1 $0 | " \
             " 1 20 " 


    #gen = " | 1 1 | 3 * 2 $0 | 4 * 3 $1 | 5 * 4 $2 | 12 + 1 $10 | 5 * = 0 % $10 7 * 100 $1"

    """gen = " | 1 1 | 3 * 2 $0 | 4 * 3 $1 | 12 + 1 $10 | 5 * = 0 % $10 7 * 100 $1"
    seq = "1.0 | 0.3 0.8 0.8  0.3 0.8 0.8  0.8 0.3 0.8  0.8 0.3 0.8" + gen
    
    gen2 = " | 12 + 1 $10 | 1 * 10 = 0 % $10 10 | 6 5 | 3 * 15 $0 | 5 * 25 $2" \
            " | 4 * = 0 % $10 43 * 15 $1 | 4 * 40 $3 | 3 * 40 $3"
    seq2 = "1.0 | 1.0 1.0 1.0  1.0 1.0 1.0  1.0 1.0 1.0  1.0 1.0 1.0" + gen2

    sense = "1.0 | 0.3 0.8 0.8  0.3 0.8 0.8  0.8 0.3 0.8  0.8 0.3 0.8 | 1 $0 " \
            "| 1 $1 | 1 $2 | 1 $3 | 1 $4 | 1 $5 | 1 $6 | 1 $7 | 1 $8 | 1 $9 | 1 $10"

    seeker = "1.0 | 1.0 1.0 1.0  1.0 1.0 1.0  1.0 1.0 1.0  1.0 1.0 1.0 | " \
             " 12 + 1 $10 | 4 * = 0 % $10 23 * 100 $1 | " \
             " 5 * 100 $2 | " \
             " 4 * 90 $4 | 3 * 90 $3 | 1 * 100 $5 | " \
             " 3 * * 80 $1 $0 | 4 * * 80 $1 - 1 $0 | " \
             " 1 20 " 
    """
            # Increment state per step, random turn
            # Suck up stuff if it's present underneath bot
            # Turn towards food
            # If bumped, turn away from obstacle
            # Baseline instinct to move forward


    """slist = []

    for _ in range(10):
        rseq = "1.0 | " + " ".join([str(random.random()) for _ in range(12)]) + gen
        slist.append(rseq)

    slist.append(seq)
    slist.append(sense)
    slist.append(seq2)"""

    print("Generated Goombas")
    bredgen = genome.Genome(*genome.cross_genome_sequences((meta, gen), (meta, gen)))
    bredgen.mutate()
    

    wrld = world.World(50, 50, [bredgen.sequences()]) #[(meta, gen)]*10)
    for goom in wrld.goombas:
        print([str(gene.function) for gene in goom.genome.genes])
    print("Generated World")

    canv = display.get_canvas(wrld)
    canv.title = "Genetic Roombas!"
    print("Generated Canvas")

    canv.show()

    app.run()


if __name__ == "__main__":
    main()
    #cProfile.run('main()')
