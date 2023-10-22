from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
import random
import requests
import argparse
import time


# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000

# every type of player 
class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4
#defines two players, who plays next 
class Player(Enum):
    """The 2 players."""
    Attacker = 0
    Defender = 1

    def next(self) -> Player:
        """The next (other) player."""
        if self is Player.Attacker:
            return Player.Defender
        else:
            return Player.Attacker
#scenarios of the game 
class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3

##############################################################################################################

@dataclass(slots=True)
class Unit:
    player: Player = Player.Attacker
    type: UnitType = UnitType.Program 
    health : int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table : ClassVar[list[list[int]]] = [
        [3,3,3,3,1], # AI
        [1,1,6,1,1], # Tech
        [9,6,1,6,1], # Virus
        [3,3,3,3,1], # Program
        [1,1,1,1,1], # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table : ClassVar[list[list[int]]] = [
        [0,1,1,0,0], # AI
        [3,0,0,3,3], # Tech
        [0,0,0,0,0], # Virus
        [0,0,0,0,0], # Program
        [0,0,0,0,0], # Firewall
    ]
    # check if unit is alive based on health
    def is_alive(self) -> bool:
        """Are we alive ?"""
        return self.health > 0
    #makes sure health stays in range of 0-9 nothing below or hugher
    def mod_health(self, health_delta : int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9
    #does naming of units
    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"
    
    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()
    #returns damage without exceeding remaining health
    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        amount = self.damage_table[self.type.value][target.type.value]
        if target.health - amount < 0:
            return target.health
        return amount
    #returning it without exceeding max health 
    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        amount = self.repair_table[self.type.value][target.type.value]
        if target.health + amount > 9:
            return 9 - target.health
        return amount

##############################################################################################################

@dataclass(slots=True)
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row : int = 0
    col : int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
                coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
                coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string()+self.col_string()
    
    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()
    
    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row-dist,self.row+1+dist):
            for col in range(self.col-dist,self.col+1+dist):
                yield Coord(row,col)
    #generates the up down left left
    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row-1,self.col)
        yield Coord(self.row,self.col-1)
        yield Coord(self.row+1,self.col)
        yield Coord(self.row,self.col+1)

    @classmethod
    def from_string(cls, s : str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 2):
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None

##############################################################################################################

@dataclass(slots=True)
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src : Coord = field(default_factory=Coord)
    dst : Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string()+" "+self.dst.to_string()
    
    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.copy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row,self.dst.row+1):
            for col in range(self.src.col,self.dst.col+1):
                yield Coord(row,col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0,col0),Coord(row1,col1))
    
    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0,0),Coord(dim-1,dim-1))
    
    @classmethod
    def from_string(cls, s : str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 4):
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None

##############################################################################################################

@dataclass(slots=True)
class Options:
    """Representation of the game options."""
    dim: int = 5
    max_depth : int | None = 4 #max depth of game tree 
    min_depth : int | None = 2
    max_time : float | None = 5.0 #of each turn 
    game_type : GameType = GameType.AttackerVsDefender #humanvshuman
    alpha_beta : bool = True
    max_turns : int | None = 100
    randomize_moves : bool = True
    broker : str | None = None
    heuristic: str | None = None  # Add the heuristic argument

##############################################################################################################

@dataclass(slots=True)
class Stats:
    """Representation of the global game statistics."""
    evaluations_per_depth : dict[int,int] = field(default_factory=dict) #stores the number of evaluations performed at each search depth in the game tree
    total_seconds: float = 0.0

