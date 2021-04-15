from pysc2.agents import base_agent
from pysc2.env import sc2_env
from pysc2.lib import actions, features, units
from absl import app
from fysom import Fysom
import random


#Actions
_BUILD_SPAWNINGPOOL = actions.FUNCTIONS.Build_SpawningPool_screen.id
_BUILD_EXTRACTOR = actions.FUNCTIONS.Build_Extractor_screen.id
_TRAIN_OVERLORD = actions.FUNCTIONS.Train_Overlord_quick.id
_TRAIN_ZERGLING = actions.FUNCTIONS.Train_Zergling_quick.id
_SELECT_ARMY = actions.FUNCTIONS.select_army.id
_ATTACK_MINIMAP = actions.FUNCTIONS.Attack_minimap.id
_SELECT_IDLE_WORKER = actions.FUNCTIONS.select_idle_worker.id
_HARVEST_GATHER_SCREEN = actions.FUNCTIONS.Harvest_Gather_screen.id 

#Features
_UNIT_TYPE = features.SCREEN_FEATURES.unit_type.index
_DRONE_GAS = 0
_EXTRACTORS = []

class ZergAgent(base_agent.BaseAgent):
  drone_selected = False
  def __init__(self):
    super(ZergAgent, self).__init__()
    self.attack_coordinates = None

  ########################
  ### Fonctions utiles ###
  ########################
  def unit_type_is_selected(self, obs, unit_type):
    if (len(obs.observation.single_select) > 0 and
        obs.observation.single_select[0].unit_type == unit_type):
      return True
    
    if (len(obs.observation.multi_select) > 0 and
        obs.observation.multi_select[0].unit_type == unit_type):
      return True
    
    return False

  def get_units_by_type(self, obs, unit_type):
    return [unit for unit in obs.observation.feature_units
            if unit.unit_type == unit_type]

  def get_unit(self, units):
    unit = random.choice(units)
    return actions.FUNCTIONS.select_point("select", (unit.x, unit.y))
  
  def get_units(self, units, n):
    units = []
    i = 0
    while i < n:
      unit = random.choice(units)
      units.append((unit.x, unit.y))
    return units
  
  def can_do(self, obs, action):
    return action in obs.observation.available_actions

  ########################
  ###    Bâtiments     ###
  ########################
  def build_SpawningPool(self):
    x = random.randint(0, 83)
    y = random.randint(0, 83)
    return actions.FUNCTIONS.Build_SpawningPool_screen("now", (x, y))

  def build_Extractor(self):
    x = random.randint(0, 83)
    y = random.randint(0, 83)
    return actions.FUNCTIONS.Build_Extractor_screen("now", (x, y))

  ########################
  ###     Attaques     ###
  ########################
  def attack_zerglings(self, obs):
    if self.unit_type_is_selected(obs, units.Zerg.Zergling):
      if self.can_do(obs, _ATTACK_MINIMAP):
        return actions.FUNCTIONS.Attack_minimap("now", self.attack_coordinates)
    if self.can_do(obs, _SELECT_ARMY):
      return actions.FUNCTIONS.select_army("select")

  ########################
  ###       Armée      ###
  ########################
  def train_Zergling(self):
    return actions.FUNCTIONS.Train_Zergling_quick("now")

  def train_Overlord(self):
    return actions.FUNCTIONS.Train_Overlord_quick("now")


  ########################
  ###    Procédure     ###
  ########################
  def step(self, obs, fsm):
    super(ZergAgent, self).step(obs)
    global _DRONE_GAS

    if obs.first():
      player_y, player_x = (obs.observation.feature_minimap.player_relative ==
                            features.PlayerRelative.SELF).nonzero()
      xmean = player_x.mean()
      ymean = player_y.mean()
      
      if xmean <= 31 and ymean <= 31:
        self.attack_coordinates = (49, 49)
      else:
        self.attack_coordinates = (12, 16)


    extractors = self.get_units_by_type(obs, units.Zerg.Extractor)
    spawning_pools = self.get_units_by_type(obs, units.Zerg.SpawningPool)
    drones = self.get_units_by_type(obs, units.Zerg.Drone)

    if fsm.current == "base":
      fsm.select_drone()
      return actions.FUNCTIONS.no_op()


    if fsm.current == "selected_drone":
      if not self.drone_selected:
        if len(drones) > 0:
          if self.can_do(obs, _SELECT_IDLE_WORKER): #Drone inactif
            return actions.FUNCTIONS.select_idle_worker("select")
          fsm.build_buildings()
          return self.get_unit(drones)

    if fsm.current == "build":
      #Création des extracteurs
      unit_type = obs.observation["feature_screen"][_UNIT_TYPE]
      vespene_y, vespene_x = (unit_type == units.Neutral.VespeneGeyser).nonzero()
      if len(extractors) == 0:
        if self.unit_type_is_selected(obs, units.Zerg.Drone):
          if self.can_do(obs, _BUILD_EXTRACTOR):
            x = random.randint(0, 83)
            y = random.randint(0, 83)
            
            self.drone_selected = False
            fsm.init()
            return actions.FUNCTIONS.Build_Extractor_screen("now", (x, y))
      if _DRONE_GAS < 3:
        if self.unit_type_is_selected(obs, units.Zerg.Drone):
          if self.can_do(obs, _HARVEST_GATHER_SCREEN):
            _DRONE_GAS += 1
            self.drone_selected = False
            fsm.init()
            return actions.FUNCTIONS.Harvest_Gather_screen("now", (vespene_x[0], vespene_y[0]))

      #Création du spawningPool
      if (len(spawning_pools) == 0):
        if self.unit_type_is_selected(obs, units.Zerg.Drone):
          if self.can_do(obs, _BUILD_SPAWNINGPOOL):
            self.drone_selected = False
            fsm.init()
            return self.build_SpawningPool()


    #Attaque zerglings simple --- TEST
    zerglings = self.get_units_by_type(obs, units.Zerg.Zergling)
    if len(zerglings) >= 20:
      return self.attack_zerglings(obs)
    
    # Création zerglings & overlord -- TEST
    if self.unit_type_is_selected(obs, units.Zerg.Larva):
      if (obs.observation.player.food_cap - obs.observation.player.food_used) == 0:
        if self.can_do(obs, _TRAIN_OVERLORD): #Overlord
          return self.train_Overlord()
      if self.can_do(obs, _TRAIN_ZERGLING):   #Zerglings
        return self.train_Zergling()
    
    larvas = self.get_units_by_type(obs, units.Zerg.Larva) #Sélection larves pour les créations & tests
    if len(larvas) > 0:
      return self.get_unit(larvas)
    
    return actions.FUNCTIONS.no_op()

