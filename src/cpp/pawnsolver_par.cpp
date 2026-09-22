// Exact pawn-game solver (C++ core).
//
// Mirrors the validated Python reference (pawn.exact): identical rules, the same
// *proven* passed-pawn race evaluator (loss-rule only), and the same board
// symmetries.  Values are exact: -1 loss, 0 draw, +1 win from the side to move.
//
// Transposition table: open-addressing with 16-byte packed entries.  A position
// (two 48-bit pawn masks on ranks 2-7, side to move, a 5-bit en-passant code) is
// packed into 102 bits; the 2-bit value code is stored in the low bits, so each
// slot is a single 128-bit integer and there is no separate key storage.
//
// Symmetries fold each position to a canonical representative:
//   * left-right file mirror (always), and
//   * color-swap + vertical flip (optional, --colorsym), roughly another 2x.
// Both are validated against the Python oracle.
//
// Build:  clang++ -O3 -std=c++17 -o pawnsolver pawnsolver.cpp
// Usage:  pawnsolver <n> <loss|draw> [--no-race] [--no-sym] [--colorsym]
//                    [--justify=left|center|right] [--bits=K]
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <chrono>
#include <string>
#include <atomic>
#include <thread>
#include <vector>
#include <unordered_set>
#include <sstream>
#include <iostream>
#include <cctype>

typedef uint64_t u64;
typedef unsigned __int128 u128;

// Per-thread counter of new internal nodes (drives the subtree-threshold cache
// gate).  A solve() call and all its recursion run on one thread, so this is a
// correct per-subtree measure without cross-thread interference.
static thread_local unsigned long long tl_nodes = 0;

static const int WHITE = 0, BLACK = 1;
static const int INF_STEPS = 99;
static const int NONE = 2;               // race "no decision"
static const u64 MASK48 = 0xFFFFFFFFFFFFULL;
static int g_noep = 0;  // --noep: play the variant with en passant disabled

// ------------------------------------------------------------------ board
struct Board { u64 wp, bp; int8_t turn; int8_t ep; };

static inline u64 my_pawns(const Board& b)  { return b.turn == WHITE ? b.wp : b.bp; }
static inline u64 opp_pawns(const Board& b) { return b.turn == WHITE ? b.bp : b.wp; }

static inline uint16_t mk_move(int from, int to, int is_ep) { return (uint16_t)(from | (to << 6) | (is_ep << 12)); }
static inline int mv_from(uint16_t m) { return m & 63; }
static inline int mv_to(uint16_t m)   { return (m >> 6) & 63; }
static inline int mv_ep(uint16_t m)   { return (m >> 12) & 1; }
static inline bool is_touchdown(uint16_t m) { int r = mv_to(m) >> 3; return r == 0 || r == 7; }

// ------------------------------------------------------- precomputed tables
static u64 g_obstacle[2][64];
static uint8_t g_rev[256];

static void init_tables() {
    for (int color = 0; color < 2; ++color) {
        int step = (color == WHITE) ? 8 : -8;
        for (int sq = 0; sq < 64; ++sq) {
            int f = sq & 7; u64 mask = 0;
            for (int adj = -1; adj <= 1; ++adj) {
                int nf = f + adj; if (nf < 0 || nf > 7) continue;
                int s = sq + step + adj;
                while (s >= 0 && s < 64) { mask |= (1ULL << s); s += step; }
            }
            g_obstacle[color][sq] = mask;
        }
    }
    for (int i = 0; i < 256; ++i) { uint8_t r = 0; for (int b = 0; b < 8; ++b) if (i & (1 << b)) r |= (1 << (7 - b)); g_rev[i] = r; }
}

