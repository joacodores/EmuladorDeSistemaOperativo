from hardware import *
from so import *
import log


##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(10)
    
    #Y El tamaño de los frames
    HARDWARE.mmu.frameSize = 4

    

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo con el tipo de Scheduler que seleccionemos 
    kernel = Kernel()
    kernel.scheduler = SchedulerFCFS(kernel)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.CPU(7)])
    prg3 = Program("prg3.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])
    
    #Guardamos los progrmas en el disco
    kernel.fileSystem.write("prg1.exe", prg1)
    kernel.fileSystem.write("prg2.exe", prg2)
    kernel.fileSystem.write("prg3.exe", prg3)

    # execute all programs "concurrently"
    kernel.run("prg1.exe",1)
    kernel.run("prg2.exe",2)
    kernel.run("prg3.exe",3)
     ## Switch on computer
    HARDWARE.switchOn()





