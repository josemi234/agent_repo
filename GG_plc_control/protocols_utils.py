##Funciones auxiliares de RTU, para manterner orden en el code
# CAMBIAR NOMBRE DEL MODULO
##para los metodos escritura from_mobdus :
# https://appdividend.com/2021/06/14/how-to-convert-python-int-to-binary-string/

from datetime import date, datetime
from serial_adapter.ModbusSerialClientAdapter import  ModbusSerialClientAdapter
from TCPIP_adapter.ModbusTcpClientAdapter import ModbusTcpClientAdapter
import logging
import traceback

log = logging.getLogger()

##clase "wrapper" de RTU #################################
## se debe cambiar nombre agregar rtu // crear otro para tcp
class modbus_wrapper_RTU():

    def __init__(self, device_info, resource, handle_local_echo, strict = False):
        self.id = device_info["id"]
        self.dev_type = device_info["device_type"]
        self.timeout = device_info.get("timeout",0.5)
        self.unit = device_info["unit"]
        self.baudrate = device_info.get("baudrate",9600)
        self.stopbits = device_info.get("stopbits",1)
        self.bytesize = device_info.get("bytesize",8)
        self.parity = device_info.get("parity", "N")

        self.master = ModbusSerialClientAdapter(method="rtu", port=resource, baudrate=self.baudrate,
                    stopbits=self.stopbits, parity=self.parity, bytesize=self.bytesize, timeout=self.timeout,
                    strict=strict, handle_local_echo=handle_local_echo)

    def read_variable(self, register, bit=None): #register is the json object, not just value

        log.info(f"[RTU GENERAL] trying to connect to device {self.id}")
        self.master.client.connect()
        log.info(f"[RTU GENERAL] successfully connected to device {self.id}")
        try:
            var_value = self.master.read_value(address=register["address"], count=register["count"],
                        unit=self.unit, value_format=register["value_format"], byteorder_key=register["byteorder_key"],
                        wordorder_key=register["wordorder_key"], read_function=register["read_function"], bit=bit)

            return var_value
        except:
            log.info(f"[RTU GENERAL] An error occurred while trying to read to {self.id}")
            err = traceback.format_exc()
            log.info(f"[RTU GENERAL]->>> ERROR: {err}")
            return None

    def write_variable(self, register, bit, value):

        log.info(f"[RTU GENERAL] Connecting to device {self.id}")
        self.master.client.connect()
        try:
            self.master.write_value(address=register["address"], value=value, unit=self.unit, value_format=register["value_format"],
            byteorder_key=register["byteorder_key"],wordorder_key=register["wordorder_key"], write_function=register["write_function"], bit=bit, count=register["count"] )
            log.info(f"[RTU GENERAL] variable has been written sucessfullly")
            return True

        except:
            log.info(f"[RTU GENERAL] An error occurred while trying to read to {self.id}")
            err = traceback.format_exc()
            log.info(f"->>> ERROR: {err}")
            return None

################################################################

### clase wrapper tcp   ***PROBAR
class modbus_wrapper_TCP():

    def __init__(self, device_info, resource= None, handle_local_echo= None, strict = False):
        self.id = device_info["id"]
        self.dev_type = device_info["device_type"]
        self.timeout = device_info.get("timeout",0.5)
        self.unit = device_info["unit"]
        self.ip = device_info["ip"]
        self.port = device_info["port"]
        self.source_address = (device_info.get('source_address_0', ''), device_info.get('source_address_1', 0))

        self.master = ModbusTcpClientAdapter(ip= self.ip ,port= self.port, source_address=self.source_address,timeout=self.timeout)

    def read_variable(self, register, bit=None): #register is the json object, not just the name

        log.info(f"[TCP GENERAL] trying to connect to device {self.id}")
        self.master.client.connect()
        log.info(f"[TCP GENERAL] successfully connected to device {self.id}")
        try:
            var_value = self.master.read_value(address=register["address"], count=register["count"], unit=self.unit,
                                               value_format=register["value_format"],byteorder_key=register["byteorder_key"],
                                               wordorder_key=register["wordorder_key"],read_function=register["read_function"], bit=bit)

            return var_value
        
        except:
            log.info(f"[TCP GENERAL] An error occurred while trying to read to {self.id}")
            err = traceback.format_exc()
            log.info(f"[TCP GENERAL]->>> ERROR: {err}")
            return None

    def write_variable(self, register, bit, value):

        log.info(f"[RTU GENERAL] Connecting to device {self.id}")
        self.master.client.connect()
        try:
            self.master.write_value(address=register["address"], value=value, unit=self.unit, value_format=register["value_format"],
            byteorder_key=register["byteorder_key"],wordorder_key=register["wordorder_key"], write_function=register["write_function"], bit=bit, count=register["count"] )
            log.info(f"[RTU GENERAL] variable has been written sucessfullly")
            return True

        except:
            log.info(f"[RTU GENERAL] An error occurred while trying to read to {self.id}")
            err = traceback.format_exc()
            log.info(f"->>> ERROR: {err}")
            return None

