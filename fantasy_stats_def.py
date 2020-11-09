#!/usr/bin/env python
# coding: utf-8

# ### TO DO ###
#
# - [x] Fix no data for first week
# - [x] Add cumulative to standings
# - [x] Check by week when new data comes
# - [ ] Add value for players who don't play
# - [x] Goal difference statistic
# - [ ] Above or below average score
# - [ ] Pandas Stylesheet
# - [ ] Graphs


import requests
import pandas as pd
# import numpy as np

# #### Definitions ####

owners = ['Luke', 'Emma', 'Fat', 'Olivia', 'Claire', 'Matt', 'George']
owner_ids = ['18900', '18935', '18967', '19180', '19424', '20043', '20626']
team_details_url = {}
lineup_url = {}

for owner_id, owner in enumerate(owners):
    team_details_url[owner] = 'https://draft.premierleague.com/api/entry/' + \
        owner_ids[owner_id] + '/history'
    for gameweek in range(1, 39):
        lineup_url[owner, gameweek] = 'https://draft.premierleague.com/api/entry/' + \
            owner_ids[owner_id] + '/event/' + str(gameweek)

bootstrap_url = 'https://draft.premierleague.com/api/bootstrap-static'
fantasy_bootstrap_url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
player_owner_url = 'https://draft.premierleague.com/api/league/5857/element-status'
league_details_url = 'https://draft.premierleague.com/api/league/5857/details'
transactions_url = 'https://draft.premierleague.com/api/draft/league/5857/transactions'

current_gameweek = requests.get(bootstrap_url).json()['events']['current']
total_fantasy_players = requests.get(fantasy_bootstrap_url).json()['total_players']


def url_to_df(url, datatype):
    request = requests.get(url)
    json = request.json()
    df = pd.DataFrame(json[datatype])
    return df


# #### Create Dataframes ####

raw_player_types_df = url_to_df(bootstrap_url, 'element_types')

raw_teams_df = url_to_df(bootstrap_url, 'teams')

raw_player_owner_df = url_to_df(player_owner_url, 'element_status')
raw_player_owner_df = raw_player_owner_df.sort_values('element', ignore_index=True)

raw_league_entries_df = url_to_df(league_details_url, 'league_entries')
raw_league_standings_df = url_to_df(league_details_url, 'standings')
raw_league_standings_df = raw_league_standings_df.sort_values('league_entry', ignore_index=True)
raw_league_standings_df = pd.concat(
    [raw_league_entries_df[['entry_id', 'id', 'entry_name', 'player_first_name', 'waiver_pick']],
     raw_league_standings_df[['last_rank', 'rank', 'event_total', 'total']]], axis=1)

raw_player_info_df = url_to_df(bootstrap_url, 'elements')
raw_player_info_df['team'] = raw_player_info_df.team.map(raw_teams_df.set_index('id').name)
raw_player_info_df['element_type'] = raw_player_info_df.element_type.map(
    raw_player_types_df.set_index('id').singular_name)
raw_player_info_df.insert(3, 'owner',
                          raw_player_owner_df.owner.map(raw_league_entries_df.set_index('entry_id').player_first_name))

transactions_df = url_to_df(transactions_url, 'transactions')
transactions_df['entry'] = transactions_df.entry.map(
    raw_league_entries_df.set_index('entry_id').player_first_name)
transactions_df['player in'] = transactions_df.element_in.map(
    raw_player_info_df.set_index('id').web_name)
transactions_df['player out'] = transactions_df.element_out.map(
    raw_player_info_df.set_index('id').web_name)
transactions_df = transactions_df[['entry', 'kind', 'result', 'player in', 'player out']]

successful_transactions_df = transactions_df.loc[transactions_df['result'] == 'a']
failed_transactions_df = transactions_df.loc[transactions_df['result'] != 'a']


# #### Functions for making specific DataFrames ####

