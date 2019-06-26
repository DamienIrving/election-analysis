"""
Functions for analysing election data.

"""

import pdb
import glob

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import geoviews as gv
from geoviews import dim
#import cartopy.crs as ccrs
#from geoviews import opts, tile_sources as gvts


party_names = ['The Greens', 'Australian Greens']

def prepoll_filter(polling_place_name):
    if ('PPVC' in polling_place_name) or ('PREPOLL' in polling_place_name):
        not_prepoll = False
    else:
        not_prepoll = True
    
    return not_prepoll


def read_polling_place_data(electorate, year, remove_prepoll=False):
    """Create DataFrame from AEC senate first preference polling place data files"""
    
    assert year in [2019, 2016, 2013, 2010]
    
    #polling_pattern = 'data/Fed' + str(year)[2:] + '-GeneralPollingPlacesDownload*'
    polling_pattern = 'data/Fed19-GeneralPollingPlacesDownload*'
    polling_place_file = glob.glob(polling_pattern)[0]
    
    file_pattern = 'data/' + electorate + str(year)[2:] + '-SenateDivisionFirstPrefsByPollingPlaceDownload*'
    votes_file = glob.glob(file_pattern)[0]
    
    # Votes
    raw_votes_df = pd.read_csv(votes_file, skiprows=1)
    totals = raw_votes_df.groupby('PollingPlaceID').OrdinaryVotes.sum()
    
    greens_totals = raw_votes_df[raw_votes_df.PartyNm.isin(party_names)].groupby('PollingPlaceID').OrdinaryVotes.sum()

    totals_dict = {'PollingPlaceID': totals.index.values,
                   'DivisionNm': [electorate] * len(totals),
                   'TotalVotes': totals.values,
                   'GreensVotes': greens_totals.values,
                   'GreensPercentage': (greens_totals.values / totals.values) * 100}
    
    votes_df = pd.DataFrame(totals_dict)
    votes_df = votes_df.set_index('PollingPlaceID')
    
    # Polling places
    raw_polling_place_df = pd.read_csv(polling_place_file, skiprows=1)
    polling_place_df = raw_polling_place_df[raw_polling_place_df['DivisionNm'] == electorate]
    polling_place_df = polling_place_df[['PollingPlaceID', 'PollingPlaceNm', 'PremisesNm', 'Latitude', 'Longitude']]
    polling_place_df = polling_place_df.set_index('PollingPlaceID')
    
    # Join
    df = polling_place_df.join(votes_df)
    df = df.sort_values(by=['GreensPercentage'], ascending=False)
    
    if remove_prepoll:
        not_prepoll = df['PollingPlaceNm'].apply(prepoll_filter)
        df = df[not_prepoll]
    
    return df


def read_vote_type_data(year):
    """Create DataFrame from AEC senate first preference vote type data files"""

    assert year in [2019, 2016, 2013, 2010]
    
    file_pattern = 'data/Fed' + str(year)[2:] + '-SenateFirstPrefsByDivisionByVoteTypeDownload*'
    votes_type_file = glob.glob(file_pattern)[0]
        
    raw_votes_df = pd.read_csv(votes_type_file, skiprows=1)
    
    party_names = ['The Greens', 'Australian Greens']
    greens_totals = raw_votes_df[raw_votes_df.PartyName.isin(party_names)].groupby('DivisionNm')
    greens_totals = greens_totals['OrdinaryVotes', 'AbsentVotes', 'ProvisionalVotes',
                                  'PrePollVotes', 'PostalVotes', 'TotalVotes'].sum()

    totals = raw_votes_df.groupby('DivisionNm')['OrdinaryVotes', 'AbsentVotes', 'ProvisionalVotes',
                                                'PrePollVotes', 'PostalVotes', 'TotalVotes'].sum()

    df = greens_totals.join(totals, lsuffix='Greens', rsuffix='Total')
    
    return df


def get_polling_place_swing(df_current, df_previous):
    """Calculate the swing between two elections"""
    
    df = df_current.join(df_previous['GreensPercentage'], rsuffix='Previous')
    df['Swing'] = df['GreensPercentage'] - df['GreensPercentagePrevious']
    df = df.sort_values(by=['Swing'], ascending=False)
    
    return df


def mega_polling_place_df(electorate_list, current_year, previous_year, remove_prepoll=False):
    """Create a dataframe containing polling place data for many electorates."""
    
    df_list = []
    for electorate in electorate_list:
        df_current = read_polling_place_data(electorate, current_year,
                                             remove_prepoll=remove_prepoll)
        df_previous = read_polling_place_data(electorate, previous_year,
                                              remove_prepoll=remove_prepoll)
        df_swing = get_polling_place_swing(df_current, df_previous)
        df_list.append(df_swing)
    
    return pd.concat(df_list)


