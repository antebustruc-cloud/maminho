"""
Population limits (Phase 3d) — single tunable module. All values are
placeholders, "per league" currently means per sport league / game world
(one country at launch, so region == world).
"""

# Max players on a club's roster at once (team sports).
MAX_ROSTER_PER_CLUB = 35

# Free-agent pool size per league that season_population tops up toward
# (soft target for generation — never a hard block).
FREE_AGENT_POOL_TARGET = 220

# Registration of new manager-role users is blocked at this count.
MAX_MANAGERS_PER_LEAGUE = 50

# Company founding per type is blocked at this count (per country/region;
# one region at launch).
MAX_COMPANIES_PER_TYPE = 3

# Youth intake per active sport per season (season_population).
YOUTH_INTAKE_MIN = 30
YOUTH_INTAKE_MAX = 40
YOUTH_AGE_MIN = 16
YOUTH_AGE_MAX = 18

# Retirement age: players strictly older than this retire at rollover.
RETIREMENT_AGE = 34