def get_lineup_info(p_owner, p_gameweek=current_gameweek, p_with_totals=True):
    # check valid gameweek:
    if p_gameweek > current_gameweek:
        print("Gameweek not yet played")
        return 'ERROR'

    # create dataframe:
    info_columns = ['name', 'team', 'position']
    points_columns = ['minutes', 'goals_scored', 'goals_conceded', 'penalties_missed', 'penalties_saved', 'assists',
                      'saves', 'own_goals', 'yellow_cards', 'red_cards', 'total_points']
    lineup_df = pd.DataFrame(columns=info_columns + ['value', 'selected %'] + points_columns,
                             index=url_to_df(lineup_url[p_owner, p_gameweek], 'picks')['element'])
    lineup_df.insert(15, 'foul points', pd.Series([], dtype=object))

    # all player data:
    lineup_df['name'] = lineup_df.index.map(raw_player_info_df.set_index('id').web_name)
    lineup_df['team'] = lineup_df.index.map(raw_player_info_df.set_index('id').team)
    lineup_df['position'] = lineup_df.index.map(raw_player_info_df.set_index('id').element_type)

    # player by player data:
    for i, player in enumerate(lineup_df.index):
        for data in points_columns + ['value', 'selected %']:
            lineup_df.loc[lineup_df.index == player, data] = 0
        player_url = 'https://draft.premierleague.com/api/element-summary/' + str(player)
        player_df = url_to_df(player_url, 'history')
        fantasy_player_url = 'https://fantasy.premierleague.com/api/element-summary/' + \
            str(player) + '/'
        fantasy_player_df = url_to_df(fantasy_player_url, 'history')
        if not player_df.loc[player_df['event'] == p_gameweek].empty:
            lineup_df.loc[lineup_df.index == player, 'value'] = \
                fantasy_player_df.loc[fantasy_player_df['round'] == p_gameweek]['value'].iloc[0] / 10
            lineup_df.loc[lineup_df.index == player, 'selected %'] = \
                fantasy_player_df.loc[fantasy_player_df['round'] ==
                                      p_gameweek]['selected'].iloc[0] / total_fantasy_players * 100
            for data in points_columns:
                lineup_df.loc[lineup_df.index == player, data] = \
                    player_df.loc[player_df['event'] == p_gameweek][data].iloc[0]
            if not lineup_df.loc[lineup_df.index == player, 'red_cards'].iloc[0] == 0:
                lineup_df.loc[lineup_df.index == player, 'foul points'] = 3
            elif not lineup_df.loc[lineup_df.index == player, 'yellow_cards'].iloc[0] == 0:
                lineup_df.loc[lineup_df.index == player, 'foul points'] = 1
            else:
                lineup_df.loc[lineup_df.index == player, 'foul points'] = 0

    if p_with_totals:
        # add totals row:
        totals_df = pd.DataFrame(index=['totals (inc. bench)', 'totals'])
        for data in info_columns:
            totals_df.loc[:, data] = ''
        for data in ['value', 'foul points'] + points_columns:
            totals_df.loc['totals (inc. bench)', data] = lineup_df[data].sum()
            totals_df.loc['totals', data] = lineup_df.head(11)[data].sum()
        totals_df.loc['totals (inc. bench)', 'name'] = sum(lineup_df['minutes'] > 0)
        totals_df.loc['totals', 'name'] = sum(lineup_df.head(11)['minutes'] > 0)
        totals_df.loc['totals (inc. bench)', 'selected %'] = lineup_df['selected %'].mean()
        totals_df.loc['totals', 'selected %'] = lineup_df.head(11)['selected %'].mean()
        totals_df.loc['totals (inc. bench)', 'team'] = lineup_df['team'].nunique()
        totals_df.loc['totals', 'team'] = lineup_df.head(11)['team'].nunique()
        lineup_df = pd.concat([lineup_df, totals_df])

    # make reader friendly:
    lineup_df.index.name = None
    lineup_df = lineup_df.rename(columns={'goals_scored': 'goals scored', 'goals_conceded': 'goals conceded',
                                          'own_goals': 'own goals', 'yellow_cards': 'yellow cards',
                                          'red_cards': 'red cards', 'total_points': 'total points',
                                          'penalties_missed': 'penalties missed', 'penalties_saved': 'penalties saved'})
    return lineup_df


def get_league_points_df(cumulative=True, totals=True):
    gameweek_range = range(1, current_gameweek + 1)
    # create dataframe:
    league_standings_df = pd.DataFrame(columns=gameweek_range, index=owners)
    if totals:
        league_standings_df.insert(current_gameweek, 'total points', 0)
    team_info_df = {}
    for i_owner in owners:
        team_info_df[i_owner] = url_to_df(team_details_url[i_owner], 'history')
        for i_gameweek in gameweek_range:
            points = team_info_df[i_owner].loc[team_info_df[i_owner]
                                               ['event'] == i_gameweek, 'points'].iloc[0]
            if i_gameweek == 1 or not cumulative:
                league_standings_df.loc[i_owner, i_gameweek] = points
            else:
                league_standings_df.loc[i_owner, i_gameweek] = league_standings_df.loc[i_owner, i_gameweek - 1] + points
        if totals:
            if cumulative:
                league_standings_df.loc[i_owner, 'total points'] = league_standings_df.loc[i_owner, current_gameweek]
            else:
                league_standings_df.loc[i_owner, 'total points'] = league_standings_df.loc[i_owner, :].sum()

    league_standings_df = league_standings_df.sort_values(
        league_standings_df.columns[-1], ascending=False)
    return league_standings_df


