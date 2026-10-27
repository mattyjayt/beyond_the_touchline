# Determinants of 1v1 Defensive Duels vs Dribbling Wingers, and How Analytics Models Matchups

Scope: elite football, mostly 2010–2026. Research budget was about 17 tool calls, so the evidence is directional. The tracking-data studies with the most rigour are Oonk et al. 2024 (Eredivisie), Bauer et al. 2025 (UCL pose data), and a J1-League physics model.

## Q1. Sports science and coaching evidence on 1v1 defending: acceleration vs top speed, reaction, body orientation, starting distance, deceleration, agility

### Takeaway
Elite tracking studies agree on one point: what decides a duel is the **interaction** between the two players at the moment of confrontation. That means relative velocity, accelerations, interpersonal distance and the defender's stance angle. The defender's top speed alone does not decide it. Reactive agility and deceleration technique are separate qualities from pre-planned change-of-direction (COD) and top speed. Most quantified evidence comes from small or youth samples.

### Cited Findings
- **Elite Eredivisie tracking study (Oonk, Kempe, Buurke, Lemmink, ECSS 2024).** It covered 734 1v1 actions from 43 matches (356 successful, 378 unsuccessful), labelled by three raters (Fleiss kappa 0.76 for selection, 0.89 for outcome). There were 24 tracking variables in three groups: *individual* (e.g. defender velocity), *interaction* (e.g. attacker–defender relative velocity) and *environmental* (e.g. pitch location). A MANOVA showed that outcome had an overall effect (Wilks' λ = 0.881, F(23,710) = 4.178, p < 0.001). Post-hoc tests found **five individual variables** that differed between successful and unsuccessful actions. The accessible abstract is cut off before it names them. — [SPONET/DFB record](https://lida.sport-iat.de/dfb/Record/4093794)
- **UCL 2022/23 3D-pose study ("What Makes a Dribble Successful?", arXiv 2506.22503).** It covered 1,736 one-on-one dribbles from 125 matches (690 successful, 1,046 unsuccessful), using Hawk-Eye SkeleTRACK at 25 Hz plus Stats Perform events. Findings:
  - Higher **maximum speed** of both attacker and defender went with *lower* dribble success.
  - A **relative speed advantage** for the attacker went with *higher* success.
  - **Higher defensive pressure** lowered success.
  - Dribbles **further from the sideline** were more likely to succeed.
  - A larger angle between attacker and defender hip vectors, i.e. a defender who is more **"squared-up"**, went with higher attacker success. This implies a side-on stance helps the defender. Stances were grouped as side-on, intermediate and squared-up.
  - A large attacker **torso lean** went with failure. Ball-touch frequency and ball–foot distance had minimal effect.
  - The model was L2 logistic regression. F1 scores: 0.35 for location only, 0.49 for 2D features, 0.52 for 2D + 3D. Brier scores were about 0.243–0.244, so predictive power is modest overall.
  - The 2D feature set was: distance to sideline, distance to goal, attacker max speed, defender max speed, attacker max acceleration, attacker max direction change, max relative speed, and mean pressure score.
  — [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1)
- **Frontal 1v1 study using LPM position data (Univ. Vienna thesis; related IJPAS 2015 paper on youth players).** The **moment of confrontation** was key. **Accelerations of both players** and **defender velocity** differed significantly between successful and unsuccessful trials. — [Univ. Vienna (Phaidra)](https://services.phaidra.univie.ac.at/api/object/o:1323609/download)
- **Ecological dynamics of 1v1 sub-phases (Duarte et al. 2010).** Six U13 players did 120 trials from four defender–ball starting distances between 1 and 2.5 m. The dyad broke from stable into unstable states (the attacker getting past) at moments of **higher relative velocity and lower interpersonal distance**. **Starting distance** was manipulated as a control variable. — [Univ. Évora repository](https://rdpc.uevora.pt/handle/10174/2095); [SHU repository](https://shura.shu.ac.uk/3343/)
- **U18 1v1 with goalkeeper (Clemente et al. 2013).** Eleven players took part. Attacker–defender **distance, speed and angular separation** rose when the attacker tried to get past. — [RCAAP](https://dspace.rcaap.pt/entities/publication/dc357f2b-3ea2-4846-afc5-b5db84cdbf0e/full)
- **Defensive cutting biomechanics (Sasaki et al. 2015, J Hum Kinet).** Six collegiate match scenes were reconstructed in 3D. A **lower centre of mass at initial contact** (mainly through more hip flexion) went with less vertical travel during the defensive cut, i.e. a more efficient reaction. — [PMC4519200](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4519200/)
- **Defensive backward COD (Kawahara et al., ISBS 2018).** Thirteen players did a reactive agility test. Faster defenders **decelerated quickly through high step frequency** before and after the COD. They also kept the trunk tilted backward and the centre of gravity low. — [ISBS proceedings PDF](https://sprinz.aut.ac.nz/__data/assets/pdf_file/0016/203083/205_1553_Kawahara.pdf); [NMU ISBS](https://commons.nmu.edu/isbs/vol36/iss1/252)
- **Reactive vs pre-planned agility.** This evidence comes from rugby, not football. Reactive conditions produced lower lateral speed and more lateral foot displacement. **Anticipation** separated fast from slow performers. Earlier research found **less than 50% shared variance** between reactive and pre-planned agility. — [JSSM 9(3):445](https://www.jssm.org/jssm-09-445.xml-Fulltext)
- **Position and reactivity in youth (Fiorilli et al., JSSM 2017).** In 92 elite Italian youth players, forwards were significantly more reactive than defenders on the Y-agility test (p < 0.05). — [JSSM 16(2):247](https://jssm.org/16-2-247.p_d_f)
- **Coaching guidance (body orientation).** Correct body orientation gives defenders more information for decisions. Nuno Mendes keeps an open body shape so he can see his direct opponent and still intervene. — [Coaches' Voice](https://learning.coachesvoice.com/cv/body-shape-orientation-football-tactics-explained-pedri-van-dijk/)
- **Coaching guidance (approach and starting position).** The approach cue is "Fast, Slow, Sideways, Low". The full-back either matches the winger's pace to block the cross or retreats to affect it. — [Elite Soccer Coaching](https://elitesoccercoaching.net/out-of-possession/full-backs-defending-in-wide-areas). Other coaching points:
  - Start narrow to stop the CB–FB pass.
  - Jockey on the winger's first touch.
  - "Show the winger down the line" and don't over-commit.
  — [Sport Session Planner](https://www.sportsessionplanner.com/s/v77Ci/position-specfic-working-on-full-backs-defending-1v1.html)

### Inferences
- **Acceleration and relative velocity matter more than top speed.** Top speed even correlates negatively with success in the UCL data, probably because high-speed duels are open-field situations that already favour one side. For a simulator, model duels with **relative** terms (attacker acceleration/agility minus defender acceleration/reactive agility) rather than absolute pace.
- **Deceleration and low centre of mass are the physical basis of "jockeying".** A defender's deceleration/COD quality is a separate attribute from sprint speed.
- **Body orientation (side-on vs square) is the best-supported technical variable** in elite tracking. It is a technique/discipline attribute.
- **Starting/interpersonal distance and closing speed** are state variables. Small distance plus high relative velocity marks the moment a duel is lost.
- **Pitch context matters.** Near the touchline the attacker succeeds less often (the line acts as an extra defender), so "show down the line" is consistent with the data.

### Gaps
- I could not access the names of the five significant individual variables in Oonk et al. 2024 (abstract truncated). A full paper may exist but I did not find it.
- I found no quantified elite study isolating **simple reaction time** or 10 m acceleration tests as predictors of match 1v1 success.
- A 2026 arXiv preprint, "A behavioral principle underlying attacker-defender interactions in soccer" (J1 League, 306 games), was too large to fetch, so its findings are unknown — [arXiv 2607.05845](https://arxiv.org/pdf/2607.05845)
- No effect sizes were extractable from the UCL paper's SHAP figure.

## Q2. Analytics approaches: duel models, dribbled-past rates, opponent-adjusted metrics, positional versatility and retraining

### Takeaway
Public industry metrics for 1v1 defending are still mostly **ratio stats from event data**, such as tackle/dribbled-past % or "true tackle" win %. Academic models use **tracking-derived features** in logistic regression or physics-based models. Opponent-adjusted or matchup-specific duel models are rare in public work. Coaches who retrain players cite on-ball comfort, tactical intelligence and the player's own belief more than raw 1v1 defending.

### Cited Findings
- **Opta "true tackles".** These are successful tackles (ball regained or put out of play), plus challenges lost without touching the ball, plus fouls committed while trying to tackle. 2025/26 PL leaders against dribbles (minimum 20 dribbles faced, data to 12 Nov 2025):
  - Maxence Lacroix: 87.0% (20/23).
  - Marc Guéhi: 81.5% (22/27).
  - Kieran Trippier was lowest at 32.3% (10 fouls, dribbled past 11 times).
  — [Premier League / Opta Analyst](https://www.premierleague.com/en/news/4461616/opta-analyst-on-quirkier-stats-in-2025-26-including-most-long-throws-and-best-defenders-v-dribbles)
- **Scouting use of StatsBomb data.** Hudl/StatsBomb scouting workflows use **Tackle/Dribbled Past %** as a competence filter in ground duels, alongside player archetypes. — [Hudl blog](https://www.hudl.com/blog/modern-scouting-workflows-player-archetypes-statsbomb)
- **StatsBomb Defensive Responsibility (DefR).** It is event-based and spreads defensive accountability across the team by comparing expected and actual defensive actions per player. It could be adapted to 1v1 matchups. — [Hudl/StatsBomb DefR](https://www.hudl.com/blog/defensive-responsibility-defr-statsbomb)
- **Off-ball defending (StatsBomb/Hudl research, 2025).** "Cover shadows" quantify off-ball defensive impact. — [Casciolio & Wang PDF](https://static.hudl.com/craft/performance-insights-research-stage/2025/Quantifying-Off-Ball-Defensive-Impact-through-Cover-Shadows-Lorenzo-Casciolio-Allen-Wang.pdf)
- **Community 1v1 definition from StatsBomb 360 data.** A 1v1 is a reception where the nearest defender is more than 3 yd away and the second-nearest is more than 7 yd away. The thresholds were chosen by video review. Outcomes were valued with OBV. The author notes that set pieces create artificial 1v1s. — [Substack: introducing 1v1s](https://talatabont.substack.com/p/introducing-1v1s-to-football)
- **Physics-based Attacker–Defender model (arXiv 2512.22596).** It used 31,028 dribbles from 306 J1-League 2023 matches. Each player has a driving force (f), a time to reach max speed (τ), and a goal-vs-opponent weighting (β). Defenders cluster into four behaviour quadrants (pressing, retreating, approaching from the side, and so on). The model is descriptive and is not linked to outcomes. Fit was good in 88.5% of events. — [arXiv 2512.22596](https://arxiv.org/html/2512.22596v1)
- **Review.** A scoping review covers tracking data for defensive play. — [SPONET record](https://lida.sport-iat.de/dfb/Record/4083204)
- **Ben White, CB to RB.** At Brighton he had played on the right of a back three, driving forward to support Lamptey. Arteta said: "We all believed (White) had the qualities to (play fullback) and the most important step was for him to believe he could do it". White said that for Arteta, "you've got to be a centre mid, a centre-back, a winger, a No 10." — [Sky Sports interview](https://www.skysports.com/football/news/12040/12988142/ben-white-exclusive-interview-arsenals-versatile-defender-thriving-under-mikel-arteta-and-eyeing-long-stay); [Arseblog tactics column](https://arseblog.com/2024/03/tactics-column-swiss-army-white/)
- **Myles Lewis-Skelly, CM to inverted LB.** He came through the academy as a ball-carrying CM. He was tried as an inverted LB at U18/U21 level late in 2023/24, then moved into midfield to form a 3-2-5 in build-up. Cited traits:
  - Press resistance: "control, speed and aggression to maintain possession under pressure".
  - Being right-footed limits his overlapping.
  - He is still balancing going forward against the space he leaves behind.
  - Arteta: "he's much more a midfielder than a full-back."
  — [Hayters](https://hayters.com/is-it-time-for-mikel-arteta-to-play-myles-lewis-skelly-in-midfield/); [Premier League analysis](https://www.premierleague.com/news/4212354)

### Inferences
- A defensible synthetic duel model is a **logistic model** on relative physical terms, defender technique (stance and timing) and context (pitch zone, pressure/support). This matches the published academic form, and its modest predictive power fits the high randomness of duels.
- **Dribbled-past %** and **true tackle win %** are the event-level outputs the advisor should report. Raw tackle counts are biased by exposure and have no opponent adjustment. No public source I found gives an opponent-adjusted 1v1 metric, so the advisor could legitimately add one (e.g. a defender's win % against the attacker's expected win %), labelled as simulated.
- Versatility and retraining cases point to **transferable attributes**: positional/tactical intelligence, comfort on the ball under pressure, carrying ability, footedness, and work-rate to recover space. These are mostly *not* 1v1 defending attributes. That supports a penalty for out-of-position defenders in duels while keeping their build-up value.

### Gaps
- I did not research sources for Bale (LB to RW), Lahm, Kimmich or Milner, because the searches returned nothing usable. Do not cite any specific coach quotes about them.
- I found no public player-similarity or positional-versatility model methodology (e.g. clustering, role-fit scores) within budget.
- I did not access the details of StatsBomb's own (non-community) 1v1 duel or "dribbled past" methodology.

## Q3. Contextual variables: game state, minute/fatigue, yellow-card caution, support/double-up, line height, inverted full-back positioning

### Takeaway
Pressure and support from nearby defenders, plus pitch location, are the contextual variables most clearly linked to duel outcome in elite tracking. Booking or suspension threat measurably reduces fouling. Fatigue effects on running are smaller and more position-dependent than usually assumed. I found little direct evidence for line height or inverted full-back exposure in 1v1 terms.

### Cited Findings
- **Pressure and pitch location.** Higher average defensive pressure lowered dribble success. Distance from the sideline raised it. — [arXiv 2506.22503](https://arxiv.org/html/2506.22503v1)
- **Second defender.** The community 1v1 definition explicitly ignores what the second defender is doing and flags this as a limitation. This implies support is a confounder to model. — [Substack](https://talatabont.substack.com/p/introducing-1v1s-to-football)
- **Card caution (PL 2011-12).** Players one card from suspension, rather than two, fouled about **12% less** when facing a one-game ban and about **23% less** when facing a two-game ban. They also received fewer yellows. The study covers all positions, not defenders specifically. — [SPONET record](https://lida.sport-iat.de/ta/Record/4048925?lng=en); [J Sports Econ](https://https-sage-cnpereading-com-443.webvpn1.xju.edu.cn/doi/10.1177/1527002516674761)
- **Cards and results.** In the Bundesliga, yellow and red cards lower the carded team's probability of winning. — [SPONET record](https://lida.sport-iat.de/ta/Record/4020677?lng=en). StatsBomb Conference 2024 also has a paper on how yellow cards change player and team behaviour, but I could not extract its results. — [StatsBomb 2024 research paper](https://blogarchive.statsbomb.com/uploads/2024/11/Research-Paper-StatsBomb-2024.pdf)
- **Fatigue and position.** When effective playing time is accounted for, the drop in high-speed running and sprinting from first to second half is not significant. **Full-backs maintained** their high-speed and sprint efforts, and central defenders increased sprint distance. — [SPONET record](https://lida.sport-iat.de/ta/Record/4087619?lng=en)
- **Interpreting second-half declines** is complex: they may reflect physical or mental fatigue, pacing, or context. — [Leeds Beckett, Factors impacting match running](https://eprints.leedsbeckett.ac.uk/id/eprint/3168)
- **Fatigue in a defending experiment.** Fatigue had no large effect on interception success or top sprint speed, and fatigued players worked harder on defending than on attacking tasks. — [Inside Science / AIP](https://www.aip.org/inside-science/world-cup-showcases-elite-players-fight-against-fatigue)
- **Youth fatigue timing.** Fatigue appeared early in the second half and late in the game, which contrasts with earlier reports of fatigue mainly in the final 15 minutes. — [Western Sydney Univ.](https://researchers.westernsydney.edu.au/en/publications/high-intensity-activity-profile-in-elite-youth-soccer-match-play/)
- **Inverted full-back exposure.** In Lewis-Skelly's case, analysts flag the space left behind when an inverted LB moves into midfield. — [Hayters](https://hayters.com/is-it-time-for-mikel-arteta-to-play-myles-lewis-skelly-in-midfield/)

### Inferences
- In the simulator, a booking should push a defender towards **lower foul and tackle propensity and more jockeying/retreating**. That probably raises the attacker's progression and cross probability while lowering the defender's tackle-win rate. This direction is supported by general fouling evidence. The size of the effect on 1v1s is not.
- Fatigue should be a **modest, position-dependent** modifier, applied more to acceleration/repeat-sprint and decision quality than to top speed. A fatigued full-back against a fresh winger is the classic case where relative acceleration shifts.
- Support or double-up (a second defender within a few metres) should strongly lower the attacker's 1v1 success, consistent with the pressure finding.

### Gaps
- I found no elite study quantifying 1v1 win rate **by match minute**, **by game state**, or under **high vs low defensive line**.
- I found no defender-specific evidence on how a booking changes tackling style. The XGLAB/StatsBomb 2024 working paper may cover it, but its results were not accessible.

## Q4. Substitution impact: do subs change outcomes, typical timing, fresh-legs physical effect

### Takeaway
Substitutes produce **more high-intensity running per minute** than the players they replace, especially attackers. The effect is meaningful but short-lived. Evidence that subs *change outcomes* is contested: the well-known 58'/73'/79' timing rule (Myers) was challenged by later Bayesian work.

### Cited Findings
- **Myers.** He analysed the 2009-10 top-four European leagues, MLS 2010 and the 2010 World Cup. His rule for a **trailing team** is: first sub before 58', second before 73', third before 79'. Teams that followed it improved their goal difference by at least one about **36%** of the time, against **about 18.5%** for teams that didn't. — [Freakonomics summary](https://freakonomics.com/2011/02/09/when-should-a-soccer-manager-insert-his-subs)
- **Silva and Swartz (2016, JQAS).** Using Bayesian logistic regression, they found a second-half scoring advantage for trailing teams between evenly matched sides, but **no discernible substitution time window** that gave a benefit. Myers published a rejoinder. — [De Gruyter, Silva & Swartz](https://www.degruyterbrill.com/document/doi/10.1515/jqas-2015-0114/html?lang=de); [Myers rejoinder](https://www.degruyterbrill.com/document/doi/10.1515/jqas-2016-0081/html)
- **Substitute running output.** Substitutes covered **15% more high-intensity running** than full-match players over the same period (p < 0.01, ES 0.5). The gap was largest for attackers. Pass completion did not differ. Subs went "all-out" while full-match players paced themselves, and the effect was meaningful but short-lived. — [PubMed 23808376](https://pubmed.ncbi.nlm.nih.gov/23808376); [Leeds Beckett eprint](https://eprints.leedsbeckett.ac.uk/id/eprint/4486)
- **Starters vs subs (2023/24, 21 players, 16 matches, GNSS).** Starter or substitute status did not significantly affect intensity **except in the final periods**. Position mattered more. — [PMC10955740](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10955740/)
- **Peak demands after pitch entry.** A 2020 study examined peak physical demands of professional substitutes after entry, including contextual influences. — [Catapult-hosted PDF](https://unleash.catapult.com/wp-content/uploads/research//Worst%20Case%20Scenario/(2020)%20Quantifying%20the%20Peak%20Physical%20Match-Play%20demands%20of%20professional%20soccer%20substitutes%20following%20pitch-entry_%20Assesing%20contextual%20influences.pdf)
- **Five-substitute rule.** A study of 17 LaLiga teams compared 2019-20 (three subs) with 2020-21 (five subs) for effects on high-speed running. I did not see its results. — [Int J Sports Med 2023](https://thieme-connect.de/products/ejournals/abstract/10.1055/a-1982-9808)
- **Substitution timing.** A separate German analysis of substitution times exists, but I did not access its findings. — [SPONET](https://www.iat.uni-leipzig.de/datenbanken/iks/sponet/Record/4042150)

### Inferences
- A "fresh legs" modifier in the advisor should be **moderate (around +10–15% high-intensity capacity)**, **larger for attacking subs**, and **decay over roughly 15–20 minutes**. The decay window is an inference from "short-lived", not a measured figure.
- Advice should present timing as a heuristic and keep a KEEP option. Outcome effects of substitutions are contested.

### Gaps
- I found no study directly measuring whether bringing on a fresh full-back against a winger changes **duel win rates**.
- Typical PL substitution minute distributions under the 5-sub rule were not found within budget.

---

### Draft ranked variable shortlist (inference only, for the synthetic advisor; the cited findings above are the evidence)
1. Attacker–defender relative velocity/acceleration at confrontation (Oonk 2024; UCL pose study; Vienna LPM).
2. Interpersonal distance / closing distance at engagement (Duarte 2010; Clemente 2013).
3. Defender stance angle / body orientation (side-on vs square) (UCL pose study; Coaches' Voice).
4. Defensive pressure / support defender proximity (UCL pose study).
5. Pitch zone: distance to sideline and to goal (UCL pose study).
6. Defender acceleration / first-step quickness (Vienna LPM).
7. Defender deceleration and backward COD (Kawahara 2018).
8. Reactive agility / anticipation (JSSM 2010; Fiorilli 2017).
9. Low centre of mass / hip flexion technique (Sasaki 2015).
10. Attacker dribbling agility and direction-change ability (UCL 2D features).
11. Attacker balance / torso lean (UCL pose study).
12. Tackle timing and discipline (true-tackle / foul share, Opta).
13. Historical dribbled-past % / true tackle win % (Opta; StatsBomb).
14. Yellow-card / suspension caution (PL suspension study).
15. Fatigue / minutes played, position-dependent (effective-time study; Leeds Beckett).
16. Fresh-legs substitute boost with decay (PubMed 23808376).
17. Game state / score and minute (Myers; Silva & Swartz).
18. Positional familiarity / out-of-position penalty (White, Lewis-Skelly cases).
19. Footedness relative to the side defended (Lewis-Skelly case).
20. Inverted full-back positioning and space left behind (Lewis-Skelly analysis).
21. Approach strategy, i.e. show outside / down the line vs inside (coaching sources).
22. Top speed (weak or negative direct effect; mainly matters in open-field recovery) (UCL pose study).

Items 1–11 have tracking or biomechanical support. Items 12–22 rest on event data, economics, coaching or case evidence. Their weights would be assumptions to label as simulated.
