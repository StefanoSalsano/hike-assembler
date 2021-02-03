import copy
import pprint

import re

HIKE_DEFS_FILE = 'hike-definitions.h'

# TODO IMPLEMENT THE MAIN PROGRAM WITH PROPER PARAMETERS AND OUTPUT
# TODO CHECK TO AVOID REDEFINITION OF A LABEL OR OF A PROGRAM/CHAIN NAME
# TODO READ THE INSTRUCTIONS CODES FROM THE .H 
# TODO ACCEPT ALSO A PROGRAM ID OR CHAIN ID IN ADDITION TO PROG/CHAIN NAME
# TODO SUPPORT OF #INCLUDE DIRECTIVE

COMMA_IS_MANDATORY = True
#COMMA_IS_MANDATORY = False

REGISTER_1=1
REGISTER_2=2
IMMEDIATE=4
BRANCH=8
PROG_CHAIN=16

BASIC=1
EXTENDED=2

MAX_U16 = 2**16
'''for unsigned int, the maximum value is MAX_U16-1
for signed int, the range is from -MAX_U16/2 to MAX_U16/2-1
'''

MAX_U24 = 2**24
'''for unsigned int, the maximum value is MAX_U24-1
for signed int, the range is from -MAX_U24/2 to MAX_U24/2-1
'''

MAX_U32 = 2**32
'''for unsigned int, the maximum value is MAX_U32-1
for signed int, the range is from -MAX_U32/2 to MAX_U32/2-1
'''


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
  'class' : 0,
  'op' : 0,
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

hike_instr_type_jump1 = { 'template':BASIC, 'dst': '','src': '','off':'%1', 'imm': '',
                     'params':[BRANCH]
}

hike_instr_type_jump2 = { 'template':BASIC, 'dst': '%1','src': '','off':'%3', 'imm': '%2',
                           'params':[REGISTER_1, IMMEDIATE, BRANCH]
}

hike_instr_type_hcall = { 'template':EXTENDED, 'prch':'%1', 'imm': '%2',
                         'params':[PROG_CHAIN, IMMEDIATE]
}

hike_instr_type_exit = { 'template':BASIC, 'dst': '','src': '','off':'', 'imm': '',
                         'params':[]
}

hike_instr_type_alu_imm = { 'template':BASIC, 'dst': '%1','src': '','off':'', 'imm': '%2',
                         'params':[REGISTER_1, IMMEDIATE]
}

hike_instr_type_alu_reg = { 'template':BASIC, 'dst': '%1','src': '%2','off':'', 'imm': '',
                         'params':[REGISTER_1, REGISTER_2]
}

hike_instructions = {
  'JA64':  {'class':0x05, 'op':0x00,'modifier':0x00,'more': hike_instr_type_jump1},
  'JEQ64': {'class':0x05, 'op':0x10,'modifier':0x00,'more': hike_instr_type_jump2}, 
  'JGT64': {'class':0x05, 'op':0x20,'modifier':0x00,'more': hike_instr_type_jump2}, 
  'JGE64': {'class':0x05, 'op':0x30,'modifier':0x00,'more': hike_instr_type_jump2}, 
  'JNE64': {'class':0x05, 'op':0x50,'modifier':0x00,'more': hike_instr_type_jump2},
  'JLT64': {'class':0x05, 'op':0xA0,'modifier':0x00,'more': hike_instr_type_jump2}, 
  'JLE64': {'class':0x05, 'op':0xB0,'modifier':0x00,'more': hike_instr_type_jump2},
  'HCALL': {'class':0x05, 'op':0xF0,'modifier':0x00,'more': hike_instr_type_hcall},
  'EXIT':  {'class':0x05, 'op':0x90,'modifier':0x00,'more': hike_instr_type_exit},
  'ADDS64':{'class':0x07, 'op':0x00,'modifier':0x00,'more':hike_instr_type_alu_imm},
  'MOV64': {'class':0x07, 'op':0xb0,'modifier':0x00,'more':hike_instr_type_alu_imm},
  'MOVR64': {'class':0x07, 'op':0xb0,'modifier':0x08,'more':hike_instr_type_alu_reg},
}

hike_registers = {
  'A': {'code':0}, 
  'B': {'code':1},
  'W': {'code':2}, 
}

hike_jump_instr_sample = {
  'chain_name' : '',
  'instr' : {} 
}

hike_call_inst_sample = {
  'chain_name' : '',
  'instr' : {} 
}

