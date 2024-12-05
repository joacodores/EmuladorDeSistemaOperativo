El proyecto fue desarrollado bajo un marco academico, como proyecto final de la materia "sistemas operativos" de la universidad de Quilmes, en la carrera tecnicatura en programación informatica. 

Este proyecto es un **Emulador de sistema operativo** desarrollado en **Python** que simula el comportamiento de un sistema operativo básico en consola. 
Su objetivo principal es ilustrar cómo funcionan los componentes esenciales de un sistema operativo y cómo interactúan entre sí.  

Durante la ejecución, el sistema muestra en la consola el estado de la memoria, la ejecución de instrucciones de los programas cargados y, cada cierto tiempo, genera un diagrama de Gantt para visualizar el
estado de los procesos.  

## Características principales

- **Kernel**: Actúa como el núcleo del sistema operativo, integrando y coordinando los diferentes componentes y clases.
- **Gestión de Procesos**:
  - **PCB (Process Control Block)** y **PCB Table** para manejar información sobre los procesos.
  - **Dispatcher** para gestionar el cambio de contexto entre procesos.
  - **Ready Queue** organizada según el algoritmo de planificación seleccionado.
- **Planificadores (Schedulers)**:
  - Algoritmos disponibles:
    - First-Come, First-Served (FCFS).
    - Prioridad (con y sin expropiación).
    - Round Robin (RR).
  - Soporte para **Aging** en algoritmos por prioridad.
  - Capacidad de intercambiar el algoritmo de scheduling "en frío".
- **Gestión de Memoria**:
  - **Memory Manager** para administrar el espacio en memoria.
  - Soporte para fallos de página (Page Fault).
- **Sistema de Archivos**:
  - **FileSystem** simulado para gestionar datos de entrada/salida.
- **Gestión de Dispositivos de I/O**:
  - **IODeviceController** y dispositivos abstractos como una impresora.
- **Manejo de interrupciones**:
  - Interrupciones como `NEW`, `KILL`, `IO_IN`, `IO_OUT`, estadísticas (para el diagrama de Gantt) y fallos de página.
- **Simulación de Hardware**:
  - Emulación de componentes como:
    - **CPU**.
    - **MMU (Memory Management Unit)**.
    - **Memoria**.
    - **Clock** y **Timer**.
    - **Interrupt Vector** para manejar interrupciones.
- **Loader**: Carga programas en memoria de forma simulada.
- **Logger**: Registra eventos del sistema y estados de los procesos.
- **Tabulate**: Formatea las salidas en la consola para mayor claridad.

## ¿Cómo funciona?

El proyecto se ejecuta desde consola y simula la carga y ejecución de programas en memoria.  
El sistema opera en ciclos de reloj (`clock ticks`) y gestiona eventos como:  
- Ejecución de instrucciones en la CPU.  
- Operaciones de entrada/salida.  
- Cambio de contexto entre procesos.  

A medida que avanza la ejecución, se imprime en la consola el estado de la memoria, las colas de procesos, y, eventualmente, un **diagrama de Gantt** que muestra la utilización de CPU por los procesos en un intervalo de tiempo.

## Estructura del proyecto

- **`s.o.`**: Contiene las clases principales del sistema operativo:
  - `Program`, `IODeviceController`, handlers para interrupciones, PCB Table, Scheduler, Dispatcher, Memory Manager, FileSystem, Loader y el Kernel.
- **`hardware`**: Simula componentes de hardware como CPU, memoria, MMU, dispositivos de I/O, reloj, vector de interrupciones y timer.
- **`main`**: Archivo principal que ejecuta la simulación.
- **`logger`**: Gestiona los registros de eventos del sistema.
- **`tabulate`**: Mejora la presentación de los datos impresos en consola.

