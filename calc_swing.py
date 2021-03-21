"""Merge data from two elections and calculate booth swings"""

import argparse
import pandas as pd


def main(args):
    """Run the program."""
    
    recent_df = pd.read_csv(args.recent_election_csv)
    old_df = pd.read_csv(args.old_election_csv)
    old_df_clipped = old_df[['PollingPlaceNm',
                             'GreensVotes',
                             'TotalVotes',
                             'GreensPercentage',
                             'PremisesNm',
                             'PremisesAddress']]

    swing_df = pd.merge(recent_df,
                        old_df_clipped,
                        how='left',
                        on=['PollingPlaceNm'],
                        suffixes=('_' + args.recent_year, '_' + args.old_year),)
                        
    swing_df['SwingPercentage'] = swing_df['GreensPercentage_' + args.recent_year] - \
                                  swing_df['GreensPercentage_' + args.old_year]
    
    if not args.verbose:
        swing_df = swing_df[['PollingPlaceNm',
                             'DivisionNm',
                             'GreensVotes_' + args.recent_year,
                             'TotalVotes_' + args.recent_year,
                             'GreensPercentage_' + args.recent_year,
                             'SwingPercentage',
                             'PremisesNm_' + args.recent_year,
                             'PremisesAddress_' + args.recent_year,
                             'Latitude',
                             'Longitude',
                             'LegCo',
                             'LocalCouncil']]
                             
    swing_df.to_csv(args.outfile, index=False)
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("recent_election_csv", type=str, help="vote file for recent election")
    parser.add_argument("recent_year", type=str, help="year of the recent election")
    parser.add_argument("old_election_csv", type=str, help="vote file for recent election")
    parser.add_argument("old_year", type=str, help="year of the old election")
    parser.add_argument("outfile", type=str, help="Output file")
    parser.add_argument("--verbose", action="store_true", default=False,
                        help="Include more old election information in output")    
    args = parser.parse_args()
    main(args)