def update_hike_defs (file_name : str):

  global hike_instructions

  hike_instr_map = {
  'JA64': {'op':'HIKE_JA', 'class':'', 'modifier':'HIKE_K'},  
  'JEQ64': {'op':'HIKE_JEQ', 'class':'', 'modifier':'HIKE_K'},  
  'JGT64': {'op':'HIKE_JGT', 'class':'', 'modifier':'HIKE_K'}, 
  'JGE64': {'op':'HIKE_JGE', 'class':'', 'modifier':'HIKE_K'}, 
  'JNE64': {'op':'HIKE_JNE', 'class':'', 'modifier':'HIKE_K'},
  'JLT64': {'op':'HIKE_JLT', 'class':'', 'modifier':'HIKE_K'}, 
  'JLE64': {'op':'HIKE_JLE', 'class':'', 'modifier':'HIKE_K'},
  'HCALL': {'op':'HIKE_TAIL_CALL', 'class':'HIKE_JMP64', 'modifier':'HIKE_K'},
  'EXIT':  {'op':'HIKE_EXIT', 'class':'HIKE_JMP64', 'modifier':'HIKE_K'},
  'ADDS64': {'op':'HIKE_ADD', 'class':'', 'modifier':'HIKE_K'},
  'MOV64': {'op':'HIKE_MOV', 'class':'', 'modifier':'HIKE_K'},
  'MOVR64': {'op':'HIKE_MOV', 'class':'', 'modifier':'HIKE_X'},
  }

  def find_opcode(instr):
    for line in stripped:
      if re.match ('#define\s'+instr+'\s',line) :
        return line.split()[2]
    fatal_error("OPERATION NOT FOUND: "+instr)

  def find_class_code(my_class):
    for line in stripped:
      if re.match ('#define\s'+my_class+'\s',line) :
        return line.split()[2]
    fatal_error("OPERATION NOT FOUND: "+my_class)

  def find_class_of_op(instr):
    for line in stripped:
      if re.match ('HIKE_ALU64_IMM_INSN\('+instr,line) :
        return 'HIKE_ALU64'
      elif re.match ('HIKE_JMP64_IMM_INSN\('+instr,line) :
        return 'HIKE_JMP64'
    fatal_error("OPERATION NOT FOUND: "+instr)

  def find_modif(my_modif):
    for line in stripped:
      if re.match ('#define\s'+my_modif+'\s',line) :
        return line.split()[2]
    fatal_error("MODIFIER NOT FOUND: "+my_modif)

  with open(file_name) as f:
    h_lines = f.readlines()
  stripped= []
  for line in h_lines:
      stripped.append(line.strip())
  #print (stripped)

  for instr, model in  hike_instr_map.items():
    #print (model['op'])
    #find_opcode(model['op'])
    hike_instructions[instr]['op']=int(find_opcode(model['op']),0)
    if model['class'] != '':
      hike_instructions[instr]['class']=int(find_class_code(model['class']),0)
    else:
      hike_instructions[instr]['class']=int(find_class_code(find_class_of_op(model['op'])),0)
    hike_instructions[instr]['modifier']=int(find_modif(model['modifier']),0)  

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
    try:
      all_progs [my_tokens[1]] =  int(my_tokens[2],0)
      #print ("DEFINED PROG ID: "+all_progs [my_tokens[1]])
    except:
      fatal_error ("ERROR IN #DEF (PROGRAM ID CANNOT BE PARSED)")

  elif my_tokens[1].startswith('C_'):
    try:
      all_chains [my_tokens[1]] =  int(my_tokens[2],0)
      #print ("DEFINED CHAIN ID: "+all_chains [my_tokens[1]])
    except:
      fatal_error ("ERROR IN #DEF (CHAIN ID CANNOT BE PARSED)")

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
  #global_chains[current_chain['name']]=copy.deepcopy(current_chain)
  global_chains[current_chain['name']]=current_chain
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
    if my_type==REGISTER_1:
      if my_token in hike_registers:
        return_param['reg_name_1'] = my_token
      else:
        fatal_error ("UNNKOWN REGISTER")
    elif my_type==REGISTER_2:
      if my_token in hike_registers:
        return_param['reg_name_2'] = my_token
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
  instruction['class'] = instr_model['class']
  instruction['op'] = instr_model['op']
  instruction['params'] = []

  #print ('instr id: '+str(instr_model['op']))
  if (len(my_tokens)-1) != len(instr_model['more']['params']):
    fatal_error ("WRONG PARAMETER NUMBER, EXPECTED:"+str(len(instr_model['more']['params'])))
  param_num=0
  for param_type in instr_model['more']['params']:
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