// ----------------------------------------------------------- move generation
static int gen_moves(const Board& b, uint16_t* out) {
    int n = 0;
    u64 me = my_pawns(b), opp = opp_pawns(b);
    u64 occ = b.wp | b.bp, empty = ~occ;
    int d = (b.turn == WHITE) ? 8 : -8;
    int start_rank = (b.turn == WHITE) ? 1 : 6;
    u64 m = me;
    while (m) {
        int frm = __builtin_ctzll(m); m &= m - 1;
        int f = frm & 7, one = frm + d;
        if (empty & (1ULL << one)) {
            out[n++] = mk_move(frm, one, 0);
            if ((frm >> 3) == start_rank) { int two = frm + 2 * d; if (empty & (1ULL << two)) out[n++] = mk_move(frm, two, 0); }
        }
        if (f > 0) { int to = one - 1; if (opp & (1ULL << to)) out[n++] = mk_move(frm, to, 0); }
        if (f < 7) { int to = one + 1; if (opp & (1ULL << to)) out[n++] = mk_move(frm, to, 0); }
    }
    if (b.ep >= 0 && (opp & (1ULL << (b.ep - d)))) {
        for (int df = -1; df <= 1; df += 2) {
            int frm = b.ep - d - df;
            if (frm >= 0 && frm < 64) {
                int ff = frm & 7, ef = b.ep & 7;
                if ((ff - ef == 1 || ef - ff == 1) && (me & (1ULL << frm))) out[n++] = mk_move(frm, b.ep, 1);
            }
        }
    }
    return n;
}

static Board apply_move(const Board& b, uint16_t mv) {
    Board c = b;
    int frm = mv_from(mv), to = mv_to(mv), is_ep = mv_ep(mv);
    int d = (b.turn == WHITE) ? 8 : -8;
    u64 from_bit = 1ULL << frm, to_bit = 1ULL << to;
    if (b.turn == WHITE) c.wp = (c.wp & ~from_bit) | to_bit; else c.bp = (c.bp & ~from_bit) | to_bit;
    int captured = -1;
    if (is_ep) captured = to - d;
    else if ((b.turn == WHITE ? c.bp : c.wp) & to_bit) captured = to;
    if (captured >= 0) { u64 cb = 1ULL << captured; if (b.turn == WHITE) c.bp &= ~cb; else c.wp &= ~cb; }
    int new_ep = -1;
    if (!g_noep && ((to - frm == 16) || (frm - to == 16))) {
        int skipped = frm + d; u64 opp_now = (b.turn == WHITE) ? c.bp : c.wp; int tf = to & 7;
        for (int adj = -1; adj <= 1; adj += 2) {
            int a = to + adj;
            if (a >= 0 && a < 64) { int af = a & 7; if ((af - tf == 1 || tf - af == 1) && (opp_now & (1ULL << a))) { new_ep = skipped; break; } }
        }
    }
    c.ep = (int8_t)new_ep; c.turn = (b.turn == WHITE) ? BLACK : WHITE;
    return c;
}

// --------------------------------------------------- proven race evaluator
static inline int steps_lb(int sq, int color) {
    int rank = sq >> 3;
    if (color == WHITE) { int d = 7 - rank; if (rank == 1) d -= 1; return d; }
    int d = rank; if (rank == 6) d -= 1; return d;
}
static int min_promo_lb(u64 pawns, int color) {
    int best = INF_STEPS;
    while (pawns) { int sq = __builtin_ctzll(pawns); pawns &= pawns - 1; int s = steps_lb(sq, color); if (s < best) best = s; }
    return best;
}
static int min_unstoppable(u64 pawns, u64 enemy, int color, u64 occ) {
    int best = INF_STEPS;
    while (pawns) {
        int sq = __builtin_ctzll(pawns); pawns &= pawns - 1;
        if (g_obstacle[color][sq] & enemy) continue;
        int rank = sq >> 3, dist;
        if (color == WHITE) { dist = 7 - rank; if (rank == 1 && !(occ & (1ULL << (sq + 8))) && !(occ & (1ULL << (sq + 16)))) dist -= 1; }
        else                { dist = rank;     if (rank == 6 && !(occ & (1ULL << (sq - 8))) && !(occ & (1ULL << (sq - 16)))) dist -= 1; }
        if (dist < best) best = dist;
    }
    return best;
}
static int race_value(const Board& b) {
    u64 me = my_pawns(b), opp = opp_pawns(b), occ = b.wp | b.bp;
    int my_color = b.turn, opp_color = (b.turn == WHITE) ? BLACK : WHITE;
    if (min_unstoppable(me, opp, my_color, occ) <= min_promo_lb(opp, opp_color)) return 1;
    if (min_unstoppable(opp, me, opp_color, occ) < min_promo_lb(me, my_color)) return -1;
    return NONE;
}

