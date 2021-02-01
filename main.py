import copy
import pprint

# TODO CHECK TO AVOID REDEFINITION OF A LABEL OR OF A PROGRAM/CHAIN NAME

COMMA_IS_MANDATORY = True
#COMMA_IS_MANDATORY = False

REGISTER=1
IMMEDIATE=2
BRANCH=4
PROG_CHAIN=8

hike_chain_sample = {
  'name' : '',
  'id': 0,
  'first_instr' : -1,
  'last_instr' : -1,
  'instructions' : []
}

hike_instruction_sample = {
  'name' : '',
  'chain' : '',
  'id' : 0,
  'params' : [],
  'globl_instr_cnt' : -1,
  'chain_instr_cnt' : -1,
  'line_number' : -1,
  'bytecode' : []
}

hike_param_sample = {
  'type' : '',
  'value' : 0,
  'reg_name_1' : '',
  'reg_name_2' : '',
  'label' : '',
  'offset' : 0,
  'offset_resolved' : False, 
  'prog_chain_name' :'',
  'prog_chain_id' : 0,
  'prog_chain_resolved' : False
}

hike_instructions = {
  'JEQ64': {'id':1,'params':[REGISTER, IMMEDIATE, BRANCH]}, 
  'MOV64': {'id':2,'params':[REGISTER, IMMEDIATE]},
  'JGT64': {'id':3,'params':[REGISTER, IMMEDIATE, BRANCH]}, 
  'CALL': {'id':4,'params':[PROG_CHAIN, IMMEDIATE]},
  'EXIT': {'id':5,'params':[]},
  'JA64': {'id':6,'params':[BRANCH]},
  'ADDS64': {'id':7,'params':[REGISTER, IMMEDIATE]}
}

hike_registers = {
  'A': {'id':0}, 
  'B': {'id':1},
  'W': {'id':2}, 
}

hike_jump_instr_sample = {
  'chain_name' : '',
  'instr' : {} 
}

hike_call_inst_sample = {
  'chain_name' : '',
  'instr' : {} 
}



def check_commas (my_tokens):
  token_num = len (my_tokens)
  if token_num == 1 :
    return my_tokens
  return_tokens = []
  if COMMA_IS_MANDATORY :
    my_string = ""
    counter = 0
    for token in my_tokens:
      if counter == 0:
        return_tokens.append(token)
      else:
        my_string = my_string+token
      counter= counter + 1
    for token in my_string.split(","):
      return_tokens.append(token)  
  else:
    for token in my_tokens:
      if token == "," :
        pass
      else:
        if token.endswith(","):
          return_tokens.append(token.split(',')[0])
        else:
          return_tokens.append(token)
  return return_tokens

def set_label(token, instr_cnt) :
  all_jmp_labels[token]=instr_cnt

def def_progs_chains (my_tokens):
  if len(my_tokens) != 3 :
    fatal_error ("ERROR IN #DEF (WRONG NUMBER OF PARAMS)")

  if my_tokens[1].startswith('P_'):
    all_progs [my_tokens[1]] =  my_tokens[2];
    #print ("DEFINED PROG ID: "+all_progs [my_tokens[1]])

  elif my_tokens[1].startswith('C_'):
    all_chains [my_tokens[1]] =  my_tokens[2];
    #print ("DEFINED CHAIN ID: "+all_chains [my_tokens[1]])

  else: 
    fatal_error ("CHAIN OR PROG NAME ERROR IN #DEF")

def fatal_error(my_string, line_number = -1 ):
  print (my_string)
  if line_number == -1 :
    print ("LINE NUMBER: "+str(line_cnt))
  else:
    print ("LINE NUMBER: "+str(line_number))  
  exit(-1)

def start_chain (my_tokens):
  global current_chain
  if not current_chain == {}:
    fatal_error("CHAIN DEFINITIONS CANNOT BE NESTED\nCHAIN "+
    current_chain['name']+ " IS CURRENTLY BEING DEFINED")
  if not my_tokens[1].startswith("C_"):
    fatal_error ("INVALID CHAIN NAME") 
  #global_chains[current_chain_name]=hike_chain_sample
  current_chain = copy.deepcopy(hike_chain_sample)
  current_chain['name'] = my_tokens[1]
  current_chain['first_instr']=instr_cnt

