from pysc2.agents import base_agent
from pysc2.env import sc2_env
from pysc2.lib import actions, features, units
from absl import app
from fysom import Fysom
import random

# def onpanic(e):
#     print ('panic! ' + e.msg)
# def oncalm(e):
#     print ('thanks to ' + e.msg + ' done by ' + e.args[0])
# def ongreen(e):
#     print ('green')
# def onyellow(e):
#     print ('yellow')
# def onred(e):
#     print ('red')
# fsm = Fysom({'initial': 'green',
#              'events': [
#                  {'name': 'warn', 'src': 'green', 'dst': 'yellow'},
#                  {'name': 'panic', 'src': 'yellow', 'dst': 'red'},
#                  {'name': 'panic', 'src': 'green', 'dst': 'red'},
#                  {'name': 'calm', 'src': 'red', 'dst': 'yellow'},
#                  {'name': 'clear', 'src': 'yellow', 'dst': 'green'}],
#              'callbacks': {
#                  'onpanic': onpanic,
#                  'oncalm': oncalm,
#                  'ongreen': ongreen,
#                  'onyellow': onyellow,
#                  'onred': onred }})

# fsm.panic(msg='killer bees')
# fsm.calm('bob', msg='sedatives in the honey pots')

# quit()

class ZergAgent(base_agent.BaseAgent):
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
    return actions.FUNCTIONS.select_point("select_all_type", (unit.x, unit.y)) 
  
  def can_do(self, obs, action):
    return action in obs.observation.available_actions

  ########################
  ###    Bâtiments     ###
  ########################
  def build_SpawningPool(self):
    x = random.randint(0, 83)
    y = random.randint(0, 83)
    return actions.FUNCTIONS.Build_SpawningPool_screen("now", (x, y))

  ########################
  ###     Attaques     ###
  ########################
  def attack_zerglings(self, obs):
    if self.unit_type_is_selected(obs, units.Zerg.Zergling):
      if self.can_do(obs, actions.FUNCTIONS.Attack_minimap.id):
        return actions.FUNCTIONS.Attack_minimap("now", self.attack_coordinates)
    if self.can_do(obs, actions.FUNCTIONS.select_army.id):
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
    
    if obs.first():
      player_y, player_x = (obs.observation.feature_minimap.player_relative ==
                            features.PlayerRelative.SELF).nonzero()
      xmean = player_x.mean()
      ymean = player_y.mean()
      
      if xmean <= 31 and ymean <= 31:
        self.attack_coordinates = (49, 49)
      else:
        self.attack_coordinates = (12, 16)

    #----
    # S'il n'y a pas de spawning pool
    #----
    spawning_pools = self.get_units_by_type(obs, units.Zerg.SpawningPool)
    if fsm.current == "base":
      if len(spawning_pools) == 0:
        fsm.select_spawning_pool()

    drones = self.get_units_by_type(obs, units.Zerg.Drone)
    if fsm.current == "spawning_pool_select_drone":
      if self.unit_type_is_selected(obs, units.Zerg.Drone):
        if self.can_do(obs, actions.FUNCTIONS.Build_SpawningPool_screen.id):
          fsm.create_spawning_pool()
          return self.build_SpawningPool()
        else:
          fsm.init()

      if len(drones) > 0:
        return self.get_unit(drones)
    #----
    # S'il n'y a que un Overlord dans le terrain
    #----

    #Attaque zerglings simple
    zerglings = self.get_units_by_type(obs, units.Zerg.Zergling)
    if len(zerglings) >= 20:
      return self.attack_zerglings(obs)

    #Création SpawningPools avec drone
    #spawning_pools = self.get_units_by_type(obs, units.Zerg.SpawningPool)
    #if len(spawning_pools) == 0:
    #  if self.unit_type_is_selected(obs, units.Zerg.Drone):
    #    if self.can_do(obs, actions.FUNCTIONS.Build_SpawningPool_screen.id):
    #      return self.build_SpawningPool()
    #  drones = self.get_units_by_type(obs, units.Zerg.Drone)
    #  if len(drones) > 0:
    #    return self.get_unit(drones)
    
    #Création zerglings & overlord
    if self.unit_type_is_selected(obs, units.Zerg.Larva):
      free_supply = (obs.observation.player.food_cap -
                     obs.observation.player.food_used)
      if free_supply == 0:
        if self.can_do(obs, actions.FUNCTIONS.Train_Overlord_quick.id): #Overlord
          return self.train_Overlord()
      if self.can_do(obs, actions.FUNCTIONS.Train_Zergling_quick.id):   #Zerglings
        return self.train_Zergling()
    
    larvas = self.get_units_by_type(obs, units.Zerg.Larva)
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
                  {'name': 'select_spawning_pool', 'src': 'base', 'dst': 'spawning_pool_select_drone'},
                  {'name': 'create_spawning_pool', 'src': 'spawning_pool_select_drone', 'dst': 'base'},
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