// ------------------------------------------------------------- symmetries
static inline u64 fliplr_mask(u64 m) { u64 o = 0; for (int r = 0; r < 8; ++r) o |= (u64)g_rev[(m >> (8 * r)) & 0xFF] << (8 * r); return o; }
static inline int ep_code(int ep) {
    if (ep < 0) return 0;
    if (ep >= 16 && ep <= 23) return 1 + (ep - 16);
    if (ep >= 40 && ep <= 47) return 9 + (ep - 40);
    return 0;
}
static inline u128 pack(u64 wp, u64 bp, int turn, int ep) {
    u64 wp48 = (wp >> 8) & MASK48, bp48 = (bp >> 8) & MASK48;
    u128 p = (u128)wp48;
    p |= (u128)bp48 << 48;
    p |= (u128)(turn & 1) << 96;
    p |= (u128)(ep_code(ep)) << 97;
    return p;
}
static int g_colorsym = 0;
static u128 canonical_packed(const Board& b) {
    u128 best = pack(b.wp, b.bp, b.turn, b.ep);
    // LR mirror
    {
        u64 wp2 = fliplr_mask(b.wp), bp2 = fliplr_mask(b.bp);
        int ep2 = (b.ep < 0) ? -1 : ((b.ep & ~7) | (7 - (b.ep & 7)));
        u128 p = pack(wp2, bp2, b.turn, ep2);
        if (p < best) best = p;
    }
    if (g_colorsym) {
        // color-swap + vertical flip: white<->black pawns, rank r <-> 7-r, turn flips
        u64 cwp = __builtin_bswap64(b.bp), cbp = __builtin_bswap64(b.wp);
        int cep = (b.ep < 0) ? -1 : (8 * (7 - (b.ep >> 3)) + (b.ep & 7));
        int ct = b.turn ^ 1;
        { u128 p = pack(cwp, cbp, ct, cep); if (p < best) best = p; }
        // color-swap + vertical flip + LR
        u64 cwp2 = fliplr_mask(cwp), cbp2 = fliplr_mask(cbp);
        int cep2 = (cep < 0) ? -1 : ((cep & ~7) | (7 - (cep & 7)));
        { u128 p = pack(cwp2, cbp2, ct, cep2); if (p < best) best = p; }
    }
    return best;
}

// ------------------------------------------------------------------ TT
struct TT {
    // Atomic 16-byte slots: on Apple Silicon these are lock-free, so a whole
    // entry is read/written without tearing.  Concurrent races can only cause a
    // benign recompute or overwrite of one *valid* entry by another; a probe
    // never sees a half-written slot, so parallel search stays exact.
    std::atomic<u128>* slots = nullptr;
    size_t mask = 0, cap = 0;
    std::atomic<size_t> count{0};
    void init(int bits) {
        cap = (size_t)1 << bits;
        slots = new (std::nothrow) std::atomic<u128>[cap]();
        if (!slots) { fprintf(stderr, "alloc failed for 2^%d slots\n", bits); exit(2); }
        mask = cap - 1;
    }
    static inline size_t hsh(u128 p) { u64 lo = (u64)p, hi = (u64)(p >> 64); u64 h = lo * 0x9E3779B97F4A7C15ULL; h ^= hi + 0x9E3779B97F4A7C15ULL + (h << 6) + (h >> 2); return (size_t)h; }
    // Each slot: (position << 4) | (flag << 2) | (value+2).  flag: 0=EXACT,1=LOWER,2=UPPER.
    inline size_t probe(u128 p) const {
        size_t i = hsh(p) & mask;
        while (true) { u128 e = slots[i].load(std::memory_order_relaxed); if (e == 0) return i; if ((e >> 4) == p) return i; i = (i + 1) & mask; }
    }
};

