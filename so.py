#!/usr/bin/env python

from hardware import *
import log



## emulates a compiled program
class Program():

    def __init__(self, name, instructions):
        self._name = name
        self._instructions = self.expand(instructions)

    @property
    def name(self):
        return self._name

    @property
    def instructions(self):
        return self._instructions

    def addInstr(self, instruction):
        self._instructions.append(instruction)

    def expand(self, instructions):
        expanded = []
        for i in instructions:
            if isinstance(i, list):
                ## is a list of instructions
                expanded.extend(i)
            else:
                ## a single instr (a String)
                expanded.append(i)

        ## now test if last instruction is EXIT
        ## if not... add an EXIT as final instruction
        last = expanded[-1]
        if not ASM.isEXIT(last):
            expanded.append(INSTRUCTION_EXIT)

        return expanded

    def __repr__(self):
        return "Program({name}, {instructions})".format(name=self._name, instructions=self._instructions)


## emulates an Input/Output device controller (driver)
class IoDeviceController():

    def __init__(self, device):
        self._device = device
        self._waiting_queue = []
        self._currentPCB = None

    def runOperation(self, pcb, instruction):
        pair = {'pcb': pcb, 'instruction': instruction}
        # append: adds the element at the end of the queue
        self._waiting_queue.append(pair)
        # try to send the instruction to hardware's device (if is idle)
        self.__load_from_waiting_queue_if_apply()

    def getFinishedPCB(self):
        finishedPCB = self._currentPCB
        self._currentPCB = None
        self.__load_from_waiting_queue_if_apply()
        return finishedPCB

    def __load_from_waiting_queue_if_apply(self):
        if (len(self._waiting_queue) > 0) and self._device.is_idle:
            ## pop(): extracts (deletes and return) the first element in queue
            pair = self._waiting_queue.pop(0)
            #print(pair)
            pcb = pair['pcb']
            instruction = pair['instruction']
            self._currentPCB = pcb
            self._device.execute(instruction)


    def __repr__(self):
        return "IoDeviceController for {deviceID} running: {currentPCB} waiting: {waiting_queue}".format(deviceID=self._device.deviceId, currentPCB=self._currentPCB, waiting_queue=self._waiting_queue)

def add_pcb_to_ready_queue_if_valid():
    pass 
## emulates the  Interruptions Handlers
class AbstractInterruptionHandler():
    def __init__(self, kernel):
        self._kernel = kernel

    @property
    def kernel(self):
        return self._kernel

    def execute(self, irq):
        log.logger.error("-- EXECUTE MUST BE OVERRIDEN in class {classname}".format(classname=self.__class__.__name__))


class NewInterruptionHandler(AbstractInterruptionHandler):
    def execute(self, irq):
        parameters = irq.parameters 
        path = parameters['path']
        priority = parameters['priority']
        pcb_pid = self.kernel.pcb_table.getNewPID()
        pageTable = self.kernel.loader.load(path)
        pcb = PCB(pcb_pid, pageTable, path, priority)
        
        #Si hubiera mas scheduler expropiativos podriamos preguntar aca pero como solo hay uno prefiero que se encargue el scheduler
        self.kernel.scheduler.manage(pcb)
        self.kernel.pcb_table.add(pcb)

        
        log.logger.info("\n Executing program: {name}".format(name=path))
        log.logger.info(HARDWARE)


class KillInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        log.logger.info(" Program Finished ")
        
        pcb = self.kernel.runningPCB
        self.kernel.dispatcher.save(self.kernel.running_pcb) 
        self.kernel.running_pcb.state = "terminated"
        
        self.kernel.memoryManager.free(pcb.pageTable.values())
        
        if (self.kernel.scheduler.is_empty()):
            self.kernel.running_pcb = None #Ponemos que no hay programa corriendo
            HARDWARE.cpu.pc = -1## dejamos el CPU IDLE
        else:
            pcb = self.kernel.scheduler.get_next()
            #Si ya esta cargado
            if pcb.pageTable:
                self.kernel.dispatcher.load(pcb)
                self.kernel.running_pcb = pcb
                pcb.process_state = "running"
            #Antes no habia paginas libres asi que ahora que se libero lo cargamos de vuelta
            else:
                pcb.pageTable = self.kernel.loader.load(pcb.path)
                self.kernel.pcb_table.runningPCB = pcb
                self.kernel.dispatcher.load(pcb)
        

