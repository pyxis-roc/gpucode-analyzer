# gpucode-analyzer

This is a framework for building analyses of binary GPU code. It is
intended to be generic and not specific to any particular ISA.

Currently it only supports NVIDIA's SASS ISA.

## Installation

Install this in develop mode, by executing in the directory:

```
pip install -e .
```


## Usage

First you must load the code using an ISA-specific loader. For SASS,
this is the `SASSFile` loader.

```
from gpucodeanalyzer.isa.sass import SASSFile

sass = SASSFile(filename)
```

This is currently not a full-fledged SASS parser, so expect some rough
edges. You can iterate through the `code` attribute to get the
instructions:

```
for i in sass.code:
    print(i)
```

Of particular interest are the `reads()` and `writes()` methods which
return the registers read and written by the instruction
respectively. Note that the predicate register, if any, is available
via the `predicate` property.

## Building a CFG

The analyzer contains utilities for building a CFG generically. See
the file `buildcfg.py` for code that builds a CFG. Once built, you can
access each basic block in the program.