def plot_polling_place_vote(df, backend, electorate=None, color_range=None):
    """Setup for plotting the vote at each polling place."""
    
    assert backend in ['bokeh', 'matplotlib']
    
    if electorate:
        plot_df = df[df['DivisionNm'] == electorate]
    else:
        plot_df = df

    votes = gv.Dataset(plot_df, kdims=['GreensPercentage', 'TotalVotes'])
    points = votes.to(gv.Points, ['Longitude', 'Latitude'],
                      ['PollingPlaceNm', 'GreensVotes', 'TotalVotes', 'GreensPercentage'])

    if backend == 'bokeh':
        points = points.opts(color='GreensPercentage', cmap='Greens', size=10, 
                             tools=['hover'], width=600, height=600, padding=0.1,
                             colorbar=True, line_color='black',
                             title='Greens senate primary vote, 2019 Federal Election',
                             clabel='%', xaxis=None, yaxis=None)
                             #size=dim('TotalVotes')*0.015,
        background = gv.tile_sources.Wikipedia
        
    else:
        points = points.opts(color='GreensPercentage', cmap='Greens', s=30,
                             padding=0.1, colorbar=True,
                             title='Greens senate primary vote, 2019 Federal Election',
                             clabel='%', xaxis=None, yaxis=None)
        #background = gvts.CartoEco
        #background = background.opts(zoom=7, projection=ccrs.PlateCarree())

        background = gv.tile_sources.Wikipedia
        #background = background.opts(zoom=10)
    
    if color_range:
        points = points.redim.range(GreensPercentage=color_range)  

    return points * background


def plot_polling_place_swing(df, backend, electorate=None, color_range=None):
    """Setup for plotting the swing at each polling place.
    
    This will remove all polling places that don't exist 
    in both the current and previous election.
    
    """
    
    assert backend in ['bokeh']
    
    if electorate:
        plot_df = df[df['DivisionNm'] == electorate].dropna()
    else:
        plot_df = df.dropna()
    
    votes = gv.Dataset(plot_df, kdims=['Swing', 'GreensVotes'])
    points = votes.to(gv.Points, ['Longitude', 'Latitude'],
                      ['PollingPlaceNm', 'TotalVotes', 'GreensVotes', 'Swing'])

    if backend == 'bokeh':
        points = points.opts(color='Swing', cmap='RdBu_r', size=10,
                             tools=['hover'], width=600, height=600, padding=0.1,
                             colorbar=True, line_color='black',
                             title='Greens senate swing, 2019 vs 2016 Federal Election',
                             clabel='%', xaxis=None, yaxis=None)
                            # size=dim('GreensVotes')*0.1

    if color_range:
        points = points.redim.range(Swing=color_range)    

    background = gv.tile_sources.Wikipedia
    
    return points * background

def print_vote_type_by_electorate(vote_type, current_year, previous_year):
    """Print electorate senate result for a given vote type """

    assert current_year in [2019, 2016, 2013, 2010]
    assert previous_year in [2019, 2016, 2013, 2010]
    assert vote_type in ['OrdinaryVotes', 'AbsentVotes', 'ProvisionalVotes',
                         'PrePollVotes', 'PostalVotes', 'TotalVotes']
    
    print('## ' + vote_type + ' stats, ' + str(current_year) + ' vs ' + str(previous_year))
    
    electorates = ['Bass', 'Braddon', 'Clark', 'Franklin', 'Lyons']
    green_votes_current_sum = 0
    total_votes_current_sum = 0
    green_votes_previous_sum = 0
    total_votes_previous_sum = 0
    for electorate in electorates:
        df_current = read_vote_type_data(current_year)
        green_votes_current = df_current.loc[electorate][vote_type + 'Greens']
        total_votes_current = df_current.loc[electorate][vote_type + 'Total']
        percentage_current = (green_votes_current / total_votes_current) * 100

        df_previous = read_vote_type_data(previous_year)
        green_votes_previous = df_previous.loc[electorate][vote_type + 'Greens']
        total_votes_previous = df_previous.loc[electorate][vote_type + 'Total']
        percentage_previous = (green_votes_previous / total_votes_previous) * 100

        swing = percentage_current - percentage_previous

        print(electorate.upper())
        print('vote:', str(percentage_current.round(2)) + '%')
        print('swing:', str(swing.round(2)) + '%')

        green_votes_current_sum = green_votes_current_sum + green_votes_current
        total_votes_current_sum = total_votes_current_sum + total_votes_current
        green_votes_previous_sum = green_votes_previous_sum + green_votes_previous
        total_votes_previous_sum = total_votes_previous_sum + total_votes_previous

    percentage_current_tas = (green_votes_current_sum / total_votes_current_sum) * 100 
    percentage_previous_tas = (green_votes_previous_sum / total_votes_previous_sum) * 100

    swing = percentage_current_tas - percentage_previous_tas

    print('TASMANIA')
    print('vote:', str(percentage_current_tas.round(2)) + '%')
    print('swing:', str(swing.round(2)) + '%')
    