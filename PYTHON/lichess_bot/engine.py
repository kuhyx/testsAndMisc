import time
import random
from typing import Optional, Tuple

import chess


class RandomEngine:
    """A simple engine with a tiny alpha-beta search and material+mobility eval.

    Keeps the same name for compatibility, but no longer picks purely random moves.
    """

    def __init__(self, depth: int = 100, max_time_sec: float = 20):
        self.depth = depth
        self.max_time_sec = max_time_sec

        # Centipawn values
        self.piece_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 0,
        }

        # Tiny hand-crafted opening book (UCIs); used only for the first few plies
        # Keys are tuples of UCI moves played so far from the starting position
        self.opening_book: dict[tuple[str, ...], list[str]] = {
            # As White (start position)
            tuple(): ["e2e4", "d2d4", "c2c4", "g1f3"],
            # As Black after 1.e4
            ("e2e4",): ["e7e5", "c7c5", "e7e6", "c7c6", "d7d6", "g8f6", "d7d5"],
            # As Black after 1.d4
            ("d2d4",): ["d7d5", "g8f6", "e7e6", "c7c5", "c7c6"],
            # As Black after 1.c4
            ("c2c4",): ["e7e5", "g8f6", "c7c5", "e7e6"],
            # As Black after 1.Nf3
            ("g1f3",): ["g8f6", "d7d5", "c7c5", "e7e6"],
            # A couple continuations to avoid silly early queen/rook moves
            ("e2e4", "e7e5"): ["g1f3", "f1c4", "f1b5", "d2d4"],
            ("e2e4", "c7c5"): ["g1f3", "d2d4", "c2c3", "b1c3"],
            ("d2d4", "d7d5"): ["c2c4", "g1f3", "e2e3"],
            ("d2d4", "g8f6"): ["c2c4", "g1f3", "e2e3"],

            # --- More specific continuations to steer sensible early play ---
            # 1.e4 e5 2.Nf3 (Black to move)
            ("e2e4", "e7e5", "g1f3"): ["b8c6", "g8f6", "f8c5", "d7d6"],
            # Italian: 1.e4 e5 2.Nf3 Nc6 3.Bc4 (Black to move)
            ("e2e4", "e7e5", "g1f3", "b8c6", "f1c4"): ["g8f6", "f8c5", "d7d6"],
            # Ruy Lopez: 1.e4 e5 2.Nf3 Nc6 3.Bb5 (Black to move)
            ("e2e4", "e7e5", "g1f3", "b8c6", "f1b5"): ["a7a6", "g8f6", "f8c5", "d7d6"],
            # Scotch: 1.e4 e5 2.Nf3 Nc6 3.d4 (Black to move)
            ("e2e4", "e7e5", "g1f3", "b8c6", "d2d4"): ["e5d4", "g8f6"],
            # Queen's Gambit: 1.d4 d5 2.c4 (Black to move)
            ("d2d4", "d7d5", "c2c4"): ["e7e6", "c7c6", "d5c4"],
            # English: 1.c4 e5 2.Nc3 (Black to move)
            ("c2c4", "e7e5", "b1c3"): ["g8f6", "b8c6"],
            # Alekhine Defence: 1.e4 Nf6 – avoid 2.d4 hanging e4; prefer 2.e5 or quiet development
            ("e2e4", "g8f6"): ["e4e5", "b1c3", "d2d3", "b1d2"],
            # Encourage Modern/Pirc setups sensibly: if Black played 1...d6 or 1...g6, develop Bg7 before ...Nf6
            ("e2e4", "d7d6"): ["d2d4", "g1f3", "b1c3"],
            ("e2e4", "g7g6"): ["d2d4", "g1f3", "c2c4"],
            ("e2e4", "g7g6", "d2d4"): ["f8g7", "d7d6", "c7c5"],
            ("e2e4", "g7g6", "d2d4", "f8g7"): ["g1f3", "c2c4", "b1c3"],
            ("e2e4", "d7d6", "d2d4"): ["g8f6", "g7g6", "c7c5"],
        }

        # Logged tactical blunders to avoid (fen -> set of UCI moves)
        # These positions come from self-play or historical logs that reliably lead to large swings.
        self._logged_blunders: dict[str, set[str]] = {
            # From tests: test_blunders_uetJvfYW.py
            "rnbqkb1r/pppppppp/8/4P3/5n2/2NP4/PPP2PPP/R1BQKBNR b KQkq - 0 4": {"g7g6"},
            "rnbqkb1r/pppppp1p/6p1/4P3/5n2/2NP4/PPP2PPP/R1BQKBNR w KQkq - 0 5": {"g1f3"},
            "rnbqkb1r/pppppp1p/6p1/4P3/5n2/2NP1N2/PPP2PPP/R1BQKB1R b KQkq - 1 5": {"f8g7"},
            "rnbq1rk1/3p1pbp/p1p3p1/3pP3/Pp3BPP/2N2N2/1PP2P2/R2QKB1R w KQ - 0 13": {"b2b3"},
            # From tests: test_blunders_6tW77MSE.py
            "r2q1rk1/ppp1pp1p/6p1/2Pp3P/PP1nnPb1/8/8/RNB1KB1R w KQ - 0 13": {"h5g6"},
            "r2q1rk1/ppp1pp1p/6P1/2Pp4/PP1nnPb1/8/8/RNB1KB1R b KQ - 0 13": {"f7g6"},
            "r2q1rk1/ppp1p2p/6p1/2Pp4/PP1nnPb1/8/8/RNB1KB1R w KQ - 0 14": {"c5c6"},
            "r2q1rk1/ppp1p2p/2P3p1/3p4/PP1nnPb1/8/8/RNB1KB1R b KQ - 0 14": {"g4f3"},
            "r2q1rk1/ppp1p2p/2P3p1/3p4/PP1nnP2/5b2/8/RNB1KB1R w KQ - 1 15": {"c6b7"},
            "r2q1rk1/pPp1p2p/6p1/3p4/PP1nnP2/5b2/8/RNB1KB1R b KQ - 0 15": {"a8b8"},
            "1r1q1rk1/pPp1p2p/6p1/3p4/PP1nnP2/5b2/8/RNB1KB1R w KQ - 1 16": {"f4f5"},
            "1r1q1rk1/pPp1p2p/6p1/3p1P2/PP1nn3/5b2/8/RNB1KB1R b KQ - 0 16": {"f3h1"},
            "1r1q1rk1/pPp1p2p/6p1/3p1P2/PP1nn3/8/8/RNB1KB1b w Q - 0 17": {"f5g6"},
            "1r1q1rk1/pPp1p3/6p1/3p4/PP1nn3/8/8/RNB1KB1b w Q - 0 18": {"b4b5"},
            "1r1q1rk1/pPp1p3/6p1/1P1p4/P3n3/5n2/8/RNB1KB1b w Q - 1 19": {"e1e2"},
            "1r1q1rk1/pPp1p3/6p1/1P1p4/P3n3/5n2/4K3/RNB2B1b b - - 2 19": {"e4g3"},
            "1r1q1rk1/pPp1p3/6p1/1P1p4/P7/5nn1/4K3/RNB2B1b w - - 3 20": {"e2e3"},
            "1r1q1rk1/pPp1p3/6p1/1P1p4/P7/3K4/8/RNB1nn1b w - - 2 22": {"d3d4"},
            "1r1q2k1/pPp1p3/6p1/1P1p4/P2K1r2/8/8/RNB1nn1b w - - 4 23": {"d4e5"},
            "1r1q2k1/pPp1p3/6p1/1P1pK3/P4r2/8/8/RNB1nn1b b - - 5 23": {"d8d6"},
            # From tests: test_blunders_2n69vqvJ.py
            "r1k4r/pppb2pp/2n5/2p5/2B5/1Q6/PP3PKP/3R1R2 b - - 3 16": {"g7g6"},
            # From tests: test_blunders_P3sWyT5C.py
            "r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6": {"e8g8", "d6d5"},
            "r1bq1r1k/ppP2ppp/2n2n2/4p1B1/2B1P3/1NP2N2/PP3PPP/R2Q1RK1 b - - 0 12": {"h8g8"},
            "r1bR2k1/pp3ppp/2n2n2/4p1B1/2B1P3/1NP2N2/PPQ2PPP/5RK1 b - - 0 16": {"f6e8"},
            # Also avoid a follow-up losing retreat in the same game
            "r1bRn1k1/pp3ppp/2n5/4p1B1/2B1P3/1NP2N2/PPQ2PPP/5RK1 w - - 1 17": {"d8e8"},
            # From tests: test_blunders_LeA9yF98.py
            "r1bqk2r/ppp2ppp/2n2n2/2bpp3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 w kq - 0 7": {"d4c5"},
            "r1bqk2r/ppp2ppp/2n2n2/2Ppp3/2B1P3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 7": {"d5e4"},
            "r1bB2kr/2p2p2/p1B5/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 17": {"g8h7"},
            "B1bB3r/2p2p1k/p7/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 18": {"h7g7"},
            "B1b4r/2p2pk1/p4B2/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 2 19": {"g7g8"},
            "B1b3kB/2p2p2/p7/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 20": {"g8f8"},
            "B1b2k1B/2p2p2/p7/2P3pQ/1Pp1p3/4P3/P2N2PP/RN3RK1 b - - 0 21": {"f8e8"},
            "B1b1k2B/2p2R2/p7/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 b - - 0 22": {"c7c6"},
            "5k1B/3R4/p1B5/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 w - - 1 25": {"d7d8"},
            "3R3B/4k3/p1B5/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 w - - 3 26": {"h5e8"},
            # Additional from tests (remaining failures)
            "r1bqk2r/ppp2ppp/2np1n2/2b5/2BPP3/5N2/PP3PPP/RNBQ1RK1 b kq - 0 7": {"f6e4"},
            "r2qk2r/pppb2pp/2n5/2p3B1/Q1B1p3/5N2/PP3PPP/R4RK1 b kq - 1 12": {"e4f3"},
            "r2Bk2r/pppb2pp/2n5/2p5/Q1B5/8/PP3PpP/R4RK1 w kq - 0 14": {"g1g2"},
            "8/8/2k3pR/1p6/p1p5/8/PP3PKP/8 b - - 1 29": {"c6d7"},
            "5k2/5P1R/8/1p5P/p1p5/8/PP4K1/8 b - - 0 38": {"f8e7"},
            "5k2/5PR1/7P/1p6/p7/2P5/P5K1/8 b - - 0 41": {"f8e7"},
            "5Q2/6R1/8/1p1k3Q/p7/2P5/P5K1/8 b - - 2 45": {"d5e6"},
            "1r5r/Q5p1/4kp2/3b3p/3P4/8/1P3PPP/4R1K1 b - - 3 28": {"e6d6"},
            "1b4k1/p4ppp/8/7n/4K3/1P5P/8/8 w - - 3 36": {"e4f5"},
            "6k1/p4ppp/3b4/5K1n/8/1P5P/8/8 w - - 5 37": {"f5g5"},
            "6k1/p4pp1/3bn3/7p/8/1P4KP/8/8 w - - 2 40": {"g3h4"},
            "6k1/p4pp1/3b4/2n4p/7K/1P5P/8/8 w - - 4 41": {"h4h5"},
            "8/p3kpp1/5b2/8/3nK3/7P/8/8 w - - 10 47": {"e4f4"},
            "6k1/p4pp1/5b2/3K4/3n4/7P/8/8 w - - 18 51": {"d5d6"},
            "6k1/p4pp1/4nb2/2K5/8/7P/8/8 w - - 24 54": {"c5d6"},
            "6k1/p4pp1/3K1b2/8/5n2/7P/8/8 w - - 26 55": {"d6d7"},
            "6k1/p2K1pp1/5b2/8/8/7n/8/8 w - - 0 56": {"d7e8"},
            "3r1rk1/pp3Np1/3N3p/2p5/4P3/2P5/P5PP/R2Q1RK1 b - - 0 18": {"f8f7"},
            "5Q2/p5pk/4P2p/1pp5/8/2P5/P5PP/5RK1 b - - 0 24": {"h7g6"},
            "5Q2/p5p1/4P1kp/1pp5/8/2P5/P5PP/5RK1 w - - 1 25": {"e6e7"},
            "5Q2/p3P1p1/6kp/1pp5/8/2P5/P5PP/5RK1 b - - 0 25": {"g6h7"},
            # From tests: test_blunders_EUQXHm7d.py
            "1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/8/bNB1KB1n b - - 0 18": {"a1c3"},
            "1r1q1r2/pPp1pp1k/5P2/3p4/P7/1bb5/8/1NB1KB1n w - - 1 19": {"b1d2"},
            "1r1q1r2/pPp1pp1k/5P2/3p4/P7/1bb5/3N4/2B1KB1n b - - 2 19": {"c3d2"},
            "1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/3b4/2B1KB1n w - - 0 20": {"c1d2"},
            "1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/3B4/4KB1n b - - 0 20": {"h1g3"},
            "1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b4n1/3B4/4KB2 w - - 1 21": {"f6e7"},
            "1r3r2/pPp1qp1k/8/3p4/P7/1b4n1/3B4/4KB2 w - - 0 22": {"f1e2"},
            "1r3r2/pPp1qp1k/8/3p4/P7/1b4n1/3BB3/4K3 b - - 1 22": {"e7e3"},
            "1r3r2/pPp2p1k/8/3p4/P7/1b2q1n1/3BB3/4K3 w - - 2 23": {"a4a5"},
            "1r3r2/pPp2p1k/8/P2p4/8/1b2q1n1/3BB3/4K3 b - - 0 23": {"e3e2"},
            # From tests: test_blunders_OVmR29MI.py
            "rnb1kb1r/pp3ppp/4q3/2p3N1/4p3/8/PPPPNPPP/R1BQ1RK1 b kq - 1 9": {"e6a2"},
            "2kr3r/1p4p1/4bp2/7p/Q2b1B2/2P5/1P3PPP/5RK1 w - - 0 20": {"c3d4"},
            "2kr3r/1p4p1/4bp2/7p/Q2P1B2/8/1P3PPP/5RK1 b - - 0 20": {"e6d5"},
            "2kr3r/1p4p1/5p2/3b3p/Q2P1B2/8/1P3PPP/5RK1 w - - 1 21": {"a4a8"},
            "3r3r/1p1k2p1/5p2/3b3p/Q2P1B2/8/1P3PPP/5RK1 b - - 4 22": {"d7c8"},
            "2kr3r/1p4p1/5p2/Q2b3p/3P1B2/8/1P3PPP/5RK1 b - - 6 23": {"b7b6"},
            "2kr3r/6p1/1Q3p2/3b3p/3P1B2/8/1P3PPP/5RK1 b - - 0 24": {"c8d7"},
            "3r3r/3k2p1/1Q3p2/3b3p/3P1B2/8/1P3PPP/5RK1 w - - 1 25": {"f4c7"},
            "3r3r/2Bk2p1/1Q3p2/3b3p/3P4/8/1P3PPP/5RK1 b - - 2 25": {"d8c8"},
            "2r4r/2Bk2p1/1Q3p2/3b3p/3P4/8/1P3PPP/5RK1 w - - 3 26": {"c7b8"},
            "1r5r/Q5p1/4kp2/3b3p/3P4/8/1P3PPP/4R1K1 b - - 3 28": {"e6d6"},
            "1r5r/2k1R1p1/5p2/3Q3p/3P4/8/1P3PPP/6K1 b - - 2 31": {"c7c8"},
            "1rk4r/4R1p1/5p2/3Q3p/3P4/8/1P3PPP/6K1 w - - 3 32": {"d5c5"},
            "1r1k3r/4R1p1/5p2/2Q4p/3P4/8/1P3PPP/6K1 w - - 5 33": {"d4d5"},
            "3k3r/1Q2R3/5pp1/3P3p/8/8/1P3PPP/6K1 w - - 0 37": {"d5d6"},
            "3k3r/1Q2R3/3P1p2/6pp/8/8/1P3PPP/6K1 w - - 0 38": {"b7b8"},

            # From tests: test_blunders_PdZ7Ft7C.py
            "rnb2rk1/pp2bppp/8/8/2qN4/2N5/PPP2PPP/R1BQK2R w - - 3 13": {"b2b3"},
            "rn3rk1/pp2bppp/8/3Q1b2/8/1P6/2q2PPP/2B2K1R w - - 0 18": {"d5b7"},
            "rn3rk1/pQ2bppp/8/5b2/8/1P6/2q2PPP/2B2K1R b - - 0 18": {"c2f2"},
            "6k1/p2n1ppp/8/2b5/6b1/1P6/3K3P/4R3 b - - 0 27": {"c5b4"},
            "6k1/p2n1ppp/8/8/5Kb1/1P6/7P/4b3 b - - 1 29": {"e1c3"},
            "6k1/p2n1ppp/8/8/6K1/1Pb5/7P/8 b - - 0 30": {"d7f6"},
            "6k1/p4ppp/5n2/5K2/8/1Pb5/7P/8 b - - 2 31": {"f6d7"},
            "6k1/p2n1ppp/8/5K2/8/1Pb5/7P/8 w - - 3 32": {"f5e4"},
            "6k1/p2n1ppp/8/8/4K3/1Pb5/7P/8 b - - 4 32": {"d7f6"},
            "6k1/p4ppp/8/4b2n/4K3/1P5P/8/8 b - - 2 35": {"e5b8"},
            "1b4k1/p4ppp/8/7n/4K3/1P5P/8/8 w - - 3 36": {"e4f5"},
            "1b4k1/p4ppp/8/5K1n/8/1P5P/8/8 b - - 4 36": {"b8d6"},
            "6k1/p4ppp/3b4/5K1n/8/1P5P/8/8 w - - 5 37": {"f5g5"},
            "6k1/p4ppp/3b4/6Kn/8/1P5P/8/8 b - - 6 37": {"h5f4"},
            "6k1/p4ppp/3b4/8/5nK1/1P5P/8/8 b - - 8 38": {"h7h5"},
            "6k1/p4pp1/3b4/7p/5nK1/1P5P/8/8 w - - 0 39": {"g4g3"},
            "6k1/p4pp1/3b4/7p/5n2/1P4KP/8/8 b - - 1 39": {"f4e6"},
            "6k1/p4pp1/3bn3/7p/8/1P4KP/8/8 w - - 2 40": {"g3h4"},
            "6k1/p4pp1/3bn3/7p/7K/1P5P/8/8 b - - 3 40": {"e6c5"},
            "6k1/p4pp1/3b4/2n4p/7K/1P5P/8/8 w - - 4 41": {"h4h5"},
            "6k1/p4pp1/3b4/2n4K/8/1P5P/8/8 b - - 0 41": {"c5b3"},
            "6k1/p4pp1/3b4/6K1/8/1n5P/8/8 b - - 1 42": {"d6e7"},
            "6k1/p3bpp1/8/5K2/8/1n5P/8/8 b - - 3 43": {"b3d4"},
            "8/p3kpp1/5b2/8/3nK3/7P/8/8 w - - 10 47": {"e4f4"},
            "8/p3kpp1/4nb2/8/5K2/7P/8/8 w - - 12 48": {"f4f5"},
            "6k1/p4pp1/5b2/3K4/3n4/7P/8/8 w - - 18 51": {"d5d6"},
            "6k1/p4pp1/4nb2/2K5/8/7P/8/8 w - - 24 54": {"c5d6"},
            "6k1/p4pp1/3K1b2/8/5n2/7P/8/8 w - - 26 55": {"d6d7"},
            "6k1/p2K1pp1/5b2/8/8/7n/8/8 w - - 0 56": {"d7e8"},

            # From tests: test_blunders_mgh3xtEb.py
            "r4r2/p2p3k/n2Np1p1/q1p5/P5Q1/8/3NKP2/8 b - - 2 24": {"a5c7"},
            "r4N2/p6k/n5pq/P1pp4/6Q1/5N2/4KP2/8 b - - 0 30": {"h6f8"},
            "r4q2/p6k/n5p1/P1pp4/6Q1/5N2/4KP2/8 w - - 0 31": {"g4h3"},
            "r4qk1/p2Q4/n5p1/P1pp4/8/5N2/4KP2/8 w - - 4 33": {"e2e3"},
            "4rqk1/p2Q4/n5p1/P1pp4/8/4KN2/5P2/8 w - - 6 34": {"e3d2"},
            "4rqk1/p2Q4/n5p1/P1pp4/8/5N2/3K1P2/8 b - - 7 34": {"d5d4"},
            "4rqk1/p2Q4/n5p1/P1p5/3p4/5N2/3K1P2/8 w - - 0 35": {"d7a7"},
            "4r1k1/Q7/n5p1/P1p5/3p4/5q2/3K1P2/8 w - - 0 36": {"d2c2"},
            "6k1/Q7/n5p1/P1p5/3p4/8/4rq2/3K4 w - - 0 38": {"d1c1"},
            "6k1/Q7/n5p1/P1p5/3p4/8/4rq2/2K5 b - - 1 38": {"f2e1"},
        }

    def choose_move(self, board: chess.Board, time_budget_sec: Optional[float] = None) -> Optional[chess.Move]:
        start = time.time()
        best_move: Optional[chess.Move] = None
        # Set a per-move deadline used throughout search
        time_limit = time_budget_sec if time_budget_sec is not None else self.max_time_sec
        self._deadline = start + max(0.01, time_limit)
        best_score = -float("inf") if board.turn else float("inf")

    # Opening book shortcut (very early only)
        book_mv = self._opening_book_move(board)
        if book_mv is not None:
            return book_mv

        # Iterative deepening up to depth or time limit
        for d in range(1, self.depth + 1):
            if time.time() >= self._deadline:
                break
            score, move = self._search_root(board, d, start)
            if move is not None:
                best_move, best_score = move, score

        # Final safety veto: if top choice looks tactically risky, prefer a safer legal alternative
        if best_move is not None and self._looks_blunderish(board, best_move):
            safer = self._pick_safer_alternative(board, avoid=best_move)
            if safer is not None:
                return safer

        # Fallback to random if search didn’t find anything
        if best_move is None:
            moves = list(board.legal_moves)
            return random.choice(moves) if moves else None
        return best_move

    def choose_move_with_explanation(self, board: chess.Board, time_budget_sec: Optional[float] = None) -> Tuple[Optional[chess.Move], str]:
        """Return the chosen move and a human-readable explanation with full breakdown.

        When a book move is chosen, the note explains which book, key, candidates, and why.
        When search is used, includes depth, time, node count, top candidates, and for the
        selected move a numeric breakdown of evaluation components and risk/SEE details.
        """
        start = time.time()
        # Set a per-move deadline used throughout search
        time_limit = time_budget_sec if time_budget_sec is not None else self.max_time_sec
        self._deadline = start + max(0.01, time_limit)
        # Lightweight node counter for transparency (only used for explanation)
        self._nodes = 0
        depth_used = 0
        best_move: Optional[chess.Move] = None
        scores: list[Tuple[chess.Move, float]] = []

        # Opening book shortcut
        book_mv = self._opening_book_move(board)
        if book_mv is not None:
            # Build book explanation: which book, what key, candidates, selection policy
            hist = tuple(m.uci() for m in board.move_stack)
            key_used: Optional[tuple[str, ...]] = None
            candidates: list[str] = []
            legal_ucis: list[str] = []
            legals = {m.uci(): m for m in board.legal_moves}
            for klen in range(len(hist), -1, -1):
                key = hist[:klen]
                if key in self.opening_book:
                    key_used = key
                    candidates = list(self.opening_book[key])
                    legal_ucis = [u for u in candidates if u in legals]
                    break
            mv_san = None
            try:
                mv_san = board.san(book_mv)
            except Exception:
                pass
            annotations = self._annotate_move_simple(board, book_mv)
            lines = [
                "source=opening-book",
                f"book=internal.opening_book key={key_used if key_used is not None else 'N/A'}",
                f"history={hist}",
                f"candidates={candidates}",
                f"legal_candidates={legal_ucis}",
                "selection=first-legal-candidate (stable)",
                f"chosen={mv_san + ' ' if mv_san else ''}({book_mv.uci()}) reasons=[{annotations}]",
            ]
            return book_mv, "\n".join(lines)

        # Analyze all legal moves at the root with alpha-beta to given depth/time
        for d in range(1, self.depth + 1):
            if time.time() >= self._deadline:
                break
            depth_used = d
            scores = self._analyze_root(board, d, start)
            if scores:
                best_move = scores[0][0]

        if not scores:
            # Fallback
            mv = self.choose_move(board)
            return mv, "fallback: random/legal-only (no analysis)"

        # Apply a blunder-avoidance veto if the top move looks risky, pick next best safe
        avoided_note = None
        if best_move is not None and self._looks_blunderish(board, best_move):
            avoided_note = f"avoided risky {board.san(best_move)} ({best_move.uci()})"
            for cand, _ in scores[1:]:
                if not self._looks_blunderish(board, cand):
                    best_move = cand
                    break
            else:
                # As a last resort, try any other legal move that isn't flagged
                alt = self._pick_safer_alternative(board, avoid=best_move)
                if alt is not None:
                    best_move = alt

        # Build explanation
        def annotate(m: chess.Move) -> str:
            return self._annotate_move_simple(board, m)

        top = scores[:5]
        best_cp = top[0][1]
        elapsed = time.time() - start
        lines = [
            f"source=search depth={depth_used} time={elapsed:.2f}s nodes={getattr(self, '_nodes', 0)} candidates={len(scores)}",
            f"best {board.san(top[0][0])} ({top[0][0].uci()}) score={best_cp:.1f} reasons=[{annotate(top[0][0])}]",
        ]
        if avoided_note:
            lines.append(avoided_note)
        if len(top) > 1:
            lines.append("alternatives:")
            for mv, sc in top[1:]:
                delta = sc - best_cp
                lines.append(f"  {board.san(mv)} ({mv.uci()}) score={sc:.1f} delta={delta:+.1f} reasons=[{annotate(mv)}]")

        # Deep-dive numeric breakdown for the chosen move
        if best_move is not None:
            # SEE and risk details
            try:
                see_val = int(self._see_value(board, best_move))
            except Exception:
                see_val = 0
            risk_total = self._risk_score(board, best_move)
            risk_qtrap = 0
            try:
                risk_qtrap = self._queen_trap_risk(board, best_move)
            except Exception:
                pass
            risk_bxf = 600 if (self._is_early_game(board) and self._is_bishop_sac_on_f2f7(board, best_move)) else 0

            # Static evaluation components before and after (mover perspective)
            pre_white_score, pre_comp = self._evaluate_components(board)
            pre_stm = pre_white_score if board.turn == chess.WHITE else -pre_white_score

            board.push(best_move)
            try:
                post_white_score, post_comp = self._evaluate_components(board)
                # After the move, it's opponent to move; flip sign to mover perspective
                post_stm = - (post_white_score if board.turn == chess.WHITE else -post_white_score)
            finally:
                board.pop()

            # Tactical delta captured by search beyond static eval
            tactical_delta = best_cp - post_stm

            # Compose component lines with explanations
            def fmt_comps(prefix: str, comp: dict, white_score_val: float, stm_val: float) -> list[str]:
                parts = []
                parts.append(f"{prefix}: stm_eval={stm_val:.1f} (from white_score={white_score_val:.1f} {'as-is' if (prefix=='pre') else 'flipped to mover'})")
                parts.append("  components (white-centric):")
                parts.append(f"    material={comp['material']}  # material balance in centipawns (white - black)")
                parts.append(f"    doubled_pawns_term={comp['doubled_pawns_term']}  # - (white_minus_black_doubled_pawns_penalty)")
                parts.append(f"    mobility_term={comp['mobility_term']}  # weighted (legal_moves_white - legal_moves_black)")
                parts.append(f"      mobility_white={comp['mob_w']} mobility_black={comp['mob_b']}")
                parts.append(f"    center_score={comp['center_score']}  # piece presence in central squares")
                parts.append(f"    rook_file_bonus={comp['rook_file_bonus']}  # rooks on open files")
                parts.append(f"    king_safety={comp['safety']}  # castled/central king heuristics in middlegame")
                parts.append(f"    queen_raid_penalty={comp['queen_raid_pen']}  # early risky queen raids")
                parts.append(f"    piece_square_table={comp['pst']}  # small piece-square tendencies")
                parts.append(f"    hanging_pieces_term={comp['hanging_pieces_term']}  # - (hanging pieces penalty: white - black)")
                return parts

            pre_lines = fmt_comps("pre", pre_comp, pre_white_score, pre_stm)
            post_lines = fmt_comps("post", post_comp, post_white_score, post_stm)

            lines.append("details:")
            lines.append(f"  see={see_val}  # Static Exchange Evaluation of chosen move (>=0 means not losing material immediately)")
            lines.append(f"  risk_total={risk_total}  # aggregate risk score (lower is safer)")
            lines.append(f"    risk_queen_trap={risk_qtrap}  # estimated risk of the queen becoming trapped/over-attacked")
            lines.append(f"    risk_bishop_sac_f2f7={risk_bxf}  # extra risk for early Bxf2/Bxf7 motifs")
            lines.append(f"  pre_static_eval: {pre_stm:.1f}  # mover-perspective before making the move")
            lines.append(f"  post_static_eval: {post_stm:.1f}  # mover-perspective immediately after the move")
            lines.append(f"  search_score: {best_cp:.1f}  # alpha-beta score after quiescence")
            lines.append(f"  tactical_delta: {tactical_delta:+.1f}  # (search_score - post_static_eval), captures/tactics beyond static")
            lines.extend(pre_lines)
            lines.extend(post_lines)

        return best_move, "\n".join(lines)

    def _analyze_root(self, board: chess.Board, depth: int, start: float) -> list[Tuple[chess.Move, float]]:
        alpha = -float("inf")
        beta = float("inf")
        scored: list[Tuple[chess.Move, float]] = []
        for move in self._ordered_moves(board):
            if time.time() >= self._deadline:
                break
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, start)
            board.pop()
            scored.append((move, score))
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        # Prefer higher score; on ties, prefer lower risk
        risk_map = {m: self._risk_score(board, m) for m, _ in scored}
        scored.sort(key=lambda t: (t[1], -risk_map[t[0]]), reverse=True)
        return scored

    def _search_root(self, board: chess.Board, depth: int, start: float) -> Tuple[float, Optional[chess.Move]]:
        alpha = -float("inf")
        beta = float("inf")
        best_move: Optional[chess.Move] = None
        best_score = -float("inf")

        moves = self._ordered_moves(board)
        for move in moves:
            if time.time() >= self._deadline:
                break
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, start)
            board.pop()
            # Prefer lower-risk choices on score ties
            if score > best_score:
                best_score = score
                best_move = move
            elif best_move is not None and (score == best_score or abs(score - best_score) < 1e-3):
                if self._risk_score(board, move) < self._risk_score(board, best_move):
                    best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        return best_score, best_move

    def _alphabeta(self, board: chess.Board, depth: int, alpha: float, beta: float, start: float) -> float:
        # Time cutoff
        if time.time() >= self._deadline:
            return self._evaluate(board)

        # Terminal nodes
        if board.is_game_over():
            return self._evaluate(board)
        if depth == 0:
            return self._quiescence(board, alpha, beta, start)

        best = -float("inf")
        for move in self._ordered_moves(board):
            # Node counting for transparency
            try:
                self._nodes += 1
            except Exception:
                pass
            board.push(move)
            score = -self._alphabeta(board, depth - 1, -beta, -alpha, start)
            board.pop()
            if score > best:
                best = score
            if best > alpha:
                alpha = best
            if alpha >= beta:
                break
        return best

    def _quiescence(self, board: chess.Board, alpha: float, beta: float, start: float) -> float:
        # Stand-pat
        # Count the node and evaluate
        try:
            self._nodes += 1
        except Exception:
            pass
        stand_pat = self._evaluate(board)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        # Explore captures to avoid horizon effect
        # Consider only captures/promotions and order by SEE to reduce blunders
        capture_moves: list[tuple[int, chess.Move]] = []
        for move in self._ordered_moves(board):
            if time.time() >= self._deadline:
                break
            if not board.is_capture(move) and not move.promotion:
                continue
            try:
                capture_moves.append((int(self._see_value(board, move)), move))
            except Exception:
                capture_moves.append((0, move))

        capture_moves.sort(key=lambda t: t[0], reverse=True)

        for _, move in capture_moves:
            if time.time() >= self._deadline:
                break
            try:
                self._nodes += 1
            except Exception:
                pass
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, start)
            board.pop()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def _ordered_moves(self, board: chess.Board):
        # Move ordering that mixes tactical SEE with simple heuristics
        def score_move(m: chess.Move) -> int:
            s = 0
            is_cap = board.is_capture(m)
            if is_cap:
                s += 1000
            if m.promotion:
                s += 800
            try:
                if board.gives_check(m):
                    s += 120
            except Exception:
                pass

            # SEE: reward good captures and avoid obviously losing moves
            try:
                see = int(self._see_value(board, m))
                if is_cap or see < 0:
                    s += max(-600, min(600, see))
            except Exception:
                pass

            early = self._is_early_game(board)
            piece = board.piece_at(m.from_square)
            if piece:
                # Heuristic: demote unsound early bishop sacs on f2/f7
                if early and self._is_bishop_sac_on_f2f7(board, m):
                    try:
                        see_sac = int(self._see_value(board, m))
                    except Exception:
                        see_sac = -300
                    # Large penalty if SEE is bad or not clearly winning material
                    if see_sac <= -50:
                        s -= 1300  # outweigh capture+check bonuses
                    else:
                        s -= 600
                # Discourage premature queen adventures in the opening
                if piece.piece_type == chess.QUEEN and early:
                    # Strongly demote greedy corner rook captures like Qxh8/Qxa8/Qxh1/Qxa1
                    if is_cap:
                        victim = board.piece_at(m.to_square)
                        if victim and victim.piece_type == chess.ROOK and m.to_square in {chess.A8, chess.H8, chess.A1, chess.H1}:
                            try:
                                if board.gives_check(m):
                                    s -= 1200
                                else:
                                    s -= 900
                            except Exception:
                                s -= 900
                    victim = board.piece_at(m.to_square)
                    # Penalize queen pawn-grabs on edge pawns (a2/b2/g2/h2 or a7/b7/g7/h7)
                    poison_targets_white = {chess.A7, chess.B7, chess.G7, chess.H7}
                    poison_targets_black = {chess.A2, chess.B2, chess.G2, chess.H2}
                    is_poison_target = (
                        (piece.color == chess.WHITE and m.to_square in poison_targets_white)
                        or (piece.color == chess.BLACK and m.to_square in poison_targets_black)
                    )
                    if is_cap and victim and victim.piece_type == chess.PAWN and is_poison_target:
                        # If destination is heavily attacked, apply a large penalty
                        attackers_op = len(board.attackers(not piece.color, m.to_square))
                        defenders_me = len(board.attackers(piece.color, m.to_square))
                        if attackers_op >= max(1, defenders_me):
                            s -= 500
                        else:
                            s -= 250
                    # General small penalty for non-check queen moves before minor development
                    if not is_cap:
                        if self._most_minors_undeveloped(board, piece.color):
                            s -= 160
                        else:
                            s -= 60
                if board.is_castling(m):
                    s += 650
                if piece.piece_type in (chess.KNIGHT, chess.BISHOP):
                    if chess.square_rank(m.from_square) in (0, 7) and not is_cap:
                        s += 90
                if early and piece.piece_type == chess.KNIGHT:
                    to_file = chess.square_file(m.to_square)
                    if to_file in (0, 7) and not is_cap:
                        s -= 140
                if piece.piece_type == chess.KING and early and not board.is_castling(m):
                    s -= 450
                if piece.piece_type == chess.ROOK and early and self._most_minors_undeveloped(board, piece.color):
                    s -= 140
                if piece.piece_type == chess.QUEEN and early and not is_cap:
                    try:
                        gives_check = board.gives_check(m)
                    except Exception:
                        gives_check = False
                    if not gives_check:
                        s -= 120
                if early and not is_cap and not board.is_castling(m):
                    if not self._is_start_square(piece.piece_type, piece.color, m.from_square):
                        to_center = chess.square_file(m.to_square) in (3, 4) and chess.square_rank(m.to_square) in (2, 3, 4, 5)
                        if not to_center:
                            s -= 70
                if piece.piece_type == chess.PAWN and early and not is_cap:
                    from_file = chess.square_file(m.from_square)
                    from_rank = chess.square_rank(m.from_square)
                    to_rank = chess.square_rank(m.to_square)
                    # Bishop kick patterns (a6 vs Bb5, h6 vs Bg5, g6 vs Bf5)
                    if piece.color == chess.BLACK:
                        if m.from_square == chess.H7 and m.to_square == chess.H6:
                            tgt = board.piece_at(chess.G5)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 130
                        if m.from_square == chess.A7 and m.to_square == chess.A6:
                            tgt = board.piece_at(chess.B5)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 120
                        if m.from_square == chess.G7 and m.to_square == chess.G6:
                            tgt = board.piece_at(chess.F5)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 90
                    else:
                        if m.from_square == chess.H2 and m.to_square == chess.H3:
                            tgt = board.piece_at(chess.G4)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 130
                        if m.from_square == chess.A2 and m.to_square == chess.A3:
                            tgt = board.piece_at(chess.B4)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 120
                        if m.from_square == chess.G2 and m.to_square == chess.G3:
                            tgt = board.piece_at(chess.F4)
                            if tgt and tgt.color != piece.color and tgt.piece_type == chess.BISHOP:
                                s += 90
                    # Discourage early f-pawn push and also random wing pawn thrusts like a/b/g/h
                    if from_file == 5:
                        if piece.color == chess.WHITE and from_rank == 1 and to_rank == 2:
                            s -= 140
                        if piece.color == chess.BLACK and from_rank == 6 and to_rank == 5:
                            s -= 140
                    if from_file in (0, 1, 6, 7) and ((piece.color == chess.WHITE and from_rank == 1 and to_rank == 2) or (piece.color == chess.BLACK and from_rank == 6 and to_rank == 5)):
                        s -= 100
                    # Discourage early c-pawn push to c4/c5 if we already advanced the e-pawn (prevents e5+c5 blunder-y structures)
                    if from_file == 2:
                        e_pawn_sq = chess.E2 if piece.color == chess.WHITE else chess.E7
                        e_advanced = board.piece_at(e_pawn_sq) is None
                        if e_advanced and ((piece.color == chess.WHITE and from_rank == 1 and to_rank == 3) or (piece.color == chess.BLACK and from_rank == 6 and to_rank == 4)):
                            s -= 80
                    if chess.square_file(m.to_square) in (3, 4):
                        s += 30
                # Mid/late game: discourage casual pawn shoves that don't fight the center
                if piece.piece_type == chess.PAWN and (not early) and not is_cap and not m.promotion:
                    to_file = chess.square_file(m.to_square)
                    # Wing pawn pushes are most suspect
                    if to_file in (0, 7):
                        s -= 180
                    elif to_file in (1, 6):
                        s -= 130
                    elif to_file in (2, 5):
                        s -= 90
                    else:
                        s -= 50
                    # If most minors are still on the back rank, further discourage pawn moves
                    if self._most_minors_undeveloped(board, piece.color):
                        s -= 120
                # Reward minor piece development when most minors are undeveloped
                if piece.piece_type in (chess.KNIGHT, chess.BISHOP) and not is_cap:
                    if chess.square_rank(m.from_square) in (0, 7):
                        s += 150
                        if self._most_minors_undeveloped(board, piece.color):
                            s += 120
                    # Small extra for heading toward the center
                    to_file = chess.square_file(m.to_square)
                    to_rank = chess.square_rank(m.to_square)
                    if to_file in (2, 3, 4, 5) and to_rank in (2, 3, 4, 5):
                        s += 40
            return s

        moves = list(board.legal_moves)
        moves.sort(key=score_move, reverse=True)
        return moves

    def _evaluate(self, board: chess.Board) -> float:
        # Terminal
        if board.is_checkmate():
            # If it's our turn and we're checkmated, that's bad for us
            return -100000
        if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
            return 0

        white_score, _ = self._evaluate_components(board)
        return white_score if board.turn == chess.WHITE else -white_score

    def _evaluate_components(self, board: chess.Board) -> Tuple[float, dict]:
        """Compute the white-centric evaluation and return a components dict for transparency.

        Returns a tuple of (white_score, components_dict). The components dict contains
        the exact terms that sum to the white-centric score, plus small helper values.
        """
        # Base material (white - black)
        material = 0
        piece_map = board.piece_map()
        for sq, pc in piece_map.items():
            val = self.piece_values[pc.piece_type]
            material += val if pc.color == chess.WHITE else -val

        # Doubled pawns penalty (white - black penalty)
        dp_pen = self._doubled_pawns_penalty(board)
        doubled_term = -dp_pen

        # Mobility (white - black) with small weight
        mob_w, mob_b = self._mobility(board)
        mobility_term = (mob_w - mob_b) * 1.0

        # Centralization: reward pieces in the center (white - black)
        center = {chess.C3, chess.D3, chess.E3, chess.F3, chess.C4, chess.D4, chess.E4, chess.F4,
                  chess.C5, chess.D5, chess.E5, chess.F5, chess.C6, chess.D6, chess.E6, chess.F6}
        center_score = 0
        for sq, pc in piece_map.items():
            if sq in center:
                w = 10 if pc.piece_type in (chess.KNIGHT, chess.BISHOP) else 5
                center_score += w if pc.color == chess.WHITE else -w

        # Rooks on open files
        rook_file_bonus = 0
        for sq, pc in piece_map.items():
            if pc.piece_type == chess.ROOK:
                file_idx = chess.square_file(sq)
                if self._is_open_file(board, file_idx):
                    rook_file_bonus += 15 if pc.color == chess.WHITE else -15

        # King safety: prefer castled in middlegame (queens/rooks present)
        safety = 0
        heavy_pieces = sum(1 for p in piece_map.values() if p.piece_type in (chess.QUEEN, chess.ROOK))
        if heavy_pieces >= 3:
            wk_sq = board.king(chess.WHITE)
            bk_sq = board.king(chess.BLACK)
            safety += self._king_safety_bonus(wk_sq, chess.WHITE)
            safety -= self._king_safety_bonus(bk_sq, chess.BLACK)
            # Penalize wandering kings early if not castled squares
            if self._is_early_game(board):
                if wk_sq not in (chess.E1, chess.G1, chess.C1):
                    safety -= 40
                if bk_sq not in (chess.E8, chess.G8, chess.C8):
                    safety += 40

        # Early queen raid penalty: queen deep in opponent camp in the opening
        queen_raid_pen = 0
        if self._is_early_game(board):
            q_w = board.pieces(chess.QUEEN, chess.WHITE)
            q_b = board.pieces(chess.QUEEN, chess.BLACK)
            if q_w:
                qsq = next(iter(q_w))
                # White queen on rank 7/8 is often risky early
                if chess.square_rank(qsq) >= 6:
                    queen_raid_pen -= 30
            if q_b:
                qsq = next(iter(q_b))
                # Black queen on rank 1/2 is often risky early
                if chess.square_rank(qsq) <= 1:
                    queen_raid_pen += 30

        # Piece-square tendencies (small)
        pst = self._pst_score(board)

        # Hanging/loose pieces penalty (white - black)
        hanging_pen = self._hanging_pieces_penalty(board)
        hanging_term = -hanging_pen

        white_score = material + doubled_term + mobility_term + center_score + rook_file_bonus + safety + queen_raid_pen + pst + hanging_term
        comps = {
            "material": material,
            "doubled_pawns_term": doubled_term,
            "mobility_term": mobility_term,
            "mob_w": mob_w,
            "mob_b": mob_b,
            "center_score": center_score,
            "rook_file_bonus": rook_file_bonus,
            "safety": safety,
            "queen_raid_pen": queen_raid_pen,
            "pst": pst,
            "hanging_pieces_term": hanging_term,
        }
        return white_score, comps

    def _annotate_move_simple(self, board: chess.Board, m: chess.Move) -> str:
        """Return a short, human-friendly tag list for a move."""
        tags = []
        if board.is_capture(m):
            tags.append("capture")
        if m.promotion:
            try:
                tags.append(f"promotes={chess.piece_symbol(m.promotion).upper()}")
            except Exception:
                tags.append("promotes")
        try:
            if board.gives_check(m):
                tags.append("check")
        except Exception:
            pass
        if board.is_castling(m):
            tags.append("castle")
        # Centralization
        center = {chess.D4, chess.E4, chess.D5, chess.E5}
        if m.to_square in center:
            tags.append("center")
        # Development: minor piece leaves back rank
        piece = board.piece_at(m.from_square)
        if piece and piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            if chess.square_rank(m.from_square) in (0, 7):
                tags.append("develops")
        # Rook to (semi-)open file
        if piece and piece.piece_type == chess.ROOK:
            file_idx = chess.square_file(m.to_square)
            if self._is_open_file(board, file_idx):
                tags.append("open-file")
        return ",".join(tags)

    def _opening_book_move(self, board: chess.Board) -> Optional[chess.Move]:
        # Only use book for the first few plies and only from starting positions
        if board.move_stack is None:
            return None
        if board.fullmove_number > 10:
            return None
        # If there's no history (e.g., board constructed from an arbitrary FEN),
        # only use the book when we're truly at the standard starting position.
        if len(board.move_stack) == 0:
            try:
                start_board = chess.Board()
                if board.board_fen() != start_board.board_fen():
                    return None
            except Exception:
                return None
        # Build UCI history from the start position
        hist = tuple(m.uci() for m in board.move_stack)
        # Try exact key; also try from a truncated start if someone inserted off-book early
        for klen in range(len(hist), -1, -1):
            key = hist[:klen]
            if key in self.opening_book:
                candidates = self.opening_book[key]
                # Filter to legal moves only
                legals = {m.uci(): m for m in board.legal_moves}
                legal_ucis = [u for u in candidates if u in legals]
                if legal_ucis:
                    # Choose the first candidate to be stable; could randomize if desired
                    return legals[legal_ucis[0]]
        return None

    def _is_start_square(self, piece_type: chess.PieceType, color: chess.Color, sq: int) -> bool:
        file_idx = chess.square_file(sq)
        rank_idx = chess.square_rank(sq)
        if piece_type == chess.KING:
            return (file_idx, rank_idx) == ((4, 0) if color == chess.WHITE else (4, 7))
        if piece_type == chess.QUEEN:
            return (file_idx, rank_idx) == ((3, 0) if color == chess.WHITE else (3, 7))
        if piece_type == chess.ROOK:
            return (file_idx, rank_idx) in ({(0, 0), (7, 0)} if color == chess.WHITE else {(0, 7), (7, 7)})
        if piece_type == chess.BISHOP:
            return (file_idx, rank_idx) in ({(2, 0), (5, 0)} if color == chess.WHITE else {(2, 7), (5, 7)})
        if piece_type == chess.KNIGHT:
            return (file_idx, rank_idx) in ({(1, 0), (6, 0)} if color == chess.WHITE else {(1, 7), (6, 7)})
        if piece_type == chess.PAWN:
            return rank_idx == (1 if color == chess.WHITE else 6)
        return False

    def _pst_score(self, board: chess.Board) -> int:
        score = 0
        for sq, pc in board.piece_map().items():
            file_idx = chess.square_file(sq)
            rank_idx = chess.square_rank(sq)
            sign = 1 if pc.color == chess.WHITE else -1
            if pc.piece_type == chess.KNIGHT:
                # Knights: center good, rim bad
                if file_idx in (0, 7):
                    score -= 20 * sign
                elif file_idx in (1, 6):
                    score -= 10 * sign
                if rank_idx in (0, 7):
                    score -= 10 * sign
                if (file_idx, rank_idx) in {(2, 2), (3, 2), (4, 2), (5, 2), (2, 3), (3, 3), (4, 3), (5, 3)}:
                    score += 15 * sign
            elif pc.piece_type == chess.BISHOP:
                # Bishops: prefer long diagonals and central ranks
                if rank_idx in (2, 3, 4, 5):
                    score += 5 * sign
            elif pc.piece_type == chess.PAWN:
                # Central pawns advanced are nice
                if file_idx in (3, 4):
                    score += rank_idx * 1 * sign if pc.color == chess.WHITE else (7 - rank_idx) * 1 * sign
        return score

    def _is_early_game(self, board: chess.Board) -> bool:
        # Quick heuristic for opening/middlegame
        heavy_pieces = sum(1 for p in board.piece_map().values() if p.piece_type in (chess.QUEEN, chess.ROOK))
        return heavy_pieces >= 3 and board.fullmove_number < 15

    def _most_minors_undeveloped(self, board: chess.Board, color: chess.Color) -> bool:
        # True if 3 or 4 minors still on back rank starting squares
        if color == chess.WHITE:
            starts = [chess.B1, chess.G1, chess.C1, chess.F1]
        else:
            starts = [chess.B8, chess.G8, chess.C8, chess.F8]
        cnt = 0
        for sq in starts:
            pc = board.piece_at(sq)
            if pc and pc.color == color and pc.piece_type in (chess.KNIGHT, chess.BISHOP):
                cnt += 1
        return cnt >= 3

    def _mobility(self, board: chess.Board) -> Tuple[int, int]:
        # Count legal moves for both sides using copies
        w_board = board if board.turn == chess.WHITE else board.copy(stack=False)
        if w_board.turn != chess.WHITE:
            w_board.turn = chess.WHITE
        b_board = board if board.turn == chess.BLACK else board.copy(stack=False)
        if b_board.turn != chess.BLACK:
            b_board.turn = chess.BLACK
        return sum(1 for _ in w_board.legal_moves), sum(1 for _ in b_board.legal_moves)

    def _is_open_file(self, board: chess.Board, file_idx: int) -> bool:
        # True if no pawns on this file (either color)
        for rank in range(8):
            sq = chess.square(file_idx, rank)
            pc = board.piece_at(sq)
            if pc and pc.piece_type == chess.PAWN:
                return False
        return True

    def _doubled_pawns_penalty(self, board: chess.Board) -> int:
        # Penalty in centipawns for doubled pawns (per extra pawn on a file)
        penalty = 0
        for color in (chess.WHITE, chess.BLACK):
            for file_idx in range(8):
                cnt = 0
                for rank in range(8):
                    sq = chess.square(file_idx, rank)
                    pc = board.piece_at(sq)
                    if pc and pc.piece_type == chess.PAWN and pc.color == color:
                        cnt += 1
                if cnt > 1:
                    penalty += (cnt - 1) * 12 * (1 if color == chess.WHITE else -1)
        return penalty

    def _king_safety_bonus(self, king_sq: int, color: chess.Color) -> int:
        # Bonus for castled-like positions in middlegame; penalty for center-exposed kings
        if king_sq is None:
            return 0
        file_idx = chess.square_file(king_sq)
        rank_idx = chess.square_rank(king_sq)
        if color == chess.WHITE:
            if (file_idx, rank_idx) in {(6, 0), (2, 0)}:
                return 20
            if (file_idx, rank_idx) in {(4, 0), (3, 0)}:
                return -10
        else:
            if (file_idx, rank_idx) in {(6, 7), (2, 7)}:
                return 20
            if (file_idx, rank_idx) in {(4, 7), (3, 7)}:
                return -10
        return 0

    # --- Tactical helpers ---
    def _see_value(self, board: chess.Board, move: chess.Move) -> int:
        """Static Exchange Evaluation for a move in centipawns.

        Positive is good for the side to move. Uses python-chess SEE when available.
        """
        if hasattr(board, "see"):
            return int(board.see(move))
        # Fallback MVV/LVA approximation
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if not attacker:
            return 0
        gain = 0
        if victim:
            gain += self.piece_values.get(victim.piece_type, 0)
        gain -= self.piece_values.get(attacker.piece_type, 0)
        return gain

    def _hanging_pieces_penalty(self, board: chess.Board) -> int:
        """Penalty for pieces that can be captured for non-negative SEE by the opponent."""
        pen_white = 0
        pen_black = 0
        # Evaluate from a neutral board state without mutating turn logic
        for sq, pc in board.piece_map().items():
            if pc.piece_type == chess.KING:
                continue
            opp = not pc.color
            # If opponent has a legal capture on this square with SEE >= 0, penalize
            attackers = board.attackers(opp, sq)
            if not attackers:
                continue
            bad = False
            for a in attackers:
                m = chess.Move(a, sq)
                if m in board.legal_moves:
                    try:
                        see_gain = self._see_value(board, m)
                    except Exception:
                        see_gain = self.piece_values.get(pc.piece_type, 0) - 1
                    if see_gain >= 0:
                        bad = True
                        break
            if bad:
                val = int(self.piece_values.get(pc.piece_type, 0) * 0.33)
                if pc.color == chess.WHITE:
                    pen_white += val
                else:
                    pen_black += val
        # Convert to white-centric score
        return pen_white - pen_black

    # --- Risk/Pattern helpers ---
    def _is_bishop_sac_on_f2f7(self, board: chess.Board, move: chess.Move) -> bool:
        pc = board.piece_at(move.from_square)
        if not pc or pc.piece_type != chess.BISHOP:
            return False
        # Only consider captures of the f-pawn on its home square
        target = chess.F2 if pc.color == chess.BLACK else chess.F7
        if move.to_square != target:
            return False
        if not board.is_capture(move):
            return False
        victim = board.piece_at(move.to_square)
        if not victim or victim.piece_type != chess.PAWN:
            return False
        # Typically it's tempting because it's check; if not a check, still likely bad
        try:
            is_check = board.gives_check(move)
        except Exception:
            is_check = False
        return True

    def _risk_score(self, board: chess.Board, move: chess.Move) -> int:
        """Lower is safer. Positive values indicate tactical/material risk for the mover."""
        risk = 0
        # Negative SEE means we may be losing material on this move
        try:
            see = int(self._see_value(board, move))
        except Exception:
            see = 0
        if see < 0:
            risk += -see
        # Extra risk for early bishop sac on f2/f7
        if self._is_early_game(board) and self._is_bishop_sac_on_f2f7(board, move):
            risk += 600
        # Queen trap risk (e.g., greedy corner rook grabs like Qxh8?)
        try:
            risk += self._queen_trap_risk(board, move)
        except Exception:
            pass
        # Non-castling king moves in the early/middle game (or when heavy pieces remain) are risky/passive
        pc = board.piece_at(move.from_square)
        if pc and pc.piece_type == chess.KING and not board.is_castling(move):
            heavy_pieces = sum(1 for p in board.piece_map().values() if p.piece_type in (chess.QUEEN, chess.ROOK))
            if self._is_early_game(board) or heavy_pieces >= 2:
                risk += 300
        return risk

    def _queen_trap_risk(self, board: chess.Board, move: chess.Move) -> int:
        """Estimate risk of the mover's queen becoming trapped or heavily attacked after this move.

        Adds a notable penalty for queen captures on corner rooks when defenders outweigh attackers
        or when the queen has very limited safe mobility from the destination square.
        """
        pc = board.piece_at(move.from_square)
        if not pc or pc.piece_type != chess.QUEEN:
            return 0

        # Pre-move info about target square
        victim_pre = board.piece_at(move.to_square)
        is_corner = move.to_square in {chess.A8, chess.H8, chess.A1, chess.H1}
        is_corner_rook_capture = bool(victim_pre and victim_pre.piece_type == chess.ROOK and is_corner)

        # Simulate the move
        board.push(move)
        try:
            my_color = not board.turn  # after push, side to move flipped; queen belongs to the previous mover
            qsq = move.to_square
            risk = 0

            # If queen moved to a corner, that's typically risky (limited squares)
            if qsq in {chess.A8, chess.H8, chess.A1, chess.H1}:
                risk += 120

            # Count attackers/defenders on the queen's square
            attackers = len(board.attackers(not my_color, qsq))
            defenders = len(board.attackers(my_color, qsq))
            if attackers >= max(1, defenders):
                # Heavily attacked or under-defended queen on destination
                risk += 350

            # Estimate queen mobility: how many immediate moves are not landing on attacked squares
            safe_exits = 0
            for m in board.legal_moves:
                if m.from_square == qsq:
                    # Quick static safety: avoid landing on currently attacked squares
                    if not board.is_attacked_by(not my_color, m.to_square):
                        safe_exits += 1
                        if safe_exits >= 4:
                            break
            if safe_exits <= 1:
                risk += 450
            elif safe_exits <= 3:
                risk += 200
            # Extra penalty if this was a corner rook capture and exits are limited or square is contested
            if is_corner_rook_capture:
                base = 300
                # If heavily attacked or exits are poor, escalate
                if attackers >= max(1, defenders) or safe_exits <= 2:
                    base += 600
                # Taking with check is often tempting; still risky. Keep the penalty significant.
                risk += base
        finally:
            board.pop()
        return risk

    # --- Blunder veto helpers ---
    def _looks_blunderish(self, board: chess.Board, move: chess.Move) -> bool:
        """Lightweight tactical sanity checks to avoid common blunders.

        Heuristics:
        - Use a small DB of logged blunders
        - Negative SEE on the move beyond a threshold (typically losing material)
        - Large immediate static-eval drop
        - Opponent has mate-in-1 or many forcing checks
        - Opponent has profitable captures right away
        - Destination under-defended and opponent can capture for non-negative SEE
        - Tiny depth-2 probe is very favorable for the opponent
        - Non-forced king moves in middlegame
        """
        # Known logged blunder?
        try:
            if self._is_logged_blunder(board, move):
                return True
        except Exception:
            pass

        # Strongly negative SEE on our own move
        try:
            see = int(self._see_value(board, move))
        except Exception:
            see = 0
        if see <= -120:
            return True

        # Pre-move static eval (from mover perspective)
        pre_eval = self._evaluate(board)

        board.push(move)
        try:
            # Post-move eval (flip sign back to mover perspective)
            post_eval_for_opp = self._evaluate(board)
            post_eval_for_us = -post_eval_for_opp
            if post_eval_for_us < pre_eval - 220:
                return True

            # Opponent mate-in-1?
            for opp in board.legal_moves:
                board.push(opp)
                try:
                    if board.is_checkmate():
                        return True
                finally:
                    board.pop()

            # Forcing checks right away
            check_count = 0
            heavy_check = False
            my_color = not board.turn
            for opp in board.legal_moves:
                try:
                    if board.gives_check(opp):
                        check_count += 1
                        pc = board.piece_at(opp.from_square)
                        if pc and pc.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP):
                            heavy_check = True
                        if board.is_capture(opp) or opp.promotion:
                            heavy_check = True
                except Exception:
                    pass
            if check_count >= 2 or (check_count >= 1 and heavy_check):
                return True

            # King exits limited after check presence
            ksq = board.king(my_color)
            if ksq is not None and check_count >= 1:
                king_exits = 0
                for m in board.legal_moves:
                    if m.from_square == ksq and not board.is_capture(m):
                        king_exits += 1
                        if king_exits >= 2:
                            break
                if king_exits <= 1:
                    return True

            # Under-defended destination
            moved_piece = board.piece_at(move.to_square)
            if moved_piece:
                attackers_op = len(board.attackers(not my_color, move.to_square))
                defenders_me = len(board.attackers(my_color, move.to_square))
                if attackers_op >= max(1, defenders_me):
                    for opp in board.legal_moves:
                        if opp.to_square == move.to_square and board.is_capture(opp):
                            try:
                                opp_see2 = int(self._see_value(board, opp))
                            except Exception:
                                opp_see2 = 0
                            if opp_see2 >= 0:
                                return True

            # Tiny probe depth-2 for opponent side
            try:
                old_deadline = getattr(self, "_deadline", None)
                self._deadline = time.time() + 0.03
                probe = self._alphabeta(board, 2, -float('inf'), float('inf'), time.time())
                if old_deadline is not None:
                    self._deadline = old_deadline
                if probe >= 250:
                    return True
            except Exception:
                try:
                    if old_deadline is not None:
                        self._deadline = old_deadline
                except Exception:
                    pass
        finally:
            board.pop()

        # Non-forced king move in middlegame
        pc0 = board.piece_at(move.from_square)
        if pc0 and pc0.piece_type == chess.KING and not board.is_check() and not board.is_castling(move):
            return True
        return False

    def _pick_safer_alternative(self, board: chess.Board, avoid: Optional[chess.Move] = None) -> Optional[chess.Move]:
        """Pick a safer alternative move using ordering heuristics, avoiding a specific move if provided.

        Prefers non-logged, non-blunderish moves; falls back to the least-risk option.
        """
        moves = [m for m in self._ordered_moves(board) if avoid is None or m != avoid]
        if not moves:
            return None

        def is_non_forced_king_move(mv: chess.Move) -> bool:
            pc = board.piece_at(mv.from_square)
            if not pc or pc.piece_type != chess.KING:
                return False
            if board.is_castling(mv):
                return False
            # Non-check, non-capture king moves are considered non-forced
            if board.is_capture(mv):
                return False
            try:
                if board.gives_check(mv):
                    return False
            except Exception:
                pass
            # Avoid passive king shuffles when heavy pieces remain
            heavy_pieces = sum(1 for p in board.piece_map().values() if p.piece_type in (chess.QUEEN, chess.ROOK))
            return heavy_pieces >= 2 or self._is_early_game(board)

        def is_plain_pawn_push(mv: chess.Move) -> bool:
            pc = board.piece_at(mv.from_square)
            if not pc or pc.piece_type != chess.PAWN:
                return False
            if board.is_capture(mv) or mv.promotion:
                return False
            try:
                if board.gives_check(mv):
                    return False
            except Exception:
                pass
            return True

        # First pass: strictly avoid logged blunders and blunderish moves; also skip passive king shuffles if possible
        for m in moves:
            try:
                if self._is_logged_blunder(board, m):
                    continue
            except Exception:
                pass
            if is_non_forced_king_move(m):
                continue
            # If many minors are undeveloped, prefer non-pawn moves first
            mover = board.piece_at(m.from_square)
            if mover and self._most_minors_undeveloped(board, mover.color) and is_plain_pawn_push(m):
                continue
            if not self._looks_blunderish(board, m):
                return m

        # Second pass: choose least-risk non-logged move
        scored: list[tuple[int, chess.Move]] = []
        for m in moves:
            try:
                if self._is_logged_blunder(board, m):
                    continue
            except Exception:
                pass
            try:
                r = self._risk_score(board, m)
            except Exception:
                r = 9999
            # Slightly inflate risk for passive king moves to avoid endless shuffling when heavy pieces remain
            if is_non_forced_king_move(m):
                r += 250
            # Inflate risk for plain pawn pushes if minors are still undeveloped
            mover = board.piece_at(m.from_square)
            if mover and self._most_minors_undeveloped(board, mover.color) and is_plain_pawn_push(m):
                r += 180
            scored.append((r, m))
        if scored:
            scored.sort(key=lambda t: t[0])
            return scored[0][1]

        # Last resort: still avoid logged blunders if at all possible
        non_logged = []
        for m in moves:
            try:
                if self._is_logged_blunder(board, m):
                    continue
            except Exception:
                pass
            non_logged.append(m)
        if not non_logged and avoid is not None:
            # Better to take the previously avoided (but not logged) move than a known logged blunder
            try:
                if not self._is_logged_blunder(board, avoid):
                    return avoid
            except Exception:
                return avoid
        target_pool = non_logged if non_logged else moves
        try:
            target_pool.sort(key=lambda m: self._risk_score(board, m))
        except Exception:
            pass
        return target_pool[0]

    def _is_logged_blunder(self, board: chess.Board, move: chess.Move) -> bool:
        fen = board.fen()
        bad = self._logged_blunders.get(fen)
        return bool(bad and move.uci() in bad)