def single_oper_bytecode (my_instr):
  instr_model = hike_instructions[my_instr['name']]
  #print (my_instr['name'])
  #print (instr_model)
  my_byte0 = instr_model['class'] | instr_model['op'] | instr_model['modifier']
  
  my_instr['bytecode'].append(my_byte0)
  
  resolved_params=[]
  param_index=0
  for param_type in instr_model['more']['params']:
    param=my_instr['params'][param_index]
    if param_type == REGISTER_1:
      resolved_params.append(hike_registers[param['reg_name_1']]['code'] )
    elif param_type == REGISTER_2:
      resolved_params.append(hike_registers[param['reg_name_2']]['code'] )
    elif param_type == IMMEDIATE:
      resolved_params.append(param['value'])
    elif param_type == BRANCH:
      resolved_params.append(param['offset'])
    elif param_type == PROG_CHAIN:
      resolved_params.append(param['prog_chain_id'])
    param_index=param_index+1

  my_byte1=0
  my_byte2=0
  my_byte3=0

  if instr_model['more']['template'] == BASIC:
    if instr_model['more']['dst'] != '':
      my_byte1 = my_byte1 | resolved_params[int(instr_model['more']['dst'][1:2])-1]
    if instr_model['more']['src'] != '':
      my_byte1 = my_byte1 | 16 * resolved_params[int(instr_model['more']['src'][1:2])-1]
    
    my_instr['bytecode'].append(my_byte1)

    if instr_model['more']['off'] != '':
      resolved = resolved_params[int(instr_model['more']['off'][1:2])-1]
      if resolved >= MAX_U16/2 or resolved < - MAX_U16/2:
        error_string = 'OUT OF RANGE OFFSET PARAMETER (16 BITS)'
        fatal_error(error_string, my_instr['line_number'])      
      if resolved < 0 :
        resolved = resolved + MAX_U16        
      my_byte2 = resolved % 256
      my_byte3 = resolved // 256

    my_instr['bytecode'].append(my_byte2)
    my_instr['bytecode'].append(my_byte3)

    my_imm = 0
    if instr_model['more']['imm'] != '':
      my_imm = resolved_params[int(instr_model['more']['imm'][1:2])-1]      
      if my_imm >= MAX_U32 or my_imm < - MAX_U32/2:
        error_string = 'OUT OF RANGE IMMEDIATE PARAMETER (32 BITS)'
        fatal_error(error_string, my_instr['line_number'])      
      if my_imm < 0 :
        my_imm = my_imm + MAX_U32        

    my_instr['bytecode'].append(my_imm % 256)
    my_imm = my_imm // 256
    my_instr['bytecode'].append(my_imm % 256)
    my_imm = my_imm // 256
    my_instr['bytecode'].append(my_imm % 256)
    my_imm = my_imm // 256
    my_instr['bytecode'].append(my_imm)

  elif instr_model['more']['template'] == EXTENDED:
    
    my_off=0
    if instr_model['more']['prch'] != '':
      my_off= resolved_params[int(instr_model['more']['prch'][1:2])-1]
      if my_off >= MAX_U24 or my_off < - MAX_U24/2:
        error_string = 'OUT OF RANGE PROG/CHAIN PARAMETER (24 BITS)'
        fatal_error(error_string, my_instr['line_number'])      
      if my_off < 0 :
        my_off = my_off + MAX_U24

    my_instr['bytecode'].append(my_off % 256)
    my_off = my_off // 256
    my_instr['bytecode'].append(my_off % 256)
    my_off = my_off // 256
    my_instr['bytecode'].append(my_off % 256)

    my_imm = 0
    if instr_model['more']['imm'] != '':
      my_imm = resolved_params[int(instr_model['more']['imm'][1:2])-1]
      if my_imm >= MAX_U32 or my_imm < - MAX_U32/2:
        error_string = 'OUT OF RANGE IMMEDIATE PARAMETER (32 BITS)'
        fatal_error(error_string, my_instr['line_number'])      
      if my_imm < 0 :
        my_imm = my_imm + MAX_U32        

    my_instr['bytecode'].append(my_imm % 256)
    my_imm = my_imm // 256
    my_instr['bytecode'].append(my_imm % 256)
    my_imm = my_imm // 256
    my_instr['bytecode'].append(my_imm % 256)
    my_imm = my_imm // 256
    my_instr['bytecode'].append(my_imm)
   
  else:
    error_string = 'UNNKOWN ERROR IN SINGLE_OPERATION_BYTECODE'
    fatal_error(error_string, my_instr['line_number']) 

  print(' '.join('{:02X}'.format(x) for x in my_instr['bytecode']))



def generate_bytecode():
  for chain_name, chain in global_chains.items():
    #print (chain)
    for instr in chain['instructions']:
      #print(instr['name'])
      single_oper_bytecode(instr)

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

update_hike_defs(HIKE_DEFS_FILE)

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

generate_bytecode()


#pprint.pprint(global_chains)
#pprint.pprint(jump_instructions)
#pprint.pprint(call_instructions)

