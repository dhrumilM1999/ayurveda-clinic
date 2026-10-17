"""
PDF safety: the PDF maker may only use pictures that are embedded in the page itself ("data:" pictures such as
the logo and QR code). It never opens files from the server disk or other websites, even if someone typed such
an address into a name or a note.
ASK FIRST before editing.
"""
try:  # WeasyPrint 68 and newer: a fetcher object that only allows "data:" addresses
    from weasyprint.urls import URLFetcher

    embedded_only_fetcher = URLFetcher(allowed_protocols=["data"])

    def check_address(url):
        return embedded_only_fetcher.fetch(url)
except ImportError:  # older WeasyPrint: a function
    from weasyprint import default_url_fetcher

    def embedded_only_fetcher(url, *args, **kwargs):
        if not url.lower().startswith("data:"):
            raise ValueError("Only embedded pictures are allowed in documents.")
        return default_url_fetcher(url, *args, **kwargs)

    check_address = embedded_only_fetcher