def end_chain (my_tokens):
  global current_chain
  current_chain['last_instr']=instr_cnt-1
  global_chains[current_chain['name']]=copy.deepcopy(current_chain)
  current_chain = {}

def process_instruction(my_tokens: list) -> dict:
  '''
  process an instruction 

  returns the instruction dict
  '''

  def get_param(my_type: int, my_token : str, my_instr : object, 
                my_num : int) -> dict:
    '''
    parse a single parameter

    my_num is not used currenty, can be used to give the
    errored param number in the error message  
    '''

    global jump_instructions
    global call_instructions

    return_param = copy.deepcopy(hike_param_sample)
    if my_type==REGISTER:
      if my_token in hike_registers:
        return_param['reg_name_1'] = my_token
      else:
        fatal_error ("UNNKOWN REGISTER")
    elif my_type==IMMEDIATE:
      try:
        value = int(my_token,0)
      except:
        fatal_error ("INVALID IMMEDIATE VALUE")
      #print (valore)
      return_param['value']=value
    elif my_type==BRANCH:
      jump_instr=copy.deepcopy(hike_jump_instr_sample)
      if current_chain != {}:
        jump_instr['chain_name']=current_chain['name']
      jump_instr['instr']=my_instr
      jump_instructions.append(jump_instr)
      if my_token.endswith(":"):
        return_param['label']=my_token
      else:
        try:
          value = int(my_token,0)
        except:
          fatal_error ("INVALID BRANCH TARGET")
        return_param['offset'] = value 
        return_param['offset_resolved'] = True
    elif my_type==PROG_CHAIN:
      call_instr=copy.deepcopy(hike_call_inst_sample)
      if current_chain != {}:
        call_instr['chain_name']=current_chain['name']
      call_instr['instr']=my_instr
      call_instructions.append(call_instr)
      if my_token.startswith("P_"):
        return_param['prog_chain_name'] = my_token
      elif my_token.startswith("C_"):
        return_param['prog_chain_name'] = my_token
      else:
        fatal_error ("INVALID PROGRAM OR CHAIN REFERENCE")
    else:
      fatal_error ("BAD ERROR IN GET_PARAM")
    
    return return_param

  #start of process_instruction(my_tokens)

  instr_model = hike_instructions[my_tokens[0]]
  instruction = copy.deepcopy(hike_instruction_sample)
  instruction['name'] = my_tokens[0]
  instruction['id'] = instr_model['id']
  instruction['params'] = []

  #print ('instr id: '+str(instr_model['id']))
  if (len(my_tokens)-1) != len(instr_model['params']):
    fatal_error ("WRONG PARAMETER NUMBER, EXPECTED:"+str(instr_model['num_param']))
  param_num=0
  for param_type in instr_model['params']:
    param_num=param_num+1
    instruction['params'].append(get_param(param_type,
                                          my_tokens[param_num],
                                          instruction,
                                          param_num))
  
  return instruction

def resolve_call_references():
  '''
  after the first pass, called to resolve the call references
  
  sets the global variable unreferenced_chains
  '''

  global unreferenced_chains
  already_resolved= 0
  resolved = 0
  to_be_resolved = 0
  for call_instr in call_instructions:

    instr = call_instr['instr']
    param = instr['params'][0]
    print(param['prog_chain_name']) #DEBUG PRINT
    if param ['prog_chain_resolved']:
      already_resolved = already_resolved + 1
    elif param['prog_chain_name'] in all_chains:
      param['prog_chain_id']=all_chains[param['prog_chain_name']]
      param ['prog_chain_resolved']=True
      resolved = resolved + 1
    elif param['prog_chain_name'] in all_progs:
      param['prog_chain_id']=all_progs[param['prog_chain_name']]
      param ['prog_chain_resolved']=True
      resolved = resolved + 1
    elif param['prog_chain_name'] in global_chains:
      to_be_resolved = to_be_resolved  + 1
    else:
      error_string = "UNRESOLVED NAME: "+ param['prog_chain_name']
      fatal_error(error_string, instr['line_number']) 
  unreferenced_chains=to_be_resolved
  print ('already resolved: '+str(already_resolved)+
          ' resolved: '+str(resolved)+' to be resolved: '+str(to_be_resolved))

