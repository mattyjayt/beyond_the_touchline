# Relative acceleration, not pace, wins wing duels

When a defender tries to stop an elite dribbling winger, the best predictors of who wins are **interaction variables measured at the moment of confrontation**. These are the attacker–defender relative velocity and acceleration, the gap between them and how fast it closes, the defender's stance angle, how much defensive pressure or support is nearby, and how far the duel is from the touchline. Absolute top speed matters much less. In a 1,736-dribble Champions League tracking study, a higher maximum speed for either player actually went with *lower* dribble success, while a relative speed advantage for the attacker raised it ([arXiv 2506.22503](https://arxiv.org/html/2506.22503v1)). That matters for a substitution or matchup advisor. Jérémy Doku, the most extreme dribbler in Premier League data (about **10.8 take-on attempts and 6.8 completions per 90 in 2024/25**), has a top speed of only **35.14 km/h**, and his threat comes from acceleration over "two or three yards" ([Premier League](https://www.premierleague.com/en/news/4293725)). The advisor should therefore weight short-range acceleration, deceleration, reactive agility, fatigue and context above raw pace. Pace should be kept mainly for recovery runs over 40 m or more. Public positional ranges are solid for running volume and top speed, rough for event metrics, and almost absent for acceleration and change of direction. Public figures for the Arsenal defenders (White, Timber, Mosquera) are thin, and some are non-official. The catalogue below lists 108 candidate variables in eight families and ranks the top 25. Every range is tagged as sourced, or as an analyst estimate for use in a **simulated** product.

## Duel outcomes hinge on the gap, the angle and the help nearby

The most rigorous evidence comes from three elite tracking datasets, and they agree. In the UCL 2022/23 3D-pose study (Hawk-Eye SkeleTRACK at 25 Hz, 125 matches), these factors predicted the outcome of a dribble:

- **Relative speed advantage** for the attacker raised success.
- **Higher mean defensive pressure** lowered it.
- Dribbles **further from the sideline** succeeded more often.
- A more **squared-up defender**, with a wider angle between the two players' hip vectors, conceded more often. This implies a side-on stance is the protective technique.
- **Large attacker torso lean** went with failure.
- Ball-touch frequency and ball–foot distance had minimal effect.