##### clase externa propia del loop

class control_plcs():

    def __init__(self, variables, devices, registers, controls, master_info={}):

        #information settings 
        self.variables_info = variables #info desde json de las variables de CONTROL
        self.devices = devices #info de los dispositivos 
        self.registers = registers #info de los registros de cada dispositivo
        self.controls = controls  #info de las cosaas a controlar

        self.variables_values = {} #actual values of variables
        self.variables_desired_statuses = [] #desired statuses for variables (according to chosen law)
        self.control_statuses = {} # automode and chosen law for every law
        #hardware settings (general)
        self.handle_local_echo = master_info.get("handle_local_echo", False)
        self.strict = master_info.get("strict", False)
        self.resource = master_info.get("resource", "/dev/ttyAMA2")

    def read_variables(self):  ##leer TODAS las vars y guardarlas
        
        masters = {}
        variables = {} #guardo local% valores leidos

        #organizing variables x slave
        for var in self.variables_info:
            var_info = self.variables_info[var]
            m = var_info.get("master")
            if not(m in masters.keys()):
                masters.update({m:{}})
                masters[m].update({var:var_info})
            else:
                masters[m].update({var:var_info})

        #reading and saving values
        log.info("[PLC CONTROL] Reading of variables is about to start...")

        for master in masters:  ##agregar fx o ke se yo pa definir tipo
            #def el tipo de protocolo
            # crear master segun protocolo
            log.info(f" > [PLC CONTROL] Reading variables from device {master}")
            protocol = self.devices[master]["protocol"]

            if protocol=="RTU":
                client = modbus_wrapper_RTU(self.devices[master], resource=self.resource, handle_local_echo=self.handle_local_echo)

            elif protocol=="TCP":
                client = modbus_wrapper_TCP(self.devices[master])

            else:
                print(f"[PLC CONTROL] protocol {protocol} NOT supported, avaliable options: RTU, TCP")
                return

            for reg in masters[master]:
                log.info(f" >> [PLC CONTROL] Obtaining variable status from {reg}")
                
                var_type = masters[master][reg]["register"]
                bit =  masters[master][reg].get("bit", None)
                master_type = self.devices[master]["device_type"]
                reg_info = self.registers[master_type]["registers"][var_type]

                var_value = client.read_variable(reg_info, bit)
                #update variables map
                variables.update({reg:var_value})

        log.info(f"[PLC CONTROL] STATES OF THE READ VARIABLES: {variables}")
        self.variables_values = variables #update mapa de variables:valor