enum { F_EXACT = 0, F_LOWER = 1, F_UPPER = 2 };

// ------------------------------------------------------------------ solver
struct Solver {
    bool stalemate_is_loss, use_race, use_sym;
    TT tt;
    std::atomic<unsigned long long> total_nodes{0};  // summed across threads for reporting
    unsigned long long minsub = 1;   // cache a node only if its subtree had >= minsub new nodes
    bool raceorder = false;          // race-aware move ordering (speed only)

    inline u128 keyof(const Board& b) { return use_sym ? canonical_packed(b) : pack(b.wp, b.bp, b.turn, b.ep); }

    // Fail-soft negamax alpha-beta.  Values in {-1,0,1}; call the root with a
    // wide window (-2,2) to get the exact value.  The transposition table stores
    // (value, EXACT/LOWER/UPPER); the passed-pawn race supplies exact leaves
    // under the loss-rule and proven +-window bounds under the draw-rule.
    int solve(const Board& b, int alpha, int beta) {
        const int alpha0 = alpha, beta0 = beta;
        u128 p = keyof(b);
        size_t idx = tt.probe(p);
        u128 e = tt.slots[idx].load(std::memory_order_relaxed);
        if (e != 0) {
            int code = (int)(e & 15), v = (code & 3) - 2, flag = code >> 2;
            if (flag == F_EXACT) return v;
            if (flag == F_LOWER) { if (v >= beta) return v; if (v > alpha) alpha = v; }
            else /* F_UPPER */   { if (v <= alpha) return v; if (v < beta) beta = v; }
            if (alpha >= beta) return v;
        }

        // Exact leaves -- cheap to recompute, so never cached.
        if (opp_pawns(b) == 0) return 1;
        if (my_pawns(b) == 0)  return -1;
        uint16_t moves[64];
        int nm = gen_moves(b, moves);
        if (nm == 0) return stalemate_is_loss ? -1 : 0;
        for (int i = 0; i < nm; ++i) if (is_touchdown(moves[i])) return 1;

        if (use_race) {
            int rv = race_value(b);   // +1: value>=0 ; -1: value<=0 ; NONE
            if (rv != NONE) {
                if (stalemate_is_loss) return rv;          // loss-rule: exact leaf
                // draw-rule: rv is a *bound* around 0.
                if (rv == 1) { if (0 >= beta) return 0; if (0 > alpha) alpha = 0; }
                else         { if (0 <= alpha) return 0; if (0 < beta) beta = 0; }
            }
        }

        unsigned long long nb = tl_nodes;
        ++tl_nodes;
        order_moves(b, moves, nm);
        int best = -2;
        for (int i = 0; i < nm; ++i) {
            Board c = apply_move(b, moves[i]);
            int cv = -solve(c, -beta, -alpha);
            if (cv > best) { best = cv; if (best > alpha) alpha = best; }
            if (alpha >= beta) break;   // alpha-beta cutoff
            if (best >= 1) break;       // +1 is the maximum value
        }

        // Cache only nodes whose subtree created >= minsub new nodes.
        if (tl_nodes - nb >= minsub) {
            int flag = (best <= alpha0) ? F_UPPER : (best >= beta0) ? F_LOWER : F_EXACT;
            u128 entry = (p << 4) | ((u128)flag << 2) | (u128)(best + 2);
            size_t idx2 = tt.probe(p);  // re-probe: children may have taken slots
            u128 e2 = tt.slots[idx2].load(std::memory_order_relaxed);
            if (e2 == 0) {
                // Claim the empty slot atomically so `count` is exact under races
                // (a plain store would let two racing threads both count it).
                u128 expected = 0;
                if (tt.slots[idx2].compare_exchange_strong(expected, entry, std::memory_order_relaxed)) {
                    size_t c = tt.count.fetch_add(1, std::memory_order_relaxed) + 1;
                    if ((c & ((1ULL << 25) - 1)) == 0)
                        fprintf(stderr, "  [progress] stored=%zu (%.1fGB)\n", c, (double)c * 16 / 1e9);
                    if (c * 10 > tt.cap * 9) { fprintf(stderr, "TT overflow (>90%% of 2^%zu). Increase --bits.\n", (size_t)__builtin_ctzll((unsigned long long)tt.cap)); exit(3); }
                }
                // if the CAS failed another thread claimed the slot: skip (benign)
            } else {
                // Non-empty: overwrite only with a more informative entry for the
                // same position (no count change). Every stored entry is a valid
                // bound/exact for p, so this is race-safe.
                int oc = (int)(e2 & 15), ov = (oc & 3) - 2, of = oc >> 2;
                if (of != F_EXACT && (flag == F_EXACT ||
                     (flag == F_LOWER && (of != F_LOWER || best > ov)) ||
                     (flag == F_UPPER && (of == F_UPPER && best < ov))))
                    tt.slots[idx2].store(entry, std::memory_order_relaxed);
            }
        }
        return best;
    }

