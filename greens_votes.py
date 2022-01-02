"""Greens vote information from general electoral commission data"""

import argparse
import pdb

import numpy as np
import pandas as pd


def prepoll_filter(polling_place_name):
    if ('PPVC' in polling_place_name) or ('PREPOLL' in polling_place_name):
        not_prepoll = False
    else:
        not_prepoll = True
    
    return not_prepoll


def hospital_filter(polling_place_name):
    if 'special hospital' in polling_place_name.lower():
        not_hospital = False
    else:
        not_hospital = True
    
    return not_hospital


def get_name_and_address(polling_place, election_polling_places):
    """Get the PollingPlaceNm, PremisesNm and PremisesAddress."""
    
    ref_name = polling_place.split('(')[0].strip()
    election_polling_place_list = election_polling_places['PollingPlaceNm'].to_list()
    
    if polling_place in election_polling_place_list:
        selection = election_polling_places['PollingPlaceNm'] == polling_place
    else:
        assert ref_name in election_polling_place_list, 'Polling place name mismatch'
        selection = election_polling_places['PollingPlaceNm'] == ref_name
        
    election_info = election_polling_places[selection]
    address_headers = [header for header in election_info.columns if 'PremisesAddress' in header]
    election_info['PremisesAddress'] = election_info[address_headers].apply(lambda x: ', '.join(x[x.notnull()]), axis=1)
    election_address = election_info['PremisesAddress'].values[0] + ', ' + election_info['PremisesSuburb'].values[0].upper()
    election_premises = election_info['PremisesNm'].values[0]
    print(f'Election polling place: {election_premises}, {election_address}')

    return ref_name, election_premises, election_address
    

def add_polling_place_info(votes_dict,
                           election_polling_places,
                           ref_polling_places,
                           division):
    """Merge election day and reference polling place info."""
    
    votes_dict['DivisionNm'] = []
    votes_dict['LegCo'] = []
    votes_dict['LocalCouncil'] = []
    votes_dict['PremisesAddress'] = []
    votes_dict['PremisesNm'] = []
    votes_dict['Latitude'] = []
    votes_dict['Longitude'] = []

    
    for polling_place in votes_dict['PollingPlaceNm']:
        print(polling_place)
        ref_name, election_premises, election_address = get_name_and_address(polling_place, election_polling_places)
        ref_info = ref_polling_places[ref_polling_places['PollingPlaceNm'] == ref_name]
        div_ref_info = ref_info[ref_info['DivisionNm'] == division]
        if not div_ref_info.empty:
            ref_info = div_ref_info
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
                votes_dict['DivisionNm'].append(ref_match['DivisionNm'])
                votes_dict['LegCo'].append(ref_match['LegCo'])
                votes_dict['LocalCouncil'].append(ref_match['LocalCouncil'])
                votes_dict['PremisesNm'].append(ref_match['PremisesNm'])
                votes_dict['PremisesAddress'].append(f"{address}, {suburb} {postcode}")
                votes_dict['Latitude'].append(ref_match['Latitude'])
                votes_dict['Longitude'].append(ref_match['Longitude'])
                break
        assert address_match or premises_match, f"No reference polling place for {polling_place}"

    return votes_dict


def read_tec_votes(votes_file, thousands):
    """Read a TEC votes file."""
    
    thousands_dict = {'space': ' ', 'comma': ','}
    raw_votes_df = pd.read_csv(votes_file, thousands=thousands_dict[thousands], skipinitialspace=True)
    raw_votes_df = raw_votes_df.dropna(axis=1, how='all')
    column_end = np.where(raw_votes_df.columns.values == 'Total Ordinary Votes')[0][0]
    polling_places = raw_votes_df.columns.values[1: column_end]
    total_votes = raw_votes_df[raw_votes_df['Candidates'] == 'Total Formal Votes'].values[0][1:column_end]
    greens_votes = raw_votes_df[raw_votes_df['Candidates'] == 'Tasmanian Greens'].values[0][1:column_end]
    greens_pct = (greens_votes / total_votes) * 100
    greens_pct = greens_pct.astype(float)
    
    votes_dict = {'PollingPlaceNm': polling_places,
                  'GreensVotes': greens_votes,
                  'TotalVotes': total_votes,
                  'GreensPercentage': greens_pct}
                 
    return votes_dict
    

