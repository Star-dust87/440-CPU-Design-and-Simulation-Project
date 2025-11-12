import sys
from typing import Dict, Optional
from riscv_cpu import (
    ALU, ALUOp, RegisterFile, Memory, ControlUnit, 
    InstructionDecoder, OpcodeType
)

class PipelineRegister:
    def __init__(self):
        self.valid = False  
        self.stall = False  
        
    def flush(self):
        self.valid = False
    
    def __repr__(self):
        return f"{self.__class__.__name__}(valid={self.valid})"

class IF_ID_Register(PipelineRegister):
    def __init__(self):
        super().__init__()
        self.pc = 0
        self.instruction = 0

class ID_EX_Register(PipelineRegister):
    def __init__(self):
        super().__init__()
        self.pc = 0
        self.rs1_data = 0
        self.rs2_data = 0
        self.rs1 = 0
        self.rs2 = 0
        self.rd = 0
        self.imm = 0
        self.funct3 = 0
        self.funct7 = 0
        self.opcode = 0
        
        self.reg_write = False
        self.mem_read = False
        self.mem_write = False
        self.mem_to_reg = False
        self.alu_src = False
        self.branch = False
        self.jump = False
        self.jalr = False

class EX_MEM_Register(PipelineRegister):
    def __init__(self):
        super().__init__()
        self.pc = 0
        self.alu_result = 0
        self.rs2_data = 0
        self.rd = 0
        self.branch_target = 0
        self.branch_taken = False
        
        self.reg_write = False
        self.mem_read = False
        self.mem_write = False
        self.mem_to_reg = False
        self.jump = False

class MEM_WB_Register(PipelineRegister):
    def __init__(self):
        super().__init__()
        self.alu_result = 0
        self.mem_data = 0
        self.rd = 0
        self.reg_write = False
        self.mem_to_reg = False

class HazardDetectionUnit:
    
    @staticmethod
    def detect_load_use_hazard(id_ex: ID_EX_Register, if_id: IF_ID_Register, 
                               decoded: Dict) -> bool:
        
        if not id_ex.valid:
            return False
            
        if id_ex.mem_read and id_ex.rd != 0:
            if (id_ex.rd == decoded['rs1'] or id_ex.rd == decoded['rs2']):
                return True
        return False
    
    @staticmethod
    def detect_control_hazard(ex_mem: EX_MEM_Register) -> bool:
        
        return ex_mem.valid and (ex_mem.branch_taken or ex_mem.jump)

class ForwardingUnit:
   
    @staticmethod
    def get_forward_a(id_ex: ID_EX_Register, ex_mem: EX_MEM_Register, 
                      mem_wb: MEM_WB_Register) -> str:
        
        if (ex_mem.valid and ex_mem.reg_write and ex_mem.rd != 0 and 
            ex_mem.rd == id_ex.rs1):
            return 'EX_MEM'
        
        if (mem_wb.valid and mem_wb.reg_write and mem_wb.rd != 0 and 
            mem_wb.rd == id_ex.rs1):
            return 'MEM_WB'
        
        return 'NO_FORWARD'
    
    @staticmethod
    def get_forward_b(id_ex: ID_EX_Register, ex_mem: EX_MEM_Register, 
                      mem_wb: MEM_WB_Register) -> str:
       
        if (ex_mem.valid and ex_mem.reg_write and ex_mem.rd != 0 and 
            ex_mem.rd == id_ex.rs2):
            return 'EX_MEM'
        
        if (mem_wb.valid and mem_wb.reg_write and mem_wb.rd != 0 and 
            mem_wb.rd == id_ex.rs2):
            return 'MEM_WB'
        
        return 'NO_FORWARD'

