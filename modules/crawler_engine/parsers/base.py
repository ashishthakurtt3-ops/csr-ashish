class BaseParser:
    def __init__(self, company, url, final_url, html_content):
        self.company = company
        self.url = url
        self.final_url = final_url
        self.html_content = html_content

    def extract_jobs(self):
        """Returns a list of dicts representing extracted jobs."""
        return []

    def extract_csr(self):
        """Returns a list of dicts representing extracted CSR info."""
        return []

    def extract_contacts(self):
        """Returns a list of dicts representing contacts."""
        return []

    def get_extraction_method(self):
        return "BASE"
