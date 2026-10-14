# Online enquiry from the clinic website

People who visit your clinic website can ask for an appointment. Their request lands on the **Online enquiry** screen,
where the front desk calls or messages them. They are not patients until the desk registers them.

## Turn it on

1. Log in as the owner → **Additional settings** → group **Online enquiry** → switch on
   **Online enquiry from the clinic website**.
2. A new menu item **Online enquiry** appears for the owner, admin and receptionist. A red number shows how many
   enquiries are still **New**.

## Put the form on your website (two ways)

The form is a normal web page of this software: **`https://YOUR-APP-ADDRESS/enquiry`** (on the demo PC:
`http://localhost:5173/enquiry`). Nobody needs to log in to use it. It works on a phone and in English, Gujarati
and Hindi.

1. **A button or link** on your website: "Book an appointment" → the address above.
2. **Inside a page** (iframe): paste this where the form should appear (the screen **Online enquiry → Link for your
   website → Copy embed code** gives you the same line with the right address):

   ```html
   <iframe src="https://YOUR-APP-ADDRESS/enquiry" width="100%" height="760" style="border:0"></iframe>
   ```

If your website developer prefers to build their own form, they can send the data straight to the API. Add the
website address to `.env` first (otherwise the browser blocks it):

```
ENQUIRY_ALLOWED_ORIGINS=https://www.myclinic.in
```

```
GET  /api/v1/public/enquiry-form/   -> clinic name, branches, quick concerns, "enabled"
POST /api/v1/public/enquiries/      JSON: name, phone, email, concern, message, preferred_date (YYYY-MM-DD),
                                    preferred_time (any|morning|evening), language (en|gu|hi), branch (id, optional),
                                    consent_contact (must be true)
```

## What the front desk does

| Step | Where |
|---|---|
| See new enquiries | **Online enquiry** (filters: Open, New, Contacted, Appointment booked, Not interested, Closed) |
| Call / WhatsApp | The phone and WhatsApp buttons on each row (WhatsApp opens a ready message; the staff presses Send) |
| Write what happened, set "call again on" | **Notes** |
| Person decides to come | **Register patient** (name and mobile are already filled; the enquiry is linked to the new patient), then book the appointment, then set the status **Appointment booked** |
| Phone call or walk-in asking | **Add phone enquiry** (so every enquiry is in one list) |

## Safety (read once)

- The form asks only: name, mobile, optional email, what the problem is about, a short message, preferred date and
  time, and a tick that the clinic may contact them (DPDP consent). The message box says not to write medical reports.
- Spam control: a hidden field that only bots fill, a limit of 10 enquiries per hour from one internet address, and the
  same mobile number within 10 minutes counts as one enquiry. Nothing is sent to anyone automatically.
- Enquiries are never deleted (only the status changes). Everything staff change is written in the audit log.
- Switching the feature off closes the form ("Online enquiries are closed") and hides the screen. Nothing is deleted.
- For several clinics on one server later: the public form currently belongs to the first clinic. The place to choose
  the clinic from the web address is marked in `backend/apps/organizations/views.py` (`PublicBrandingView`).
