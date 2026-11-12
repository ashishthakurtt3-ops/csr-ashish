for mod in ['pypdf', 'pdfplumber', 'fitz', 'pypdf2']:
    try:
        __import__(mod)
        print(f"{mod} is installed")
    except ImportError:
        print(f"{mod} NOT installed")

