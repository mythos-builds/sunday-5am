# Sunday, 5 AM

A 49-second film for BCH BLAZE 2026 (Media track). Mom needs $50. The bank is closed until Monday. Bitcoin Cash isn't.

**Watch:** https://mythos-builds.github.io/sunday-5am/

Every frame is drawn and every sound is synthesized by one script, `cash.py`: no stock footage, no samples, no keyframes. The picture and the music share one beat grid (120 BPM written, played at 0.45 speed, so 54 BPM), so they cannot drift apart.

## BCH BLAZE banner

- CashTokens address for EMBER2026 votes: `bitcoincash:zz26kltcxsatnd0t6td6dp0d6y27tt6tqsu97xv2dd`
- New work, not a pre-existing project: the story, frames, music and sound were made from 15 November 2026. The drawing and synth helpers come from an earlier promo script of ours.
- Made by one human and an AI agent. Also in BLAZE: [Countersign](https://countersign.cash/) (mainnet track).

## Render it yourself

Needs Python 3 with numpy, scipy and Pillow, plus ffmpeg. Put these fonts (all SIL Open Font License, from Google Fonts) in `fonts/`:
`BigShouldersDisplay-900.ttf` (Big Shoulders Display Black), `InstrumentSerif-400i.ttf` (Instrument Serif Italic),
`IBMPlexMono-500.ttf` and `IBMPlexMono-700.ttf` (IBM Plex Mono Medium and Bold), `Inter.ttf` (Inter, variable).
`bch-logo.png` is `bch-logo.svg` rasterized at 600 px (`cairosvg bch-logo.svg -o bch-logo.png -W 600 -H 600`).

```
python3 cash.py                   # → out/sunday-5am.mp4 (about 45 s on a laptop)
python3 cash.py --fps 30          # quicker render
python3 cash.py --stills 1,3,5.2  # → out/stills.png, frames at those seconds
```

## What the film claims, and where it comes from

- « Fees under a penny » and « in seconds »: bitcoincash.org's own words (« fees under a penny and confirmations in seconds »). A typical payment is about 220 bytes at 1 sat per byte.
- « every day, all day »: the network has no business hours.
- The quote is the opening of the abstract of *Bitcoin: A Peer-to-Peer Electronic Cash System* (2008).

## License

Code: MIT (`LICENSE`). The film (`docs/sunday-5am.mp4` and its frames): CC BY 4.0, share and re-cut it freely. The Bitcoin Cash logo is the community's mark.