    // ---- parallel driver: root-subtree splitting over a shared atomic TT ----
    // Collect distinct (canonical) non-terminal positions exactly `depth` plies
    // from the root; each becomes an independent work unit.
    void collect(const Board& b, int depth, std::unordered_set<u128>& seen, std::vector<Board>& out) {
        if (opp_pawns(b) == 0 || my_pawns(b) == 0) return;
        uint16_t moves[64];
        int nm = gen_moves(b, moves);
        if (nm == 0) return;
        if (depth == 0) { if (seen.insert(keyof(b)).second) out.push_back(b); return; }
        for (int i = 0; i < nm; ++i) {
            if (is_touchdown(moves[i])) continue;   // terminal child; handled in the final serial pass
            Board c = apply_move(b, moves[i]);
            collect(c, depth - 1, seen, out);
        }
    }

    // Solve `root` using `threads` workers.  Each worker solves whole task
    // subtrees serially; they share the TT, so the exact value is unchanged --
    // parallelism only reorders work and shares transpositions.
    int solve_parallel(const Board& root, int threads, int split_depth) {
        std::unordered_set<u128> seen;
        std::vector<Board> tasks;
        collect(root, split_depth, seen, tasks);
        fprintf(stderr, "  [parallel] %zu task subtrees, %d threads\n", tasks.size(), threads);
        std::atomic<size_t> next{0};
        auto worker = [&]() {
            tl_nodes = 0;
            while (true) {
                size_t i = next.fetch_add(1, std::memory_order_relaxed);
                if (i >= tasks.size()) break;
                solve(tasks[i], -2, 2);
            }
            total_nodes.fetch_add(tl_nodes, std::memory_order_relaxed);
        };
        std::vector<std::thread> pool;
        for (int t = 0; t < threads; ++t) pool.emplace_back(worker);
        for (auto& th : pool) th.join();
        // Final serial pass: recurses only the shallow top (< split_depth), then
        // hits the TT the workers filled.  Returns the exact root value.
        tl_nodes = 0;
        int v = solve(root, -2, 2);
        total_nodes.fetch_add(tl_nodes, std::memory_order_relaxed);
        return v;
    }

    // ---- perfect-play analysis (run after solve(); reuses the populated TT) ----
    static std::string uci(uint16_t m) {
        auto sq = [](int s) { std::string r; r += char('a' + (s & 7)); r += char('1' + (s >> 3)); return r; };
        return sq(mv_from(m)) + sq(mv_to(m));
    }

    // Optimal first moves for the side to move (all value-preserving moves).
    std::string optimal_first_moves(const Board& b, int v) {
        uint16_t moves[64];
        int nm = gen_moves(b, moves);
        std::string out;
        for (int i = 0; i < nm; ++i) {
            int cv;
            if (is_touchdown(moves[i])) cv = 1;
            else { Board c = apply_move(b, moves[i]); cv = -solve(c, -2, 2); }
            if (cv == v) { if (!out.empty()) out += " "; out += uci(moves[i]); }
        }
        return out;
    }

