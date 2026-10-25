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

| # | Payload | Advanced | Question it answers |
|---|---|---|---|
| 1 | POS logs, 10 KB | defaults | Does everything work end to end? |
| 2 | POS logs, 100 KB | defaults (ECC H) | Baseline for the realistic size |
| 3 | POS logs, 100 KB | ECC **M** | Do bigger modules capture better? |
| 4 | POS logs, 100 KB | defaults (ECC H) | Repeat of run 2, to see how much runs vary |
| 5 | POS logs, 100 KB | ECC **M** | Repeat of run 3 |
| 6 | POS logs, 500 KB | whichever of H or M did better | The "real log pull" number |

Optional, if you have time: repeat run 6 with **Frame speed: Fast**.

## What happens with the reports

Paste all the reports back in one message. Each one says how long the receive took, what share of the frames the phone caught (capture rate), whether any frames were corrupt, and the settings, so nothing needs annotating. We then decide:

- **ECC default:** switch to M if its capture rate and time are at least as good as H.
- **Frame speed:** go faster if capture stays above about 85% at Fast.
- **Data per frame:** if capture is comfortably high, test larger blocks next.
