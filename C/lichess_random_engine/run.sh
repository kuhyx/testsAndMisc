#!/usr/bin/env bash
set -e
make
echo "Usage: ./random_engine --fen \"<FEN>\" move1 move2 ..."
echo "       ./random_engine --fen \"<FEN>\" --explain move1 ..."