class IoInInterruptionHandler(AbstractInterruptionHandler):

    def execute(self, irq):
        operation = irq.parameters
        pcb = self.kernel.runningPCB 
        pcb.process_state = "waiting"
        self.kernel.dispatcher.save(pcb)
        self.kernel.ioDeviceController.runOperation(pcb, operation)
        #
        
        if (self.kernel.scheduler.is_empty()):
            self.kernel.running_pcb = None #Ponemos que no hay programa corriendo
            HARDWARE.cpu.pc = -1## dejamos el CPU IDLE
            
        else:
            next_pcb = self.kernel.scheduler.get_next()
            self.kernel.dispatcher.load(next_pcb)
            next_pcb.process_state = "running"
            self.kernel.running_pcb = next_pcb
            
        
        #
        log.logger.info(self.kernel.ioDeviceController)


class IoOutInterruptionHandler(AbstractInterruptionHandler):
    #pcb = irq.parameter
    #mandar pcb a running y si esta ocupada mandar a ready(con el dispatcher, load pcb)
    def execute(self, irq):
        pcb = self.kernel.ioDeviceController.getFinishedPCB()
        self.kernel.scheduler.manage(pcb)
        log.logger.info(self.kernel.ioDeviceController)

class TimeOutInterruptionHandler(AbstractInterruptionHandler):
    def execute(self,irq):
        self.kernel.scheduler.update_ready_queue()
        
class StatInterruptionHandler(AbstractInterruptionHandler):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.gantt_printed = False
        
    def execute(self, irq):
        self.kernel.diagram.stateAct()  # Actualizar el estado de los procesos
        if(HARDWARE.clock.currentTick == 30): #set en 28 asi hace el print antes de que finalize el ultimo programa, sino se apaga.
            self.kernel.diagram.print()
            
            
class PageFaultIntHandler(AbstractInterruptionHandler):
    def execute(self, irq):
        
        pageId = irq.parameters
        pcb = self.kernel.pcb_table.runningPCB
        
        allocFrame = self.kernel.memoryManager.alloc()
         
        log.logger.info(f"Alojado en frame : {allocFrame}")
        if allocFrame is None:
            victim = self.selectVictim()  # Selecciona una página para reemplazar
            log.logger.info(f"Seleccionando víctima: {victim}")
            self.kernel.memoryManager.free([victim])
            allocFrame = victim
            
        
        self.kernel.loader.loadPage(pcb.path, pageId, allocFrame)

        # Actualizar la tabla de páginas del PCB para reflejar el nuevo marco asignado
        pcb.pageTable[pageId] = allocFrame
        # Actualizar la TLB para indicar que ya a sido cargado
        HARDWARE.mmu.setPageFrame(pageId,allocFrame)
        
    def selectVictim(self):
        #Agarro el primero que es el que fue ultimo usado 
        victim = HARDWARE.mmu.access.pop(0)  # Pop de la cabeza para LRU
        log.logger.info(f"Página víctima seleccionada: {victim}")
        return victim
        
