import sys
from typing import List, Dict, Tuple
from enum import Enum

class OpcodeType(Enum):
    LOAD = 0b0000011
    STORE = 0b0100011
    BRANCH = 0b1100011
    JALR = 0b1100111
    JAL = 0b1101111
    OP_IMM = 0b0010011
    OP = 0b0110011
    AUIPC = 0b0010111
    LUI = 0b0110111
    SYSTEM = 0b1110011

class ALUOp(Enum):
    ADD = 0
    SUB = 1
    SLL = 2
    SLT = 3
    SLTU = 4
    XOR = 5
    SRL = 6
    SRA = 7
    OR = 8
    AND = 9

class ALU:
    
    @staticmethod
    def execute(op: ALUOp, a: int, b: int) -> int:
        # Convert to 32-bit signed
        a = ALU._to_signed(a)
        b = ALU._to_signed(b)
        
        if op == ALUOp.ADD:
            result = a + b
        elif op == ALUOp.SUB:
            result = a - b
        elif op == ALUOp.SLL:
            result = a << (b & 0x1F)
        elif op == ALUOp.SLT:
            result = 1 if a < b else 0
        elif op == ALUOp.SLTU:
            result = 1 if ALU._to_unsigned(a) < ALU._to_unsigned(b) else 0
        elif op == ALUOp.XOR:
            result = a ^ b
        elif op == ALUOp.SRL:
            result = ALU._to_unsigned(a) >> (b & 0x1F)
        elif op == ALUOp.SRA:
            result = a >> (b & 0x1F)
        elif op == ALUOp.OR:
            result = a | b
        elif op == ALUOp.AND:
            result = a & b
        else:
            result = 0
        
        return ALU._to_32bit(result)
    
    @staticmethod
    def _to_signed(val: int) -> int:
        val = val & 0xFFFFFFFF
        if val & 0x80000000:
            return val - 0x100000000
        return val
    
    @staticmethod
    def _to_unsigned(val: int) -> int:
        return val & 0xFFFFFFFF
    
    @staticmethod
    def _to_32bit(val: int) -> int:
        return val & 0xFFFFFFFF

class RegisterFile:
  
    def __init__(self):
        self.regs = [0] * 32
    
    def read(self, reg: int) -> int:
        if reg < 0 or reg > 31:
            return 0
        return self.regs[reg]
    
    def write(self, reg: int, value: int):
        if reg > 0 and reg < 32:
            self.regs[reg] = value & 0xFFFFFFFF
    
    def dump(self) -> str:
        output = "Register File:\n"
        for i in range(0, 32, 4):
            line = ""
            for j in range(4):
                reg_num = i + j
                if reg_num < 32:
                    line += f"x{reg_num:2d}=0x{self.regs[reg_num]:08x}  "
            output += line + "\n"
        return output

class Memory:
    
    def __init__(self, size: int = 0x20000):  # 128KB
        self.size = size
        self.mem = bytearray(size)
    
    def read_word(self, addr: int) -> int:
        addr = addr & 0xFFFFFFFF
        if addr >= self.size - 3:
            return 0
        return (self.mem[addr] | 
                (self.mem[addr+1] << 8) | 
                (self.mem[addr+2] << 16) | 
                (self.mem[addr+3] << 24))
    
    def write_word(self, addr: int, value: int):
        addr = addr & 0xFFFFFFFF
        value = value & 0xFFFFFFFF
        if addr < self.size - 3:
            self.mem[addr] = value & 0xFF
            self.mem[addr+1] = (value >> 8) & 0xFF
            self.mem[addr+2] = (value >> 16) & 0xFF
            self.mem[addr+3] = (value >> 24) & 0xFF
    
    def load_program(self, hex_file: str):
        with open(hex_file, 'r') as f:
            addr = 0
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    instr = int(line, 16)
                    self.write_word(addr, instr)
                    addr += 4

