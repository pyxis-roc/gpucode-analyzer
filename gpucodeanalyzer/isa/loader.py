from .sass.sass_dispatch import SASSDispatcher

DISPATCHERS = [SASSDispatcher()]

def get_dispatcher(filename):
    for d in DISPATCHERS:
        if d.can_handle_by_ext(filename):
            return d

def get_loader_class(filename):
    d = get_dispatcher(filename)
    return d.loader() if d is not None else None

def load(filename):
    cls = get_loader_class(filename)

    if cls is None:
        raise ValueError(f"Unrecognized file format {filename}")
    else:
        return cls(filename)

