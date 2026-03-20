# gpucode-analyzer

This is a framework for building analyses of binary GPU code. It is
intended to be generic and not specific to any particular ISA.

Currently it only supports NVIDIA's SASS ISA.

## Installation

Install this in develop mode, by executing in the directory:

```
pip install -e .
```

## Utilities

### buildcfg

Run `gca-buildcfg` to obtain a control flow graph as a DOT file.

### skelcfg

Run `gca-skelcfg` to obtain a skeletonized control-flow graph as a DOT file.

### slice

Run `gca-slicecfg` to obtain a sliced control-flow graph as a DOT
file. Unlike `gca-skelcfg`, this allows you to specify instructions to
mark as important either using their addresses/labels or a regular
expression matching the opcode. Example:

```
gca-skelcfg test.sass re:WARPSYNC 00ab
```

You can use `-o` to obtain a DOT file, and `-c` to obtain a text file
of the code.


### classcfg

Run `gca-classcfg` to obtain the classification of each instruction, as
well as a static summary count.

### cfg2c

Run `gca-cfg2c` to convert CFG to its skeleton and then to C. This is an
experimental tool not meant for general use. It only works for SASS
files. It outputs a C file which when run will output a basic block
count.

## bbcount

Run `gca-bbcount` with the source code and the basic block count to obtain
the frequency of each instruction. A count of generic operations
is also provided.


## Usage as a Library

NOTE: This section is obsolete. A generic dispatcher that can
recognize file formats and return the appropriate loader is available,
see `classifier.py` for example usage.

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