def resolve_label_offsets():
  '''after the first pass, called to resolve the label offsets
  
  for numerical offsets, checks that the offset is within the
  chain boudary
  '''

  already_resolved= 0
  resolved = 0
  for jump_instr in jump_instructions:
    instr = jump_instr['instr']
    found_offset_param = False
    for par in instr['params']:
      if (par['label'] == '') and (par['offset'] == 0) and (par['offset_resolved'] == False): 
        continue
      found_offset_param = True
      break
    if not found_offset_param:
      error_string = 'OFFSET PARAM NOT FOUND IN INSTR '+instr['name']
      fatal_error(error_string, instr['line_number']) 
    if par['offset_resolved']:
      already_resolved = already_resolved +1
    else:
      print(par['label'])  #DEBUG PRINT
      if not par['label'] in all_jmp_labels:
        error_string = 'UNABLE TO RESOLVE LABEL: '+par['label']
        fatal_error(error_string, instr['line_number'])
      current_pc = (instr['globl_instr_cnt']) + 1
      target_instr = (all_jmp_labels[par['label']])
      if global_chains[instr['chain']]['first_instr'] > target_instr :
        error_string = 'TARGET LABEL: '+par['label']\
                      + ' IS BEFORE CHAIN START'
        fatal_error(error_string, instr['line_number'])   
      if global_chains[instr['chain']]['last_instr'] < target_instr :
        error_string = 'TARGET LABEL: '+par['label']\
                      + ' IS AFTER CHAIN END'
        fatal_error(error_string, instr['line_number'])   
            
      par['offset'] = target_instr - current_pc
      par['offset_resolved']=True
      resolved = resolved + 1

  print ('already resolved: '+str(already_resolved)+
          ' resolved: '+str(resolved))

with open('in.hikeasm') as f:
  all_lines = f.readlines()

all_jmp_labels = {}
'''collects che labels in the first pass'''

all_chains = {}
'''collects the chains defined with #DEF in the first pass'''

all_progs = {}
'''collects the programs defined with #DEF in the first pass'''

instr_cnt = 0
line_cnt = 0

current_chain = {}
'''the current chain, see hike_chain_sample dict'''

global_chains = {}
'''collects all the chains 

the key is the chain name, the value is a hike_chain_sample dict
'''

jump_instructions = []
'''collects the list of all jump instructions in the first pass'''

call_instructions = []
'''collects the list of all call instructions in the first pass'''

unreferenced_chains = 0
'''after check_call_references'''

#first pass on the code
for line in all_lines:
  #print(i)
  strip = line.strip()
  #print(len(strip))
  #print(strip)
  line_cnt = line_cnt+1
  if len(strip)==0:
    continue
  if (strip.startswith(";")):
    continue

  tokens=line.split()
  #tokens=re.split(' ',line)
  #print (tokens)
  #print (len(tokens))
  token_num = len (tokens)
  #print (tokens)
  #print (strip)
  if token_num == 1 and strip.endswith(":"):
    #print ("label: "+line)
    set_label(tokens[0], instr_cnt)
    pass
  elif tokens[0] == "#INCLUDE" :
    print ("##INCLUDE###: "+strip)
    pass
  elif tokens[0] == "#DEF":
    def_progs_chains (tokens)

  elif tokens[0] == "#STARTCHAIN":
    start_chain (tokens)

  elif tokens[0] == "#ENDCHAIN":
    end_chain (tokens)

  else:
    tokens = check_commas(tokens) 
    if tokens[0] in hike_instructions :
      print (tokens)
      instruction = process_instruction(tokens)
      if current_chain != {}:
        instruction['chain']=current_chain['name']
        instruction['globl_instr_cnt']=instr_cnt
        instruction['chain_instr_cnt']=instr_cnt-current_chain['first_instr']
        instruction['line_number']=line_cnt
        current_chain['instructions'].append(instruction)
      instr_cnt=instr_cnt+1
    else :
      fatal_error ("UNNKOWN INSTRUCTION ERROR: "+tokens[0])

#end of first pass on the code

print ('Total instructions: '+str(instr_cnt))
print ('Number of chains: '+str(len(global_chains)))
print ('Number of labels: '+str(len(all_jmp_labels)))
print ('Number of call instructions: '+str(len(call_instructions)))
pprint.pprint(all_jmp_labels)

resolve_call_references()
resolve_label_offsets()

pprint.pprint(global_chains)
#pprint.pprint(jump_instructions)
#pprint.pprint(call_instructions)