    // A perfect line: at each node take a value-preserving move (touchdown first).
    std::string principal_variation(const Board& root, int maxply = 100) {
        Board b = root;
        std::string out;
        for (int ply = 0; ply < maxply; ++ply) {
            if (opp_pawns(b) == 0 || my_pawns(b) == 0) break;
            uint16_t moves[64];
            int nm = gen_moves(b, moves);
            if (nm == 0) break;
            int v = solve(b, -2, 2);
            order_moves(b, moves, nm);
            int chosen = -1;
            for (int i = 0; i < nm && chosen < 0; ++i) {
                if (is_touchdown(moves[i])) { if (v == 1) chosen = i; continue; }
                Board c = apply_move(b, moves[i]);
                if (-solve(c, -2, 2) == v) chosen = i;
            }
            if (chosen < 0) chosen = 0;
            if (!out.empty()) out += " ";
            out += uci(moves[chosen]);
            bool td = is_touchdown(moves[chosen]);
            b = apply_move(b, moves[chosen]);
            if (td) break;
        }
        return out;
    }

    void order_moves(const Board& b, uint16_t* mv, int nm) {
        u64 opp = opp_pawns(b); int white = (b.turn == WHITE); int score[64];
        for (int i = 0; i < nm; ++i) {
            int to = mv_to(mv[i]); int s = 0;
            // Race-aware ordering (pure ordering: never changes a value): try
            // moves that leave the opponent in a proven-lost race first, so the
            // alpha-beta cutoff fires before the losing siblings are searched.
            if (raceorder && use_race) {
                Board c = apply_move(b, mv[i]);
                if (opp_pawns(c) == 0) s += 50000;          // captured last pawn
                else { int rv = race_value(c); if (rv == -1) s += 50000; else if (rv == 1) s -= 50000; }
            }
            if (mv_ep(mv[i]) || (opp & (1ULL << to))) s += 100;
            int r = to >> 3; s += white ? r : (7 - r); score[i] = s;
        }
        for (int i = 1; i < nm; ++i) { uint16_t m = mv[i]; int s = score[i]; int j = i - 1; while (j >= 0 && score[j] < s) { mv[j + 1] = mv[j]; score[j + 1] = score[j]; --j; } mv[j + 1] = m; score[j + 1] = s; }
    }
};

static Board parse_fen(const std::string& fen) {
    Board b; b.wp = 0; b.bp = 0; b.turn = WHITE; b.ep = -1;
    std::istringstream ss(fen);
    std::string place, turn = "w", ep = "-", tmp;
    ss >> place >> turn >> tmp >> ep;
    int rank = 7, file = 0;
    for (char c : place) {
        if (c == '/') { rank--; file = 0; }
        else if (isdigit((unsigned char)c)) file += c - '0';
        else { int sq = rank * 8 + file; if (c == 'P') b.wp |= 1ULL << sq; else if (c == 'p') b.bp |= 1ULL << sq; file++; }
    }
    b.turn = (turn == "b") ? BLACK : WHITE;
    if (ep.size() >= 2 && ep[0] != '-') b.ep = (ep[1] - '1') * 8 + (ep[0] - 'a');
    return b;
}

static Board start_board(int n, const std::string& justify) {
    int space = 8 - n, left;
    if (justify == "left") left = 0; else if (justify == "right") left = space; else left = space / 2;
    Board b; b.wp = 0; b.bp = 0; b.turn = WHITE; b.ep = -1;
    for (int f = left; f < left + n; ++f) { b.wp |= 1ULL << (8 + f); b.bp |= 1ULL << (48 + f); }
    return b;
}

static int default_bits(int n) {
    switch (n) { case 8: return 32; case 7: return 29; case 6: return 26; case 5: return 23; default: return 20; }
}

