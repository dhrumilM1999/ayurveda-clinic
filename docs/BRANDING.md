# Klinvexa: the software's brand

**Name:** Klinvexa. **Tagline (optional):** Clinic Operations, Connected.
Shown inside the software only (menu, login screen, browser tab). It is never printed on prescriptions, bills or
other print-outs: those carry the clinic's own logo and letterhead.

## Files
| File | What it is |
|---|---|
| `frontend/public/brand/klinvexa-logo.svg` | wordmark for light screens |
| `frontend/public/brand/klinvexa-logo-white.svg` | wordmark for dark screens (menu, login panel) |
| `frontend/public/brand/klinvexa-mark.svg` | the K app icon (collapsed menu) |
| `frontend/public/favicon.svg` | browser tab icon |
| `brand/klinvexa/final/` | every version: horizontal, no tagline, dark, black and white, app icons, in two colour sets |
| `brand/klinvexa/build_reference.py` | makes all of the above (run `python brand/klinvexa/build_reference.py`; needs `pip install fonttools shapely`) |

## Colours (the software uses the second set)
- Brief colours: navy `#0F172A`, blue `#2563EB`, teal `#14B8A6`, light grey `#E2E8F0`.
- Software colours: charcoal `#1F2430`, ember orange `#E0560F`, teal `#0F8F84`.
To switch the whole look later, change `DEFAULT_COLORS` in `frontend/src/config/clinic.ts` and re-run the logo script with the other colour set.
Preview a colour set without saving it: add `?palette=klinvexa` (brief colours) or `?palette=default` to any address.

## Font
Satoshi Bold (wordmark) and Satoshi Regular (tagline), free for commercial use, licence in `backend/assets/fonts/`.

## How to use it
- Keep clear space around the logo of at least the height of the letter "i" dot.
- Do not stretch, recolour with other colours, add shadows or gradients. For one-colour use take the black or white versions.
- The name, logo and colours are a working choice: check the trademark and the domain before using the name publicly.
