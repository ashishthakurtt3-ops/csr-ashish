try:
    import playwright
    print('Playwright is installed')
except ImportError:
    print('Playwright NOT installed')

try:
    import curl_cffi
    print('curl_cffi is installed')
except ImportError:
    print('curl_cffi NOT installed')