##############################################################################################################
class Heuristics:
    @staticmethod
    def e0(game, player):
        """
        Heuristic function e0.
        """
        vp1 = game.count_units(player, UnitType.Virus)
        tp1 = game.count_units(player, UnitType.Tech)
        fp1 = game.count_units(player, UnitType.Firewall)
        pp1 = game.count_units(player, UnitType.Program)
        aip1 = game.count_units(player, UnitType.AI)

        other_player = Player.Defender if player == Player.Attacker else Player.Attacker
        vp2 = game.count_units(other_player, UnitType.Virus)
        tp2 = game.count_units(other_player, UnitType.Tech)
        fp2 = game.count_units(other_player, UnitType.Firewall)
        pp2 = game.count_units(other_player, UnitType.Program)
        aip2 = game.count_units(other_player, UnitType.AI)

        # Calculate the heuristic value
        heuristic_value = (3 * vp1 + 3 * tp1 + 3 * fp1 + 3 * pp1 + 9999 * aip1) - (3 * vp2 + 3 * tp2 + 3 * fp2 + 3 * pp2 + 9999 * aip2)

        return heuristic_value

    @staticmethod
    def e1(game, player):
        # Number of alive units belonging to the attacker player
        attacker_units = sum(1 for _, unit in game.player_units(Player.Attacker) if unit.is_alive())

        # Number of alive units belonging to the defender player
        defender_units = sum(1 for _, unit in game.player_units(Player.Defender) if unit.is_alive())

        # The total health of alive units for the attacker player
        attacker_health = sum(unit.health for _, unit in game.player_units(Player.Attacker) if unit.is_alive())

        # The total health of alive units for the defender player
        defender_health = sum(unit.health for _, unit in game.player_units(Player.Defender) if unit.is_alive())

        # The heuristic value is a weighted sum of unit count and total health difference
        return 2 * (attacker_units - defender_units) + 0.5 * (attacker_health - defender_health)

    @staticmethod
    def e2(game, player):
        """
        Heuristic function e2.
        This heuristic evaluates the game state based on the number of safe moves for the player.
        """
        if player == Player.Attacker:
            safe_moves = len(game.get_safe_attacker_moves())
        else:
            safe_moves = len(game.get_safe_defender_moves())
        return safe_moves

##############################################################################################################