def main(unused_argv):
  agent = ZergAgent()
  try:
    while True:
      with sc2_env.SC2Env(
          map_name="Simple64",
          players=[sc2_env.Agent(sc2_env.Race.zerg),
                   sc2_env.Bot(sc2_env.Race.random,
                               sc2_env.Difficulty.very_easy)],
          agent_interface_format=features.AgentInterfaceFormat(
              feature_dimensions=features.Dimensions(screen=84, minimap=64),
              use_feature_units=True),
          step_mul=16,
          game_steps_per_episode=0,
          visualize=True) as env:
          
        fsm = Fysom({'initial': {'state': 'base', 'event': 'init'},
              'events': [
                  {'name': 'select_drone', 'src': 'base', 'dst': 'selected_drone'},
                  {'name': 'build_buildings', 'src': 'selected_drone', 'dst': 'build'},
                  {'name': 'init', 'dst': 'base'}]
              })
        
        agent.setup(env.observation_spec(), env.action_spec())
        
        timesteps = env.reset()
        agent.reset()
        
        while True:
          step_actions = [agent.step(timesteps[0], fsm)]
          if timesteps[0].last():
            break
          timesteps = env.step(step_actions)
      
  except KeyboardInterrupt:
    pass
  
if __name__ == "__main__":
  app.run(main)