# emulates the core of an Operative System
class Kernel():

    def __init__(self):

        ## controls the Hardware's I/O Device
        self._ioDeviceController = IoDeviceController(HARDWARE.ioDevice) 
        self._pcb_table = PCB_Table()
        self._scheduler = None
        self._memoryManager = MemoryManager()
        self.dispatcher = Dispatcher()
        self._diagram = GanttDiagram(self)
        self._fileSystem = FileSystem()
        self._loader = Loader(self._fileSystem, self._memoryManager)
        
        ## setup interruption handlers
        newHandler = NewInterruptionHandler(self)
        HARDWARE.interruptVector.register(NEW_INTERRUPTION_TYPE, newHandler)
        
        killHandler = KillInterruptionHandler(self)
        HARDWARE.interruptVector.register(KILL_INTERRUPTION_TYPE, killHandler)

        ioInHandler = IoInInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_IN_INTERRUPTION_TYPE, ioInHandler)

        ioOutHandler = IoOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(IO_OUT_INTERRUPTION_TYPE, ioOutHandler)
        
        timeoutHandler = TimeOutInterruptionHandler(self)
        HARDWARE.interruptVector.register(TIMEOUT_INTERRUPTION_TYPE, timeoutHandler)
        
        statHandler = StatInterruptionHandler(self)
        HARDWARE.interruptVector.register(STAT_INTERRUPTION_TYPE, statHandler)
        
        pageHandler = PageFaultIntHandler(self)
        HARDWARE.interruptVector.register(PAGE_FAULT_INTERRUPTION_TYPE, pageHandler)

    @property
    def scheduler(self):
        # Getter para la propiedad scheduler
        return self._scheduler
    
    @property
    def loader(self):
        # Getter para la propiedad scheduler
        return self._loader

    @scheduler.setter
    def scheduler(self, scheduler_class):
        self._scheduler = scheduler_class
    
    @property
    def diagram(self): 
        return self._diagram

    @property
    def ioDeviceController(self):
        return self._ioDeviceController

    @property
    def runningPCB(self):
        return self._pcb_table.runningPCB

    @property
    def pcb_table(self):
        return self._pcb_table


    @property
    def getPCBTable(self): 
        return self.pcb_table.table 
    
    @property
    def fileSystem(self):
        return self._fileSystem
    
    @property
    def memoryManager(self):
        return self._memoryManager


    @runningPCB.setter
    def running_pcb(self, running_pcb):
        self.pcb_table.runningPCB = running_pcb

    ## emulates a "system call" for programs execution
    def run(self, programPath, priority):
        
        parameters = {'path': programPath, 'priority': priority}
        newIRQ = IRQ(NEW_INTERRUPTION_TYPE, parameters) 
        HARDWARE.interruptVector.handle(newIRQ)
        
        #Log
        log.logger.info("\n Executing program: {name}".format(name=programPath))
        log.logger.info(HARDWARE)
        
    def __repr__(self):
        return "Kernel "

class Loader():
    #carga el programa en la memoria y y devuelve la pageTable

    def __init__(self,fileSystem,memoryManager):
        self._fileSystem = fileSystem
        self._memoryManager = memoryManager   
        self.frameSize = HARDWARE.mmu.frameSize 
               
    def load(self, path):

        prg = self._fileSystem.read(path)
        prgSize = len(prg.instructions)
        requiredFrames = prgSize // self.frameSize
    
        #Si queda un resto del programa le agrego uno mas a los frames requeridos
        if prgSize % self.frameSize:
            requiredFrames = requiredFrames + 1
            
        #Inician vacios   
        allocFrames = {i: None for i in range(requiredFrames)}
        return allocFrames    
    
    def loadPage(self,pcb,pageToLoad,freeFrame):
        prg = self._fileSystem.read(pcb)

        start = pageToLoad * self.frameSize
        end = start + self.frameSize
        
        for i in range(start, min(end, len(prg.instructions))):
            inst = prg.instructions[i]
            memoryAddress = (freeFrame * self.frameSize) + (i % self.frameSize)  # Calcular la dirección física
            HARDWARE.memory.write(memoryAddress, inst)
         
        log.logger.info(HARDWARE)
           
        


class Dispatcher():
    #busca la baseDir del proceso en la pcbtable y la carga en la mmu
    #pone un proceso en running(setea pc y le dice a la mmu la baseDir)
    #saca un proceso de running(toma el pc de la cpu y setea el pc en -1)
    #algo asi:
    
    def load(self, pcb):
        HARDWARE.cpu.pc = pcb.pc 
        HARDWARE.mmu.resetTLB()

        for pageIndex, frameIndex in pcb.pageTable.items():
            HARDWARE.mmu.setPageFrame(pageIndex, frameIndex)

    def save(self, pcb): 
        pcb.pc = HARDWARE.cpu.pc
        HARDWARE.cpu.pc = -1 #queda idle hasta el proximo load 
    

class PCB():
    def __init__(self, process_id, pageTable, prg_name, priority,):
        self.process_id = process_id  # Identificador único del proceso
        self.pageTable = pageTable  # La page table
        self.pc = 0  # Contador de programa (PC)
        self.process_state = "new"  # Estado del proceso (new, ready, running, waiting, terminated)
        self.path = prg_name # Path del programa asociado al proceso
        self.priority = priority

    @property   
    def program_counter(self):
        return self.pc
    
    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value  # Establece el valor de la propiedad
    
    @property
    def pageTable(self):
        return self._pageTable
    
    @pageTable.setter
    def pageTable(self, newPageTable):
        self._pageTable = newPageTable

    @property 
    def state(self):
        return self.process_state 
    
    @state.setter 
    def state(self,newState):
        self.process_state = newState

    def __repr__(self):
        return (f"PCB(process_id={self.process_id}, pages={self.pageTable}, "
                f"program_counter={self.program_counter}, process_state={self.process_state}, path={self.path})")