@dataclass(slots=True)
class Game:
    """Representation of the game state."""
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: Player = Player.Attacker #attacker first
    turns_played : int = 0 #keep track of turns 
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai : bool = True
    _defender_has_ai : bool = True

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim-1
        self.set(Coord(0,0),Unit(player=Player.Defender,type=UnitType.AI))
        self.set(Coord(1,0),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(0,1),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(2,0),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(0,2),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(1,1),Unit(player=Player.Defender,type=UnitType.Program))
        self.set(Coord(md,md),Unit(player=Player.Attacker,type=UnitType.AI))
        self.set(Coord(md-1,md),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md,md-1),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md-2,md),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md,md-2),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md-1,md-1),Unit(player=Player.Attacker,type=UnitType.Firewall))

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new

    def is_empty(self, coord : Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def get(self, coord : Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord : Coord, unit : Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit
    #check that theres a unit at coord, then health, then empties
    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord,None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False
    #sees the coord, checks it unit there, sees its health, calls mod health to modify, sees if it needs to be removed
    def mod_health(self, coord : Coord, health_delta : int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)

    def perform_combat(self, attacker_coord: Coord, defender_coord: Coord):
        attacker = self.get(attacker_coord) #get coords
        defender = self.get(defender_coord)
        #if unit is missing , no action performed 
        if attacker is None or defender is None:
            return

        # Check if the units belong to different players, combat not allowed for same
        if attacker.player == defender.player:
            return

        # Calculate damage amounts for both units
        attacker_damage = attacker.damage_amount(defender)
        defender_damage = defender.damage_amount(attacker)

        # Update unit health based on damage
        self.mod_health(attacker_coord, -defender_damage)
        self.mod_health(defender_coord, -attacker_damage)
        #print(f" Attack from {attacker.player.name} from {attacker_coord} to {defender_coord}")
        # Check if units are destroyed and remove them from the board
        if not attacker.is_alive():
            self.set(attacker_coord, None)
        if not defender.is_alive():
            self.set(defender_coord, None)    

    def is_valid_move(self, coords: CoordPair) -> bool:
        """Validate a move expressed as a CoordPair."""
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False # checks is src or dst is valid, if not false
        #retrieves unit, , checks if it is missing or not the same as next player
        unit = self.get(coords.src)
        if unit is None or unit.player != self.next_player:
            return False
        #checks is if it is destructive
        unit_dest = self.get(coords.dst)
        if self.is_valid_self_destruction(coords):  # Condition for self-destruction
            return True

        # Calculate the absolute row and column differences
        row_diff = abs(coords.dst.row - coords.src.row)
        col_diff = abs(coords.dst.col - coords.src.col)

        # Check if an adversarial unit is adjacent
        adversarial_adjacent = any(
            self.is_valid_coord(adj_coord) and
            self.get(adj_coord) is not None and
            self.get(adj_coord).player != unit.player
            for adj_coord in coords.src.iter_adjacent()
        )

        if row_diff + col_diff == 1:  # Only adjacent move is valid, diff=1  means it is up down left or right
            if self.is_empty(coords.dst) is True: # check is dst is empty 
                if unit.type == UnitType.Virus or unit.type == UnitType.Tech:
                    # Virus and Tech can move anywhere that is free
                    return True
                if unit.player == Player.Attacker:
                    if coords.dst.row < coords.src.row or coords.dst.col < coords.src.col:
                        # Attacker unit Program, Firewall, and AI can only move up or left
                        return not adversarial_adjacent
                if unit.player == Player.Defender:
                    if coords.dst.row > coords.src.row or coords.dst.col > coords.src.col:
                        # Defender unit Program, Firewall, and AI can only move down or right
                        return not adversarial_adjacent #return if it is empty and no aversary there

        # Allow an attack move if it meets the conditions
        if self.is_valid_attack(coords):
            return True

        return False

    def is_valid_attack(self, coords: CoordPair) -> bool:
        # Check if it's a valid attack move
        src_unit = self.get(coords.src) #get coords
        dst_unit = self.get(coords.dst)
        #if either doesnt exist return false
        if src_unit is None or dst_unit is None:
            return False
        #if they belong to same player it cannot go on
        if src_unit.player == dst_unit.player:
            return False

        # Check if the destination coordinate is adjacent to the source coordinate, if so returns true
        return coords.dst in coords.src.iter_adjacent()
    
    #check if it is self destruction
    def is_valid_self_destruction(self, coords: CoordPair) -> bool:
        src_unit = self.get(coords.src)
        dst_unit = self.get(coords.dst)
        if self.is_empty(coords.src) is True: #if src is empty, false
            return False
        if src_unit == dst_unit: #if source and dest are same , true
            return True
        
        return False
    
    #destroys self destructed and inflict -2 damage to surrounding
    def perform_self_destruction(self, src_coord: Coord):
        source = self.get(src_coord)
        if source is not None:  # Check if source is not None
            self.mod_health(src_coord, -source.health)
        number_damages = 0
        for dst in src_coord.iter_range(1):
            if self.is_valid_coord(dst):
                if self.is_empty(dst) is False:
                    number_damages = number_damages + 2
                    self.mod_health(dst, -2)
                    self.remove_dead(dst)

        # Return the value of number_damages
        return number_damages
  

    def repair_unit(self, source_coord: Coord, target_coord: Coord) -> Tuple[bool, str]:
        source_unit = self.get(source_coord)
        target_unit = self.get(target_coord)

        # Check if source and target units exist and belong to the same player
        if source_unit is None or target_unit is None or source_unit.player != target_unit.player:
            return False, "Invalid repair action."

        # Check if source and target units are adjacent, diff=1
        if abs(source_coord.row - target_coord.row) + abs(source_coord.col - target_coord.col) != 1:
            return False, "Source and target units must be adjacent for repair."

        # Check if the target unit's health is not already at the maximum (9)
        if target_unit.health == 9:
            return False, "Target unit's health is already at the maximum."

        # Calculate the amount of health to repair based on unit types
        repair_amount = source_unit.repair_amount(target_unit) #check repair amount it could make
        target_unit.mod_health(repair_amount) #mod health to that amount

        # Remove dead units if there are in target, and say what is repaired
        self.remove_dead(target_coord) 
        #output_file.write(f"Unit repaired: {target_unit.type.name} at {target_coord}" + "\n")
        return True, f"Unit repaired: {target_unit.type.name} at {target_coord}"

    def perform_move(self, coords: CoordPair, is_final=False) -> Tuple[bool, str]:
        src_unit = self.get(coords.src)
        if self.is_valid_self_destruction(coords):
            number_damages = self.perform_self_destruction(coords.src)
            if is_final:
                print(f"{src_unit.player.name} self-destruct at {coords.src}") 
                print(f"self-destructed for {number_damages} total damages")
            #output_file.write(f"{src_unit.player.name} self-destruct at {coords.src}" + "\n")
            self.perform_self_destruction(coords.src)
            return True, "Self destruction successful"
        if self.is_valid_attack(coords):
            self.perform_combat(coords.src, coords.dst)
            if is_final:
                print(f"{src_unit.player.name} attacks from {coords.src} to {coords.dst}")
            return True, "Attack successful"
        elif self.is_valid_move(coords):
            if is_final:
                print(f"{src_unit.player.name} move from {coords.src} to {coords.dst}")
            #output_file.write(f"{src_unit.player.name} move from {coords.src} to {coords.dst}" + "\n")
            self.set(coords.dst, self.get(coords.src))  # set new coords
            self.set(coords.src, None)  # empty source
            return True, "Move successful"
        elif self.is_valid_repair(coords):
            success, result = self.repair_unit(coords.src, coords.dst)  # stores result
            return success, result
        return False, "Invalid move"


    # Add this method to check if a repair action is valid
    def is_valid_repair(self, coords: CoordPair) -> bool:
        source_unit = self.get(coords.src)
        target_unit = self.get(coords.dst)

        if source_unit is None or target_unit is None:
            return False

        # Check if source and target units are adjacent and belong to the same player
        if (
            abs(coords.src.row - coords.dst.row) + abs(coords.src.col - coords.dst.col) == 1
            and source_unit.player == target_unit.player
        ):
            return True

        return False


    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()
    
    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                return coords
            else:
                print('Invalid coordinates! Try again.')
    
    def human_turn(self):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success,result) = self.perform_move(mv)
                    print(f"Broker {self.next_player.name}: ",end='')
                    print(result)
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success,result) = self.perform_move(mv)
                if success:
                    print(f"Player {self.next_player.name}: ",end='')
                    print(result)
                    self.next_turn()
                    break
                else:
                    print("The move is not valid! Try again.")

    def computer_turn(self) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move()

        if mv is not None:
            src_unit = self.get(mv.src)

            if src_unit is not None and src_unit.type == UnitType.AI:
                if self.is_valid_self_destruction(mv):
                    # Handle the AI's decision here, e.g., choose an alternative move or do nothing
                    alternative_mv = self.choose_alternative_move(src_unit)
                    if alternative_mv is not None:
                        mv = alternative_mv

            (success, result) = self.perform_move(mv, is_final=True)
            if success:
                print(f"Computer {self.next_player.name}: ", end='')
                print(result)
                self.next_turn()
        return mv

    def choose_alternative_move(self, src_unit) -> CoordPair | None:
        # Get the list of available move candidates for the AI
        move_candidates = list(self.move_candidates())

        # Filter out the moves that result in self-destruction for the AI unit
        safe_moves = []
        for move in move_candidates:
            # Check if the move results in self-destruction
            if not self.is_valid_self_destruction(move):
                safe_moves.append(move)

        if safe_moves:
            # Choose a random safe move from the available alternatives
            return random.choice(safe_moves)
        else:
            # If there are no safe moves, return None to indicate no valid moves are available
            return None
        
    def player_units(self, player: Player) -> Iterable[Tuple[Coord,Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord,unit)
                
    def count_units(game, player, unit_type):
        """Helper function to count the number of units of a specific type for a player."""
        count = 0
        for (_, unit) in game.player_units(player):
            if unit.type == unit_type and unit.is_alive():
                count += 1
        return count
    
    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            return Player.Defender
        if self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return Player.Attacker    
        return Player.Defender

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src,_) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move):
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def random_move(self) -> Tuple[int, CoordPair | None, float]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return (0, move_candidates[0], 1)
        else:
            return (0, None, 0)

    def suggest_move(self) -> CoordPair | None:
        start_time =  time.time()
        depth = self.options.max_depth

        if (self.options.alpha_beta):
            (score, move) = self.alpha_beta(depth, MIN_HEURISTIC_SCORE, MAX_HEURISTIC_SCORE, True, start_time)
        else:
            (score, move) = self.minimax(self.options.max_depth, True, start_time)
       

        elapsed_seconds = (time.time() - start_time)
        self.stats.total_seconds += elapsed_seconds
        print(f"Heuristic score: {score}")
        print(f"Elapsed time: {elapsed_seconds:0.1f}s")
        print(f"Evals per depth: ",end='')
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            print(f"{k}:{self.stats.evaluations_per_depth[k]} ",end='')
        print()
        total_evals = sum(self.stats.evaluations_per_depth.values())
        if self.stats.total_seconds > 0:
            print(f"Eval perf.: {total_evals/self.stats.total_seconds/1000:0.1f}k/s")
        print(f"Elapsed time: {elapsed_seconds:0.1f}s")
        return move
    
    def minimax(self, depth: int, maximizing_player: bool, start_time: datetime) -> Tuple[int, CoordPair | None]:
        print(depth)
        
        # Base case: if reached maximum depth or game is finished, evaluate the node
        if depth == 0 or self.is_finished():
            score = self.options.heuristic(self, self.next_player)  # Evaluate the current game state
            return score, None

        move_candidates = list(self.move_candidates()) # Get available moves

        if maximizing_player:
            max_score = MIN_HEURISTIC_SCORE
            best_move = None
            for move in move_candidates:
                child_node = self.clone() # Create a clone of the current game
                (success, _) = child_node.perform_move(move, is_final=False) 
                if success:
                     # Recur with the child node, reducing depth, and switching player
                    child_score, _ = child_node.minimax(depth - 1, False, start_time)
                    if child_score > max_score:
                        max_score = child_score # Update max_score if a better move is found
                        best_move = move
                    elapsed_time =  time.time() - start_time
                    if elapsed_time > self.options.max_time:
                        break  # Timeout, interrupt the search
            return max_score, best_move
        else:
            min_score = MAX_HEURISTIC_SCORE
            best_move = None
            for move in move_candidates:
                child_node = self.clone()
                (success, _) = child_node.perform_move(move, is_final=False)
                if success:
                    child_score, _ = child_node.minimax(depth - 1, True, start_time)
                    if child_score < min_score:
                        min_score = child_score
                        best_move = move
                    elapsed_time =  time.time() - start_time
                    if elapsed_time > self.options.max_time:
                        break  # Timeout, interrupt the search
            return min_score, best_move

    def alpha_beta(self, depth: int, alpha: int, beta: int, maximizing_player: bool, start_time: datetime) -> Tuple[int, CoordPair | None]:
        print(depth)
         # Base case: if reached maximum depth or game is finished, evaluate the node
        if depth == 0 or self.is_finished(): 
            score = self.options.heuristic(self, self.next_player) # Evaluate the current game state
            return score, None  # Return the score and no move (leaf node)

        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)  # Shuffle for better randomness
        if maximizing_player:
            max_score = MIN_HEURISTIC_SCORE # Initialize max_score to negative infinity
            best_move = None
            for move in move_candidates:
                child_node = self.clone() # Create a clone of the current node
                (success, _) = child_node.perform_move(move, is_final=False)
                if success:
                     # Recur with the child node, reducing depth, and switching player
                    child_score, _ = child_node.alpha_beta( depth - 1, alpha, beta, False, start_time)
                    if child_score > max_score:
                        max_score = child_score
                        best_move = move
                    alpha = max(alpha, max_score) # Update alpha with max_score
                    elapsed_time =  time.time() - start_time
                    if elapsed_time > self.options.max_time:
                        break  # Timeout, interrupt the search
                    if beta <= alpha:
                        break  # Beta cut-off, prune the search tree
            return max_score, best_move # Return the maximum score and the corresponding move
        else:
            min_score = MAX_HEURISTIC_SCORE 
            best_move = None
            for move in move_candidates:
                child_node = self.clone()
                (success, _) = child_node.perform_move(move, is_final=False)
                if success:
                    child_score, _ = child_node.alpha_beta( depth - 1, alpha, beta, True, start_time)
                    if child_score < min_score:
                        min_score = child_score
                        best_move = move
                    beta = min(beta, min_score)
                    elapsed_time =  time.time() - start_time
                    if elapsed_time > self.options.max_time:
                        break  # Timeout, interrupt the search
                    if beta <= alpha:
                        break  # Alpha cut-off, prune the search tree
            return min_score, best_move

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played+1:
                        move = CoordPair(
                            Coord(data['from']['row'],data['from']['col']),
                            Coord(data['to']['row'],data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None

    def get_safe_attacker_moves(self):
        safe_moves = []
        for move in self.move_candidates():
            if not self.is_valid_self_destruction(move):
                # Check if the move results in an attack
                if self.is_valid_attack(move):
                    safe_moves.append(move)
                # Check if the move results in a repair
                elif self.is_valid_repair(move):
                    safe_moves.append(move)
                # Check if the move results in a regular move
                elif self.is_valid_move(move):
                    safe_moves.append(move)
                # Add other criteria for safe moves specific to your game

        return safe_moves

    def get_safe_defender_moves(self):
        safe_moves = []
        for move in self.move_candidates():
            if not self.is_valid_self_destruction(move):
                # Check if the move results in a repair
                if self.is_valid_repair(move):
                    safe_moves.append(move)
                # Check if the move results in a regular move
                elif self.is_valid_move(move):
                    safe_moves.append(move)
                # Add other criteria for safe moves specific to your game

        return safe_moves
##############################################################################################################

def main():
    print("Choose the play mode:")
    print("1. H-H (Human vs Human)")
    print("2. H-AI (Human vs AI)")
    print("3. AI-H (AI vs Human)")
    print("4. AI-AI (AI vs AI)")

    choice = input("Enter the number of your choice: ").strip()
    while choice not in ['1', '2', '3', '4']:
        print("Please enter a valid choice (1, 2, 3, or 4).")
        choice = input("Enter the number of your choice: ").strip()

    if choice == '1':
        game_type = GameType.AttackerVsDefender  # H-H
    elif choice == '2':
        game_type = GameType.AttackerVsComp  # H-AI
    elif choice == '3':
        game_type = GameType.CompVsDefender  # AI-H
    else:
        game_type = GameType.CompVsComp  # AI-AI
    
    while True:
        # Prompt the user for the maximum time per turn
        max_time = float(input("Enter the maximum time (in seconds) the program should take per turn: "))
        if max_time <= 0:
            print("Please enter a positive value for maximum time.")
        else:
            break

    while True:
        # Prompt the user for the maximum number of turns before the end of the game
        max_turns = int(input("Enter the maximum number of turns before the end of the game: "))
        if max_turns <= 0:
            print("Please enter a positive value for maximum turns.")
        else:
            break

    # Parse the heuristic choice
    print("Choose a heuristic:")
    print("1. Heuristic e0")
    print("2. Heuristic e1")
    print("3. Heuristic e2")
    heuristic_choice = input("Enter the number of your chosen heuristic: ").strip()

    # Define a mapping from user's choice to Heuristics class attributes
    heuristic_mapping = {
        '1': Heuristics.e0,
        '2': Heuristics.e1,
        '3': Heuristics.e2,
    }
    # Prompt the user for the choice between Minimax (False) and Alpha-Beta (True)
    alpha_beta_choice = input("Choose the search algorithm (Minimax: 0, Alpha-Beta: 1): ").strip()
    while alpha_beta_choice not in ['0', '1']:
        print("Please enter a valid choice (0 for Minimax or 1 for Alpha-Beta).")
        alpha_beta_choice = input("Choose the search algorithm (Minimax: 0, Alpha-Beta: 1): ").strip()

    while True:
        # Prompt the user for the AI depth
        try:
            ai_depth = int(input("Enter the AI depth for the search algorithm: "))
            if ai_depth < 1:
                print("Please enter a positive integer for the AI depth.")
            else:
                break
        except ValueError:
            print("Invalid input. Please enter a positive integer for the AI depth.")

    # Select the heuristic based on the user's choice
    selected_heuristic = heuristic_mapping.get(heuristic_choice)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--game_type', type=str, default="manual", help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    args = parser.parse_args()

    # Set up game options
    options = Options(
        game_type=game_type,
        max_time=max_time,
        max_turns=max_turns,
        heuristic=selected_heuristic,
        alpha_beta=(alpha_beta_choice == '1'),  # Convert the choice to a boolean
        max_depth=ai_depth  # Specify the AI depth (you can change this value as needed)
)

    # Override class defaults via command line options
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.broker is not None:
        options.broker = args.broker

    # Create a new game
    game = Game(options=options)
    try:
        global output_file
        output_file = open(f"gameTrace-{options.alpha_beta}-{options.max_time}-{options.max_turns}-{selected_heuristic.__name__}.txt", "w")
        output_file.write(str(options) + "\n")

        # The main game loop
        while True:
            print()
            print(game)
            
            # Log the current game state to the output file
            output_file.write(str(game) + "\n")
            output_file.write("####################################" + "\n")
            winner = game.has_winner()
            if winner is not None:
                print(f"{winner.name} wins!")
                output_file.write(f"{winner.name} wins in {game.turns_played} turns" + "\n")
                # Write the timeout value (t) and maximum number of turns to the file
                output_file.write(f"Value of Timeout (s): {options.max_time} seconds\n")
                output_file.write(f"Maximum number of turns: {options.max_turns}\n")
                output_file.close()
                break
            if game.options.game_type == GameType.AttackerVsDefender:
                game.human_turn()
            elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
                game.human_turn()
            elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
                game.human_turn()
            else:
                player = game.next_player
                move = game.computer_turn()
                if move is not None:
                    game.post_move_to_broker(move)
                else:
                    print("Computer doesn't know what to do!!!")
                    exit(1)
    finally:
        if 'output_file' in locals():
            output_file.close()

if __name__ == '__main__':
    main()
