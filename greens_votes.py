"""Greens vote information from general electoral commission data"""

import argparse
import pandas as pd


def merge_polling_place_info(polling_places,
                             election_polling_place_df,
                             ref_polling_place_df):
    """Merge election day and reference polling place info."""
    
    merge_dict = {}
    merge_dict['legco'] = []
    merge_dict['council'] = []
    merge_dict['address'] = []
    merge_dict['premises'] = []
    merge_dict['lat'] = []
    merge_dict['lon'] = []

    for polling_place in polling_places:
        print(polling_place)
        ref_polling_place = polling_place.split('(')[0].strip()
    
        if polling_place in election_polling_place_df['PollingPlaceName'].to_list():
            selection = election_polling_place_df['PollingPlaceName'] == polling_place
        else:
            assert ref_polling_place in election_polling_place_df['PollingPlaceName'].to_list(), \
            'Polling place name mismatch'
            selection = election_polling_place_df['PollingPlaceName'] == ref_polling_place
        election_info = election_polling_place_df[selection]
        
        election_address = election_info['PremiseAddress1'].values[0] + ', ' + election_info['PremiseLocality'].values[0].upper()
        election_premises = election_info['PremiseName'].values[0]
        print(f'Election polling place: {election_premises}, {election_address}')
    
        ref_info = ref_polling_place_df[ref_polling_place_df['PollingPlaceNm'] == ref_polling_place]
        address_match = False
        premises_match = False
        for index, ref_match in ref_info.iterrows():
            ref_address = ref_match['PremisesAddress'] + ', ' + ref_match['PremisesSuburb']
            ref_premises = ref_match['PremisesNm']
            address_match = (ref_address.lower() in election_address.lower()) or (election_address.lower() in ref_address.lower())
            premises_match = (ref_premises.lower() in election_premises.lower()) or (election_premises.lower() in ref_premises.lower())
            print(f'Reference polling place: {ref_premises}, {ref_address}')
            if address_match or premises_match:
                address = ref_match['PremisesAddress']
                suburb = ref_match['PremisesSuburb']
                postcode = ref_match['PremisesPostCode']
                merge_dict['legco'].append(ref_match['LegCo'])
                merge_dict['council'].append(ref_match['LocalCouncil'])
                merge_dict['premises'].append(ref_match['PremisesNm'])
                merge_dict['address'].append(f"{address}, {suburb} {postcode}")
                merge_dict['lat'].append(ref_match['Latitude'])
                merge_dict['lon'].append(ref_match['Longitude'])
                break
        assert address_match or premises_match, f"No reference polling place for {polling_place}"

    return merge_dict


def main(args):
    """Run the program."""
    
    raw_votes_df = pd.read_csv(args.votes, skiprows=1, thousands=' ')
    raw_votes_df = raw_votes_df.dropna(axis=1, how='all')

    polling_places = raw_votes_df.columns.values[1: -7]
    total_votes = raw_votes_df[raw_votes_df['Candidates'] == 'Total Formal Votes'].values[0][1:-7]
    greens_votes = raw_votes_df[raw_votes_df['Candidates'] == 'Tasmanian Greens'].values[0][1:-7]
    greens_pct = (greens_votes / total_votes) * 100
    greens_pct = greens_pct.astype(float)
    
    election_polling_place_df = pd.read_csv(args.election_polling_places)
    ref_polling_place_df = pd.read_csv(args.reference_polling_places, na_filter=False)
    merge_dict = merge_polling_place_info(polling_places,
                                          election_polling_place_df,
                                          ref_polling_place_df)
    
    votes_dict = {'PollingPlaceNm': polling_places,
                  'DivisionNm': [args.division] * len(polling_places),
                  'GreensVotes': greens_votes,
                  'TotalVotes': total_votes,
                  'GreensPercentage': greens_pct,
                  'PremisesNm': merge_dict['premises'],
                  'PremisesAddress': merge_dict['address'],
                  'Latitude': merge_dict['lat'],
                  'Longitude': merge_dict['lon'],
                  'LegCo': merge_dict['legco'],
                  'LocalCouncil': merge_dict['council']
                  }    
    votes_df = pd.DataFrame(votes_dict)
    votes_df = votes_df.round({'GreensPercentage': 1})
    votes_df['Latitude'] = votes_df['Latitude'].map('{:.6f}'.format)
    votes_df['Longitude'] = votes_df['Longitude'].map('{0:.6f}'.format)
    votes_df.to_csv(args.outfile)
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("division", type=str, help="Division name")
    parser.add_argument("votes", type=str, help="Votes file from AEC or TEC")
    parser.add_argument("election_polling_places", type=str, help="Election day polling place file")
    parser.add_argument("reference_polling_places", type=str, help="Reference polling place file")
    parser.add_argument("outfile", type=str, help="Output file")
    
    args = parser.parse_args()
    main(args)
