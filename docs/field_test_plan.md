# Field test plan

About 20 minutes. You need a laptop (sender) and a phone (receiver). The app records the measurements, so you only change one thing at a time and copy the report after each run.

## Setup (same for every run)

- Laptop screen at full brightness, normal room light, no direct glare on the screen.
- Laptop: open the site and choose **Send**. Phone: scan the QR code shown on the laptop with the Camera app. It opens the receiver directly.
- Hold the phone by hand about 30 cm (1 ft) from the screen, so the code fills most of the frame.

## Each run

1. Laptop: pick the payload and any **Advanced** setting the run calls for, then press **Start sending**.
2. Phone: tap **Start receiving** and hold it there until it shows ✓.
3. Phone: tap 😀, 😐 or 😞, add a note if anything stood out, then tap **Copy report**.
4. Paste the report into a single running note or message. Then press **Stop** on the laptop.

If a run stalls for more than a minute, tap **Pause** and copy the report anyway. Incomplete runs are useful data.

## Runs

The baseline is already measured: 500 KB at the defaults (ECC M, 224 B, Fast) took 106 s with every frame caught. The open question is how much data per frame the phone can handle.

| # | Payload | Advanced | Question it answers |
|---|---|---|---|
| 1 | POS logs, 500 KB | Data per frame **416 B**, Frame speed **Normal** | Can the phone read the densest code (v16) reliably? Estimate ~85 s |
| 2 | POS logs, 500 KB | Data per frame **416 B**, Fast (default) | The fastest setting. Estimate ~57 s if capture holds |
| 3 | POS logs, 500 KB | Data per frame **304 B**, Fast (default) | The middle option, if run 2 drops many frames. Estimate ~78 s |

Keep ECC at M (the default) for all three.

## What happens with the reports

Paste all the reports back in one message. Each one says how long the receive took, what share of the frames the phone caught (capture rate), whether any frames were corrupt, and the settings, so nothing needs annotating. We then decide:

- **Default data per frame:** whichever of runs 1–3 has the lowest total time (lock plus receiving). Dropped frames only cost time, never correctness, so the fastest finish wins.
- **Is 300 ms still right:** if run 2's capture falls well below 90%, try 416 B at Normal speed as the default instead.
