from enum import Enum


class Directions(Enum):
    North = 1
    NorthEast = 2
    East = 3
    SouthEast = 4
    South = 5
    SouthWest = 6
    West = 7
    NorthWest = 8

    #                ^
    #       ^        |        ^
    #        \     North     /
    #     NorthWest      NorthEast
    # <- West                  East ->
    #     SouthWest      SouthEast
    #         /     South    \
    #        v        |      v
    #                 v
