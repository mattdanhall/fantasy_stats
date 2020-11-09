#!/usr/bin/env python
# coding: utf-8

import matplotlib.pyplot as plt
import fantasy_stats_def as fs

league_points_gap_df = fs.get_league_points_gap_df()
# league_positions_df = fs.get_league_positions_df()

league_points_gap_df.transpose().plot(linewidth=4)
plt.xticks(range(1,fs.current_gameweek+1))
plt.grid(b=True)
plt.margins(0)
plt.xlabel('Gameweek')
plt.ylabel('Points ahead of last place')
plt.legend(bbox_to_anchor=(1.01, 1), loc='upper left', borderaxespad=0.)


# for i_owner in fs.owners:
#     plt.annotate(xy=[fs.current_gameweek,league_points_gap_df.loc[i_owner, fs.current_gameweek]], text=i_owner)

plt.show()