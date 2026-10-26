# Physical / Tracking Performance Metrics of Elite Premier League Footballers, by Position

Scope: PL and elite European football, recent seasons where possible (2019-2026). Older but foundational EPL studies (Bradley 2009, Di Salvo 2009) are included and marked as older. **[NON-OFFICIAL]** marks values from fan or aggregator sites. **[ESTIMATE]** marks values I derived. Providers differ: Opta (PL website), Tracab/ChyronHego (LaLiga Mediacoach), Second Spectrum (PL optical tracking), and GPS. Thresholds and filtering vary by provider, so absolute values are not interchangeable.

### Variable catalogue (quick reference for simulator design)

| Variable | Definition | Unit | CB | FB | CM | Winger / wide | Source basis |
|---|---|---|---|---|---|---|---|
| Top speed (match peak) | Highest instantaneous speed reached in a match or season | km/h | 30-37 (season peak); team mean about 34.7 (9.63 m/s) | 33-37.3 | 29-36.7 | 32-36.7 | PL/Opta leaderboards; Kavanagh 2024 |
| Total distance | Distance covered per match or per 90 | km | about 8.5-10.0 | about 10-11 [ESTIMATE] | about 11.6-12.9 | about 10.5-11 | PL/Opta; Kavanagh 2024 |
| Total distance rate | Total distance divided by minutes played | m/min | about 103 | - | about 120 | about 112 (forwards) | Kavanagh 2024 |
| High-speed running (HSR) | Distance above 5.5 m/s (19.8 km/h) | m per match | about 700 (defenders as a group) | higher than CB | about 990 | about 940 (forwards) | Kavanagh 2024 |
| High-intensity running (HIR, older definition) | Distance above the HIR threshold (threshold not stated in the abstract; see Gaps) | m per match | 1,834 | 2,605 | 2,825 | 3,138 (wide midfielders) | Bradley 2009 (2005/06 season) |
| Sprint distance | Distance above 7 m/s (25.2 km/h) | m per match | about 150 (defenders) | - | about 160 | about 200 (forwards) | Kavanagh 2024 |
| Sprint count | Number of runs above 25 km/h | count per season | - | up to 702 over 29 matchweeks (A. Robinson) | - | 640-670 over 29 matchweeks (Gordon, Mbeumo) | PL/Opta 2024/25 |
| % of time sprinting | Share of match time spent above 25 km/h | % | - | about 1.0-1.05 | - | about 1.1-1.17 | PL/Opta 2024/25 |
| Theoretical max acceleration (A0) | Intercept of the in-match acceleration-speed profile at 0 km/h | m/s² | max 7.89, mean 6.79 | max 7.84, mean 6.70 | max 7.30, mean 6.44 | max 7.84, mean 6.40 | LaLiga Mediacoach 2020-23 |
| Acceleration-speed slope | Loss of acceleration per km/h of starting speed | m/s² per km/h | -0.255 | -0.237 | -0.241 | -0.233 | LaLiga 2020-23 |
| High-intensity accelerations / decelerations | Count of efforts above +3 (or 2.5) m/s² or below -3 (or -2.5) m/s² | count per match | lower | highest | - | - | EPL vs Ligue 1 study; Harper 2019; SMF 2022 |
| 10 m / 30 m sprint time (test) | Time over 10 m and 30 m from a standing start | s | about 2.25 at 10 m (defenders, U21) | - | about 2.19 at 10 m | about 2.17 at 10 m (forwards) | Slovak U21 study (small sample) |
| Fatigue drop | Last-15-minute vs first-15-minute HIR | % | about -20% | about -19% | about -20% | about -21% | Bradley 2009 |
| Recovery between very high-intensity bouts | Time between very high-intensity efforts | s | overall mean 72 (65 in the first 15 min, 83 in the last 15 min) | | | | Bradley 2009 |

---

## 1. Top sprint speed: ranges, PL leaderboards, and the named players' top speeds

