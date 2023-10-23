# AI-Wargame
### In this game there are four play modes
 - human vs human
 - human vs ai 
 - ai vs human
 - ai vs ai

### Game prompts 
- choose a play mode
- the maximum time for a turn
- the maximum number of turns
- a heuristic if an ai-player is playing
- a search algorithm for the ai-player to use
- a depth for the search the ai-player will use

### Players can do the following actions
 - movement
 - attack
 - repair
 - self destruct
### Information displayed
 - the turn number
 - name of player
 - action taken
 - time for an action taken (if possible)
 - heuristic score (if possible)
 - new board after a move (if possible)
 - the number of states evaluated by the heuristic function since the beginning of the game, also by depth and by percentage (if possible)
 - branching factor (if possible)
 - winner
### Overview of heuristics
- **Heuristic e0** evaluates the game state by considering the unit counts for different types (Virus, Tech, Firewall, Program, and AI) of both the current player and the opponent, with a strong penalty for AI units, to determine the overall game situation.
- **Heuristic e1** assesses the game state based on factors such as the number of alive units and total health for both players, with a special focus on Tech units on the Attacker side by giving a healing component to prioritize healing actions.
- **Heuristic e2** evaluates the game state by calculating the number of safe moves available to the player, focusing on the player's ability to make moves without putting their units in immediate danger.
# Members
- Fatema Akther (40177866)
- Julie Trinh (40175335)
- Leon Zhang (40175616)