##escribe variable y revisa si escritura se logro
    def write_variable(self, variable_name, value):  # recibe nombre de la var y valor 
        
        log.info(f"[PLC CONTROL] trying to set variable {variable_name} in its new value {value}")
        
        var_info = self.variables_info[variable_name]
        master_info = self.devices[var_info["master"]]
        master_type = master_info["device_type"]
        #Write new value
        register_info = self.registers[master_type]["registers"][var_info["register"]]

        protocol = master_info["protocol"]
        if protocol == "RTU":
            client = modbus_wrapper_RTU(master_info, resource=self.resource, handle_local_echo=self.handle_local_echo)

        elif protocol == "TCP":
            client = modbus_wrapper_TCP(master_info)

        else:
            print(f"[PLC CONTROL] protocol {protocol} NOT supported, avaliable options: RTU, TCP")
            return
        
        try:
            client.write_variable(register_info, var_info["bit"], value)
            log.info("[PLC CONTROL] variable has been written successfully")

            #check if new value has been written or not
            new_value = client.read_variable(register_info, var_info["bit"])

            if value == new_value:
                log.info(f"[PLC CONTROL] new value has been readed succesfully: \n {variable_name}")

                #actualizo el valor de la variable en lista de valores
                self.variables_values.update({variable_name:new_value})
                return True

            else:
                log.info("[PLC CONTROL] Could not set variable to new value")
                return False

        except:
            err = traceback.format_exc()
            log.info(f"[PLC CONTROL] Couldn't write variable. ERROR: \n {err}")
            return False

    def check_law(self):
        
        log.info("[PLC CONTROL] Checking control laws")

        for process in self.controls:
            log.info(f"[PLC CONTROL] >> Working on process {process}")
          
            law_info = self.controls[process]
            automode = law_info["automode"]

            log.info(f"[PLC CONTROL] automode is {automode}")
            
            if automode == 0:
                applied_law = self.manual_control(law_info)

            elif automode == 1:
                applied_law = self.automatic_control(law_info)

            else:
                log.info(f"[PLC CONTROL] automode value {automode} is invalid. Only options are 1 and 0")
                return

            self.control_statuses.update({process: {"automode":automode, "applied_law": applied_law}})

    def manual_control(self, law_info):

        log.info("[PLC CONTROL] manual control is activated. Changing to default values if needed.")
        law = law_info["manual_actions"]
        
        var_to_check = {}
        parsed_str = law.replace(" ", "").replace("\n", "").split(",")
        for v in parsed_str:
            name, value = v.split("=")
            value = int(value)
            #comparo valor actual de la var con el que quiero:
            actual_value = self.variables_values[name]
            if actual_value != value:
                log.info(f"[PLC CONTROL] value for {name} must be changed to {value}")
                #escribo valor deseado
                state = self.write_variable(name, value) #escribe y chequea si funciono c:
                if state:
                    self.variables_values.update({name:value})
                    log.info(f"[PLC CONTROL] Value of {name} has been changed sucessfully")

                else: 
                    log.info(f"[PLC CONTROL] Unable to change value for {name}")

        self.variables_desired_statuses.append(law)

        return 0

    def automatic_control(self, law_info):

        log.info("[PLC CONTROL] automatic mode is activated. Checking laws, applying depending on case.")
        laws = law_info["automatic_actions"]
        applied_law  = None

        for i in range(1, len(laws)+1):
            section = laws[i-1]
            condition = section["condition"]
            action = section["action"]
            c_state = False
             #evaluo condicion: para caso other_case se dbe eagregar algo mais por aqui (un pre if) c:
            if condition != "other_case":
                try:
                    c_state = eval(condition, self.variables_values.copy())
                
                except Exception:
                    err = traceback.format_exc()
                    print(f"[PLC CONTROL] An error occurred evaluating law {i}: \n {err}")

            else:
                log.info(f"[PLC CONTROL] applying '{condition}' condition for any other case not specified 'else' ...")
                c_state = True

            if c_state: #si se cumple alguna condicion
                log.info(f"[PLC CONTROL] Applying law number {i}: {condition}")
                
                self.variables_desired_statuses.append(action) #se guardan desired status
                applied_law = i
                action = section["action"].replace(" ", "").split(",")

                log.info(f"[PLC CONTROL] actions to perfom: {action}")
                #comparar valor de las variables con el deseado 
                for var_desired_status in action:
                    name, value = var_desired_status.split("=")
                    value = int(value)
                    actual_value = self.variables_values[name]
                    log.info(f"[PLC CONTROL] actual value for {name} is {actual_value}, desired is {value}")
                    
                    if actual_value != value: 
                        log.info(f"[PLC CONTROL] changing value for {name}")
                        state  = self.write_variable(name, value)
                        if state:
                            log.info(f"[PLC CONTROL] Value of {name} has been changed sucessfully")
                            self.variables_values.update({name: value})
                break

            else: #no condition matchs
                print(f"[PLC CONTROL] condition {condition} does not match, skipping ...")
                
            
        return applied_law

