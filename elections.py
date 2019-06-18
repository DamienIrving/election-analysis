"""
Functions for analysing election data.

"""

import glob

import pandas as pd
import geoviews as gv
from geoviews import dim


def prepoll_filter(polling_place_name):
    if ('PPVC' in polling_place_name) or ('PREPOLL' in polling_place_name):
        not_prepoll = False
    else:
        not_prepoll = True
    
    return not_prepoll


def create_electorate_df(electorate, year, remove_prepoll=False):
    """Create DataFrame from AEC data files"""
    
    polling_place_file = 'data/Fed19-GeneralPollingPlacesDownload-24310.csv'
    file_pattern = 'data/' + electorate + str(year)[2:] + '*'
    votes_file = glob.glob(file_pattern)[0]
    
    # Votes
    raw_votes_df = pd.read_csv(votes_file, skiprows=1)
    totals = raw_votes_df.groupby('PollingPlaceID').OrdinaryVotes.sum()
    greens_totals = raw_votes_df[raw_votes_df.PartyNm == 'The Greens'].groupby('PollingPlaceID').OrdinaryVotes.sum()

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
    df = polling_place_df.join(votes_df).dropna()
    df = df.sort_values(by=['GreensPercentage'], ascending=False)
    
    if remove_prepoll:
        not_prepoll = df['PollingPlaceNm'].apply(prepoll_filter)
        df = df[not_prepoll]
    
    return df


def get_swing(df_current, df_previous):
    """Calculate the swing between two elections"""
    
    df = df_current.join(df_previous['GreensPercentage'], rsuffix='Previous')
    df['Swing'] = df['GreensPercentage'] - df['GreensPercentagePrevious']
    df = df.sort_values(by=['Swing'], ascending=False)
    
    return df


def create_mega_df(electorate_list, current_year, previous_year, remove_prepoll=False):
    """Create a dataframe containing many electorates."""
    
    df_list = []
    for electorate in electorate_list:
        df_current = create_electorate_df(electorate, current_year,
                                          remove_prepoll=remove_prepoll)
        df_previous = create_electorate_df(electorate, previous_year,
                                           remove_prepoll=remove_prepoll)
        df_swing = get_swing(df_current, df_previous)
        df_list.append(df_swing)
    
    return pd.concat(df_list)


def vote_plot_setup(df, backend, electorate=None, color_range=None):
    """Setup for plotting the vote."""
    
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
    else:
        points = points.opts(color='GreensPercentage', cmap='Greens', s=30,
                             padding=0.1, colorbar=True,
                             title='Greens senate primary vote, 2019 Federal Election',
                             clabel='%', xaxis=None, yaxis=None)
    
    if color_range:
        points = points.redim.range(GreensPercentage=color_range)  
    
    tiles = gv.tile_sources.Wikipedia
    
    return tiles, points


def swing_plot_setup(df, backend, electorate=None, color_range=None):
    """Setup for plotting the swing"""
    
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

    tiles = gv.tile_sources.Wikipedia
    
    return tiles, points