class ControlUnit:
    
    @staticmethod
    def decode(opcode: int) -> Dict[str, bool]:

        signals = {
            'reg_write': False,
            'mem_read': False,
            'mem_write': False,
            'mem_to_reg': False,
            'alu_src': False,
            'branch': False,
            'jump': False,
            'jalr': False
        }
        
        if opcode == OpcodeType.OP.value:  # R-type
            signals['reg_write'] = True
            signals['alu_src'] = False
        elif opcode == OpcodeType.OP_IMM.value:  # I-type arithmetic
            signals['reg_write'] = True
            signals['alu_src'] = True
        elif opcode == OpcodeType.LOAD.value:  # Load
            signals['reg_write'] = True
            signals['mem_read'] = True
            signals['mem_to_reg'] = True
            signals['alu_src'] = True
        elif opcode == OpcodeType.STORE.value:  # Store
            signals['mem_write'] = True
            signals['alu_src'] = True
        elif opcode == OpcodeType.BRANCH.value:  # Branch
            signals['branch'] = True
        elif opcode == OpcodeType.JAL.value:  # JAL
            signals['reg_write'] = True
            signals['jump'] = True
        elif opcode == OpcodeType.JALR.value:  # JALR
            signals['reg_write'] = True
            signals['jump'] = True
            signals['jalr'] = True
            signals['alu_src'] = True
        elif opcode == OpcodeType.LUI.value:  # LUI
            signals['reg_write'] = True
        elif opcode == OpcodeType.AUIPC.value:  # AUIPC
            signals['reg_write'] = True
        
        return signals