def get_league_positions_df():
    gameweek_range = range(1, current_gameweek + 1)
    league_points_df = get_league_points_df(cumulative=True, totals=False)
    league_position_df = pd.DataFrame(columns=gameweek_range, index=owners)
    for i_gameweek in gameweek_range:
        league_points_df = league_points_df.sort_values(i_gameweek, ascending=False)
        for i, i_owner in enumerate(league_points_df.index):
            league_position_df.loc[i_owner, i_gameweek] = (i+1)

    league_position_df = league_position_df.sort_values(
        league_position_df.columns[-1], ascending=True)
    return league_position_df


def get_league_points_gap_df():
    gameweek_range = range(1, current_gameweek + 1)
    league_points_df = get_league_points_df(cumulative=True, totals=False)
    league_points_gap_df = pd.DataFrame(columns=gameweek_range, index=owners)
    for i_gameweek in gameweek_range:
        gameweek_min = min(league_points_df[i_gameweek])
        for i_owner in league_points_df.index:
            league_points_gap_df.loc[i_owner,
                                     i_gameweek] = league_points_df.loc[i_owner, i_gameweek]-gameweek_min

    league_points_gap_df = league_points_gap_df.sort_values(
        league_points_gap_df.columns[-1], ascending=False)
    return league_points_gap_df


# #### Get all info (only run when new info to retrieve) ####

def get_all_lineups():
    all_lineups_df = {}
    for i_gameweek in range(1, current_gameweek + 1):
        for i_owner in owners:
            all_lineups_df[i_owner, i_gameweek] = get_lineup_info(i_owner, i_gameweek, True)
    return all_lineups_df


# #### Parse All Lineups DF ####

def get_league_stats_df_by_gameweek(all_lineups_df, include_bench=False):
    if include_bench:
        value_to_get = 'totals (inc. bench)'
    else:
        value_to_get = 'totals'
    stats = ['name', 'team', 'value', 'selected %', 'minutes', 'goals scored', 'goals conceded', 'penalties missed',
             'penalties saved', 'assists', 'saves', 'own goals', 'yellow cards', 'red cards', 'foul points',
             'total points']
    league_stats_df = {}
    gameweek_range = range(1, current_gameweek + 1)
    for i_gameweek in gameweek_range:
        league_stats_df[i_gameweek] = pd.DataFrame(
            columns=stats + ['weekly position'], index=owners)
        league_stats_df[i_gameweek].insert(5, 'productivity', 0)
        league_stats_df[i_gameweek].insert(8, 'goal difference', pd.Series([], dtype=object))

        for i_owner in owners:
            for stat in stats:
                league_stats_df[i_gameweek].loc[i_owner, stat] = all_lineups_df[i_owner, i_gameweek].loc[value_to_get, stat]
        league_stats_df[i_gameweek] = league_stats_df[i_gameweek].sort_values(
            'total points', ascending=False)
        for i, i_owner in enumerate(league_stats_df[i_gameweek].index):
            league_stats_df[i_gameweek].loc[i_owner, 'productivity'] = \
                league_stats_df[i_gameweek].loc[i_owner, 'total points'] / \
                league_stats_df[i_gameweek].loc[i_owner, 'minutes']
            league_stats_df[i_gameweek].loc[i_owner, 'goal difference'] = \
                league_stats_df[i_gameweek].loc[i_owner, 'goals scored'] - \
                league_stats_df[i_gameweek].loc[i_owner, 'goals conceded']
            league_stats_df[i_gameweek].loc[i_owner, 'weekly position'] = (i + 1)
        league_stats_df[i_gameweek] = league_stats_df[i_gameweek].rename(
            columns={'name': 'active players'})
    return league_stats_df


def get_league_stats_df_by_stat(league_stats_df_by_gameweek, stat, total_type='none', sort_by_week=0):
    gameweek_range = range(1, current_gameweek + 1)

    league_stats_df_by_stat = pd.DataFrame(columns=gameweek_range, index=owners)
    if total_type == 'total':
        league_stats_df_by_stat.insert(current_gameweek, 'totals', pd.Series([], dtype=object))

    for i_owner in owners:
        for i_gameweek in gameweek_range:
            league_stats_df_by_stat.loc[i_owner, i_gameweek] = league_stats_df_by_gameweek[i_gameweek].loc[i_owner, stat]
        if total_type == 'mean' or total_type == 'average':
            league_stats_df_by_stat.loc[i_owner, 'average'] = league_stats_df_by_stat.loc[i_owner, gameweek_range].mean()
            league_stats_df_by_stat = league_stats_df_by_stat.sort_values(
                'average', ascending=False)
        elif total_type == 'total':
            league_stats_df_by_stat.loc[i_owner, 'totals'] = league_stats_df_by_stat.loc[i_owner, gameweek_range].sum()
            league_stats_df_by_stat = league_stats_df_by_stat.sort_values('totals', ascending=False)

    if not sort_by_week == 0:
        league_stats_df_by_stat = league_stats_df_by_stat.sort_values(sort_by_week, ascending=False)

    return league_stats_df_by_stat
