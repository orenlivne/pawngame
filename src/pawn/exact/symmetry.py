"""Left-right (file-mirror) symmetry.

The pawn game is invariant under mirroring the files (a<->h, b<->g, ...): the
value of a position equals the value of its mirror.  We exploit this by storing
each transposition entry under a canonical key = the lexicographically smaller of
the position and its mirror, roughly halving the table.
"""
from __future__ import annotations

# Reverse the 8 bits of a byte (mirrors the files within one rank).
_REV = [int("{:08b}".format(i)[::-1], 2) for i in range(256)]


def fliplr_mask(m: int) -> int:
    out = 0
    for r in range(8):
        out |= _REV[(m >> (8 * r)) & 0xFF] << (8 * r)
    return out


def fliplr_key(key):
    wp, bp, turn, ep = key
    ep2 = None if ep is None else (ep - (ep & 7)) + (7 - (ep & 7))
    return (fliplr_mask(wp), fliplr_mask(bp), turn, ep2)


def _sortable(key):
    wp, bp, turn, ep = key
    return (wp, bp, turn, -1 if ep is None else ep)


def canonical(key):
    """Return the canonical (mirror-invariant) form of ``key``."""
    fk = fliplr_key(key)
    return key if _sortable(key) <= _sortable(fk) else fk