### Takeaway
In recent PL seasons, the elite season-peak top speed is 36-37.4 km/h. The all-time record is Van de Ven's 37.38 km/h (Jan 2024), and the 2025/26 maximum was Tchatchoua's 37.30 km/h. Typical squad players peak at 32-35 km/h, and the slowest outfield players peak at about 29-30 km/h. The top-10 speeds are dominated by wingers, full-backs and wing-backs. Among the named players, Doku's 2024/25 PL top speed was 35.14 km/h (Opta). Figures for Saka, Rice, White, Timber and Mosquera come only from a non-official source.

### Cited Findings
- **2025/26 PL top speeds (end of season, PL official):** Tchatchoua (WOL) 37.30 km/h vs EVE on 30/08/25, and again 36.97 km/h. Then Martinelli (ARS) 36.74, Udogie (TOT) 36.41, Elanga (NEW) 36.35, Mbeumo (MUN) 36.34, Neto (CHE) 36.32, Osula (NEW) 36.29, Gordon (NEW) 36.26, Haaland (MCI) 36.20 (vs ARS 19/04/26), Frimpong (LIV) 36.18, D. James (LEE) 36.13, Minteh (BHA) 36.11. Each club's fastest player ranged from 34.68 (Maatsen, AVL) to 35.95 (Kevin, FUL). — [Premier League: Who ran fastest and furthest in 2025/26](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league)
  - The same table lists Spence (TOT) 36.62 with a date of 25/04/25, which appears to be a 2024/25 effort. This is an inconsistency in the source. — same source