class PCB_Table():
    def __init__(self):
        self._pcb_table = []
        self._nextPID= 0
        self._running_pcb = None
    
    @property 
    def table(self):
        return self._pcb_table
    
    def get(self, pid):
        return next((pcb for pcb in self._pcb_table if pcb.process_id == pid), None) 
            
    def add(self, pcb):
        self._pcb_table.append(pcb)  
    
    def getNewPID(self):
        pid = self._nextPID
        self._nextPID += 1
        return pid 

    @property   
    def runningPCB(self):
        return self._running_pcb 

    @runningPCB.setter
    def runningPCB(self, running_pcb):
        self._running_pcb = running_pcb

    def remove(self, pid): 
        self._pcb_table.remove(pid)

    
#Schedulers

class Scheduler():
    def __init__(self, kernel):
        self._ready_queue = []
        self.kernel = kernel
        
    def manage(self,pcb):         
        if (self.kernel.runningPCB): 
            pcb.process_state = "ready"
            self.kernel.scheduler.add(pcb)
        else:
            pcb.process_state = "running"
            self.kernel.dispatcher.load(pcb)
            self.kernel.running_pcb = pcb
        
    def add(self, pcb):
        self._ready_queue.append(pcb)
    
    def is_empty(self):
        return len(self._ready_queue) == 0
        
    def size(self): 
        return len(self._ready_queue) 
    
    def __repr__(self):
        return (f"Scheduler(size:{self.size}, queue={[pcb.process_id for pcb in self._ready_queue]}) ")

    def get_next(self):
        # Devuelve el primer proceso en la cola
        if not self.is_empty():
            process = self._ready_queue.pop(0)
            return process
        return None


class SchedulerFCFS(Scheduler):
    def size(self): 
        return len(self._ready_queue) 
    
    
class SchedulerPriorityNonPreemptive(Scheduler):
    
    def __init__(self,kernel):
        super().__init__(kernel)
        self._ready_queue = {0: [], 1: [], 2: [], 3: [], 4: []}
        
        
    def add(self, pcb):
        if (0 <= pcb.priority <= 4):
            self._ready_queue.get(pcb.priority).append(pcb)
        else:
            None

    def first(self):
        #Devuelve el primer proceso en la cola sin removerlo
        for priority in range (0, 5):
            if self._ready_queue[priority]:
                return self._ready_queue[priority][0]
        return None
    

    def get_next(self):
        #Devuelve el primer proceso en la cola de prioridad mas alta y lo elimina de esta
        for priority in range(0,5):
            if self._ready_queue[priority]:
                next_pcb = self._ready_queue[priority].pop(0)
                self.apply_aging() #aplicamos aging luego de cada extraccion de pcb
                return next_pcb
        return None 
    
    def apply_aging(self):
        #incrementa la prioridad de cada proceso (Se baja su posicion en la lista)
        for priority in range(1, 5):
            while self._ready_queue[priority]:
                self._ready_queue[priority - 1].append(self._ready_queue[priority].pop(0))
                
    def is_empty(self):
        return all(not self._ready_queue[priority] for priority in range(5))

