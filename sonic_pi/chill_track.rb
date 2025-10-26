# Simple Chill Groove for Sonic Pi
# Paste/run directly in Sonic Pi or use run.sh in this folder to auto-play.

use_bpm 96
use_random_seed 1234

# Chord progression: Am – F – C – G
prog = (ring chord(:a3, :minor), chord(:f3, :major), chord(:c4, :major), chord(:g3, :major))

# Master bar clock + shared progression
live_loop :bar do
  cue :bar
  sleep 4
end

live_loop :progression do
  sync :bar
  set :chord, prog.tick
end

# DRUMS
live_loop :kick do
  sample :bd_haus, amp: 2
  sleep 1
end

live_loop :snare do
  sleep 1
  sample :sn_dolf, amp: 1.2
  sleep 1
end

live_loop :hats do
  sample :drum_cymbal_closed, amp: 0.6, cutoff: 120
  sleep 0.5
end

# MUSIC
with_fx :reverb, room: 0.7, mix: 0.35 do
  live_loop :bass do
    sync :bar
    c = get(:chord)
    use_synth :tb303
    r = c.first - 12
    8.times do
      play r, release: 0.12, cutoff: rrand(90, 130), res: 0.9, wave: 0, amp: 0.9
      sleep 0.5
    end
  end

  live_loop :pads do
    sync :bar
    c = get(:chord)
    use_synth :prophet
    play c, sustain: 3.5, release: 0.5, cutoff: 100, amp: 0.5
  end

  live_loop :melody do
    sync :bar
    use_synth :pluck
    s = scale(:a4, :minor_pentatonic)
    8.times do
      play choose(s), amp: 0.5, release: 0.15, pan: rrand(-0.35, 0.35)
      sleep 0.5
    end
  end
end