- Nine of the 10 fastest speeds in 2025/26 belonged to wingers, full-backs or wing-backs. Van de Ven's 37.38 km/h vs Brentford (Jan 2024) is the all-time PL record. — [Premier League news (search summary of 2025/26 articles)](https://www.premierleague.com/en/news/4406647/fastest-players-of-202526-so-far-tchatchoua-leads-the-pack)
- **2024/25 (Opta snapshot after 29 matchweeks):** Van de Ven 37.1, Matheus Nunes 36.7, Mbeumo 36.6, Minteh 36.4, Elanga 36.2 km/h. The fastest goalkeeper was Raya at 32.7 km/h. The slowest outfield players were Bernardo Silva 29.4, Dawson 29.6, Merino 29.8, and Casemiro and Soucek 30.2 km/h. — [Premier League: Who tops the 2024/25 running charts?](https://www.premierleague.com/news/4272290)
- An earlier 2024/25 list included Antonee Robinson (FB) at 35.63 km/h and Yerson Mosquera (CB) at 35.32 km/h, the quickest defenders after Van de Ven. — [Squawka](https://www.squawka.com/en/features/fastest-premier-league-players-now-2024-25) [NON-OFFICIAL aggregator of Opta data]
- **Jérémy Doku, 2024/25 PL (Opta):** 35.14 km/h, sixth-fastest at Man City behind Nunes 36.72, Khusanov 36.27, Haaland 36.01, Marmoush 35.47 and Walker 35.24. The PL analysis says Doku's edge is acceleration over "two or three yards", not top speed. Doku has said: "over 15 metres, I back myself. But over maybe 40, I think he [Khusanov] will win." — [Premier League: Is Doku the best dribbler in the world?](https://www.premierleague.com/en/news/4293725)
- **Doku, UCL 2025/26:** UEFA's player page shows a "top speed" of 32.06 km/h over 9 matches. It is unclear whether this is a peak or an average, and it covers UEFA competition only. — [UEFA player page](https://www.uefa.com/uefachampionsleague/clubs/players/250113142--jeremy-doku)
- **Doku dribbling context, 2024/25 PL:** 10.84 dribbles attempted per 90, 6.77 completed, a 62.4% success rate (league best), 10.78 duels won per 90 (league best), and 309 progressive carries (most in the league), all in 1,303 minutes. — [Premier League](https://www.premierleague.com/en/news/4293725)
- **Arsenal 2026/27 "so far" table [NON-OFFICIAL, source of the data not named; the article links FotMob for match-level figures]:** Mosquera 34.8, Havertz 34.1, Rice 32.4, Saka 32.2, Gabriel 32.2, Ben White 32.1, Ødegaard 31.6, Timber 29.7, Calafiori 29.7 km/h. Saka reached 30.9 km/h vs Brighton on 19/09/2026. — [Daily Cannon, Sept 2026](https://dailycannon.com/2026/09/arsenals-fastest-player/)
  - **Reliability warning:** the extracted table also lists names that are unexpected at Arsenal (e.g. Ezri Konsa, Bruno Guimarães, Christos Tzolis). The list may be a misparse, may mix in opponents, or may reflect transfers I cannot verify. Use it with caution. These are early-season values (a few matches), so they sit below season peaks.
- **Mosquera, UCL 2025/26:** UEFA lists a top speed of 32.46 km/h and an average of 29.11 km/h per match. — [UEFA player page](https://www.uefa.com/uefachampionsleague/clubs/players/250129972--cristhian-mosquera) (via search summary)
- **Martinelli** is Arsenal's quickest in official data: 35.6 km/h in 2024/25 and 36.74 km/h in 2025/26. — [Planet Football 2024/25](https://www.planetfootball.com/premier-league/fastest-players-premier-league-2024-25-haaland-rashford-van-de-ven); [PL 2025/26](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league)
- **Research data, EPL optical tracking (2019-21, one club, n=16):** in-match peak speed for defenders was 9.63 ± 0.35 m/s (about 34.7 km/h), midfielders 9.37 ± 0.43 m/s (about 33.7 km/h), forwards 9.83 ± 0.32 m/s (about 35.4 km/h), and all players 9.53 m/s (about 34.3 km/h). — [Kavanagh et al. 2024, Biology of Sport](https://pmc.ncbi.nlm.nih.gov/articles/PMC11474994/)
- Opta's speed measurement method has changed across seasons, so top-speed lists from different seasons are not strictly comparable. — [search summary of Opta-based lists; e.g. NBC Sports](https://nbcsports.com/soccer/news/who-are-the-fastest-players-in-the-premier-league)

### Inferences
- Realistic simulator ranges for season-peak top speed: wingers 33-36.7, FB 32-37.3, CB 30-37 (with wide variance: Van de Ven and Khusanov are outliers), CM 29-36.7 (Nunes is an outlier, and the typical CM is about 31-33). A single match's peak is usually 1-3 km/h below the season peak [ESTIMATE, consistent with the Saka match value of 30.9 vs a table value of 32.2].
- Doku (35.14) is quick but not elite on top speed. His threat is short-range acceleration and dribble volume, so a matchup model should weight acceleration over top speed for him.

### Gaps
- No official PL/Opta top speed for Saka, Rice, White or Timber was found. The only figures are the non-official Daily Cannon list.
- No official 2025/26 PL top speed for Doku was found.
- SkillCorner and Second Spectrum public leaderboards were not retrieved.

---

## 2. Acceleration, time to 5/10 m, deceleration, change of direction

### Takeaway
In-match acceleration-speed profiling (LaLiga, 25 Hz) gives a theoretical maximal acceleration (A0) of about 6.4-6.8 m/s² on average and 7.3-7.9 m/s² at best. Acceleration falls by about 0.24 m/s² for every km/h of starting speed. Almost 90% of accelerations above 3 m/s² start below 7 km/h. Full-backs face the highest acceleration and deceleration loads. Senior position-specific 5 m and 10 m norms are sparse.

### Cited Findings
- **LaLiga, 2020/21-2022/23, Mediacoach (Tracab) at 25 Hz, 363 players, 8,426 observations:** A0 maximum and mean (m/s²) by position: CB 7.89 / 6.79; FB 7.84 / 6.70; CM 7.30 / 6.44; attacking midfielder 7.39 / 6.48; winger 7.84 / 6.40; forward 7.58 / 6.60; all players 7.63 / 6.58. Slopes range from -0.23 to -0.26 m/s² per km/h. Initial speed explained 97.7% of the variance in maximal acceleration (r = -0.99). 88-91% of accelerations above 3 m/s² began at initial speeds below 7 km/h. The authors argue that fixed acceleration thresholds misclassify efforts that start at different speeds. The text reports forwards with the highest A0 and CBs with the lowest, which conflicts with the table (CB has the highest maximum A0), so the source is internally inconsistent. — [Acceleration-speed profiles in LaLiga, Biology of Sport 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12490324/)
  - [ESTIMATE] The implied theoretical maximum speed (A0 / |slope|) is about 30-32 km/h, below observed peaks, because these are in-match profiles rather than maximal tests.
- **Spanish second division:** the acceleration-speed profile (ACC_max, A0) differed significantly by position (CB, FB, midfielder, wide midfielder, forward) and by microcycle day. — [PMC9649751](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9649751/)
- **EPL vs Ligue 1:** using a +3 m/s² threshold for explosive accelerations and decelerations, there were significant positional differences for every position except centre-forward, and a higher relative number of accelerations and decelerations in the EPL than in Ligue 1. — [Positional demands of explosive actions, EPL vs Ligue 1](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11694201/)
- Full-backs are generally exposed to higher acceleration and deceleration demands than other positions. — [Science and Medicine in Football 2022 accepted manuscript](https://oars.uos.ac.uk/2542/3/manuscript%20AAM.pdf)
- **Harper, Carling & Kiely 2019 (Sports Medicine) meta-analysis:** this review defines high-intensity accelerations and decelerations as above 2.5 m/s² and very high intensity as above 3.5 m/s², and pools GPS match data from 2010-2018. It is the main reference for the finding that decelerations outnumber accelerations. — [Harper et al. 2019, PMC6851047](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6851047/)
- **Elite Australian soccer, 5 Hz GPS, 29 players:** about 65 ± 21 maximal accelerations vs 8 ± 5 sprints per game, roughly 8 accelerations per sprint. Wide defenders performed the most maximal accelerations. CBs and midfielders sprinted less than other positions. — [Varley & Aughey, Acceleration profiles in elite Australian soccer, IJSM](https://vuir.vu.edu.au/id/eprint/23141) (older, 2013, non-PL)
- **Sprint tests, Slovak national U21 (n=20):** squad mean 10 m time 2.20 ± 0.09 s and 30 m time 4.59 ± 0.09 s. Forwards were fastest at 10 m (about 2.17 s), then midfielders (2.19), defenders (2.25) and goalkeepers (2.31). — [Slovak U21 sprint study](https://library.sk/arl-umb/en/detail-umb_un_cat-0207921-A-level-of-sprint-ability-of-elite-young-football-players-at-different-positions) (small sample, older)
- **Start-line protocol:** a 100 cm vs 30 cm start changes times by about 0.076 s at 5 m, 0.102 s at 10 m and 0.114 s at 30 m, so norms must match the protocol. — [PMC12568230](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12568230/)
- **Change of direction:** in a 45° defensive change of direction under fatigue (17 professional players), approach speed was unchanged but braking time and braking impulse fell. Fatigued defenders may not slow down enough before turning. — [de Pablo et al. 2024, Heliyon](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11609251/)

### Inferences
- For a simulator: per-match max acceleration of about 4-6 m/s² observed (because of thresholding) and an A0 of 6.4-7.9 m/s². Deceleration peaks are typically larger in magnitude than acceleration peaks [ESTIMATE; consistent with the Harper review's focus, but the exact numbers were not retrieved].
- 10 m times for elite senior players are likely about 1.65-1.85 s with a flying or 0.5 m start, or about 2.0-2.2 s from a static start [ESTIMATE; no senior PL source found].

### Gaps
- Pooled per-match high-intensity deceleration and acceleration counts from Harper 2019 could not be extracted (the PDF was not parseable).
- No public PL-official acceleration leaderboard was found.
- No senior elite position-specific 5 m and 10 m norm table was found.

---

## 3. Volume metrics per 90 (distance, HSR, sprint, counts, high-intensity actions) by position

### Takeaway
Central midfielders cover the most total distance (about 11.5-12.9 km per 90 at the top). CBs cover the least (about 8.5-10 km). Wide players and full-backs lead high-intensity and sprint volume, and CBs are lowest on every intensity metric. Modern EPL tracking gives about 700-1,000 m of HSR (above 19.8 km/h) and about 150-200 m of sprinting (above 25.2 km/h) per match.

### Cited Findings
- **EPL, 2019-21, one club, optical tracking, 630 observations (Table 2, whole match):** defenders TD 9,966 ± 515 m, HSR 697 ± 275 m, sprint 151 ± 95 m. Midfielders TD 11,594 ± 622, HSR 992 ± 205, sprint 158 ± 80. Forwards TD 10,710 ± 573, HSR 941 ± 182, sprint 202 ± 84. Per minute: defenders 103.2 / 7.2 / 1.6 m/min; midfielders 120.3 / 10.3 / 1.7; forwards 111.7 / 9.9 / 2.1. Thresholds: HSR above 5.5 m/s, sprint above 7 m/s. — [Kavanagh et al. 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11474994/)
- **EPL 2019-21, 17 players:** CBs had lower high-intensity values than full-backs, midfielders and wide midfielders. — [UCLan repository](https://knowledge.lancashire.ac.uk/id/eprint/50268/)
- **Bradley et al. 2009, EPL 2005/06, 28 matches, 370 observations [older]:** high-intensity running per match: wide midfielders 3,138 ± 565 m, CM 2,825 ± 473, FB 2,605 ± 387, attackers 2,341 ± 575, CB 1,834 ± 256. — [Bradley et al. 2009 abstract](https://lida.sport-iat.de/ta/Record/4015478?lng=en); [Sunderland repository](https://sure.sunderland.ac.uk/3478)
- **Di Salvo et al. 2009 (IJSM), EPL 2003-06, 563 players [older]:** same positional ordering for high-intensity running, with wide midfield highest (about 1,049 m) and CB lowest (about 681 m). The metric definitions differ from Bradley's. — [Thieme](https://www.thieme-connect.com/products/ejournals/html/10.1055/s-0028-1105950)
- **PL/Opta 2024/25 (after 29 matchweeks):** sprints (above 25 km/h): Antonee Robinson (FB) 702, Gordon (W) 666, Daniel Muñoz (WB) 658, Mbeumo (W) 647, Kerkez (FB) 639. Share of time sprinting: Elanga 1.17%, Gordon 1.10%, Darwin Núñez 1.07%, Muñoz 1.05%, Robinson 1.04%. Distance per 90 (1,500+ minutes): Kulusevski 12.3, Soucek 12.2, Tonali 12.2, B. Silva 11.9, Downes 11.6 km. Yarmoliuk had 12.9 km (600+ minutes). Lowest per 90: Murillo 8.5, Van Dijk 8.8, Milenkovic 8.9, Hudson-Odoi 8.9, Konaté 9.0. Van Dijk walked 76.5% of game time. — [Premier League running charts 2024/25](https://www.premierleague.com/news/4272290)
- **PL 2025/26 season totals:** Garner (EVE) 415.46 km in 3,414 minutes [ESTIMATE about 10.95 km per 90], Anderson 411.06 in 3,334, Truffert 402.59 in 3,380. **Declan Rice (ARS) 380.22 km in 3,099 minutes** [ESTIMATE about 11.04 km per 90], the highest at Arsenal. Bernardo Silva 388.85 km in 3,405 minutes. The highest single-match distance was Bruno Guimarães at 13.24 km (vs LEE 07/01/26). B. Silva had 4 of the top 8 single-match distances (12.84-13.13 km). — [Premier League 2025/26](https://www.premierleague.com/en/news/4673057/who-ran-fastest-and-furthest-in-202526-premier-league)
- **Older Australian GPS data:** about 8 ± 5 sprints and about 65 maximal accelerations per game. — [VU repository](https://vuir.vu.edu.au/id/eprint/23141)

### Inferences
- Simulator per-90 targets (recent EPL): CB TD 9.0-10.0 km, HSR 450-700 m, sprint 100-200 m, about 8-15 sprints. FB TD 10.0-11.0 km, HSR 800-1,100 m, sprint 200-350 m, about 20-30 sprints. CM TD 11.0-12.5 km, HSR 800-1,100 m, sprint 100-200 m. Winger TD 10.3-11.2 km, HSR 900-1,200 m, sprint 250-400 m, about 25-35 sprints. These are [ESTIMATE] values that combine Kavanagh's group means with the Bradley/Opta positional ordering. The sprint counts come from Opta's season totals (about 640-700 over about 29 matchweeks, or about 22-25 per match for leaders) and are scaled down for typical players.
- Rice's about 11.0 km per 90 places him at the top end for an Arsenal CM.

### Gaps
- No public per-player HSR or sprint distance for Saka, Rice, White, Timber, Mosquera or Doku was found. SkillCorner and Second Spectrum per-player data are not public.
- Recovery-run counts, a defined "high-intensity action" count, and per-position values with full-back vs winger separation in a recent EPL dataset were not found.

---

## 4. Fatigue: high-intensity decline across the match and substitute impact

### Takeaway
High-intensity running falls by about 20% from the first 15 minutes to the last 15 minutes in every position. Recovery time between very high-intensity bouts lengthens by about 28% (65 s to 83 s). Output also drops temporarily after the most intense 5-minute period. Substitutes produce more high-intensity output in the closing period than the starters still on the pitch.

### Cited Findings
- **Bradley et al. 2009 (EPL 2005/06):** high-intensity running in the first 15 minutes vs the last 15 minutes: wide midfielders 589 → 467 m; CM 534 → 429; FB 481 → 389; attackers 438 → 348; CB 344 → 276. Every decline is about 20% (p < 0.01). With possession 193 → 148 m, without possession 278 → 229 m. Recovery between very high-intensity bouts averaged 72 ± 28 s overall, 65 ± 20 s in the first 15 minutes and 83 ± 26 s in the last 15 minutes. After the peak 5-minute period, output dropped sharply (attackers 216 vs 113 m; CB 182 vs 96 m). — [Bradley et al. 2009 abstract](https://lida.sport-iat.de/ta/Record/4015478?lng=en)
- **Substitutes:** in a study cited by a review of LaLiga work, substitutes covered 25% more high-intensity actions and 63% more sprint distance than starters over the final 15 minutes. The original study was not verified. — [PMC9145854 review](https://pmc.ncbi.nlm.nih.gov/articles/PMC9145854)
- High-intensity running was greater in substitutes than in players who completed the match or were replaced. The league was not confirmed. — [Evaluation of the match performances of substitution players in elite soccer](https://sponet.de/sponet/Record/4031824)
- **Fatigue and change of direction:** braking time and impulse fall under fatigue in a defensive 45° cut. — [de Pablo et al. 2024](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11609251/)
- **Fatigue and 1v1 anticipation:** after small-sided-game fatigue, jump, 5 m acceleration and sprint performance fell, and defenders initiated movement earlier when anticipating an attacker's direction change. — [Leeds Beckett / Portsmouth study](https://eprints.leedsbeckett.ac.uk/id/eprint/7648)

### Inferences
- Simulator rule of thumb: scale high-intensity output by about 0.80 by minutes 75-90 relative to minutes 0-15 for players who started. Fresh substitutes run at about 1.0-1.25 times the starters' high-intensity rate over the same window [ESTIMATE from the cited magnitudes]. Fatigue in a defender should increase the probability of being beaten 1v1 through poorer braking and premature commitment.

### Gaps
- No PL-specific recent (2022-26) first-15 vs last-15 decline data was found. Bradley 2009 is old. Modern effects may be similar but are unverified.
- The original substitute study (the 25% / 63% figures) was not retrieved.
- Bradley's speed threshold for "high intensity" was not stated in the retrieved abstract. The conventional value in this literature is above 14.4 km/h for HIR and above 19.8 km/h for very high-intensity running, but this is unverified here.

---

## 5. Which physical qualities matter most for defending 1v1 against fast dribbling wingers?

### Takeaway
Evidence points to short-range acceleration, deceleration and braking ability, and reactive agility and anticipation as the qualities that matter most. Top speed matters less: the decisive actions are short (under about 15 m), start from low speed, and depend on reading the attacker's change of direction. Fatigue degrades braking and makes defenders commit earlier. Top speed matters mainly for recovery runs over long distances (40 m or more).

### Cited Findings
- Doku's effectiveness is attributed to acceleration over "two or three yards" rather than top speed. He backs himself over 15 m but expects the faster Khusanov to win over 40 m. Doku's top speed is 35.14 km/h, below several City teammates. — [Premier League Doku analysis](https://www.premierleague.com/en/news/4293725)
- 88-91% of high accelerations (above 3 m/s²) start below 7 km/h, and acceleration capacity falls steeply with starting speed. — [LaLiga AS profile study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12490324/)
- **Reactive agility and backward change of direction in defending:** faster players on the reactive agility test decelerated quickly with higher step frequency and a lower, backward-tilted centre of gravity during the turn. — [Kawahara et al., ISBS proceedings](https://commons.nmu.edu/isbs/vol36/iss1/252)
- **Diagonal backward change of direction in 1v1 chasing:** this study looks at the kinematic and kinetic mechanisms that let defenders re-accelerate after turning. — [Yoshida et al., Ritsumeikan](https://www.ritsumei.ac.jp/~isaka/ronbun/yosida.pdf)
- Fatigued defenders brake less in a defensive cut and anticipate prematurely in 1v1 tasks. — [de Pablo 2024](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11609251/); [Leeds Beckett](https://eprints.leedsbeckett.ac.uk/id/eprint/7648)
- Full-backs face the highest acceleration and deceleration loads of any position, consistent with repeatedly confronting wingers. — [SMF 2022 AAM](https://oars.uos.ac.uk/2542/3/manuscript%20AAM.pdf); [Varley & Aughey](https://vuir.vu.edu.au/id/eprint/23141)

### Inferences
- A suggested weighting for a simulated fullback-vs-winger 1v1 contest [ESTIMATE, design heuristic and not empirical]: acceleration (0-5 m) and deceleration/change of direction about 50%, reactive agility and anticipation about 30%, top speed about 20%. Raise the weight on top speed when the attacker gets in behind (space over 20 m). Apply a fatigue penalty after minute 70.
- **Matchup notes [inference]:**
  - Doku (top speed 35.1, elite dribble volume) vs Timber: a low top-speed reading (29.7, non-official) may matter less than Timber's change of direction, which is not measured publicly.
  - Doku vs White (32.1, non-official) is a similar case.
  - Mosquera's higher top speed (34.8, non-official) suits recovery runs.

### Gaps
- No peer-reviewed study was found that directly quantifies which physical quality best predicts 1v1 defensive success against dribblers in elite matches.
- No public deceleration or change-of-direction metrics were found for Timber, White, Mosquera, Saka, Rice or Doku.