def read_tec_polling_places(polling_places_file):
    """Read a TEC polling places file."""
    
    polling_places = pd.read_csv(polling_places_file,
                                 skipinitialspace=True)
    
    return polling_places


def read_senate_votes(votes_file):
    """Read an AEC senate votes file."""
    
    party_names = ['The Greens', 'Australian Greens']
    
    raw_votes_df = pd.read_csv(votes_file, skiprows=1)

    not_prepoll = raw_votes_df['PollingPlaceNm'].apply(prepoll_filter)
    raw_votes_df = raw_votes_df[not_prepoll]
    not_hospital = raw_votes_df['PollingPlaceNm'].apply(hospital_filter)
    raw_votes_df = raw_votes_df[not_hospital]
    
    polling_places = raw_votes_df['PollingPlaceNm'].unique()
    total_votes = raw_votes_df.groupby('PollingPlaceID').OrdinaryVotes.sum()
    greens_votes = raw_votes_df[raw_votes_df.PartyNm.isin(party_names)].groupby('PollingPlaceID').OrdinaryVotes.sum()
    greens_pct = (greens_votes / total_votes) * 100
    greens_pct = greens_pct.astype(float)
    
    votes_dict = {'PollingPlaceNm': list(polling_places),
                  'GreensVotes': greens_votes,
                  'TotalVotes': total_votes,
                  'GreensPercentage': greens_pct}
                  
    return votes_dict


def read_aec_polling_places(polling_places_file, division):
    """Read an AEC polling places file."""
    
    raw_polling_places = pd.read_csv(polling_places_file, skiprows=1)
    polling_places = raw_polling_places[raw_polling_places['DivisionNm'] == division]
#    polling_places = polling_places.set_index('PollingPlaceID')

    return polling_places
    

def main(args):
    """Run the program."""   

    if args.election == 'state':
        votes_dict = read_tec_votes(args.votes_file, args.thousands)
        election_polling_places = read_tec_polling_places(args.election_polling_places_file)
    elif args.election == 'senate':
        votes_dict = read_senate_votes(args.votes_file)
        election_polling_places = read_aec_polling_places(args.election_polling_places_file, args.division)
    else:
        raise ValueError(f'unrecognised election: {election}')
        
    ref_polling_places = pd.read_csv(args.reference_polling_places_file,
                                     na_filter=False, skipinitialspace=True) 
        
    votes_dict = add_polling_place_info(votes_dict,
                                        election_polling_places,
                                        ref_polling_places,
                                        args.division)
      
    votes_df = pd.DataFrame(votes_dict)
    votes_df = votes_df.round({'GreensPercentage': 1})
    votes_df['Latitude'] = votes_df['Latitude'].map('{:.6f}'.format)
    votes_df['Longitude'] = votes_df['Longitude'].map('{0:.6f}'.format)
    votes_df.sort_values(['PollingPlaceNm'], inplace=True)
    votes_df.to_csv(args.outfile, index=False)
    
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, 
                                     argument_default=argparse.SUPPRESS,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("election", type=str, choices=('state', 'senate'), help="Election")
    parser.add_argument("division", type=str, help="Division name")
    parser.add_argument("votes_file", type=str, help="Votes file from AEC or TEC")
    parser.add_argument("election_polling_places_file", type=str, help="Election day polling place file")
    parser.add_argument("reference_polling_places_file", type=str, help="Reference polling place file")
    parser.add_argument("outfile", type=str, help="Output file")
    
    parser.add_argument("--thousands", type=str, choices=('comma', 'space'), default='space',
                       help="Data file convention for denoting thousands separation in numbers")
    
    args = parser.parse_args()
    main(args)