class SchedulerPriorityPreemptive(Scheduler):
    def __init__(self,kernel):
        super().__init__(kernel)
        self._ready_queue = {0: [], 1: [], 2: [], 3: [], 4: []}
        
        
    def manage(self,pcb):
        if(self.kernel.runningPCB):            
            if self.mustExpropiate(self.kernel.runningPCB, pcb):
                self.preempt_current_process(pcb)
            else:
                pcb.process_state = "ready"
                self.add(pcb)  
        else:
            pcb.process_state = "running"
            self.kernel.dispatcher.load(pcb)
            self.kernel.running_pcb = pcb 

    
        
    def add(self, pcb):
        if (0 <= pcb.priority <= 4):
            self._ready_queue.get(pcb.priority).append(pcb)
        else:
            None
            
 
    def mustExpropiate(self, runningPcb, pcbToAdd):
        return pcbToAdd.priority < runningPcb.priority 
    
    def preempt_current_process(self, pcbToAdd):
        running_pcb = self.kernel.runningPCB
        running_pcb.process_state = 'ready'
        self.kernel.dispatcher.save(running_pcb)
        self.add(running_pcb)
        
        pcbToAdd.process_state = "running"
        self.kernel.dispatcher.load(pcbToAdd)
        self.kernel.running_pcb = pcbToAdd
    
    def first(self):
        #Devuelve el primer proceso en la cola sin removerlo
        for priority in range (0, 5):
            if self._ready_queue[priority]:
                return self._ready_queue[priority][0]
        return None
    
    def get_next(self):
        #Devuelve el primer proceso en la cola de prioridad mas alta y lo elimina de esta
        for priority in range(0,5):
            if self._ready_queue[priority]:
                next_pcb = self._ready_queue[priority].pop(0)
                self.apply_aging() #aplicamos aging luego de cada extraccion de pcb
                return next_pcb
        return None 
    
    def apply_aging(self):
        #incrementa la prioridad de cada proceso (Se baja su posicion en la lista)
        for priority in range(1, 5):
            while self._ready_queue[priority]:
                self._ready_queue[priority - 1].append(self._ready_queue[priority].pop(0))
                
    def is_empty(self):
        for priority in range(5):
            if (self._ready_queue[priority]):
                return False
        return True  

    
class SchedulerRoundRobin(Scheduler):
    def __init__(self, quantum, kernel):
        super().__init__(kernel)
        HARDWARE.timer.quantum = quantum
        HARDWARE.timer.reset() 
    
    def update_ready_queue(self):
        # Proceso actual
        current_process = self.kernel.running_pcb
        HARDWARE.timer.reset() 
        # Solo si hay un proceso en ejecución y no es None
        if current_process:
            self.kernel.dispatcher.save(current_process)
            current_process.process_state = 'ready'
            self._ready_queue.append(current_process)  # Añadimos el proceso al final de la cola

        # Tomar el siguiente proceso en la ready queue respetando FIFO
        next_process = self.get_next()
        if next_process:
            next_process.process_state = 'running'
            self.kernel.dispatcher.load(next_process)
            self.kernel.running_pcb = next_process
            
            
#MEMORIA MANAGMENT

class MemoryManager():
    def __init__(self):
        self._freeFrames = []
        totalFrames = HARDWARE.memory.size // HARDWARE.mmu.frameSize
        
        if not self._freeFrames:
            self._freeFrames = list(range(totalFrames))
    
    def alloc(self):
        log.logger.info(self._freeFrames)
        if self._freeFrames:
            return self._freeFrames.pop(0)  # Devuelve el primer marco libre
        else:
            return None  # No hay marcos disponibles
    
    def free(self, frame):
        self._freeFrames.extend(frame)
    
    @property
    def freeFrames(self):
        return self._freeFrames

 
#File System
class FileSystem():
    
    def __init__(self):
        self._fileSystem = dict()
    
    def write(self, path, prg):
        self._fileSystem[path] = prg
    
    def read(self, path):
        return self._fileSystem[path]
    
           

#Gantt
class GanttDiagram():
    def __init__(self, kernel):
        self.kernel = kernel
        self.diagrama = []
        
    def stateAct(self):
        row = []
        # Por cada proceso en la tabla PCB, guardo su estado en este tick
        for pcb in self.kernel.getPCBTable:
            if pcb.state == 'terminated':
                row.append("END")
            elif pcb.state == 'running':
                row.append("RUN")
            elif pcb.state == 'waiting':
                row.append("WAIT")
            elif pcb.state == 'ready':
                row.append("READY")
            else:
                row.append("NOOOOOOOOOOOOO")#No deberia haber otro estado
        self.diagrama.append(row)
        
    def print(self):
        headers = ['Tick'] + [str(i) for i in range(len(self.diagrama))] 
        data = []
        for pcb_index, row in enumerate(self.diagrama): 
            data.append([f"Tick {pcb_index}"] + row)
        print(tabulate(data, headers=headers, tablefmt="fancy_grid"))
