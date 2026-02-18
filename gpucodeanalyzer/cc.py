#!/usr/bin/env python3

import argparse

def main():
    p = argparse.ArgumentParser(description="Run compiler on gca-cfg2c code")

    p.add_argument("args", nargs="+", help="Source files and other arguments to CC")
    p.add_argument("-o", dest="output")

    args = p.parse_args()

if __name__ == "__main__":
    main()

    