class InstructionDecoder:
    
    @staticmethod
    def decode(instr: int) -> Dict:
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F
        
        imm_i = InstructionDecoder._sign_extend((instr >> 20) & 0xFFF, 12)
        imm_s = InstructionDecoder._sign_extend(
            ((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12)
        imm_b = InstructionDecoder._sign_extend(
            ((instr >> 31) << 12) | (((instr >> 7) & 0x1) << 11) |
            (((instr >> 25) & 0x3F) << 5) | (((instr >> 8) & 0xF) << 1), 13)
        imm_u = (instr & 0xFFFFF000)
        imm_j = InstructionDecoder._sign_extend(
            ((instr >> 31) << 20) | (((instr >> 12) & 0xFF) << 12) |
            (((instr >> 20) & 0x1) << 11) | (((instr >> 21) & 0x3FF) << 1), 21)
        
        return {
            'opcode': opcode,
            'rd': rd,
            'funct3': funct3,
            'rs1': rs1,
            'rs2': rs2,
            'funct7': funct7,
            'imm_i': imm_i,
            'imm_s': imm_s,
            'imm_b': imm_b,
            'imm_u': imm_u,
            'imm_j': imm_j,
            'raw': instr
        }
    
    @staticmethod
    def _sign_extend(value: int, bits: int) -> int:
        sign_bit = 1 << (bits - 1)
        if value & sign_bit:
            value = value - (1 << bits)
        return value

class RISCVCPU:
    
    def __init__(self, memory_size: int = 0x20000):
        self.pc = 0
        self.regs = RegisterFile()
        self.memory = Memory(memory_size)
        self.control = ControlUnit()
        self.cycle_count = 0
        self.instruction_count = 0
        self.halt = False
        self.debug = False
    
    def load_program(self, hex_file: str):
        self.memory.load_program(hex_file)
        print(f"Program loaded from {hex_file}")
    
    def execute_cycle(self):
        if self.halt:
            return
        
        instr_word = self.memory.read_word(self.pc)
        
        if instr_word == 0x0000006F:
            print(f"\nHalt detected at PC=0x{self.pc:08x} (infinite loop)")
            self.halt = True
            return
        
        decoded = InstructionDecoder.decode(instr_word)
        opcode = decoded['opcode']
        
        ctrl = self.control.decode(opcode)
        
        next_pc = self.pc + 4
        write_data = 0
        
        rs1_data = self.regs.read(decoded['rs1'])
        rs2_data = self.regs.read(decoded['rs2'])
        
        if self.debug:
            print(f"\n[Cycle {self.cycle_count}] PC=0x{self.pc:08x} Instr=0x{instr_word:08x}")
            print(f"  Opcode=0x{opcode:02x} rd=x{decoded['rd']} rs1=x{decoded['rs1']} rs2=x{decoded['rs2']}")
        
        if opcode == OpcodeType.OP.value:  # R-type
            alu_op = self._get_alu_op(decoded['funct3'], decoded['funct7'])
            write_data = ALU.execute(alu_op, rs1_data, rs2_data)
            
        elif opcode == OpcodeType.OP_IMM.value:  # I-type arithmetic
            alu_op = self._get_alu_op(decoded['funct3'], decoded['funct7'] if decoded['funct3'] == 0x5 else 0)
            write_data = ALU.execute(alu_op, rs1_data, decoded['imm_i'])
            
        elif opcode == OpcodeType.LOAD.value:  # Load
            addr = ALU.execute(ALUOp.ADD, rs1_data, decoded['imm_i'])
            write_data = self.memory.read_word(addr)
            
        elif opcode == OpcodeType.STORE.value:  # Store
            addr = ALU.execute(ALUOp.ADD, rs1_data, decoded['imm_s'])
            self.memory.write_word(addr, rs2_data)
            
        elif opcode == OpcodeType.BRANCH.value:  # Branch
            taken = self._evaluate_branch(decoded['funct3'], rs1_data, rs2_data)
            if taken:
                next_pc = self.pc + decoded['imm_b']
            
        elif opcode == OpcodeType.JAL.value:  # JAL
            write_data = self.pc + 4
            next_pc = self.pc + decoded['imm_j']
            
        elif opcode == OpcodeType.JALR.value:  # JALR
            write_data = self.pc + 4
            next_pc = (rs1_data + decoded['imm_i']) & 0xFFFFFFFE
            
        elif opcode == OpcodeType.LUI.value:  # LUI
            write_data = decoded['imm_u']
            
        elif opcode == OpcodeType.AUIPC.value:  # AUIPC
            write_data = self.pc + decoded['imm_u']
        
  
        if ctrl['reg_write']:
            self.regs.write(decoded['rd'], write_data)
            if self.debug:
                print(f"  Write x{decoded['rd']} = 0x{write_data:08x}")
        
        self.pc = next_pc & 0xFFFFFFFF
        self.cycle_count += 1
        self.instruction_count += 1
    
    def _get_alu_op(self, funct3: int, funct7: int) -> ALUOp:
        if funct3 == 0x0:  
            return ALUOp.SUB if (funct7 & 0x20) else ALUOp.ADD
        elif funct3 == 0x1:  
            return ALUOp.SLL
        elif funct3 == 0x2:  
            return ALUOp.SLT
        elif funct3 == 0x3:  
            return ALUOp.SLTU
        elif funct3 == 0x4:  
            return ALUOp.XOR
        elif funct3 == 0x5:  
            return ALUOp.SRA if (funct7 & 0x20) else ALUOp.SRL
        elif funct3 == 0x6:  
            return ALUOp.OR
        elif funct3 == 0x7:  
            return ALUOp.AND
        return ALUOp.ADD
    
    def _evaluate_branch(self, funct3: int, a: int, b: int) -> bool:
        a_signed = ALU._to_signed(a)
        b_signed = ALU._to_signed(b)
        
        if funct3 == 0x0:  
            return a == b
        elif funct3 == 0x1:  
            return a != b
        elif funct3 == 0x4:  
            return a_signed < b_signed
        elif funct3 == 0x5:  
            return a_signed >= b_signed
        elif funct3 == 0x6:  
            return a < b
        elif funct3 == 0x7:  
            return a >= b
        return False
    
    def run(self, max_cycles: int = 10000):
        print("\n=== Starting CPU Execution ===\n")
        while not self.halt and self.cycle_count < max_cycles:
            self.execute_cycle()
        
        if self.cycle_count >= max_cycles:
            print(f"\nMax cycles ({max_cycles}) reached")
        
        print(f"\nExecution complete:")
        print(f"  Cycles: {self.cycle_count}")
        print(f"  Instructions: {self.instruction_count}")
        print(f"  Final PC: 0x{self.pc:08x}")
    
    def dump_state(self):
        print("\n" + "="*60)
        print("CPU STATE DUMP")
        print("="*60)
        print(f"PC: 0x{self.pc:08x}")
        print(f"Cycles: {self.cycle_count}")
        print(f"Instructions: {self.instruction_count}")
        print("\n" + self.regs.dump())
        print("="*60)
    
    def dump_memory(self, start: int, length: int):
        print(f"\nMemory Dump [0x{start:08x} - 0x{start+length-1:08x}]:")
        for addr in range(start, start + length, 4):
            word = self.memory.read_word(addr)
            print(f"  0x{addr:08x}: 0x{word:08x}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python riscv_cpu.py <program.hex> [--debug]")
        sys.exit(1)
    
    program_file = sys.argv[1]
    debug = '--debug' in sys.argv
    
    cpu = RISCVCPU()
    cpu.debug = debug
    
    cpu.load_program(program_file)
    
    cpu.run(max_cycles=10000)
    
    cpu.dump_state()

    cpu.dump_memory(0x00010000, 16)

if __name__ == '__main__':
    main()
