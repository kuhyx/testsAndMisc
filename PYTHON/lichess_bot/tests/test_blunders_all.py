import os
import sys
import chess
import pytest
import re


# Ensure repo root is importable when running pytest directly
# Go up to the workspace root (tests -> lichess_bot -> PYTHON -> repo root)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PYTHON.lichess_bot.engine import RandomEngine  # noqa: E402

# Consolidated blunder cases from all per-game test files
BLUNDER_CASES = [
    ("r2q1rk1/pp2ppbp/2np2p1/2p3P1/2P5/5b1P/P4P2/R1B1KB1R w KQ - 1 15", "e1d2", "ply29_W_e1d2_best_c1d2"),
    ("r2q1rk1/pp2ppbp/2np2p1/2p3P1/2P5/7P/P2K1P2/R1B2B1b w - - 0 16", "f2f3", "ply31_W_f2f3_best_d2e1"),
    ("r2q1rk1/pp2ppbp/2np2p1/2p3P1/2P5/4Kb1P/P7/R1B2B2 b - - 1 17", "c6d4", "ply34_B_c6d4_best_d8a5"),
    ("r2q1rk1/pp2ppbp/3p2p1/2p3P1/2Pn4/4Kb1P/P7/R1B2B2 w - - 2 18", "e3d3", "ply35_W_e3d3_best_c1b2"),
    ("r2q1rk1/pp3pbp/3p2p1/2p1p1P1/2Pn4/3K1b1P/P7/R1B2B2 w - - 0 19", "d3e3", "ply37_W_d3e3_best_h3h4"),
    ("r2q1rk1/pp3pbp/3p2p1/2p3P1/2Pnp3/4Kb1P/P7/R1B2B2 w - - 0 20", "e3f4", "ply39_W_e3f4_best_e3f2"),
    ("r4rk1/pp3p1p/3p2p1/2p1b1q1/2Pn4/4pb1P/P7/R1B1KB2 b - - 1 23", "e5g3", "ply46_B_e5g3_best_g5g3"),
    ("r4qk1/p1p4p/np4p1/3p1p2/3P4/3K1N2/PP3nPP/RN5R w - - 2 18", "d3c3", "ply35_W_d3c3_best_d3e2"),
    ("r4qk1/p1p4p/np4p1/3p1p2/3P4/2K2N2/PP3nPP/RN5R b - - 3 18", "f2h1", "ply36_B_f2h1_best_f8b4"),
    ("r4qk1/p1p4p/1p4p1/3p1p2/1n1P4/3K1N2/PP4PP/RN5n w - - 2 20", "d3e3", "ply39_W_d3e3_best_d3c3"),
    ("r5k1/p1p1q2p/1p4p1/3p1p2/1n1P4/4KN2/PP4PP/RN5n w - - 4 21", "e3f4", "ply41_W_e3f4_best_f3e5"),
    ("r5k1/p1p1q2p/1p4p1/3p1p2/1n1P1K2/5N2/PP4PP/RN5n b - - 5 21", "e7e4", "ply42_B_e7e4_best_b4d3"),
    ("r5k1/p1p4p/1p4p1/3p1pK1/1n1P2q1/5N2/PP4PP/RN5n w - - 8 23", "g5h6", "ply45_W_g5h6_best_g5f6"),
    ("r5k1/p1p4p/1p4pK/3p1p2/1n1P2q1/5N2/PP4PP/RN5n b - - 9 23", "g4h5", "ply46_B_g4h5_best_g4h5"),
    ("r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6", "h7h5", "ply12_B_h7h5_best_c5b6"),
    ("r1br3k/5B2/2n2n2/pp2p1Bp/4P3/1QP2N2/PP3PPP/RN3RK1 b - - 0 13", "h5h4", "ply26_B_h5h4_best_d8d6"),
    ("r1br4/5B1k/2n2B2/pp2p3/4P2p/1QP2N2/PP3PPP/RN3RK1 w - - 1 15", "f6d8", "ply29_W_f6d8_best_f7g8"),
    ("r1bB4/5B1k/2n5/pp2p3/4P2p/1QP2N2/PP3PPP/RN3RK1 b - - 0 15", "b5b4", "ply30_B_b5b4_best_a8a7"),
    ("r1bB4/5B1k/2n5/p3p3/1p2P2p/1QP2N2/PP3PPP/RN3RK1 w - - 0 16", "f7d5", "ply31_W_f7d5_best_f7g8"),
    ("r1bB4/7k/2n5/p2Bp3/1p2P2p/1QP2N2/PP3PPP/RN3RK1 b - - 1 16", "b4c3", "ply32_B_b4c3_best_c6d8"),
    ("r1bB4/7k/2B5/p3p3/4P2p/1Qp2N2/PP3PPP/RN3RK1 b - - 0 17", "c3c2", "ply34_B_c3c2_best_a8a7"),
    ("B1bB4/7k/8/p3p3/4P2p/1Q3N2/PPp2PPP/RN3RK1 b - - 0 18", "c2b1q", "ply36_B_c2b1q_best_h7g7"),
    ("B1bB4/7k/8/p3p3/4P2p/1Q3N2/PP3PPP/1R3RK1 b - - 0 19", "a5a4", "ply38_B_a5a4_best_h7g7"),
    ("B1bB4/5Q2/7k/4p3/p3P2p/5N2/PP3PPP/1R3RK1 w - - 2 21", "d8g5", "ply41_W_d8g5_best_d8g5"),
    ("r2q1rk1/ppp1pp1p/6p1/2Pp3P/PP1nnPb1/8/8/RNB1KB1R w KQ - 0 13", "h5g6", "ply25_W_h5g6_best_a1a2"),
    ("r2q1rk1/ppp1pp1p/6P1/2Pp4/PP1nnPb1/8/8/RNB1KB1R b KQ - 0 13", "f7g6", "ply26_B_f7g6_best_d4c2"),
    ("r2q1rk1/ppp1p2p/6p1/2Pp4/PP1nnPb1/8/8/RNB1KB1R w KQ - 0 14", "c5c6", "ply27_W_c5c6_best_b1a3"),
    ("r2q1rk1/ppp1p2p/2P3p1/3p4/PP1nnPb1/8/8/RNB1KB1R b KQ - 0 14", "g4f3", "ply28_B_g4f3_best_d4c2"),
    ("r2q1rk1/ppp1p2p/2P3p1/3p4/PP1nnP2/5b2/8/RNB1KB1R w KQ - 1 15", "c6b7", "ply29_W_c6b7_best_a1a2"),
    ("r2q1rk1/pPp1p2p/6p1/3p4/PP1nnP2/5b2/8/RNB1KB1R b KQ - 0 15", "a8b8", "ply30_B_a8b8_best_d4c2"),
    ("1r1q1rk1/pPp1p2p/6p1/3p4/PP1nnP2/5b2/8/RNB1KB1R w KQ - 1 16", "f4f5", "ply31_W_f4f5_best_f1g2"),
    ("1r1q1rk1/pPp1p2p/6p1/3p1P2/PP1nn3/5b2/8/RNB1KB1R b KQ - 0 16", "f3h1", "ply32_B_f3h1_best_d4c2"),
    ("1r1q1rk1/pPp1p2p/6p1/3p1P2/PP1nn3/8/8/RNB1KB1b w Q - 0 17", "f5g6", "ply33_W_f5g6_best_c1f4"),
    ("1r1q1rk1/pPp1p3/6p1/3p4/PP1nn3/8/8/RNB1KB1b w Q - 0 18", "b4b5", "ply35_W_b4b5_best_c1f4"),
    ("1r1q1rk1/pPp1p3/6p1/1P1p4/P3n3/5n2/8/RNB1KB1b w Q - 1 19", "e1e2", "ply37_W_e1e2_best_e1d1"),
    ("1r1q1rk1/pPp1p3/6p1/1P1p4/P3n3/5n2/4K3/RNB2B1b b - - 2 19", "e4g3", "ply38_B_e4g3_best_f3d4"),
    ("1r1q1rk1/pPp1p3/6p1/1P1p4/P7/5nn1/4K3/RNB2B1b w - - 3 20", "e2e3", "ply39_W_e2e3_best_e2d1"),
    ("1r1q1rk1/pPp1p3/6p1/1P1p4/P7/3K4/8/RNB1nn1b w - - 2 22", "d3d4", "ply43_W_d3d4_best_d3c3"),
    ("1r1q2k1/pPp1p3/6p1/1P1p4/P2K1r2/8/8/RNB1nn1b w - - 4 23", "d4e5", "ply45_W_d4e5_best_d4c3"),
    ("1r1q2k1/pPp1p3/6p1/1P1pK3/P4r2/8/8/RNB1nn1b b - - 5 23", "d8d6", "ply46_B_d8d6_best_f4e4"),
    ("rnbqkb1r/pppppppp/8/4P3/5n2/2NP4/PPP2PPP/R1BQKBNR b KQkq - 0 4", "g7g6", "ply8_B_g7g6_best_f4g6"),
    ("rnbqkb1r/pppppp1p/6p1/4P3/5n2/2NP4/PPP2PPP/R1BQKBNR w KQkq - 0 5", "g1f3", "ply9_W_g1f3_best_c1f4"),
    ("rnbqkb1r/pppppp1p/6p1/4P3/5n2/2NP1N2/PPP2PPP/R1BQKB1R b KQkq - 1 5", "f8g7", "ply10_B_f8g7_best_f4e6"),
    ("rnbq1rk1/3p1pbp/p1p3p1/3pP3/Pp3BPP/2N2N2/1PP2P2/R2QKB1R w KQ - 0 13", "b2b3", "ply25_W_b2b3_best_c3e2"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/8/bNB1KB1n b - - 0 18", "a1c3", "ply36_B_a1c3_best_e7f6"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1bb5/8/1NB1KB1n w - - 1 19", "b1d2", "ply37_W_b1d2_best_b1c3"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1bb5/3N4/2B1KB1n b - - 2 19", "c3d2", "ply38_B_c3d2_best_e7f6"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/3b4/2B1KB1n w - - 0 20", "c1d2", "ply39_W_c1d2_best_e1d2"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b6/3B4/4KB1n b - - 0 20", "h1g3", "ply40_B_h1g3_best_e7f6"),
    ("1r1q1r2/pPp1pp1k/5P2/3p4/P7/1b4n1/3B4/4KB2 w - - 1 21", "f6e7", "ply41_W_f6e7_best_f1d3"),
    ("1r3r2/pPp1qp1k/8/3p4/P7/1b4n1/3B4/4KB2 w - - 0 22", "f1e2", "ply43_W_f1e2_best_e1f2"),
    ("1r3r2/pPp1qp1k/8/3p4/P7/1b4n1/3BB3/4K3 b - - 1 22", "e7e3", "ply44_B_e7e3_best_e7e2"),
    ("1r3r2/pPp2p1k/8/3p4/P7/1b2q1n1/3BB3/4K3 w - - 2 23", "a4a5", "ply45_W_a4a5_best_d2e3"),
    ("1r3r2/pPp2p1k/8/P2p4/8/1b2q1n1/3BB3/4K3 b - - 0 23", "e3e2", "ply46_B_e3e2_best_e3e2"),
    ("r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6", "d6d5", "ply12_B_d6d5_best_c5b6"),
    ("r1bqk2r/ppp2ppp/2n2n2/2bpp3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 w kq - 0 7", "d4c5", "ply13_W_d4c5_best_e4d5"),
    ("r1bqk2r/ppp2ppp/2n2n2/2Ppp3/2B1P3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 7", "d5e4", "ply14_B_d5e4_best_d5c4"),
    ("r1bB2kr/2p2p2/p1B5/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 17", "g8h7", "ply34_B_g8h7_best_c8g4"),
    ("B1bB3r/2p2p1k/p7/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 18", "h7g7", "ply36_B_h7g7_best_h7g6"),
    ("B1b4r/2p2pk1/p4B2/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 2 19", "g7g8", "ply38_B_g7g8_best_g7h6"),
    ("B1b3kB/2p2p2/p7/2P3pp/1Pp1p3/4P3/P2N2PP/RN1Q1RK1 b - - 0 20", "g8f8", "ply40_B_g8f8_best_c8g4"),
    ("B1b2k1B/2p2p2/p7/2P3pQ/1Pp1p3/4P3/P2N2PP/RN3RK1 b - - 0 21", "f8e8", "ply42_B_f8e8_best_f7f6"),
    ("B1b1k2B/2p2R2/p7/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 b - - 0 22", "c7c6", "ply44_B_c7c6_best_c8d7"),
    ("5k1B/3R4/p1B5/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 w - - 1 25", "d7d8", "ply49_W_d7d8_best_h5f7"),
    ("3R3B/4k3/p1B5/2P3pQ/1Pp1p3/4P3/P2N2PP/RN4K1 w - - 3 26", "h5e8", "ply51_W_h5e8_best_h5e8"),
    ("r1bqk2r/ppp2ppp/2np1n2/2b1p3/2BPP3/2P2N2/PP3PPP/RNBQ1RK1 b kq - 0 6", "e8g8", "ply12_B_e8g8_best_c5b6"),
    ("r1bq1r1k/ppP2ppp/2n2n2/4p1B1/2B1P3/1NP2N2/PP3PPP/R2Q1RK1 b - - 0 12", "h8g8", "ply24_B_h8g8_best_d8c7"),
    ("r1bR2k1/pp3ppp/2n2n2/4p1B1/2B1P3/1NP2N2/PPQ2PPP/5RK1 b - - 0 16", "f6e8", "ply32_B_f6e8_best_c6d8"),
    ("r1bRn1k1/pp3ppp/2n5/4p1B1/2B1P3/1NP2N2/PPQ2PPP/5RK1 w - - 1 17", "d8e8", "ply33_W_d8e8_best_d8e8"),
    ("r4r2/p2p3k/n2Np1p1/q1p5/P5Q1/8/3NKP2/8 b - - 2 24", "a5c7", "ply48_B_a5c7_best_f8f2"),
    ("r4N2/p6k/n5pq/P1pp4/6Q1/5N2/4KP2/8 b - - 0 30", "h6f8", "ply60_B_h6f8_best_a8f8"),
    ("r4q2/p6k/n5p1/P1pp4/6Q1/5N2/4KP2/8 w - - 0 31", "g4h3", "ply61_W_g4h3_best_f3g5"),
    ("r4qk1/p2Q4/n5p1/P1pp4/8/5N2/4KP2/8 w - - 4 33", "e2e3", "ply65_W_e2e3_best_d7d5"),
    ("4rqk1/p2Q4/n5p1/P1pp4/8/4KN2/5P2/8 w - - 6 34", "e3d2", "ply67_W_e3d2_best_d7e8"),
    ("4rqk1/p2Q4/n5p1/P1pp4/8/5N2/3K1P2/8 b - - 7 34", "d5d4", "ply68_B_d5d4_best_f8f4"),
    ("4rqk1/p2Q4/n5p1/P1p5/3p4/5N2/3K1P2/8 w - - 0 35", "d7a7", "ply69_W_d7a7_best_d2c1"),
    ("4r1k1/Q7/n5p1/P1p5/3p4/5q2/3K1P2/8 w - - 0 36", "d2c2", "ply71_W_d2c2_best_a7a8"),
    ("6k1/Q7/n5p1/P1p5/3p4/8/4rq2/3K4 w - - 0 38", "d1c1", "ply75_W_d1c1_best_a7a8"),
    ("6k1/Q7/n5p1/P1p5/3p4/8/4rq2/2K5 b - - 1 38", "f2e1", "ply76_B_f2e1_best_e2e1"),
    ("r1bqk2r/ppp2ppp/2np1n2/2b5/2BPP3/5N2/PP3PPP/RNBQ1RK1 b kq - 0 7", "f6e4", "ply14_B_f6e4_best_c5b6"),
    ("r2qk2r/pppb2pp/2n5/2p3B1/Q1B1p3/5N2/PP3PPP/R4RK1 b kq - 1 12", "e4f3", "ply24_B_e4f3_best_c6d4"),
    ("r2Bk2r/pppb2pp/2n5/2p5/Q1B5/8/PP3PpP/R4RK1 w kq - 0 14", "g1g2", "ply27_W_g1g2_best_f1d1"),
    ("r1k4r/pppb2pp/2n5/2p5/2B5/1Q6/PP3PKP/3R1R2 b - - 3 16", "g7g6", "ply32_B_g7g6_best_c6d4"),
    ("rk5r/ppp4p/2n2Qp1/2p5/8/8/PP3PKP/3R1R2 b - - 2 19", "b7b5", "ply38_B_b7b5_best_h8c8"),
    ("rk5r/p1p4p/2n2Qp1/1pp5/8/8/PP3PKP/3R1R2 w - - 0 20", "f6h8", "ply39_W_f6h8_best_f6c6"),
    ("r7/1kp4p/2n2Qp1/ppp5/8/8/PP3PKP/3R1R2 w - - 0 22", "d1d6", "ply43_W_d1d6_best_f1e1"),
    ("8/8/2k3pR/1p6/p1p5/8/PP3PKP/8 b - - 1 29", "c6d7", "ply58_B_c6d7_best_b5b4"),
    ("4k3/8/6R1/1p6/p1p5/8/PP3PKP/8 w - - 1 31", "f2f4", "ply61_W_f2f4_best_g2f3"),
    ("4k3/8/6R1/1p3P2/p1p5/8/PP4KP/8 w - - 1 33", "f5f6", "ply65_W_f5f6_best_g2f3"),
    ("4k3/8/5PR1/1p6/p1p5/8/PP4KP/8 b - - 0 33", "e8d8", "ply66_B_e8d8_best_b5b4"),
    ("5k2/5P1R/8/1p6/p1p4P/8/PP4K1/8 w - - 1 38", "h4h5", "ply75_W_h4h5_best_g2f3"),
    ("5k2/5P1R/8/1p5P/p1p5/8/PP4K1/8 b - - 0 38", "f8e7", "ply76_B_f8e7_best_b5b4"),
    ("5k2/5PR1/7P/1p6/p1p5/8/PP4K1/8 b - - 2 40", "c4c3", "ply80_B_c4c3_best_a4a3"),
    ("5k2/5PR1/7P/1p6/p7/2P5/P5K1/8 b - - 0 41", "f8e7", "ply82_B_f8e7_best_a4a3"),
    ("5Q2/6R1/8/1p1k3Q/p7/2P5/P5K1/8 b - - 2 45", "d5e6", "ply90_B_d5e6_best_d5c4"),
    ("5Q2/6R1/4k3/1p5Q/p7/2P5/P5K1/8 w - - 3 46", "g7g6", "ply91_W_g7g6_best_h5f5"),
    ("5Q2/3k4/6R1/1p5Q/p7/2P5/P5K1/8 w - - 5 47", "f8f7", "ply93_W_f8f7_best_h5h7"),
    ("3k4/5Q2/6R1/1p5Q/p7/2P5/P5K1/8 w - - 7 48", "h5h8", "ply95_W_h5h8_best_h5h8"),
    ("r1bqk2r/ppp2ppp/2np1n2/2b1p1B1/2B1P3/3P1N2/PPP2PPP/RN1Q1RK1 b kq - 1 6", "c5f2", "ply12_B_c5f2_best_h7h6"),
    ("r1bq1rk1/pp3ppp/3p1n2/2p1p1B1/2P1P3/2PP1N2/P5PP/RN1Q1RK1 b - - 0 11", "f6e4", "ply22_B_f6e4_best_h7h6"),
    ("3r1r2/pp3ppk/3N3p/2p1N3/4P3/2P5/P5PP/R2Q1RK1 b - - 0 17", "h7g8", "ply34_B_h7g8_best_f7f6"),
    ("3r1rk1/pp3pp1/3N3p/2p1N3/4P3/2P5/P5PP/R2Q1RK1 w - - 1 18", "e5f7", "ply35_W_e5f7_best_f1f7"),
    ("3r1rk1/pp3Np1/3N3p/2p5/4P3/2P5/P5PP/R2Q1RK1 b - - 0 18", "f8f7", "ply36_B_f8f7_best_d8d7"),
    ("5Q2/p5pk/4P2p/1pp5/8/2P5/P5PP/5RK1 b - - 0 24", "h7g6", "ply48_B_h7g6_best_b5b4"),
    ("5Q2/p5p1/4P1kp/1pp5/8/2P5/P5PP/5RK1 w - - 1 25", "e6e7", "ply49_W_e6e7_best_f8f5"),
    ("5Q2/p3P1p1/6kp/1pp5/8/2P5/P5PP/5RK1 b - - 0 25", "g6h7", "ply50_B_g6h7_best_g6h5"),
    ("4QQ2/p6k/6pp/1pp5/8/2P5/P5PP/5RK1 w - - 0 27", "f8h8", "ply53_W_f8h8_best_f8h8"),
    ("rnb1kb1r/pp3ppp/4q3/2p3N1/4p3/8/PPPPNPPP/R1BQ1RK1 b kq - 1 9", "e6a2", "ply18_B_e6a2_best_e6g6"),
    ("2kr3r/1p4p1/4bp2/7p/Q2b1B2/2P5/1P3PPP/5RK1 w - - 0 20", "c3d4", "ply39_W_c3d4_best_c3d4"),
    ("2kr3r/1p4p1/4bp2/7p/Q2P1B2/8/1P3PPP/5RK1 b - - 0 20", "e6d5", "ply40_B_e6d5_best_d8d5"),
    ("2kr3r/1p4p1/5p2/3b3p/Q2P1B2/8/1P3PPP/5RK1 w - - 1 21", "a4a8", "ply41_W_a4a8_best_f1e1"),
    ("3r3r/1p1k2p1/5p2/3b3p/Q2P1B2/8/1P3PPP/5RK1 b - - 4 22", "d7c8", "ply44_B_d7c8_best_d7e6"),
    ("2kr3r/1p4p1/5p2/Q2b3p/3P1B2/8/1P3PPP/5RK1 b - - 6 23", "b7b6", "ply46_B_b7b6_best_d8d6"),
    ("2kr3r/6p1/1Q3p2/3b3p/3P1B2/8/1P3PPP/5RK1 b - - 0 24", "c8d7", "ply48_B_c8d7_best_d8d6"),
    ("3r3r/3k2p1/1Q3p2/3b3p/3P1B2/8/1P3PPP/5RK1 w - - 1 25", "f4c7", "ply49_W_f4c7_best_f1e1"),
    ("3r3r/2Bk2p1/1Q3p2/3b3p/3P4/8/1P3PPP/5RK1 b - - 2 25", "d8c8", "ply50_B_d8c8_best_d7e8"),
    ("2r4r/2Bk2p1/1Q3p2/3b3p/3P4/8/1P3PPP/5RK1 w - - 3 26", "c7b8", "ply51_W_c7b8_best_b6d6"),
    ("1r5r/Q5p1/4kp2/3b3p/3P4/8/1P3PPP/4R1K1 b - - 3 28", "e6d6", "ply56_B_e6d6_best_e6f5"),
    ("1r5r/2k1R1p1/5p2/3Q3p/3P4/8/1P3PPP/6K1 b - - 2 31", "c7c8", "ply62_B_c7c8_best_c7b6"),
    ("1rk4r/4R1p1/5p2/3Q3p/3P4/8/1P3PPP/6K1 w - - 3 32", "d5c5", "ply63_W_d5c5_best_d5d7"),
    ("1r1k3r/4R1p1/5p2/2Q4p/3P4/8/1P3PPP/6K1 w - - 5 33", "d4d5", "ply65_W_d4d5_best_c5c7"),
    ("3k3r/1Q2R3/5pp1/3P3p/8/8/1P3PPP/6K1 w - - 0 37", "d5d6", "ply73_W_d5d6_best_b7c7"),
    ("3k3r/1Q2R3/3P1p2/6pp/8/8/1P3PPP/6K1 w - - 0 38", "b7b8", "ply75_W_b7b8_best_b7c7"),
    ("rnb2rk1/pp2bppp/8/8/2qN4/2N5/PPP2PPP/R1BQK2R w - - 3 13", "b2b3", "ply25_W_b2b3_best_d1d3"),
    ("rn3rk1/pp2bppp/8/3Q1b2/8/1P6/2q2PPP/2B2K1R w - - 0 18", "d5b7", "ply35_W_d5b7_best_d5d2"),
    ("rn3rk1/pQ2bppp/8/5b2/8/1P6/2q2PPP/2B2K1R b - - 0 18", "c2f2", "ply36_B_c2f2_best_c2d1"),
    ("6k1/p2n1ppp/8/2b5/6b1/1P6/3K3P/4R3 b - - 0 27", "c5b4", "ply54_B_c5b4_best_c5b4"),
    ("6k1/p2n1ppp/8/8/5Kb1/1P6/7P/4b3 b - - 1 29", "e1c3", "ply58_B_e1c3_best_g4e6"),
    ("6k1/p2n1ppp/8/8/6K1/1Pb5/7P/8 b - - 0 30", "d7f6", "ply60_B_d7f6_best_g7g6"),
    ("6k1/p4ppp/5n2/5K2/8/1Pb5/7P/8 b - - 2 31", "f6d7", "ply62_B_f6d7_best_g7g6"),
    ("6k1/p2n1ppp/8/5K2/8/1Pb5/7P/8 w - - 3 32", "f5e4", "ply63_W_f5e4_best_f5e4"),
    ("6k1/p2n1ppp/8/8/4K3/1Pb5/7P/8 b - - 4 32", "d7f6", "ply64_B_d7f6_best_d7b6"),
    ("6k1/p4ppp/8/4b2n/4K3/1P5P/8/8 b - - 2 35", "e5b8", "ply70_B_e5b8_best_e5c7"),
    ("1b4k1/p4ppp/8/7n/4K3/1P5P/8/8 w - - 3 36", "e4f5", "ply71_W_e4f5_best_e4d3"),
    ("1b4k1/p4ppp/8/5K1n/8/1P5P/8/8 b - - 4 36", "b8d6", "ply72_B_b8d6_best_g7g6"),
    ("6k1/p4ppp/3b4/5K1n/8/1P5P/8/8 w - - 5 37", "f5g5", "ply73_W_f5g5_best_f5e4"),
    ("6k1/p4ppp/3b4/6Kn/8/1P5P/8/8 b - - 6 37", "h5f4", "ply74_B_h5f4_best_g7g6"),
    ("6k1/p4ppp/3b4/8/5nK1/1P5P/8/8 b - - 8 38", "h7h5", "ply76_B_h7h5_best_g7g6"),
    ("6k1/p4pp1/3b4/7p/5nK1/1P5P/8/8 w - - 0 39", "g4g3", "ply77_W_g4g3_best_g4f3"),
    ("6k1/p4pp1/3b4/7p/5n2/1P4KP/8/8 b - - 1 39", "f4e6", "ply78_B_f4e6_best_f4d5"),
    ("6k1/p4pp1/3bn3/7p/8/1P4KP/8/8 w - - 2 40", "g3h4", "ply79_W_g3h4_best_g3f3"),
    ("6k1/p4pp1/3bn3/7p/7K/1P5P/8/8 b - - 3 40", "e6c5", "ply80_B_e6c5_best_g7g6"),
    ("6k1/p4pp1/3b4/2n4p/7K/1P5P/8/8 w - - 4 41", "h4h5", "ply81_W_h4h5_best_h4h5"),
    ("6k1/p4pp1/3b4/2n4K/8/1P5P/8/8 b - - 0 41", "c5b3", "ply82_B_c5b3_best_g7g6"),
    ("6k1/p4pp1/3b4/6K1/8/1n5P/8/8 b - - 1 42", "d6e7", "ply84_B_d6e7_best_b3d4"),
    ("6k1/p3bpp1/8/5K2/8/1n5P/8/8 b - - 3 43", "b3d4", "ply86_B_b3d4_best_a7a5"),
    ("8/p3kpp1/5b2/8/3nK3/7P/8/8 w - - 10 47", "e4f4", "ply93_W_e4f4_best_e4d3"),
    ("8/p3kpp1/4nb2/8/5K2/7P/8/8 w - - 12 48", "f4f5", "ply95_W_f4f5_best_f4e3"),
    ("6k1/p4pp1/5b2/3K4/3n4/7P/8/8 w - - 18 51", "d5d6", "ply101_W_d5d6_best_d5c4"),
    ("6k1/p4pp1/4nb2/2K5/8/7P/8/8 w - - 24 54", "c5d6", "ply107_W_c5d6_best_c5b4"),
    ("6k1/p4pp1/3K1b2/8/5n2/7P/8/8 w - - 26 55", "d6d7", "ply109_W_d6d7_best_h3h4"),
    ("6k1/p2K1pp1/5b2/8/8/7n/8/8 w - - 0 56", "d7e8", "ply111_W_d7e8_best_d7c6"),

]


# --- Helpers to resolve optimal move (UCI) from past game logs by label ---
_PLY_LABEL_RE = re.compile(
    r"^ply(?P<num>\d+)_([WB])_([a-h][1-8][a-h][1-8](?:[qrbn])?)(?:_best_([a-h][1-8][a-h][1-8](?:[qrbn])?))?$"
)


def _parse_label(label: str) -> tuple[int | None, str | None, str | None, str | None]:
    m = _PLY_LABEL_RE.match(label)
    if not m:
        return None, None, None, None
    num = int(m.group("num"))
    # Extract side and the trailing UCI from label for context if needed
    parts = label.split("_")
    side = parts[1] if len(parts) > 1 else None
    uci = parts[2] if len(parts) > 2 else None
    best_uci = None
    if len(parts) >= 5 and parts[3] == 'best':
        best_uci = parts[4]
    return num, side, uci, best_uci


def _iter_past_game_logs(repo_root: str):
    # Search both the canonical tools/past_games folder and repo root, since logs may be kept in either
    candidate_dirs = [
        os.path.join(repo_root, "PYTHON", "lichess_bot", "tools", "past_games"),
        repo_root,
    ]
    seen = set()
    for logs_dir in candidate_dirs:
        if not os.path.isdir(logs_dir):
            continue
        for name in os.listdir(logs_dir):
            if not name.startswith("lichess_bot_game_") or not name.endswith(".log"):
                continue
            if (logs_dir, name) in seen:
                continue
            seen.add((logs_dir, name))
            path = os.path.join(logs_dir, name)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    yield name, f.read()
            except Exception:
                continue


def _bot_side_from_log(txt: str) -> str | None:
    # Try to infer whether VibeBot was White (W) or Black (B)
    # Look for line: Players: VibeBot vs Reduktor OR Reduktor vs VibeBot
    for line in txt.splitlines():
        if line.startswith("Players:"):
            low = line.lower()
            if "vibebot vs" in low:
                return "W"
            if "vs vibebot" in low:
                return "B"
    return None


def _resolve_optimal_uci_from_logs(repo_root: str, label: str, fen: str) -> str | None:
    ply_num, side, _, _ = _parse_label(label)
    if ply_num is None or side is None:
        return None
    target_prefix = f"ply {ply_num}:"
    # We'll only return a move that's legal in the provided FEN
    try:
        position = chess.Board(fen)
    except Exception:
        position = None
    for fname, txt in _iter_past_game_logs(repo_root):
        bot_side = _bot_side_from_log(txt)
        # Prefer logs where the bot side matches the label side (heuristic)
        if bot_side is not None and bot_side != side:
            continue
        lines = txt.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith(target_prefix):
                # Look for a following line starting with 'best '
                # Usually immediate or within a couple of lines
                for j in range(i + 1, min(i + 6, len(lines))):
                    s = lines[j].strip()
                    if s.startswith("best "):
                        # Expect format: best <SAN> (<uci>) ...
                        m = re.search(r"\(([a-h][1-8][a-h][1-8](?:[qrbn])?)\)", s)
                        if m:
                            uci = m.group(1)
                            if position is not None:
                                try:
                                    mv = chess.Move.from_uci(uci)
                                    if mv in position.legal_moves:
                                        return uci
                                    else:
                                        # Skip illegal candidates and keep searching
                                        continue
                                except Exception:
                                    continue
                            return uci
                        # Fallback: sometimes lines like 'avoided risky ...' appear first, keep scanning
                        continue
                # If we hit here, this ply in this log lacks a 'best' line nearby
                # Try a little farther just in case
                for j in range(i + 1, min(i + 12, len(lines))):
                    s = lines[j].strip()
                    if s.startswith("best "):
                        m = re.search(r"\(([a-h][1-8][a-h][1-8](?:[qrbn])?)\)", s)
                        if m:
                            uci = m.group(1)
                            if position is not None:
                                try:
                                    mv = chess.Move.from_uci(uci)
                                    if mv in position.legal_moves:
                                        return uci
                                    else:
                                        continue
                                except Exception:
                                    continue
                            return uci
                # Otherwise move to next log
    return None


@pytest.mark.parametrize('fen,blunder_uci,label', BLUNDER_CASES, ids=[c[2] for c in BLUNDER_CASES])
def test_engine_avoids_logged_blunder(fen, blunder_uci, label):
    board = chess.Board(fen)
    eng = RandomEngine(depth=4, max_time_sec=1.2)
    # Prefer explanation variant if available for better failure messages
    move = None
    explanation = ''
    if hasattr(eng, 'choose_move_with_explanation'):
        try:
            mv, expl = eng.choose_move_with_explanation(board, time_budget_sec=1.2)
            move, explanation = mv, expl or ''
        except Exception:
            move = eng.choose_move(board)
    else:
        move = eng.choose_move(board)
    assert move is not None, 'Engine returned no move'
    assert move in board.legal_moves, 'Engine move is illegal'
    # If the engine repeats the blunder, gather deeper diagnostics: compare eval of blunder vs engine's best
    if move.uci() == blunder_uci:
        # Pick optimal move from parametrized data, with fallback to resolving from logs
        # First, try to extract an explicit optimal UCI encoded in the test label
        _, _, _, optimal_from_label = _parse_label(label)
        optimal_from_logs = optimal_from_label or _resolve_optimal_uci_from_logs(REPO_ROOT, label, fen)
        details = [
            f'Engine repeated blunder {blunder_uci} at {label}.',
            f'engine_move_explanation: {explanation}'.strip(),
        ]
        # Try to request a side-by-side evaluation (blunder vs optimal) from the engine if available
        try:
            if hasattr(eng, 'evaluate_proposed_move_with_suggestion'):
                try:
                    proposed_score_cp, proposed_expl, best_move, best_expl = eng.evaluate_proposed_move_with_suggestion(
                        board, blunder_uci, time_budget_sec=1.0
                    )
                    details.append('--- comparative analysis (engine provided) ---')
                    details.append(f'blunder {blunder_uci}: score={proposed_score_cp}cp explanation: {proposed_expl}')
                    # If we found an optimal move from logs, evaluate that exact move as well
                    if optimal_from_logs:
                        try:
                            opt_score_cp, opt_expl, _, _ = eng.evaluate_proposed_move_with_suggestion(
                                board, optimal_from_logs, time_budget_sec=1.0
                            )
                            details.append(f'optimal_from_logs {optimal_from_logs}: score={opt_score_cp}cp explanation: {opt_expl}')
                        except Exception as e:
                            details.append(f'optimal_from_logs {optimal_from_logs}: <error evaluating: {e}>')
                    elif optimal_from_logs is None:
                        details.append('optimal_from_logs: <not found>')
                    if best_move is not None:
                        details.append(
                            f'engine_optimal {best_move.uci()}: explanation: {best_expl}'
                        )
                    else:
                        details.append('engine_optimal: <none>')
                except Exception as e:  # fall back if the evaluation API fails
                    # Fallback 1: at least get engine optimal move + explanation
                    if hasattr(eng, 'choose_move_with_explanation'):
                        try:
                            best_mv, best_expl = eng.choose_move_with_explanation(board, time_budget_sec=1.0)
                            details.append('--- fallback analysis ---')
                            details.append(f'engine_optimal {best_mv.uci() if best_mv else "<none>"}: explanation: {best_expl}')
                        except Exception:
                            details.append(f'engine_optimal: <error obtaining explanation: {e}>')
            else:
                # Fallback 2: engine lacks evaluation API; get its best move explanation as context
                if hasattr(eng, 'choose_move_with_explanation'):
                    try:
                        best_mv, best_expl = eng.choose_move_with_explanation(board, time_budget_sec=1.0)
                        details.append('--- fallback analysis ---')
                        details.append(f'engine_optimal {best_mv.uci() if best_mv else "<none>"}: explanation: {best_expl}')
                        if optimal_from_logs:
                            details.append(f'optimal_from_logs {optimal_from_logs} (no eval available)')
                    except Exception as e:
                        details.append(f'engine_optimal: <error obtaining explanation: {e}>')
        except Exception as outer:
            details.append(f'<error during diagnostic analysis: {outer}>')

        pytest.fail("\n".join(d for d in details if d))

    assert move.uci() != blunder_uci, f'Engine repeated blunder {blunder_uci} at {label}. Explanation: {explanation}'