class PipelinedRISCVCPU:
 
    def __init__(self, memory_size: int = 0x20000):
        self.pc = 0
        self.regs = RegisterFile()
        self.memory = Memory(memory_size)
        self.control = ControlUnit()
        
        self.if_id = IF_ID_Register()
        self.id_ex = ID_EX_Register()
        self.ex_mem = EX_MEM_Register()
        self.mem_wb = MEM_WB_Register()
        
        self.hazard_unit = HazardDetectionUnit()
        self.forwarding_unit = ForwardingUnit()
        
        self.cycle_count = 0
        self.instruction_count = 0
        self.stall_count = 0
        self.data_hazard_count = 0
        self.control_hazard_count = 0
        self.halt = False
        self.debug = False
        
    def load_program(self, hex_file: str):
        self.memory.load_program(hex_file)
        print(f"Program loaded from {hex_file}")
    
    def execute_cycle(self):
        if self.halt:
            return
        
        self.writeback_stage()
        self.memory_stage()
        self.execute_stage()
        self.decode_stage()
        self.fetch_stage()
        
        self.cycle_count += 1
        
        if self.debug:
            self.print_pipeline_state()
    
    def fetch_stage(self):
        if self.hazard_unit.detect_control_hazard(self.ex_mem):
            self.if_id.flush()
            self.control_hazard_count += 1
            if self.debug:
                print(f"  [IF] Control hazard - flushing")
            return
        
        if self.if_id.stall:
            if self.debug:
                print(f"  [IF] Stalled")
            return
        
        instr = self.memory.read_word(self.pc)
        
        if instr == 0x0000006F:
            if (not self.id_ex.valid and not self.ex_mem.valid and 
                not self.mem_wb.valid and self.if_id.instruction == 0x0000006F):
                if self.debug:
                    print(f"  [IF] Halt detected - pipeline drained")
                self.halt = True
                return
        
        self.if_id.valid = True
        self.if_id.pc = self.pc
        self.if_id.instruction = instr
        
        self.pc += 4
        
        if self.debug:
            print(f"  [IF] PC=0x{self.if_id.pc:08x} Instr=0x{instr:08x}")
    
    def decode_stage(self):
        if not self.if_id.valid:
            self.id_ex.flush()
            return
        
        decoded = InstructionDecoder.decode(self.if_id.instruction)
        opcode = decoded['opcode']
        
        ctrl = self.control.decode(opcode)
        
        if self.hazard_unit.detect_load_use_hazard(self.id_ex, self.if_id, decoded):
            self.id_ex.flush()
            self.if_id.stall = True
            self.pc -= 4  
            self.stall_count += 1
            self.data_hazard_count += 1
            if self.debug:
                print(f"  [ID] Load-use hazard detected - stalling")
            return
        
        self.if_id.stall = False
        
        rs1_data = self.regs.read(decoded['rs1'])
        rs2_data = self.regs.read(decoded['rs2'])
        
        self.id_ex.valid = True
        self.id_ex.pc = self.if_id.pc
        self.id_ex.rs1_data = rs1_data
        self.id_ex.rs2_data = rs2_data
        self.id_ex.rs1 = decoded['rs1']
        self.id_ex.rs2 = decoded['rs2']
        self.id_ex.rd = decoded['rd']
        self.id_ex.funct3 = decoded['funct3']
        self.id_ex.funct7 = decoded['funct7']
        self.id_ex.opcode = opcode
        
        if opcode == OpcodeType.OP_IMM.value or opcode == OpcodeType.LOAD.value or opcode == OpcodeType.JALR.value:
            self.id_ex.imm = decoded['imm_i']
        elif opcode == OpcodeType.STORE.value:
            self.id_ex.imm = decoded['imm_s']
        elif opcode == OpcodeType.BRANCH.value:
            self.id_ex.imm = decoded['imm_b']
        elif opcode == OpcodeType.LUI.value or opcode == OpcodeType.AUIPC.value:
            self.id_ex.imm = decoded['imm_u']
        elif opcode == OpcodeType.JAL.value:
            self.id_ex.imm = decoded['imm_j']
        else:
            self.id_ex.imm = 0
        
        self.id_ex.reg_write = ctrl['reg_write']
        self.id_ex.mem_read = ctrl['mem_read']
        self.id_ex.mem_write = ctrl['mem_write']
        self.id_ex.mem_to_reg = ctrl['mem_to_reg']
        self.id_ex.alu_src = ctrl['alu_src']
        self.id_ex.branch = ctrl['branch']
        self.id_ex.jump = ctrl['jump']
        self.id_ex.jalr = ctrl['jalr']
        
        if self.debug:
            print(f"  [ID] Opcode=0x{opcode:02x} rs1=x{decoded['rs1']} rs2=x{decoded['rs2']} rd=x{decoded['rd']}")
    
    def execute_stage(self):
        if not self.id_ex.valid:
            self.ex_mem.flush()
            return
        
        forward_a = self.forwarding_unit.get_forward_a(self.id_ex, self.ex_mem, self.mem_wb)
        forward_b = self.forwarding_unit.get_forward_b(self.id_ex, self.ex_mem, self.mem_wb)
        
        if forward_a == 'EX_MEM':
            alu_input_a = self.ex_mem.alu_result
            if self.debug:
                print(f"  [EX] Forward A from EX/MEM: 0x{alu_input_a:08x}")
        elif forward_a == 'MEM_WB':
            alu_input_a = self.get_wb_data()
            if self.debug:
                print(f"  [EX] Forward A from MEM/WB: 0x{alu_input_a:08x}")
        else:
            alu_input_a = self.id_ex.rs1_data
        
        if forward_b == 'EX_MEM':
            rs2_forward = self.ex_mem.alu_result
            if self.debug:
                print(f"  [EX] Forward B from EX/MEM: 0x{rs2_forward:08x}")
        elif forward_b == 'MEM_WB':
            rs2_forward = self.get_wb_data()
            if self.debug:
                print(f"  [EX] Forward B from MEM/WB: 0x{rs2_forward:08x}")
        else:
            rs2_forward = self.id_ex.rs2_data
        
        if self.id_ex.alu_src:
            alu_input_b = self.id_ex.imm
        else:
            alu_input_b = rs2_forward
        
        opcode = self.id_ex.opcode
        alu_result = 0
        branch_taken = False
        
        if opcode == OpcodeType.OP.value or opcode == OpcodeType.OP_IMM.value:
            alu_op = self._get_alu_op(self.id_ex.funct3, self.id_ex.funct7)
            alu_result = ALU.execute(alu_op, alu_input_a, alu_input_b)
            
        elif opcode == OpcodeType.LOAD.value or opcode == OpcodeType.STORE.value:
            alu_result = ALU.execute(ALUOp.ADD, alu_input_a, alu_input_b)
            
        elif opcode == OpcodeType.BRANCH.value:
            branch_taken = self._evaluate_branch(self.id_ex.funct3, alu_input_a, rs2_forward)
            alu_result = self.id_ex.pc + self.id_ex.imm
            
        elif opcode == OpcodeType.JAL.value:
            alu_result = self.id_ex.pc + 4  
            
        elif opcode == OpcodeType.JALR.value:
            alu_result = self.id_ex.pc + 4  
            
        elif opcode == OpcodeType.LUI.value:
            alu_result = self.id_ex.imm
            
        elif opcode == OpcodeType.AUIPC.value:
            alu_result = self.id_ex.pc + self.id_ex.imm
        
        branch_target = 0
        if self.id_ex.branch:
            branch_target = self.id_ex.pc + self.id_ex.imm
        elif self.id_ex.jump and not self.id_ex.jalr:
            branch_target = self.id_ex.pc + self.id_ex.imm
        elif self.id_ex.jalr:
            branch_target = (alu_input_a + self.id_ex.imm) & 0xFFFFFFFE
        
        self.ex_mem.valid = True
        self.ex_mem.pc = self.id_ex.pc
        self.ex_mem.alu_result = alu_result
        self.ex_mem.rs2_data = rs2_forward
        self.ex_mem.rd = self.id_ex.rd
        self.ex_mem.branch_target = branch_target
        self.ex_mem.branch_taken = branch_taken and self.id_ex.branch
        self.ex_mem.reg_write = self.id_ex.reg_write
        self.ex_mem.mem_read = self.id_ex.mem_read
        self.ex_mem.mem_write = self.id_ex.mem_write
        self.ex_mem.mem_to_reg = self.id_ex.mem_to_reg
        self.ex_mem.jump = self.id_ex.jump
        
        if self.debug:
            print(f"  [EX] ALU Result=0x{alu_result:08x} Branch={branch_taken}")
    
    def memory_stage(self):
        if not self.ex_mem.valid:
            self.mem_wb.flush()
            return
        
        mem_data = 0
        
        if self.ex_mem.mem_read:
            mem_data = self.memory.read_word(self.ex_mem.alu_result)
            if self.debug:
                print(f"  [MEM] Read from 0x{self.ex_mem.alu_result:08x} = 0x{mem_data:08x}")
        
        if self.ex_mem.mem_write:
            self.memory.write_word(self.ex_mem.alu_result, self.ex_mem.rs2_data)
            if self.debug:
                print(f"  [MEM] Write to 0x{self.ex_mem.alu_result:08x} = 0x{self.ex_mem.rs2_data:08x}")
        
        if self.ex_mem.branch_taken or self.ex_mem.jump:
            self.pc = self.ex_mem.branch_target
            self.if_id.flush()
            self.id_ex.flush()
            if self.debug:
                print(f"  [MEM] Branch/Jump to 0x{self.ex_mem.branch_target:08x}")
        
        self.mem_wb.valid = True
        self.mem_wb.alu_result = self.ex_mem.alu_result
        self.mem_wb.mem_data = mem_data
        self.mem_wb.rd = self.ex_mem.rd
        self.mem_wb.reg_write = self.ex_mem.reg_write
        self.mem_wb.mem_to_reg = self.ex_mem.mem_to_reg
    
    def writeback_stage(self):
        if not self.mem_wb.valid:
            return
        
        if self.mem_wb.reg_write:
            write_data = self.get_wb_data()
            self.regs.write(self.mem_wb.rd, write_data)
            
            self.instruction_count += 1
            
            if self.debug:
                print(f"  [WB] Write x{self.mem_wb.rd} = 0x{write_data:08x}")
    
    def get_wb_data(self) -> int:
        if self.mem_wb.mem_to_reg:
            return self.mem_wb.mem_data
        else:
            return self.mem_wb.alu_result
    
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
    
    def print_pipeline_state(self):
        print(f"\n[Cycle {self.cycle_count}]")
        print(f"  IF/ID:  valid={self.if_id.valid} PC=0x{self.if_id.pc:08x}")
        print(f"  ID/EX:  valid={self.id_ex.valid} rd=x{self.id_ex.rd}")
        print(f"  EX/MEM: valid={self.ex_mem.valid} rd=x{self.ex_mem.rd}")
        print(f"  MEM/WB: valid={self.mem_wb.valid} rd=x{self.mem_wb.rd}")
    
    def run(self, max_cycles: int = 10000, max_instructions: int = 1000):
        print("\n=== Starting Pipelined CPU Execution ===\n")
        while not self.halt and self.cycle_count < max_cycles and self.instruction_count < max_instructions:
            self.execute_cycle()
        
        if self.cycle_count >= max_cycles:
            print(f"\nMax cycles ({max_cycles}) reached")
        elif self.instruction_count >= max_instructions:
            print(f"\nMax instructions ({max_instructions}) reached")
        
        print(f"\nExecution complete:")
        print(f"  Cycles: {self.cycle_count}")
        print(f"  Instructions: {self.instruction_count}")
        print(f"  CPI: {self.cycle_count / max(self.instruction_count, 1):.2f}")
        print(f"  Stalls: {self.stall_count}")
        print(f"  Data hazards: {self.data_hazard_count}")
        print(f"  Control hazards: {self.control_hazard_count}")
        print(f"  Final PC: 0x{self.pc:08x}")
    
    def dump_state(self):
        print("\n" + "="*60)
        print("PIPELINED CPU STATE DUMP")
        print("="*60)
        print(f"PC: 0x{self.pc:08x}")
        print(f"Cycles: {self.cycle_count}")
        print(f"Instructions: {self.instruction_count}")
        print(f"CPI: {self.cycle_count / max(self.instruction_count, 1):.2f}")
        print(f"Stalls: {self.stall_count}")
        print(f"Data Hazards: {self.data_hazard_count}")
        print(f"Control Hazards: {self.control_hazard_count}")
        print("\n" + self.regs.dump())
        print("="*60)
    
    def dump_memory(self, start: int, length: int):
        print(f"\nMemory Dump [0x{start:08x} - 0x{start+length-1:08x}]:")
        for addr in range(start, start + length, 4):
            word = self.memory.read_word(addr)
            print(f"  0x{addr:08x}: 0x{word:08x}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python riscv_cpu_pipelined.py <program.hex> [--debug]")
        sys.exit(1)
    
    program_file = sys.argv[1]
    debug = '--debug' in sys.argv
    
    cpu = PipelinedRISCVCPU()
    cpu.debug = debug
    
    cpu.load_program(program_file)
    
    cpu.run(max_cycles=1000, max_instructions=20)
    
    cpu.dump_state()
    
    cpu.dump_memory(0x00010000, 16)

if __name__ == '__main__':
    main()
