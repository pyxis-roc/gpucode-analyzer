from .sass.sass_dispatch import SASSDispatcher
import json

DISPATCHERS = [SASSDispatcher()]

def get_metadata(metadatafile):
    if metadatafile:
        with open(metadatafile, "r") as f:
            metadata = json.load(f)
            return metadata

    return None

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


def inject_loader_args(p):
    p.add_argument("-m", dest="metadata", help="Metadata file")
    p.add_argument("--fn", help="Function")
    p.add_argument("asmfile")

def load_asmfile(args):
    metadata = get_metadata(args.metadata)
    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile, metadata=metadata)

    return metadata, disp, code
