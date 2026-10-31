from .state import CRAWL_TASK_STATE

def start_background_crawl(*args, **kwargs):
    from .crawler import start_background_crawl as _crawl
    return _crawl(*args, **kwargs)
