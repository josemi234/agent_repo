from pymodbus.client.sync import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder

import logging
import sys

FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-30s:%(lineno)-8s %(message)s')
logging.basicConfig(format=FORMAT)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class ModbusTcpClientAdapter():

    decoder_order_dict = {
        'littleendian': Endian.Little,
        'bigendian': Endian.Big
    }

    def __init__(self, ip, port, source_address=('', 0), timeout=3, **kwargs):
        if not isinstance(ip, str) or not isinstance(port, int):
            raise(TypeError('ip must be str and port must be int'))
        self.ip = ip
        self.port = port
        self.source_address = source_address
        self.timeout = timeout
        self.client = ModbusTcpClient(
            self.ip,
            self.port,
            source_address=self.source_address,
            timeout=self.timeout,
            **kwargs
        )

    def __enter__(self):
        self.client.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.close()

    def __str__(self):
        return "ModbusTcpClientAdapter(ip={}, port={})".format(
            self.ip, self.port)

    def decode_registers(
            self, registers, value_format, byteorder_key, wordorder_key):

        byteorder = ModbusTcpClientAdapter.decoder_order_dict[byteorder_key]
        wordorder = ModbusTcpClientAdapter.decoder_order_dict[wordorder_key]

        decoder = BinaryPayloadDecoder.fromRegisters(
            registers, byteorder=byteorder, wordorder=wordorder)

        if value_format == '8int':
            return decoder.decode_8bit_int()
        elif value_format == '8uint':
            return decoder.decode_8bit_uint()
        elif value_format == '16int':
            return decoder.decode_16bit_int()
        elif value_format == '16uint':
            return decoder.decode_16bit_uint()
        elif value_format == '16float' or value_format == '16float2':
            return decoder.decode_16bit_float()
        elif value_format == '32int':
            return decoder.decode_32bit_int()
        elif value_format == '32uint':
            return decoder.decode_32bit_uint()
        elif value_format == '32float' or value_format == '32float2':
            return decoder.decode_32bit_float()
        elif value_format == '64int':
            return decoder.decode_64bit_int()
        elif value_format == '64uint':
            return decoder.decode_32bit_uint()
        elif value_format == '64float' or value_format == '64float2':
            return decoder.decode_64bit_float()
        else:
            raise Exception("'format' variable is incorrect!")
    
    def read_value(
            self, address, count, unit,
            value_format, byteorder_key, wordorder_key, 
            read_function, bit=None, **kwargs):
        
        if read_function == 'read_coils':
            result = self.client.read_coils(address, count, unit=unit, **kwargs)
            return result.bits

        elif read_function == 'read_single_coil':
            result = self.client.read_coils(address, count, unit=unit, **kwargs)
            result = result.bits[0]
            return result

        elif read_function == 'read_from_coils':
            result = self.client.read_coils(address, count, unit=unit, **kwargs)
            return int(result.bits[bit-1])

        elif read_function == 'read_discrete_inputs':
            result = self.client.read_discrete_inputs(address, count, unit=unit, **kwargs)
            result = result.bits[0]
            return result

        elif read_function == 'read_discrete_input':
            result = self.client.read_discrete_inputs(address, count, unit=unit, **kwargs)
            result = result.bits[0]
            return result
            
        elif read_function == 'read_input_registers':
            result = self.client.read_input_registers(address, count, unit=unit, **kwargs)
            
        elif read_function == 'read_holding_registers':
            result = self.client.read_holding_registers(address, count, unit=unit, **kwargs)

        elif read_function == 'read_from_holding_registers':
            result = self.client.read_holding_registers(address, count, unit=unit, **kwargs)

            value = self.decode_registers(result.registers, value_format, byteorder_key, wordorder_key)
            value = format_bits(value, value_format)
            return_bit = value[-bit]
            return int(return_bit)

        else:
            raise Exception("'read_function' variable is incorrect!")
    
                
        value = self.decode_registers(
            result.registers, value_format, byteorder_key, wordorder_key)

        return value

    def encode_value(self, value, value_format, byteorder_key, wordorder_key):

        byteorder = ModbusTcpClientAdapter.decoder_order_dict[byteorder_key]
        wordorder = ModbusTcpClientAdapter.decoder_order_dict[wordorder_key]

        builder = BinaryPayloadBuilder(
            byteorder=byteorder, wordorder=wordorder)

        if value_format == '8int':
            builder.add_8bit_int(value)
        elif value_format == '8uint':
            builder.add_8bit_uint(value)
        elif value_format == '16int':
            builder.add_16bit_int(value)
        elif value_format == '16uint':
            builder.add_16bit_uint(value)
        elif value_format == '16float' or value_format == '16float2':
            builder.add_16bit_float(value)
        elif value_format == '32int':
            builder.add_32bit_int(value)
        elif value_format == '32uint':
            builder.add_32bit_uint(value)
        elif value_format == '32float' or value_format == '32float2':
            builder.add_32bit_float(value)
        elif value_format == '64int':
            builder.add_64bit_int(value)
        elif value_format == '64uint':
            builder.add_64bit_uint(value)
        elif value_format == '64float' or value_format == '64float2':
            builder.add_64bit_float(value)
        else:
            raise Exception("'format' variable is incorrect!")

        payload = builder.to_registers()
        return payload

    def write_value(
            self, address, value, unit,
            value_format, byteorder_key, wordorder_key,
            write_function, bit=None, count=None):

        payload = self.encode_value(
            value, value_format, byteorder_key, wordorder_key)

        #self.client.write_registers(address, payload, unit=unit)
        if write_function == 'write_coil':
            if bit:
                address = bit-1
            payload = value
            self.client.write_coil(address, payload, unit=unit)

        elif write_function == 'write_coils':
            payload = value
            self.client.write_coils(address, payload, unit=unit)

        elif write_function == 'write_register':
            payload  = value
            self.client.write_register(address, payload, unit=unit)

        elif write_function == 'write_registers': ###agregar fx write from registers
            self.client.write_registers(address, payload, unit=unit)

        elif write_function == 'write_from_register':
            current_value = self.read_value(address = address, count = count, 
                        unit = unit, value_format = value_format, 
                        byteorder_key = byteorder_key, wordorder_key= wordorder_key, 
                        read_function="read_holding_registers", bit=bit)
            
            current_value = format_bits(current_value, value_format)
            #new_value = current_value[0:bit-1]+str(value)+current_value[bit:]
            new_value = list(current_value)
            new_value[-bit] = str(value)
            new_value = ''.join(new_value)
            new_value = int(new_value, 2)
            
            self.write_value(address=address, value=new_value, unit=unit, 
                             value_format=value_format, byteorder_key=byteorder_key, wordorder_key=wordorder_key,
                             write_function="write_register")

        elif write_function == 'write_from_registers':
            current_value = self.read_value(address = address, count = count, 
                        unit = unit, value_format = value_format, 
                        byteorder_key = byteorder_key, wordorder_key= wordorder_key, 
                        read_function="read_holding_registers", bit=bit)
            
            current_value = format_bits(current_value, value_format)
            #new_value = current_value[0:bit-1]+str(value)+current_value[bit:]
            new_value = list(current_value)
            new_value[-bit] = str(value)
            new_value = ''.join(new_value)
            new_value = int(new_value, 2)
            #probar
            #payload = self.encode_value(new_value, value_format, byteorder_key, wordorder_key)
            
            self.write_value(address=address, value=new_value, unit=unit, 
                             value_format=value_format, byteorder_key=byteorder_key, wordorder_key=wordorder_key,
                             write_function="write_registers")

        else:
            raise Exception("'write_function' variable is incorrect!")


def format_bits(value, value_format):

    if value_format == "8int" or value_format == "8uint":
        bit_format = '08b'
    elif value_format == "16int" or value_format == "16uint" or value_format == "16float" or value_format=="16float2":
        bit_format = '016b'
    elif value_format == "32int" or value_format == "32uint" or value_format == "32float" or value_format=="32float2":
        bit_format = '032b'
    elif value_format == "64int" or value_format == "64uint" or value_format == "64float" or value_format=="64float2":
        bit_format = '064b'

    formated_bits = format(value, bit_format)
    return formated_bits

