import json, re
import pathlib
from py_scripts import String_Handling

path = pathlib.Path(__file__).parent.absolute()
with open( '%s/lab_info.json' %path, 'r') as f:
    lab = json.load(f)

for project in lab.keys():
    for node, node_value in lab[project].items():
        if '.py' in node:
            for node_2, node_value_2 in lab[project][node].items():
                if isinstance(node_value_2, dict):
                    for variable, value in node_value_2.items():
                        if '$random_hex_' in str(value):
                            new_value = re.findall('[$]random_hex_([^?].*)', value)[0]
                            lab[project][node][node_2][variable] = String_Handling.Random_Hex(new_value)

        elif isinstance(node_value, dict):
            for variable, value in node_value.items():
                if '$random_hex_' in str(value):
                    new_value = re.findall('[$]random_hex_([^?].*)', value)[0]
                    lab[project][node][variable] = String_Handling.Random_Hex(new_value)
#f.write(json.dumps(lab))
f.close()




def find_dic(dic, target, res = False):
    for key ,values in dic.items():
        if isinstance(values, dict):
            res = find_dic(values, target)
            if res:
                return res
        else:
            if key == target:
                res = values
                return values
            elif values == target:
                res = key
                return key