([arXiv 2506.22503](https://arxiv.org/html/2506.22503v1))

Predictive power was modest. F1 rose from 0.35 for location-only features to 0.52 for 2D + 3D features, with a Brier score of about 0.24. Duels are noisy, and any advisor should present probabilities, never certainties.

An Eredivisie study of **734 labelled 1v1s from 43 matches** grouped 24 tracking variables into individual, interaction and environmental families. It found a significant overall effect of outcome (Wilks' λ = 0.881, p < 0.001) ([SPONET/DFB](https://lida.sport-iat.de/dfb/Record/4093794)). The abstract is cut off before it names its five significant individual variables, so that is a known gap. Earlier work points the same way:

- Frontal 1v1s measured with LPM position data turned on the **accelerations of both players and the defender's velocity at the moment of confrontation** ([Univ. Vienna](https://services.phaidra.univie.ac.at/api/object/o:1323609/download)).
- Ecological-dynamics trials showed the dyad "breaking", meaning the attacker gets past, at moments of **higher relative velocity and lower interpersonal distance**. Starting distance (1–2.5 m) acted as a control parameter ([Univ. Évora](https://rdpc.uevora.pt/handle/10174/2095)).

The physical basis of good jockeying is braking, not sprinting. In a reactive agility test, faster defenders **decelerated quickly with high step frequency**, kept a **low, backward-tilted centre of gravity**, and turned well ([ISBS, Kawahara 2018](https://commons.nmu.edu/isbs/vol36/iss1/252)). A **lower centre of mass at initial contact**, achieved through hip flexion, made defensive cuts more efficient ([Sasaki 2015](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4519200/)). Reactive and pre-planned agility share **less than 50% of their variance**, and anticipation separates fast from slow performers ([JSSM 9(3)](https://www.jssm.org/jssm-09-445.xml-Fulltext)). That evidence comes from rugby, and the youth-football data show forwards out-reacting defenders ([JSSM 16(2)](https://jssm.org/16-2-247.p_d_f)). Acceleration data explain why short duels favour the quick starter. In LaLiga tracking, **88–91% of accelerations above 3 m/s² started below 7 km/h**, and initial speed explained 97.7% of the variance in maximal acceleration ([Biology of Sport 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12490324/)). A winger who stops, then explodes, takes a defender exactly where the defender's acceleration capacity is decisive.

Fatigue changes the duel through **technique and decision-making** more than through speed:

- Fatigued defenders kept the same approach speed into a 45° defensive cut but **cut braking time and braking impulse** ([de Pablo 2024](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11609251/)).
- After small-sided-game fatigue, defenders **committed earlier** when anticipating an attacker's change of direction ([Leeds Beckett](https://eprints.leedsbeckett.ac.uk/id/eprint/7648)).
- One experiment found little fatigue effect on interception success or top sprint speed ([AIP Inside Science](https://www.aip.org/inside-science/world-cup-showcases-elite-players-fight-against-fatigue)).
- When effective playing time is accounted for, full-backs maintained their high-speed efforts into the second half ([SPONET](https://lida.sport-iat.de/ta/Record/4087619?lng=en)).

The steelman view is that fatigue is overrated as a duel driver. The better-supported view is that it acts on braking and premature commitment, which are exactly the failure modes against a Doku. Doku's own split hints at this. He attempted **17.6 take-ons per 90 as a substitute vs 7.9 as a starter** in 2023/24 ([Opta Analyst](https://theanalyst.com/articles/jeremy-doku-changed-pep-guardiola/)), but that comparison mixes his freshness, opponent tiredness and small samples.

Context completes the model. Players one card from a ban fouled about **12% less** facing a one-game suspension and about **23% less** facing a two-game ban ([SPONET](https://lida.sport-iat.de/ta/Record/4048925?lng=en)). That supports a "booked defender jockeys more and tackles less" modifier, although nobody has measured the effect on 1v1s specifically. The evidence on substitutes runs in two directions:

- Substitutes cover about **15% more high-intensity running** than full-match players over the same window, and the effect is short-lived ([PubMed 23808376](https://pubmed.ncbi.nlm.nih.gov/23808376)).
- Myers' timing rule for trailing teams (subs before 58', 73' and 79') was associated with goal-difference gains **36% vs 18.5%** of the time ([Freakonomics](https://freakonomics.com/2011/02/09/when-should-a-soccer-manager-insert-his-subs)). Later Bayesian work found **no discernible beneficial window** ([Silva & Swartz 2016](https://www.degruyterbrill.com/document/doi/10.1515/jqas-2015-0114/html?lang=de)).

The honest position for the advisor is that fresh legs are a real but modest physical edge, that timing rules are heuristics, and that every recommendation must include KEEP.

## Positional ranges separate cleanly on volume, blur on acceleration

Running volume orders the positions consistently. In EPL optical tracking (one club, 2019–21, 630 observations), the group means were:

- **Defenders:** 9,966 m total distance, 697 m HSR (above 19.8 km/h), 151 m sprint (above 25.2 km/h).
- **Midfielders:** 11,594 m, 992 m and 158 m.
- **Forwards:** 10,710 m, 941 m and 202 m.

([Kavanagh 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11474994/))

The older Bradley study separates full-backs from centre-backs for high-intensity running per match: wide midfielders 3,138 m, central midfielders 2,825 m, full-backs 2,605 m and centre-backs 1,834 m ([Bradley 2009](https://lida.sport-iat.de/ta/Record/4015478?lng=en)). In 2024/25 the PL sprint-count leaders over 29 matchweeks were Antonee Robinson (702), Gordon (666) and Muñoz (658). At the bottom, Van Dijk covered only 8.8 km per 90 and walked 76.5% of game time ([Premier League](https://www.premierleague.com/news/4272290)).

Top speed is where wide players stand out. Nine of the ten fastest speeds in 2025/26 belonged to wingers, full-backs or wing-backs. Tchatchoua set the 2025/26 peak at 37.30 km/h, and Van de Ven holds the all-time record of 37.38 km/h ([Premier League](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league)).

Acceleration capacity barely separates the positions. The theoretical maximal acceleration (A0) ranges from a mean of **6.40 m/s² for wingers** to **6.79 m/s² for centre-backs** ([Biology of Sport 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12490324/)), and that source is internally inconsistent about which position is highest. What does differ is acceleration *load*: full-backs accumulate the most high-intensity accelerations and decelerations ([SMF 2022](https://oars.uos.ac.uk/2542/3/manuscript%20AAM.pdf)). Fatigue is uniform across positions. High-intensity running falls about **20% from the first 15 minutes to the last 15**, and recovery between very-high-intensity bouts stretches from 65 s to 83 s ([Bradley 2009](https://lida.sport-iat.de/ta/Record/4015478?lng=en)).

| Variable (per 90 unless stated) | Centre-back | Full-back | Central mid | Winger | Basis |
|---|---|---|---|---|---|
| Season-peak top speed (km/h) | 30–37 (outliers: Van de Ven, Khusanov) | 32–37.3 | 29–36.7 (typical 31–33) | 33–36.7 | PL/Opta leaderboards; Kavanagh |
| Total distance (km) | 8.5–10.0 | 10–11 (est.) | 11.0–12.9 | 10.3–11.2 | Kavanagh; PL |
| HSR >19.8 km/h (m) | 450–700 | 800–1,100 (est.) | 800–1,100 | 900–1,200 (est.) | Kavanagh + estimate |
| Sprint distance >25.2 km/h (m) | 100–200 | 200–350 (est.) | 100–200 | 250–400 (est.) | Kavanagh + estimate |
| Sprint count >25 km/h | 8–15 (est.) | 20–30 (est.; leaders ~24/match) | — | 25–35 (est.) | Derived from PL season totals |
| A0 mean / max (m/s²) | 6.79 / 7.89 | 6.70 / 7.84 | 6.44 / 7.30 | 6.40 / 7.84 | LaLiga Mediacoach |
| 10 m sprint, static start (s) | ~2.25 (U21) | — | ~2.19 (U21) | ~2.17 (U21 forwards) | Slovak U21; senior est. 2.0–2.2 |
| HI decline, last 15' vs first 15' | −20% | −19% | −20% | −21% | Bradley 2009 |
| Tackles | 1.0–2.0 | 1.5–3.0 | 1.5–3.5 | — | Analyst estimate |
| Dribblers tackled % | 55–75% | 45–65% | — | — | Analyst estimate |
| Challenges lost (dribbled past) | 0.3–0.8 | 0.6–1.3 | — | — | Analyst estimate |
| Interceptions | 0.8–2.0 (top ~2.0) | 0.8–1.8 | 0.8–1.8 | — | FotMob leaders + estimate |
| Clearances | 3–6 (low block up to ~7.6) | 1.5–3.5 | — | — | Squawka top percentile + estimate |
| Aerials won | 1.5–3.5 (top band ~3) | 0.8–2.0 | 0.5–2.0 | — | Squawka + estimate |
| Take-on attempts | — | — | — | 2–4 typical, 5–7 elite, Doku 9.5–10.8 | Opta/PL + estimate |
| Take-on success % | — | — | — | 35–50% (league avg 36.7%) | Opta Analyst |
| Pass completion | 88–94% (possession) / 75–85% (low block) | 78–88% | 85–92% | 72–82% | Analyst estimate |
| Progressive passes | 3–6 | 3–6 | 5–9 | 2.5–5 | Analyst estimate |

Sources for the sourced cells: [Kavanagh 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11474994/), [PL 2024/25](https://www.premierleague.com/news/4272290), [PL 2025/26](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league), [LaLiga AS profiles](https://pmc.ncbi.nlm.nih.gov/articles/PMC12490324/), [Slovak U21](https://library.sk/arl-umb/en/detail-umb_un_cat-0207921-A-level-of-sprint-ability-of-elite-young-football-players-at-different-positions), [Bradley 2009](https://lida.sport-iat.de/ta/Record/4015478?lng=en), [Opta Analyst dribblers](https://theanalyst.com/articles/premier-league-dribblers-stats-2025-26), [FotMob interceptions](https://www.fotmob.com/leagues/47/stats/season/23685/players/interception/premier-league-players), [Squawka CB ranking](https://www.squawka.com/en/features/position-ranking-premier-league-best-centre-backs-right-now/).

Rows marked "estimate" have no published positional median. They are design ranges, not facts.

There are two caveats. First, provider definitions differ (Opta, Tracab, Second Spectrum and GPS thresholds; Opta's ~5 m progressive-carry rule vs FBref's 10-yard rule), so absolute values are only comparable within one provider. Second, Opta changed its speed method across seasons, so top-speed lists from different years are not strictly comparable ([NBC Sports](https://nbcsports.com/soccer/news/who-are-the-fastest-players-in-the-premier-league)).

## Doku is a three-sigma outlier; Arsenal's defenders are barely measured

Doku's numbers make him the archetype the advisor must defend against. In the 2024/25 PL (1,303 minutes) he recorded:

- **10.84 dribbles attempted** and **6.77 completed per 90**.
- **62.4% success**, the league best among players with at least 3 attempts per 90.
- **309 progressive carries**, the most in the league.
- **10.78 duels won per 90**, also the most.

([Premier League](https://www.premierleague.com/en/news/4293725))

Next-best PL volume was Sulemana at 7.24 attempts and Kudus at 6.55. Across Europe, Yamal managed 9.3 attempts. In 2025/26 Doku dipped to about **9.5 attempts and 4.3 successes per 90 (~52%)**, still first in the league, against a league-average success rate of 36.7% ([Opta Analyst](https://theanalyst.com/articles/premier-league-dribblers-stats-2025-26)). At the same time he added end product: **0.52 xG assisted per 90** and 2.4 open-play chances per match ([Premier League](https://www.premierleague.com/en/news/4432018/analysis-doku-adding-end-product-to-match-dribbling-skills)).

That shift matters tactically. A defender who simply concedes the outside to Doku now concedes chances, not just territory. Saka is a different threat profile: fewer take-ons (88 by Feb 2026) but **20.5% of them inside the box** ([Opta Analyst](https://theanalyst.com/articles/premier-league-dribblers-stats-2025-26)).

| Player | Role | Top speed (km/h) | Key event metrics | Reliability |
|---|---|---|---|---|
| Jérémy Doku | Winger (MCI) | 35.14 (PL 2024/25, Opta); 32.06 UCL 2025/26 (peak or average unclear) | 10.84 att / 6.77 succ take-ons p90, 62.4% (24/25); 9.5 att / 4.3 succ p90, ~52% (25/26); 309 prog. carries (24/25); 0.52 xGA p90 (25/26) | Official ([PL](https://www.premierleague.com/en/news/4293725), [UEFA](https://www.uefa.com/uefachampionsleague/clubs/players/250113142--jeremy-doku)) |
| Bukayo Saka | Winger (ARS) | 32.2 early 2026/27; 30.9 in one match vs Brighton | 88 take-ons by Feb 2026, 20.5% in box; 6G/10A in 25 apps (24/25) | Speed non-official ([Daily Cannon](https://dailycannon.com/2026/09/arsenals-fastest-player/)); events [Opta Analyst](https://theanalyst.com/articles/premier-league-dribblers-stats-2025-26), [RotoWire](https://web9.rotowire.com/soccer/player/bukayo-saka-29889) |
| Ben White | RB/CB (ARS) | 32.1 early 2026/27 | Dribbled past 0.89 p90 (20th pct), ~1.91 tkl, 1.28 int p90 (25/26, small sample); 5.74 prog. passes p90 (92nd pct FB) | Mixed, snippet-level ([FootyStats](https://footystats.org/kr/players/england/ben-white), [FBref](https://fbref.com/it/players/35e413f1/Ben-White)) |
| Declan Rice | CM (ARS) | 32.4 early 2026/27 | 380.22 km in 3,099 min in 25/26 (~11.0 km p90, Arsenal high); prog. passes 7.77 → 6.11 p90 (23/24 → 24/25); int 0.8 p90 (24/25) | Distance official ([PL](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league)); passing snippet ([Squawka](https://www.squawka.com/en/?p=1390907)) |
| Jurriën Timber | RB (ARS) | 29.7 early 2026/27 | 36 tackles won, 24 int in 26.9 90s (~1.3 / 0.9 p90), 30 fouls (24/25) | Speed non-official; events snippet ([FBref](https://fbref.com/en/players/41034650/Jurrien-Timber)) |
| Cristhian Mosquera | CB/RB (ARS) | 34.8 early 2026/27; UCL 2025/26 top 32.46, avg 29.11 | 2.9 tkl, 0.7 int, 1.82 aerials won p90 (25/26, 994 min) | Events agree across two sources ([Statmuse](https://www.statmuse.com/fc/ask/christhian-mosquera-tackles?l=eu5), [FootyStats](https://footystats.org/players/spain/cristhian-mosquera)); [UEFA](https://www.uefa.com/uefachampionsleague/clubs/players/250129972--cristhian-mosquera) |

The Arsenal top-speed figures come from one non-official early-season 2026/27 table. That table also lists players who are unexpected at Arsenal, so treat them as low-confidence and below season peaks. The one cross-check available shows the gap: Saka's in-match 30.9 against his table value of 32.2.

Read cautiously, the defenders' numbers suggest a few things about a Doku matchup:

- **Mosquera** has the most recovery pace and a front-foot tackle rate (2.9 per 90 is high for a CB) on a small sample.
- **White** is beaten more often than most peers on a per-90 basis. He also brings elite progressive passing and proven versatility; Arteta said the key step was White "believ[ing] he could do it" at full-back ([Sky Sports](https://www.skysports.com/football/news/12040/12988142/ben-white-exclusive-interview-arsenals-versatile-defender-thriving-under-mikel-arteta-and-eyeing-long-stay)).
- **Timber's** low top-speed reading matters less than his change of direction, which is the decisive quality and is not publicly measured for any of these players.

For benchmarking a defender's 1v1 record, Opta's "true tackle" win rate against dribbles is the best public measure. Leaders in 2025/26 were Lacroix at 87.0% and Guéhi at 81.5%, and Trippier was lowest at 32.3% ([Premier League/Opta](https://www.premierleague.com/en/news/4461616/opta-analyst-on-quirkier-stats-in-2025-26-including-most-long-throws-and-best-defenders-v-dribbles)). No Arsenal values were reported.

## A 108-variable catalogue across eight families

Each variable is tagged by evidence level: **T** = tracking or biomechanics evidence links it to duel outcome; **E** = event or descriptive metric with sourced ranges; **C** = context or case evidence; **D** = design variable with no direct outcome evidence (weights are assumptions, labelled simulated). Ranges are elite PL unless noted. "Est." marks an analyst estimate.

### A. Speed and running volume (14)

| # | Variable | Unit | Range / reference | Tag | Source |
|---|---|---|---|---|---|
| 1 | Season-peak top speed | km/h | 29–37.4; record 37.38 | E | [PL 25/26](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league) |
| 2 | Match-peak top speed | km/h | Typically 1–3 below season peak (est.); in-match mean ~34.3 | E | [Kavanagh](https://pmc.ncbi.nlm.nih.gov/articles/PMC11474994/) |
| 3 | Attacker max speed in dribble | km/h | Higher → lower success | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 4 | Defender max speed in duel | km/h | Higher → lower defensive success (open-field confound) | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 5 | Sprint count (>25 km/h) | count | Leaders 640–702 over 29 matchweeks | E | [PL 24/25](https://www.premierleague.com/news/4272290) |
| 6 | Sprint distance (>25.2 km/h) | m/match | Def 151, Mid 158, Fwd 202 | E | [Kavanagh](https://pmc.ncbi.nlm.nih.gov/articles/PMC11474994/) |
| 7 | % time sprinting | % | Leaders 1.04–1.17 | E | [PL 24/25](https://www.premierleague.com/news/4272290) |
| 8 | HSR distance (>19.8 km/h) | m/match | Def 697, Mid 992, Fwd 941 | E | [Kavanagh](https://pmc.ncbi.nlm.nih.gov/articles/PMC11474994/) |
| 9 | High-intensity running (older definition) | m/match | CB 1,834 – wide mid 3,138 | E | [Bradley 2009](https://lida.sport-iat.de/ta/Record/4015478?lng=en) |
| 10 | Total distance | km/90 | CB 8.5–10, CM up to 12.9 | E | [PL 24/25](https://www.premierleague.com/news/4272290) |
| 11 | Distance rate | m/min | Def 103, Mid 120, Fwd 112 | E | [Kavanagh](https://pmc.ncbi.nlm.nih.gov/articles/PMC11474994/) |
| 12 | % time walking | % | Up to 76.5 (Van Dijk) | E | [PL 24/25](https://www.premierleague.com/news/4272290) |
| 13 | Peak 5-min high-intensity window | m | Followed by a sharp drop (e.g. CB 182 → 96 m) | E | [Bradley 2009](https://lida.sport-iat.de/ta/Record/4015478?lng=en) |
| 14 | Single-match max distance | km | 13.24 record (25/26) | E | [PL 25/26](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league) |

### B. Acceleration, deceleration and change of direction (15)

| # | Variable | Unit | Range / reference | Tag | Source |
|---|---|---|---|---|---|
| 15 | Theoretical max acceleration (A0) | m/s² | Mean 6.40–6.79, max 7.30–7.89 | E | [LaLiga AS](https://pmc.ncbi.nlm.nih.gov/articles/PMC12490324/) |
| 16 | Acceleration–speed slope | m/s² per km/h | −0.233 to −0.255 | E | [LaLiga AS](https://pmc.ncbi.nlm.nih.gov/articles/PMC12490324/) |
| 17 | Attacker max acceleration in dribble | m/s² | Model feature | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 18 | Defender acceleration at confrontation | m/s² | Differs by outcome | T | [Vienna LPM](https://services.phaidra.univie.ac.at/api/object/o:1323609/download) |
| 19 | High-intensity accelerations (>3 m/s²) | count/match | ~65 max accelerations per game (older, non-PL); FBs highest | E | [Varley & Aughey](https://vuir.vu.edu.au/id/eprint/23141) |
| 20 | High-intensity decelerations (<−3 m/s²) | count/match | Outnumber accelerations; FBs highest | E | [Harper 2019](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6851047/) |
| 21 | Accelerations per sprint | ratio | ~8:1 | E | [Varley & Aughey](https://vuir.vu.edu.au/id/eprint/23141) |
| 22 | Share of accelerations starting <7 km/h | % | 88–91 | E | [LaLiga AS](https://pmc.ncbi.nlm.nih.gov/articles/PMC12490324/) |
| 23 | Time to 5 m | s | Protocol shifts ~0.08 s; senior norm not found | D | [PMC12568230](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12568230/) |
| 24 | Time to 10 m | s | U21 2.17–2.25 static; senior est. 1.65–1.85 flying | E | [Slovak U21](https://library.sk/arl-umb/en/detail-umb_un_cat-0207921-A-level-of-sprint-ability-of-elite-young-football-players-at-different-positions) |
| 25 | Time to 30 m | s | U21 mean 4.59 | E | [Slovak U21](https://library.sk/arl-umb/en/detail-umb_un_cat-0207921-A-level-of-sprint-ability-of-elite-young-football-players-at-different-positions) |
| 26 | Reactive agility (Y-test) | s | Forwards > defenders in youth | T | [JSSM 16(2)](https://jssm.org/16-2-247.p_d_f) |
| 27 | Pre-planned change of direction | s | <50% shared variance with reactive agility | T | [JSSM 9(3)](https://www.jssm.org/jssm-09-445.xml-Fulltext) |
| 28 | Backward/diagonal COD with high step-frequency deceleration | s, Hz | Separates fast from slow defenders | T | [Kawahara 2018](https://commons.nmu.edu/isbs/vol36/iss1/252) |
| 29 | Centre-of-mass height / hip flexion at contact | cm, ° | Lower = more efficient cut | T | [Sasaki 2015](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4519200/) |

### C. Fatigue and substitution load (10)

| # | Variable | Unit | Range / reference | Tag | Source |
|---|---|---|---|---|---|
| 30 | Minutes on pitch | min | Modifier input | D | — |
| 31 | High-intensity decline, last 15' vs first 15' | % | ~−19 to −21 | E | [Bradley 2009](https://lida.sport-iat.de/ta/Record/4015478?lng=en) |
| 32 | Recovery between very-high-intensity bouts | s | 65 → 83 | E | [Bradley 2009](https://lida.sport-iat.de/ta/Record/4015478?lng=en) |
| 33 | Braking time / impulse under fatigue | s, N·s | Falls (approach speed unchanged) | T | [de Pablo 2024](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11609251/) |
| 34 | Premature commitment under fatigue | timing | Earlier initiation | T | [Leeds Beckett](https://eprints.leedsbeckett.ac.uk/id/eprint/7648) |
| 35 | Effective-time-adjusted second-half drop | % | Not significant; FBs maintain | C | [SPONET](https://lida.sport-iat.de/ta/Record/4087619?lng=en) |
| 36 | Substitute high-intensity boost | % | +15% (largest for attackers) | E | [PubMed 23808376](https://pubmed.ncbi.nlm.nih.gov/23808376) |
| 37 | Substitute final-15' boost (reviewed) | % | +25% HI actions, +63% sprint distance (unverified original) | E | [PMC9145854](https://pmc.ncbi.nlm.nih.gov/articles/PMC9145854) |
| 38 | Fresh-legs decay window | min | "Short-lived"; ~15–20 (est.) | D | [PubMed 23808376](https://pubmed.ncbi.nlm.nih.gov/23808376) |
| 39 | Starter vs sub status | flag | Matters only in final periods | C | [PMC10955740](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10955740/) |

### D. Duel interaction and geometry (15)

| # | Variable | Unit | Range / reference | Tag | Source |
|---|---|---|---|---|---|
| 40 | Relative velocity at confrontation | m/s | Attacker advantage → success | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1); [Duarte 2010](https://rdpc.uevora.pt/handle/10174/2095) |
| 41 | Relative acceleration | m/s² | Both players' accelerations differ by outcome | T | [Vienna LPM](https://services.phaidra.univie.ac.at/api/object/o:1323609/download) |
| 42 | Interpersonal distance at engagement | m | Lower + high relative velocity → attacker breaks | T | [Duarte 2010](https://rdpc.uevora.pt/handle/10174/2095) |
| 43 | Starting distance | m | 1–2.5 m experimental range | T | [Duarte 2010](https://rdpc.uevora.pt/handle/10174/2095) |
| 44 | Angular separation | ° | Rises when the attacker tries to pass | T | [Clemente 2013](https://dspace.rcaap.pt/entities/publication/dc357f2b-3ea2-4846-afc5-b5db84cdbf0e/full) |
| 45 | Defender stance angle (hip vectors) | ° / category | Side-on protective; squared-up concedes | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 46 | Attacker torso lean | ° | Large lean → failure | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 47 | Attacker max direction change | ° | Model feature | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 48 | Distance to sideline | m | Further → more success | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 49 | Distance to goal | m | Model feature | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 50 | Mean defensive pressure score | index | Higher → lower success | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 51 | Second-defender proximity / double-up | m | Key confounder | C | [Substack 1v1s](https://talatabont.substack.com/p/introducing-1v1s-to-football) |
| 52 | Isolation flag (nearest defender >3 yd, second >7 yd) | flag | Community definition | C | [Substack 1v1s](https://talatabont.substack.com/p/introducing-1v1s-to-football) |
| 53 | Ball-touch frequency / ball–foot distance | Hz, m | Minimal effect | T | [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1) |
| 54 | Defender behaviour parameters (driving force f, τ, β) | model | Four behaviour quadrants; descriptive only | T | [arXiv 2512.22596](https://arxiv.org/html/2512.22596v1) |

### E. Winger attacking events (17)

| # | Variable | Unit | Range / reference | Tag | Source |
|---|---|---|---|---|---|
| 55 | Take-on attempts | p90 | 2–4 typical (est.); Doku 9.5–10.8 | E | [PL](https://www.premierleague.com/en/news/4293725) |
| 56 | Take-on success | % | League average 36.7%; Doku 52–62% | E | [Opta Analyst](https://theanalyst.com/articles/premier-league-dribblers-stats-2025-26) |
| 57 | Successful take-ons | p90 | 1–2 typical (est.); Doku 4.3–6.8 | E | [PL](https://www.premierleague.com/en/news/4293725) |
| 58 | Share of take-ons in the box | % | Saka 20.5 | E | [Opta Analyst](https://theanalyst.com/articles/premier-league-dribblers-stats-2025-26) |
| 59 | Progressive carries | p90 / season | Doku 309 (24/25), 9.76 p90 (25/26) | E | [PL](https://www.premierleague.com/en/news/4432018/analysis-doku-adding-end-product-to-match-dribbling-skills) |
| 60 | Progressive carry distance | m p90 | Doku 212 (23/24), 2nd to Dembélé | E | [Opta Analyst](https://theanalyst.com/articles/jeremy-doku-changed-pep-guardiola/) |
| 61 | Carries into the final third | p90 | 1.5–3 (est.) | D | — |
| 62 | Carries into the box | p90 | 1–2.5 (est.) | D | — |
| 63 | Crosses / cross accuracy | p90, % | 2–5 at 20–30% (est.) | D | — |
| 64 | Shot-creating actions (SCA) | p90 | 3–5 (est.) | D | — |
| 65 | Touches in the opposition box | p90 | 4–8 (est.); Doku 22 in one match | E | [PL](https://www.premierleague.com/en/news/4432018/analysis-doku-adding-end-product-to-match-dribbling-skills) |
| 66 | npxG | p90 | 0.2–0.4 (est.) | D | — |
| 67 | xG assisted | p90 | Doku 0.52 (league best, 25/26) | E | [PL](https://www.premierleague.com/en/news/4432018/analysis-doku-adding-end-product-to-match-dribbling-skills) |
| 68 | Open-play chances created | per match | Doku 2.1 → 2.4 | E | [PL](https://www.premierleague.com/en/news/4432018/analysis-doku-adding-end-product-to-match-dribbling-skills) |
| 69 | Carries ending in a chance | % | Doku 3.3 → 4.2 | E | [PL](https://www.premierleague.com/en/news/4432018/analysis-doku-adding-end-product-to-match-dribbling-skills) |
| 70 | Duels won (attacker) | p90 | Doku 10.78 (league best) | E | [PL](https://www.premierleague.com/en/news/4293725) |
| 71 | Take-on rate as sub vs starter | p90 | Doku 17.6 vs 7.9 | E | [Opta Analyst](https://theanalyst.com/articles/jeremy-doku-changed-pep-guardiola/) |

### F. Defending events (17)

| # | Variable | Unit | Range / reference | Tag | Source |
|---|---|---|---|---|---|
| 72 | Tackles | p90 | FB 1.5–3.0, CB 1.0–2.0 (est.); Mosquera 2.9 | E | [Statmuse](https://www.statmuse.com/fc/ask/christhian-mosquera-tackles?l=eu5) |
| 73 | Tackles won % | % | FB 55–65 (est.) | D | — |
| 74 | Dribblers tackled % | % | FB 45–65, CB 55–75 (est.) | D | [Hudl scouting](https://www.hudl.com/blog/modern-scouting-workflows-player-archetypes-statsbomb) |
| 75 | Challenges lost / dribbled past | p90 | FB 0.6–1.3 (est.); White 0.89 (20th pct) | E | [FootyStats](https://footystats.org/kr/players/england/ben-white) |
| 76 | True tackle win % vs dribbles | % | 32.3–87.0 (2025/26) | E | [PL/Opta](https://www.premierleague.com/en/news/4461616/opta-analyst-on-quirkier-stats-in-2025-26-including-most-long-throws-and-best-defenders-v-dribbles) |
| 77 | Interceptions | p90 | Leaders ~2.0 | E | [FotMob](https://www.fotmob.com/leagues/47/stats/season/23685/players/interception/premier-league-players) |
| 78 | Blocks | p90 | FB 0.8–1.5, CB 1.0–2.0 (est.) | D | — |
| 79 | Clearances | p90 | Top percentile 7.61 | E | [Squawka](https://www.squawka.com/en/features/position-ranking-premier-league-best-centre-backs-right-now/) |
| 80 | Ball recoveries | p90 | FB 4–7, CB 3.5–6 (est.) | D | — |
| 81 | Aerials won | p90 | CB top band ~3.0; Mosquera 1.82 | E | [Squawka](https://www.squawka.com/en/features/position-ranking-premier-league-best-centre-backs-right-now/) |
| 82 | Aerial win % | % | CB 55–75 (est.) | D | — |
| 83 | Fouls committed | p90 | FB 0.8–1.5 (est.); Timber ~1.1 | E | [FBref](https://fbref.com/en/players/41034650/Jurrien-Timber) |
| 84 | Fouls drawn | p90 | Timber ~1.1 | E | [FBref](https://fbref.com/en/players/41034650/Jurrien-Timber) |
| 85 | Pressures (legacy StatsBomb) | p90 | FB 12–20 (est., pre-2022 only) | D | — |
| 86 | Possession won (ground duels won + tackles + interceptions) | p90 | Provider-specific | E | [DataMB](https://datamb.football/guide/) |
| 87 | Defensive Responsibility (DefR) | index | Expected vs actual defensive actions | C | [Hudl DefR](https://www.hudl.com/blog/defensive-responsibility-defr-statsbomb) |
| 88 | Cover-shadow off-ball impact | index | Research metric | C | [Hudl research](https://static.hudl.com/craft/performance-insights-research-stage/2025/Quantifying-Off-Ball-Defensive-Impact-through-Cover-Shadows-Lorenzo-Casciolio-Allen-Wang.pdf) |

### G. Passing and build-up (6)

| # | Variable | Unit | Range / reference | Tag | Source |
|---|---|---|---|---|---|
| 89 | Pass completion | % | CM ~90 (Rice) | E | [Squawka](https://www.squawka.com/en/?p=1390907) |
| 90 | Passes attempted | p90 | Rice 46.9 | E | [Squawka](https://www.squawka.com/en/?p=1390907) |
| 91 | Progressive passes | p90 | White 5.74 (92nd pct FB); Rice 6.11–7.77 | E | [FBref](https://fbref.com/it/players/35e413f1/Ben-White) |
| 92 | Passes into the final third | p90 | 3–9 by role (est.) | D | — |
| 93 | Long balls completed | p90 | 1–5 by role (est.) | D | — |
| 94 | Chances created | p90 | Rice 1.9 (24/25) | E | [Squawka](https://www.squawka.com/en/?p=1390907) |

### H. Context and tactics (14)

| # | Variable | Unit | Range / reference | Tag | Source |
|---|---|---|---|---|---|
| 95 | Game state (score difference) | goals | Trailing teams show a second-half scoring edge | C | [Silva & Swartz](https://www.degruyterbrill.com/document/doi/10.1515/jqas-2015-0114/html?lang=de) |
| 96 | Match minute | min | Fatigue and timing input | C | [Bradley 2009](https://lida.sport-iat.de/ta/Record/4015478?lng=en) |
| 97 | Defender yellow card | flag | Pushes toward jockeying (est. on 1v1s) | C | [SPONET](https://lida.sport-iat.de/ta/Record/4048925?lng=en) |
| 98 | Suspension threat (one card from ban) | flag | −12% / −23% fouls | C | [SPONET](https://lida.sport-iat.de/ta/Record/4048925?lng=en) |
| 99 | Team red/yellow card count | count | Lowers win probability | C | [SPONET](https://lida.sport-iat.de/ta/Record/4020677?lng=en) |
| 100 | Substitutions / windows remaining | count | Five-sub rule | C | [IJSM 2023](https://thieme-connect.de/products/ejournals/abstract/10.1055/a-1982-9808) |
| 101 | Substitution-timing heuristic | min | 58'/73'/79' (contested) | C | [Freakonomics](https://freakonomics.com/2011/02/09/when-should-a-soccer-manager-insert-his-subs) |
| 102 | Positional familiarity / out-of-position flag | flag | White CB→RB; Lewis-Skelly CM→LB | C | [Sky Sports](https://www.skysports.com/football/news/12040/12988142/ben-white-exclusive-interview-arsenals-versatile-defender-thriving-under-mikel-arteta-and-eyeing-long-stay) |
| 103 | Footedness vs side defended | flag | Limits overlapping | C | [Hayters](https://hayters.com/is-it-time-for-mikel-arteta-to-play-myles-lewis-skelly-in-midfield/) |
| 104 | Inverted full-back / space left behind | flag, m | Exposure flagged | C | [Hayters](https://hayters.com/is-it-time-for-mikel-arteta-to-play-myles-lewis-skelly-in-midfield/) |
| 105 | Approach strategy (show outside vs inside) | category | "Fast, Slow, Sideways, Low" | C | [Elite Soccer Coaching](https://elitesoccercoaching.net/out-of-possession/full-backs-defending-in-wide-areas) |
| 106 | Body orientation / open shape | category | Coaching consensus | C | [Coaches' Voice](https://learning.coachesvoice.com/cv/body-shape-orientation-football-tactics-explained-pedri-van-dijk/) |
| 107 | Team defensive style (high press vs low block) | category | Shifts tackle vs clearance volume | C | [Football Analyst](https://the-footballanalyst.com/defensive-actions-per-90-football-statistics-explained/) |
| 108 | Opponent-adjusted duel win % (defender win % minus attacker's expected) | % | No public model; proposed | D | — |

## Twenty-five variables carry most of the predictive weight

The ranking combines three things: strength of outcome evidence (tracking/biomechanics first), whether the advisor can act on the variable (it changes with a substitution or tactical instruction), and whether it is observable in-match or as a profile. The top ten are the core duel model. Ranks 11–18 are the profile and fatigue modifiers that a substitution changes. Ranks 19–25 are context switches. Weights below rank 11 are assumptions and must be labelled as simulated.

| Rank | Variable (catalogue #) | Why it ranks here |
|---|---|---|
| 1 | Relative velocity at confrontation (40) | Strongest cross-study signal (UCL, Duarte, Oonk interaction family) |
| 2 | Relative acceleration, attacker vs defender (41, 17, 18) | Decides the short duels where most accelerations start below 7 km/h |
| 3 | Interpersonal / closing distance at engagement (42, 43) | Defines the moment the duel is lost |
| 4 | Defender stance angle, side-on vs square (45, 106) | Best-supported technique variable in elite pose data |
| 5 | Defensive pressure / second-defender support (50, 51) | Directly lowers success; a tactical lever (double-up) |
| 6 | Distance to sideline / pitch zone (48, 49) | Touchline acts as an extra defender; backs "show outside" |
| 7 | Defender deceleration and backward COD (28, 20) | Physical basis of jockeying |
| 8 | Reactive agility / anticipation (26) | Distinct from pre-planned COD (<50% shared variance) |
| 9 | Defender true-tackle / dribblers-tackled % (76, 74) | Best public historical 1v1 record (32–87% spread) |
| 10 | Defender challenges lost per 90 (75) | Exposure-normalised failure rate (White 0.89, 20th pct) |
| 11 | Attacker take-on attempts × success % (55, 56) | Sets threat volume; Doku is roughly 3 SD above the league |
| 12 | Defender A0 / time to 5–10 m (15, 23, 24) | Profile proxy for first-step quickness |
| 13 | Braking and commitment under fatigue (33, 34) | The fatigue mechanism that matters in 1v1s |
| 14 | Minutes played / HI decline (30, 31) | ~20% late-game drop; position-dependent |
| 15 | Fresh-legs substitute boost with decay (36, 38) | ~+15% HI, short-lived; core to substitution advice |
| 16 | Attacker take-on rate as sub (71) | Doku 17.6 vs 7.9 shows a fatigue-mismatch effect |
| 17 | Low centre of mass technique (29) | Biomechanical efficiency of the cut |
| 18 | Attacker direction-change and torso lean (46, 47) | Attacker-side duel features |
| 19 | Defender yellow card / suspension threat (97, 98) | Measurable foul reduction; tactical vulnerability |
| 20 | Game state and minute (95, 96) | Drives risk appetite and substitution timing |
| 21 | Positional familiarity / out-of-position flag (102) | Retrained defenders trade duel skill for build-up |
| 22 | Footedness vs side (103) | Changes which way the defender can show the winger |
| 23 | Attacker end product: xGA, box take-ons (67, 58) | Converts conceded duels into danger (Doku, Saka) |
| 24 | Top speed, recovery only (1, 4) | Weak or negative direct effect; matters beyond ~20–40 m |
| 25 | Inverted full-back exposure / team style (104, 107) | Structural context for isolation frequency |

## Conclusion

The research changes the matchup question. "Is my full-back fast enough for Doku?" is the wrong frame. The useful questions are whether the defender can **win the first two steps, brake without over-committing, and stay side-on with help nearby**, and whether fatigue, a booking or an unfamiliar flank is eroding exactly those qualities. That points to a defensible advisor design: a logistic duel model over relative physical terms, technique and context. This mirrors the published academic form, and its modest accuracy (F1 about 0.5) is honest about how random duels are. A substitution or tactical change mainly works through the levers the model exposes: fresh acceleration and braking, a double-up, a side-on approach, or a defender comfortable on that flank.

The biggest gaps are also the most decision-relevant. No public source gives deceleration or change-of-direction data for any of the six named players. Arsenal's top-speed figures are non-official. No elite study measures 1v1 win rate by minute, game state, line height or after a fresh full-back comes on, and no public opponent-adjusted duel metric exists. A synthetic product can fill these gaps legitimately only if every such parameter is generated from stated priors and explicitly labelled **simulated**.
