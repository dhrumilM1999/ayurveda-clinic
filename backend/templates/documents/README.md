SAFE TO EDIT: print / PDF templates (prescription, invoice, receipt, ...) live in this folder.

## How the look is controlled (PDF settings)

Every template gets one variable called `ps` (the "PDF settings" the owner chose in the app: Settings -> PDF settings).
Use it instead of writing a colour or size in the template, so the screen keeps working:

| In the template | Means |
|---|---|
| `{{ ps.accent_color }}`, `{{ ps.accent_soft }}` | the colour, and a pale tint of it for table headings |
| `{{ ps.base_pt }}pt` | the base text size (paper size and "text size %" already worked in) |
| `{{ ps.margin }}`, `page_width`, `page_height` | the page |
| `ps.show_logo`, `ps.show_letterhead`, `ps.show_signature`, `ps.show_qr`, `ps.show_doctor_reg`, `ps.show_duplicate_watermark`, `ps.show_gst_columns` | switches (true / false) |
| `ps.header_text`, `ps.footer_text`, `ps.terms_text`, `ps.thank_you_text` | extra lines of text |

Templates are filled by `render()` in `backend/apps/documents/services.py` (bills: `backend/apps/billing/pdf.py`,
labels: `backend/apps/pharmacy/labels.py` and `stock_labels.py`, reports: `backend/apps/reports/exports.py`); all of them
pass `ps`. A new template must pass `ps` too, or the switches count as "off".
The Ayurveda case sheet keeps its own green: it changes colour only when the owner picks a colour other than the
standard one. The starting values are `DEFAULTS` in `backend/apps/documents/print_settings.py`.
