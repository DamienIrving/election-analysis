"""Merge multiple CSV files"""

import argparse
import pandas as pd


def main(args):
    """Run the program."""

    combined_csv = pd.concat([pd.read_csv(f) for f in args.infiles])
    combined_csv.to_csv(args.outfile, index=False)
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("infiles", type=str, nargs='*', help="Input files")
    parser.add_argument("outfile", type=str, help="Output file")    
    args = parser.parse_args()
    main(args)
