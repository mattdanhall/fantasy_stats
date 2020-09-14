import requests
import pandas as pd
import numpy as np

bootstrap_static_url = 'https://draft.premierleague.com/api/bootstrap-static'
bootstrap_static_r = requests.get(bootstrap_static_url)
bootstrap_static_json = bootstrap_static_r.json()

league_details_url = 'https://draft.premierleague.com/api/league/5857/details'
league_details_r = requests.get(league_details_url)
league_details_json = league_details_r.json()

elements_df = pd.DataFrame(bootstrap_static_json['elements'])
elements_df.index = elements_df.index+1
elements_types_df = pd.DataFrame(bootstrap_static_json['element_types'])
teams_df = pd.DataFrame(bootstrap_static_json['teams'])
league_df = pd.DataFrame

# print(elements_df.head())

slim_elements_df = elements_df[['web_name','team','element_type','minutes','total_points']]

slim_elements_df['team'] = slim_elements_df.team.map(teams_df.set_index('id').name)
slim_elements_df['element_type'] = slim_elements_df.element_type.map(elements_types_df.set_index('id').singular_name)

print(slim_elements_df)