# AyuSutra: the software's brand

**Name:** AyuSutra (Ayu = life, Sutra = thread / rule of knowledge). **Tagline:** Ayurveda clinic software.
It is the name of the *software*. The clinic's own name and logo (for example Vednath) stay the clinic's: they are on the prescriptions, bills and the menu.

## Where it is shown, and where it is not
- Shown **inside the software only:** top of the left menu, login screen, browser tab and tab icon.
- **Never printed** on prescriptions, bills, certificates, labels or any PDF (those carry only the clinic's own letterhead). The print templates do not contain it.

## The logo
A white letter **A** made of two leaves (the plant), with a golden **drop of medicated oil** on top (Snehana / the bindu), on a blue square.

| File | Use |
|---|---|
| `frontend/public/brand/ayusutra-mark.svg` | the square mark (tab icon, menu, app icon) |
| `frontend/public/brand/ayusutra-logo.svg` | mark + name, for light backgrounds |
| `frontend/public/brand/ayusutra-logo-white.svg` | mark + name, for dark backgrounds |
| `docs/brand/*.png` | the same as pictures (mark 1024 px, logos 3120 px) for a website, a visiting card or social media |

## Colours
| Name | Code |
|---|---|
| Blue (main) | `#1d4ed8` |
| Navy (menu) | `#0b1f3f` |
| Light blue (accent) | `#7fb0ff` |
| Gold (the drop) | `#f59e0b` |

Font of the name: Fraunces (bold). Text font in the app: Plus Jakarta Sans.

## Change the name or the logo
- Name and file path: `frontend/src/config/clinic.ts` (`softwareConfig`).
- Replace the three files in `frontend/public/brand/` with your own (keep the file names).
- The words "Ayurveda clinic software" (English, Gujarati, Hindi): `frontend/src/i18n/*.json`, key `layout.softwareTagline`.

> Before using the name publicly (website, selling to other clinics), search that nobody else uses "AyuSutra" and register the trademark. The name here is a suggestion.
