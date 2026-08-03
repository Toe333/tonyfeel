# TonyFeel demo kit

Audio: `mad_4bars.wav` — Tony Bollas, 4 bars solo drums @ **114.219 BPM**.

Grid MIDI: `groove_quantized.mid`

**Default felt MIDI:** `groove_with_feel.mid` = **4-bar pack @ 25%**

## Canon pack — 4-bar loop (`tony_bollas_mad_4bar`)

Measured from **this WAV only**. Default amount **25%**.

| File | Amount |
|---|---|
| `groove_with_feel.mid` | **25% (default)** |
| `groove_4barfeel_p10.mid` | 10% |
| `groove_4barfeel_p25.mid` | 25% |
| `groove_4barfeel_p50.mid` | 50% |
| `groove_4barfeel_p100.mid` | 100% |

## Secondary — full-song (`tony_bollas_mad`)

| File | Amount |
|---|---|
| `groove_with_feel_p10.mid` … `p100.mid` | full-song pack A/Bs |

```bash
tonyfeel apply demo/groove_quantized.mid -o /tmp/felt.mid
# → tony_bollas_mad_4bar @ 25%
```

Credit: Tony Bollas, drums. Excerpt only.
