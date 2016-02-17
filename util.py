"""Utilities that belong nowhere else."""
from random import random

def weighted_choice(weighted_items, num_items=1):
    """Take a dict mapping items to weights, return a weighted random choice of the objects."""
    total = 0
    cume_list = []

    for item, weight in weighted_items.items():
        total += weight
        cume_list.append([item, total])

    for pair in cume_list:
        pair[1] /= total

    items = []

    for _ in range(num_items):
        rand = random()

        for item, val in cume_list:
            if rand <= val:
                items.append(item)
                break

    assert num_items == len(items), (weighted_items, items)

    if num_items == 1:
        return items[0]

    return items