int main(int argc, char** argv) {
    if (argc < 3) { fprintf(stderr, "usage: pawnsolver <n> <loss|draw> [--no-race] [--no-sym] [--colorsym] [--justify=left] [--bits=K]\n"); return 1; }
    init_tables();
    int n = atoi(argv[1]);
    bool loss = (std::string(argv[2]) == "loss");
    bool use_race = true, use_sym = true;
    std::string justify = "left";
    int bits = -1;
    unsigned long long minsub = 1;
    bool raceorder = false;
    bool want_pv = false, serve = false;
    int threads = 1, split_depth = 3;
    for (int i = 3; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--no-race") use_race = false;
        else if (a == "--no-sym") use_sym = false;
        else if (a == "--colorsym") g_colorsym = 1;
        else if (a.rfind("--justify=", 0) == 0) justify = a.substr(10);
        else if (a.rfind("--bits=", 0) == 0) bits = atoi(a.c_str() + 7);
        else if (a.rfind("--minsub=", 0) == 0) minsub = strtoull(a.c_str() + 9, nullptr, 10);
        else if (a == "--raceorder") raceorder = true;
        else if (a == "--pv") want_pv = true;
        else if (a == "--noep") g_noep = 1;
        else if (a == "--serve") serve = true;
        else if (a.rfind("--threads=", 0) == 0) threads = atoi(a.c_str() + 10);
        else if (a.rfind("--splitdepth=", 0) == 0) split_depth = atoi(a.c_str() + 13);
    }
    if (bits < 0) bits = default_bits(n);

    Board b = start_board(n, justify);
    Solver s; s.stalemate_is_loss = loss; s.use_race = use_race; s.use_sym = use_sym; s.minsub = minsub; s.raceorder = raceorder;
    s.tt.init(bits);

    auto t0 = std::chrono::steady_clock::now();
    int v;
    if (threads > 1) v = s.solve_parallel(b, threads, split_depth);
    else { v = s.solve(b, -2, 2); s.total_nodes.store(tl_nodes); }
    auto t1 = std::chrono::steady_clock::now();
    double dt = std::chrono::duration<double>(t1 - t0).count();

    unsigned long long visits = s.total_nodes.load();
    size_t stored = s.tt.count.load();
    const char* lab = v > 0 ? "WHITE wins" : (v < 0 ? "BLACK wins" : "DRAW");
    double gb = (double)stored * 16.0 / 1e9;
    printf("n=%d rule=%s justify=%s sym=%d colorsym=%d race=%d minsub=%llu threads=%d value=%d (%s) stored=%zu (%.1fGB) visits=%llu %.2fs (%.1fM/s)\n",
           n, loss ? "loss" : "draw", justify.c_str(), use_sym, g_colorsym, use_race, minsub, threads,
           v, lab, stored, gb, visits, dt, visits / dt / 1e6);
    if (want_pv) {
        printf("optimal_first_moves: %s\n", s.optimal_first_moves(b, v).c_str());
        printf("pv: %s\n", s.principal_variation(b).c_str());
    }

    if (serve) {
        // Move server: the root solve above filled the TT with all positions
        // reachable from the start. Read a kingless FEN per line, reply with a
        // random value-preserving (optimal) move in UCI, or "none"/"terminal".
        unsigned long long rng = 88172645463325252ULL;
        auto next_rand = [&]() { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; };
        std::cout << "READY" << std::endl;
        std::string line;
        while (std::getline(std::cin, line)) {
            if (line.rfind("seed ", 0) == 0) { rng = strtoull(line.c_str() + 5, nullptr, 10) | 1ULL; std::cout << "ok" << std::endl; continue; }
            if (line == "quit") break;
            if (line.empty()) continue;
            Board pb = parse_fen(line);
            if (opp_pawns(pb) == 0 || my_pawns(pb) == 0) { std::cout << "terminal" << std::endl; continue; }
            uint16_t moves[64];
            int nm = gen_moves(pb, moves);
            if (nm == 0) { std::cout << "none" << std::endl; continue; }
            int pv2 = s.solve(pb, -2, 2);
            std::vector<uint16_t> opts;
            for (int i = 0; i < nm; ++i) {
                int cv;
                if (is_touchdown(moves[i])) cv = 1;
                else { Board c = apply_move(pb, moves[i]); cv = -s.solve(c, -2, 2); }
                if (cv == pv2) opts.push_back(moves[i]);
            }
            uint16_t mv = opts[next_rand() % opts.size()];
            std::cout << Solver::uci(mv) << std::endl;
        }
        return 0;
    }
    return 0;
}
